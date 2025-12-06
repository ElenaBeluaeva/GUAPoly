from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from typing import Dict, Any

from .game_manager import GameManager
from .game import GameState

router = Router()


# Состояния для FSM
class GameStates(StatesGroup):
    waiting_for_buy_decision = State()
    waiting_for_trade = State()
    waiting_for_auction_bid = State()
    waiting_for_jail_decision = State()
    waiting_for_build_decision = State()


def setup_handlers(dp, game_manager: GameManager):
    """Настроить все обработчики"""

    @dp.message(CommandStart())
    async def cmd_start(message: Message):
        """Обработчик команды /start"""
        await message.answer(
            "🎲 Добро пожаловать в Монополию!\n\n"
            "Доступные команды:\n"
            "/newgame - Создать новую игру\n"
            "/join <код> - Присоединиться к игре\n"
            "/games - Список доступных игр\n"
            "/help - Правила игры"
        )

    @dp.message(Command("help"))
    async def cmd_help(message: Message):
        """Обработчик команды /help"""
        help_text = (
            "🎯 <b>Правила Монополии:</b>\n\n"
            "1. Цель игры - остаться единственным необанкротившимся игроком\n"
            "2. Игроки по очереди бросают кубики и перемещаются по полю\n"
            "3. При попадании на чужую собственность платите ренту\n"
            "4. Собирайте полные цветовые группы для строительства домов\n"
            "5. При прохождении 'Старта' получайте 200$\n"
            "6. В тюрьму можно попасть по карточке или выбросив 3 дубля подряд\n\n"
            "<b>Основные команды:</b>\n"
            "/roll - Бросить кубики\n"
            "/buy - Купить собственность\n"
            "/build - Строить дома\n"
            "/trade - Предложить обмен\n"
            "/mortgage - Заложить собственность\n"
            "/status - Статус игры"
        )
        await message.answer(help_text, parse_mode="HTML")

    @dp.message(Command("newgame"))
    async def cmd_newgame(message: Message):
        """Создать новую игру"""
        game_manager = GameManager()
        game_id = game_manager.create_game(message.from_user.id)

        if game_id:
            # Автоматически добавить создателя в игру
            game_manager.join_game(
                game_id,
                message.from_user.id,
                message.from_user.username or "Игрок",
                message.from_user.full_name
            )

            await message.answer(
                f"🎮 Игра создана!\n"
                f"Код игры: <code>{game_id}</code>\n\n"
                f"Другие игроки могут присоединиться командой:\n"
                f"<code>/join {game_id}</code>\n\n"
                f"Когда все присоединятся, нажмите /startgame",
                parse_mode="HTML"
            )
        else:
            await message.answer("❌ Вы уже участвуете в другой игре!")

    @dp.message(Command("games"))
    async def cmd_games(message: Message):
        """Показать доступные игры"""
        game_manager = GameManager()
        games = game_manager.get_available_games()

        if not games:
            await message.answer("📭 Нет доступных игр. Создайте новую /newgame")
            return

        response = "🎲 <b>Доступные игры:</b>\n\n"
        for game in games:
            players = list(game.players.values())
            creator = next((p for p in players if p.user_id == game.creator_id), None)
            creator_name = creator.username if creator else "Неизвестно"

            response += (
                f"🎮 Код: <code>{game.game_id}</code>\n"
                f"👑 Создатель: {creator_name}\n"
                f"👥 Игроков: {len(players)}/8\n"
                f"👉 Присоединиться: /join {game.game_id}\n"
                f"{'-' * 20}\n"
            )

        await message.answer(response, parse_mode="HTML")

    @dp.message(Command("join"))
    async def cmd_join(message: Message):
        """Присоединиться к игре"""
        if not message.text or len(message.text.split()) < 2:
            await message.answer("❌ Укажите код игры: /join ABC123")
            return

        game_id = message.text.split()[1].upper()
        game_manager = GameManager()

        success = game_manager.join_game(
            game_id,
            message.from_user.id,
            message.from_user.username or "Игрок",
            message.from_user.full_name
        )

        if success:
            game = game_manager.get_game(game_id)
            players_list = "\n".join([
                f"• {player.full_name} (@{player.username})"
                for player in game.players.values()
            ])

            await message.answer(
                f"✅ Вы присоединились к игре {game_id}!\n\n"
                f"👥 <b>Участники:</b>\n{players_list}\n\n"
                f"Ожидайте начала игры от создателя.",
                parse_mode="HTML"
            )

            # Уведомить других игроков
            for player in game.players.values():
                if player.user_id != message.from_user.id:
                    try:
                        await message.bot.send_message(
                            player.user_id,
                            f"🎉 К игре присоединился {message.from_user.full_name}!"
                        )
                    except:
                        pass
        else:
            await message.answer(
                "❌ Не удалось присоединиться к игре.\n"
                "Возможные причины:\n"
                "• Вы уже в другой игре\n"
                "• Игра не найдена\n"
                "• Игра уже началась\n"
                "• В игре максимальное количество игроков"
            )

    @dp.message(Command("startgame"))
    async def cmd_startgame(message: Message):
        """Начать игру"""
        game_manager = GameManager()
        game = game_manager.get_player_game(message.from_user.id)

        if not game:
            await message.answer("❌ Вы не в игре!")
            return

        if game.creator_id != message.from_user.id:
            await message.answer("❌ Только создатель игры может ее начать!")
            return

        if game.state != GameState.LOBBY:
            await message.answer("❌ Игра уже началась!")
            return

        if len(game.players) < 2:
            await message.answer("❌ Нужно хотя бы 2 игрока для начала!")
            return

        if game_manager.start_game(game.game_id):
            # Уведомить всех игроков
            for player in game.players.values():
                try:
                    await message.bot.send_message(
                        player.user_id,
                        "🎮 Игра началась!\n\n"
                        f"Порядок ходов:\n" +
                        "\n".join([
                            f"{i + 1}. {game.players[pid].full_name}"
                            for i, pid in enumerate(game.player_order)
                        ]) +
                        f"\n\nПервый ходит: {game.get_current_player().full_name}\n"
                        f"Используйте /roll для броска кубиков"
                    )
                except:
                    pass
        else:
            await message.answer("❌ Не удалось начать игру")

    @dp.message(Command("roll"))
    async def cmd_roll(message: Message, state: FSMContext):
        """Бросить кубики"""
        game_manager = GameManager()
        game = game_manager.get_player_game(message.from_user.id)

        if not game:
            await message.answer("❌ Вы не в игре!")
            return

        if game.state != GameState.IN_PROGRESS:
            await message.answer("❌ Игра не активна!")
            return

        current_player = game.get_current_player()
        if current_player.user_id != message.from_user.id:
            await message.answer(f"❌ Сейчас ходит {current_player.full_name}!")
            return

        # Проверка тюрьмы
        if current_player.status.value == "in_jail":
            await message.answer("Вы в тюрьме! Используйте /jail для действий")
            return

        # Бросок кубиков
        dice1, dice2, total = game.roll_dice()

        # Проверка на дубль
        if dice1 == dice2:
            game.double_count += 1
            if game.double_count >= 3:
                await message.answer(
                    f"🎲 Выброшен третий дубль ({dice1}-{dice2})! Вы отправляетесь в тюрьму!"
                )
                current_player.go_to_jail()
                game.next_turn()
                game_manager.save_game_state(game.game_id)
                return
        else:
            game.double_count = 0

        # Перемещение
        move_result = game.move_player(current_player, total)

        # Получить информацию о клетке
        cell_action = game.process_cell_action(current_player, total)

        # Формирование сообщения
        response = (
            f"🎲 <b>{current_player.full_name}</b> бросает кубики:\n"
            f"🎯 {dice1} + {dice2} = {total}\n\n"
        )

        if move_result["passed_go"]:
            response += f"💰 Прошли 'Старт', получили {move_result['salary']}$\n\n"

        response += f"📍 Вы на клетке: <b>{cell_action['cell'].name}</b>\n"

        if cell_action["message"]:
            response += f"📝 {cell_action['message']}\n"

        # Обработка действий
        if cell_action["action"] == "buy_property":
            response += f"\n💵 Хотите купить за {cell_action['cell'].price}$?\n"
            response += "✅ /buy - Купить\n❌ /skip - Пропустить"
            await state.set_state(GameStates.waiting_for_buy_decision)
            await state.update_data(property_id=move_result["new_position"])

        elif cell_action["action"] == "pay_rent":
            owner = game.players.get(cell_action["owner_id"])
            if owner:
                rent = cell_action["rent"]
                if current_player.deduct_money(rent):
                    owner.add_money(rent)
                    response += f"\n💸 Заплатили {rent}$ {owner.full_name}"
                else:
                    response += f"\n💥 У вас недостаточно денег для оплаты ренты {rent}$!"

        elif cell_action["action"] == "pay_tax":
            tax = cell_action["rent"]
            if current_player.deduct_money(tax):
                game.free_parking_pot += tax
                response += f"\n💰 Налог {tax}$ добавлен в банк бесплатной стоянки"
            else:
                response += f"\n💥 У вас недостаточно денег для оплаты налога!"

        elif cell_action["action"] == "go_to_jail":
            response += "\n🔒 Вы отправлены в тюрьму!"

        await message.answer(response, parse_mode="HTML")

        # Сохранить состояние
        game_manager.save_game_state(game.game_id)

        # Если не требуется решение игрока, передать ход
        if cell_action["action"] not in ["buy_property", "buy_station", "buy_utility"]:
            if dice1 != dice2:  # Если не дубль
                game.next_turn()

    @dp.message(Command("buy"))
    async def cmd_buy(message: Message, state: FSMContext):
        """Купить собственность"""
        game_manager = GameManager()
        game = game_manager.get_player_game(message.from_user.id)

        if not game:
            await message.answer("❌ Вы не в игре!")
            return

        current_player = game.get_current_player()
        if current_player.user_id != message.from_user.id:
            await message.answer(f"❌ Сейчас не ваш ход!")
            return

        data = await state.get_data()
        property_id = data.get("property_id")

        if property_id is None:
            await message.answer("❌ Нечего покупать!")
            return

        cell = game.board.get_cell(property_id)
        if game.buy_property(current_player, property_id):
            await message.answer(
                f"✅ Вы купили <b>{cell.name}</b> за {cell.price}$!\n"
                f"💰 Ваш баланс: {current_player.money}$",
                parse_mode="HTML"
            )
        else:
            await message.answer(
                f"❌ Не удалось купить {cell.name}!\n"
                f"Возможно, недостаточно денег или собственность уже куплена."
            )

        await state.clear()
        game_manager.save_game_state(game.game_id)

    @dp.message(Command("skip"))
    async def cmd_skip(message: Message, state: FSMContext):
        """Пропустить покупку"""
        game_manager = GameManager()
        game = game_manager.get_player_game(message.from_user.id)

        if not game:
            await message.answer("❌ Вы не в игре!")
            return

        data = await state.get_data()
        property_id = data.get("property_id")

        if property_id is not None:
            cell = game.board.get_cell(property_id)
            # Начать аукцион
            game.start_auction(property_id)
            await message.answer(
                f"⏭ Вы пропустили покупку {cell.name}\n"
                f"🏷 Начинается аукцион! Начальная цена: 10$\n"
                f"Используйте /bid <сумма> для ставки"
            )

        await state.clear()
        game.next_turn()
        game_manager.save_game_state(game.game_id)

    @dp.message(Command("bid"))
    async def cmd_bid(message: Message):
        """Сделать ставку на аукционе"""
        game_manager = GameManager()
        game = game_manager.get_player_game(message.from_user.id)

        if not game:
            await message.answer("❌ Вы не в игре!")
            return

        if game.state != GameState.AUCTION or not game.auction:
            await message.answer("❌ Сейчас нет активного аукциона!")
            return

        try:
            amount = int(message.text.split()[1])
        except (IndexError, ValueError):
            await message.answer("❌ Укажите сумму: /bid 100")
            return

        if game.place_bid(message.from_user.id, amount):
            cell = game.board.get_cell(game.auction.property_id)
            await message.answer(
                f"✅ Ставка принята!\n"
                f"🏷 {cell.name}: {amount}$ от {message.from_user.full_name}"
            )
        else:
            await message.answer("❌ Неверная ставка!")

    @dp.message(Command("status"))
    async def cmd_status(message: Message):
        """Показать статус игры"""
        game_manager = GameManager()
        game = game_manager.get_player_game(message.from_user.id)

        if not game:
            await message.answer("❌ Вы не в игре!")
            return

        response = f"🎮 <b>Игра {game.game_id}</b>\n\n"

        for i, player_id in enumerate(game.player_order):
            player = game.players[player_id]
            current = "👑" if i == game.current_player_index else ""
            jail = "🔒" if player.status.value == "in_jail" else ""

            response += (
                f"{current}{jail} <b>{player.full_name}</b>\n"
                f"💰 {player.money}$ | 🏠 {len(player.properties)} | 🚂 {len(player.stations)} | ⚡ {len(player.utilities)}\n"
            )

            # Показать тюремные карты
            if player.get_out_of_jail_cards > 0:
                response += f"🎫 Карт освобождения: {player.get_out_of_jail_cards}\n"

            response += "\n"

        # Показать текущего игрока
        current = game.get_current_player()
        if current:
            response += f"📊 <b>Сейчас ходит:</b> {current.full_name}\n"

        await message.answer(response, parse_mode="HTML")

    @dp.message(Command("properties"))
    async def cmd_properties(message: Message):
        """Показать собственность игрока"""
        game_manager = GameManager()
        game = game_manager.get_player_game(message.from_user.id)

        if not game:
            await message.answer("❌ Вы не в игре!")
            return

        player = game.players.get(message.from_user.id)
        if not player:
            await message.answer("❌ Вы не в игре!")
            return

        response = f"🏘 <b>Собственность {player.full_name}</b>\n\n"

        if player.properties:
            response += "<b>Улицы:</b>\n"
            for prop_id in player.properties:
                cell = game.board.get_cell(prop_id)
                if isinstance(cell, PropertyCell):
                    houses = "🏨" if cell.hotel else "🏠" * cell.houses
                    response += f"• {cell.name} {houses}\n"

        if player.stations:
            response += "\n<b>Вокзалы:</b>\n"
            for station_id in player.stations:
                cell = game.board.get_cell(station_id)
                response += f"• {cell.name}\n"

        if player.utilities:
            response += "\n<b>Коммунальные предприятия:</b>\n"
            for util_id in player.utilities:
                cell = game.board.get_cell(util_id)
                response += f"• {cell.name}\n"

        if not player.properties and not player.stations and not player.utilities:
            response += "У вас нет собственности 😢"

        await message.answer(response, parse_mode="HTML")

    @dp.message(Command("leave"))
    async def cmd_leave(message: Message):
        """Покинуть игру"""
        game_manager = GameManager()
        game = game_manager.get_player_game(message.from_user.id)

        if not game:
            await message.answer("❌ Вы не в игре!")
            return

        player_name = message.from_user.full_name
        game_manager.leave_game(message.from_user.id)

        await message.answer("👋 Вы покинули игру!")

        # Уведомить других игроков
        if game:
            for player in game.players.values():
                if player.user_id != message.from_user.id:
                    try:
                        await message.bot.send_message(
                            player.user_id,
                            f"👋 {player_name} покинул игру!"
                        )
                    except:
                        pass

    @dp.message(Command("endgame"))
    async def cmd_endgame(message: Message):
        """Завершить игру (только для создателя)"""
        game_manager = GameManager()
        game = game_manager.get_player_game(message.from_user.id)

        if not game:
            await message.answer("❌ Вы не в игре!")
            return

        if game.creator_id != message.from_user.id:
            await message.answer("❌ Только создатель может завершить игру!")
            return

        game_manager.end_game(game.game_id)
        await message.answer("🎬 Игра завершена!")

        # Уведомить других игроков
        for player in game.players.values():
            if player.user_id != message.from_user.id:
                try:
                    await message.bot.send_message(
                        player.user_id,
                        "🎬 Создатель завершил игру!"
                    )
                except:
                    pass

    @dp.message(Command("save"))
    async def cmd_save(message: Message):
        """Сохранить игру"""
        game_manager = GameManager()
        game = game_manager.get_player_game(message.from_user.id)

        if not game:
            await message.answer("❌ Вы не в игре!")
            return

        game_manager.save_game_state(game.game_id)
        await message.answer("💾 Игра сохранена!")

    @dp.message(Command("jail"))
    async def cmd_jail(message: Message):
        """Действия в тюрьме"""
        game_manager = GameManager()
        game = game_manager.get_player_game(message.from_user.id)

        if not game:
            await message.answer("❌ Вы не в игре!")
            return

        player = game.players.get(message.from_user.id)
        if player.status.value != "in_jail":
            await message.answer("❌ Вы не в тюрьме!")
            return

        response = (
            f"🔒 <b>Вы в тюрьме!</b>\n"
            f"Ход в тюрьме: {player.jail_turns + 1}/3\n\n"
            f"Доступные действия:\n"
            f"🎲 /jail_roll - Попытаться выбросить дубль\n"
            f"💵 /jail_pay - Заплатить 50$\n"
            f"🎫 /jail_card - Использовать карту освобождения"
        )

        await message.answer(response, parse_mode="HTML")

    @dp.message(Command("jail_roll"))
    async def cmd_jail_roll(message: Message):
        """Попытка выбросить дубль в тюрьме"""
        game_manager = GameManager()
        game = game_manager.get_player_game(message.from_user.id)

        if not game:
            await message.answer("❌ Вы не в игре!")
            return

        player = game.players.get(message.from_user.id)
        if player.status.value != "in_jail":
            await message.answer("❌ Вы не в тюрьме!")
            return

        dice1, dice2, _ = game.roll_dice()
        player.jail_turns += 1

        if dice1 == dice2:
            player.release_from_jail()
            await message.answer(
                f"🎲 Выброшен дубль {dice1}-{dice2}! Вы свободны!\n"
                f"Перемещайтесь на {dice1 + dice2} клеток /roll"
            )
        elif player.jail_turns >= 3:
            # После 3-х неудачных попыток платить штраф
            await message.answer(
                "⏰ Вы отбыли 3 хода в тюрьме. Должны заплатить 50$\n"
                "Используйте /jail_pay"
            )
        else:
            await message.answer(
                f"🎲 {dice1}-{dice2} - не дубль\n"
                f"Осталось попыток: {3 - player.jail_turns}"
            )

        game_manager.save_game_state(game.game_id)

    @dp.message(Command("jail_pay"))
    async def cmd_jail_pay(message: Message):
        """Заплатить за выход из тюрьмы"""
        game_manager = GameManager()
        game = game_manager.get_player_game(message.from_user.id)

        if not game:
            await message.answer("❌ Вы не в игре!")
            return

        player = game.players.get(message.from_user.id)
        if player.status.value != "in_jail":
            await message.answer("❌ Вы не в тюрьме!")
            return

        if player.deduct_money(50):
            player.release_from_jail()
            await message.answer("✅ Вы заплатили 50$ и вышли из тюрьмы!")
            game_manager.save_game_state(game.game_id)
        else:
            await message.answer("❌ Недостаточно денег для оплаты!")

    @dp.message(Command("jail_card"))
    async def cmd_jail_card(message: Message):
        """Использовать карту освобождения"""
        game_manager = GameManager()
        game = game_manager.get_player_game(message.from_user.id)

        if not game:
            await message.answer("❌ Вы не в игре!")
            return

        player = game.players.get(message.from_user.id)
        if player.status.value != "in_jail":
            await message.answer("❌ Вы не в тюрьме!")
            return

        if player.get_out_of_jail_cards > 0:
            player.get_out_of_jail_cards -= 1
            player.release_from_jail()
            await message.answer("✅ Использована карта освобождения! Вы свободны!")
            game_manager.save_game_state(game.game_id)
        else:
            await message.answer("❌ У вас нет карт освобождения!")

    @dp.message(Command("build"))
    async def cmd_build(message: Message):
        """Построить дом"""
        game_manager = GameManager()
        game = game_manager.get_player_game(message.from_user.id)

        if not game:
            await message.answer("❌ Вы не в игре!")
            return

        player = game.players.get(message.from_user.id)
        if not player:
            await message.answer("❌ Вы не в игре!")
            return

        # Найти улицы, на которых можно строить
        buildable_properties = []
        for prop_id in player.properties:
            if game.board.can_build_on_property(prop_id, player.user_id):
                cell = game.board.get_cell(prop_id)
                buildable_properties.append(cell)

        if not buildable_properties:
            await message.answer("❌ Нет доступных улиц для строительства!")
            return

        response = "🏗 <b>Строительство домов:</b>\n\n"
        for i, cell in enumerate(buildable_properties):
            houses = "🏨" if cell.hotel else "🏠" * cell.houses
            response += (
                f"{i + 1}. {cell.name} {houses}\n"
                f"   Цена дома: {cell.house_price}$\n"
                f"   /build_{cell.id} - Построить\n\n"
            )

        await message.answer(response, parse_mode="HTML")