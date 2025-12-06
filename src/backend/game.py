from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Any
from enum import Enum
import random
import json
from datetime import datetime

from .player import Player, PlayerStatus
from .board import Board, CellType


class GameState(Enum):
    LOBBY = "lobby"  # Сбор игроков
    IN_PROGRESS = "in_game"  # Игра идет
    PAUSED = "paused"  # Пауза
    FINISHED = "finished"  # Игра завершена
    AUCTION = "auction"  # Аукцион
    TRADE = "trade"  # Торговля


@dataclass
class Auction:
    """Аукцион"""
    property_id: int
    current_bid: int = 0
    current_bidder_id: Optional[int] = None
    participants: List[int] = field(default_factory=list)
    active: bool = False


@dataclass
class TradeOffer:
    """Предложение торговли"""
    from_player_id: int
    to_player_id: int
    offer_money: int = 0
    offer_properties: List[int] = field(default_factory=list)
    request_money: int = 0
    request_properties: List[int] = field(default_factory=list)
    status: str = "pending"  # pending, accepted, rejected


class Game:
    """Класс игры"""

    def __init__(self, game_id: str, creator_id: int):
        self.game_id = game_id
        self.creator_id = creator_id
        self.created_at = datetime.now()

        # Состояние игры
        self.state: GameState = GameState.LOBBY
        self.players: Dict[int, Player] = {}
        self.player_order: List[int] = []
        self.current_player_index: int = 0
        self.board = Board()

        # Игровые механики
        self.double_count: int = 0  # Счетчик дублей
        self.auction: Optional[Auction] = None
        self.trade_offers: Dict[str, TradeOffer] = {}
        self.chance_cards: List[str] = []
        self.chest_cards: List[str] = []
        self.free_parking_pot: int = 0

        # Настройки
        self.salary_amount: int = 200
        self.jail_fine: int = 50

        self._init_cards()

    def _init_cards(self):
        """Инициализация карточек"""
        self.chance_cards = [
            "Пройдите на 'Старт'. Получите 200$",
            "Отправляйтесь в тюрьму. Не проходите 'Старт' и не получайте 200$",
            "Заплатите каждому игроку по 50$",
            "Вы получаете наследство в 100$",
            "Оплатите ремонт улиц: 25$ за дом, 100$ за отель",
            "Вы выиграли конкурс красоты. Получите 10$",
            "Вас выпустили из тюрьмы. Карточку можно сохранить",
            "Заплатите налог 15$",
            "Вернитесь на 3 клетки назад",
            "Пройдите на ближайшую коммунальную службу",
            "Пройдите на ближайший вокзал",
            "Ваш рентный доход увеличился. Получите 150$"
        ]

        self.chest_cards = [
            "Ошибка банка в вашу пользу. Получите 200$",
            "Вторая премия за конкурс красоты. Получите 10$",
            "Вы заняли второе место в конкурсе. Получите 100$",
            "Заплатите больничный сбор 100$",
            "Выпуск из тюрьмы. Карточку можно сохранить",
            "Оплатите обучение 50$",
            "Получите проценты по вкладу 25$",
            "Получите доход от аренды 100$",
            "Заплатите страховку 50$",
            "Получите компенсацию 20$"
        ]

    def add_player(self, user_id: int, username: str, full_name: str) -> bool:
        """Добавить игрока"""
        if self.state != GameState.LOBBY:
            return False

        if user_id in self.players:
            return False

        player = Player(user_id, username, full_name)
        self.players[user_id] = player

        # Первый игрок - создатель
        if len(self.players) == 1:
            self.player_order.append(user_id)

        return True

    def remove_player(self, user_id: int):
        """Удалить игрока"""
        if user_id in self.players:
            del self.players[user_id]
            if user_id in self.player_order:
                self.player_order.remove(user_id)

    def start_game(self) -> bool:
        """Начать игру"""
        if len(self.players) < 2:
            return False

        if self.state != GameState.LOBBY:
            return False

        # Перемешать порядок игроков
        random.shuffle(self.player_order)

        # Установить начальные позиции
        for player in self.players.values():
            player.position = 0
            player.money = 1500

        self.state = GameState.IN_PROGRESS
        self.current_player_index = 0
        return True

    def get_current_player(self) -> Optional[Player]:
        """Получить текущего игрока"""
        if not self.player_order:
            return None

        current_id = self.player_order[self.current_player_index]
        return self.players.get(current_id)

    def next_turn(self):
        """Передать ход следующему игроку"""
        if not self.player_order:
            return

        self.current_player_index = (self.current_player_index + 1) % len(self.player_order)
        self.double_count = 0

    def roll_dice(self) -> Tuple[int, int, int]:
        """Бросок кубиков"""
        dice1 = random.randint(1, 6)
        dice2 = random.randint(1, 6)
        return dice1, dice2, dice1 + dice2

    def move_player(self, player: Player, steps: int) -> Dict[str, Any]:
        """Переместить игрока"""
        old_position = player.position
        player.position = (player.position + steps) % 40

        result = {
            "old_position": old_position,
            "new_position": player.position,
            "passed_go": False
        }

        # Проверка прохождения "Старта"
        if old_position + steps >= 40:
            player.add_money(self.salary_amount)
            result["passed_go"] = True
            result["salary"] = self.salary_amount

        return result

    def process_cell_action(self, player: Player, dice_roll: int = 0) -> Dict[str, Any]:
        """Обработать действие клетки"""
        cell = self.board.get_cell(player.position)
        result = {
            "cell": cell,
            "action": None,
            "message": "",
            "rent": 0,
            "owner_id": None
        }

        if cell.type == CellType.PROPERTY:
            if hasattr(cell, 'owner_id'):
                if cell.owner_id is None:
                    result["action"] = "buy_property"
                    result["message"] = f"Вы можете купить {cell.name} за {cell.price}$"
                elif cell.owner_id != player.user_id:
                    # Выплатить ренту
                    owner_assets = self.board.get_owner_assets(cell.owner_id)
                    rent = cell.get_rent(dice_roll, owner_assets)
                    result["action"] = "pay_rent"
                    result["rent"] = rent
                    result["owner_id"] = cell.owner_id
                    result["message"] = f"Вы должны заплатить ренту {rent}$"

        elif cell.type == CellType.STATION:
            if hasattr(cell, 'owner_id'):
                if cell.owner_id is None:
                    result["action"] = "buy_station"
                elif cell.owner_id != player.user_id:
                    owner_assets = self.board.get_owner_assets(cell.owner_id)
                    rent = cell.get_rent(dice_roll, owner_assets)
                    result["action"] = "pay_rent"
                    result["rent"] = rent
                    result["owner_id"] = cell.owner_id

        elif cell.type == CellType.UTILITY:
            if hasattr(cell, 'owner_id'):
                if cell.owner_id is None:
                    result["action"] = "buy_utility"
                elif cell.owner_id != player.user_id:
                    owner_assets = self.board.get_owner_assets(cell.owner_id)
                    rent = cell.get_rent(dice_roll, owner_assets)
                    result["action"] = "pay_rent"
                    result["rent"] = rent
                    result["owner_id"] = cell.owner_id

        elif cell.type == CellType.CHANCE:
            result["action"] = "chance"
            card = random.choice(self.chance_cards)
            result["message"] = f"Шанс: {card}"
            self._process_chance_card(player, card)

        elif cell.type == CellType.CHEST:
            result["action"] = "chest"
            card = random.choice(self.chest_cards)
            result["message"] = f"Казна: {card}"
            self._process_chest_card(player, card)

        elif cell.type == CellType.TAX:
            tax = 200 if cell.name == "Подоходный налог" else 100
            result["action"] = "pay_tax"
            result["rent"] = tax
            result["message"] = f"Заплатите налог {tax}$"

        elif cell.type == CellType.GO_TO_JAIL:
            result["action"] = "go_to_jail"
            player.go_to_jail()
            result["message"] = "Вы отправляетесь в тюрьму!"

        elif cell.type == CellType.FREE_PARKING:
            result["action"] = "free_parking"
            if self.free_parking_pot > 0:
                player.add_money(self.free_parking_pot)
                result["message"] = f"Вы получаете {self.free_parking_pot}$ с бесплатной стоянки!"
                self.free_parking_pot = 0

        return result

    def _process_chance_card(self, player: Player, card: str):
        """Обработать карточку Шанс"""
        if "Старт" in card:
            player.position = 0
            player.add_money(200)
        elif "тюрьму" in card.lower():
            player.go_to_jail()
        elif "Получите" in card:
            amount = int(''.join(filter(str.isdigit, card)))
            player.add_money(amount)
        elif "Заплатите" in card:
            amount = int(''.join(filter(str.isdigit, card)))
            player.deduct_money(amount)
            self.free_parking_pot += amount

    def _process_chest_card(self, player: Player, card: str):
        """Обработать карточку Казна"""
        if "Получите" in card:
            amount = int(''.join(filter(str.isdigit, card)))
            player.add_money(amount)
        elif "Заплатите" in card:
            amount = int(''.join(filter(str.isdigit, card)))
            player.deduct_money(amount)
            self.free_parking_pot += amount
        elif "выпуск из тюрьмы" in card.lower():
            player.get_out_of_jail_cards += 1

    def buy_property(self, player: Player, property_id: int) -> bool:
        """Купить недвижимость"""
        cell = self.board.get_cell(property_id)

        if not hasattr(cell, 'owner_id') or cell.owner_id is not None:
            return False

        if not player.can_afford(cell.price):
            return False

        if player.deduct_money(cell.price):
            cell.owner_id = player.user_id

            if isinstance(cell, PropertyCell):
                player.properties.append(property_id)
            elif isinstance(cell, StationCell):
                player.stations.append(property_id)
            elif isinstance(cell, UtilityCell):
                player.utilities.append(property_id)

            return True

        return False

    def start_auction(self, property_id: int):
        """Начать аукцион"""
        self.auction = Auction(
            property_id=property_id,
            current_bid=0,
            participants=list(self.players.keys()),
            active=True
        )
        self.state = GameState.AUCTION

    def place_bid(self, player_id: int, amount: int) -> bool:
        """Сделать ставку на аукционе"""
        if not self.auction or not self.auction.active:
            return False

        player = self.players.get(player_id)
        if not player or player_id not in self.auction.participants:
            return False

        if amount <= self.auction.current_bid:
            return False

        if not player.can_afford(amount):
            return False

        self.auction.current_bid = amount
        self.auction.current_bidder_id = player_id
        return True

    def end_auction(self):
        """Завершить аукцион"""
        if not self.auction:
            return

        if self.auction.current_bidder_id:
            winner = self.players.get(self.auction.current_bidder_id)
            if winner and winner.deduct_money(self.auction.current_bid):
                cell = self.board.get_cell(self.auction.property_id)
                cell.owner_id = winner.user_id

        self.auction = None
        self.state = GameState.IN_PROGRESS

    def create_trade_offer(self, from_player_id: int, to_player_id: int,
                           offer: Dict, request: Dict) -> Optional[str]:
        """Создать предложение торговли"""
        if from_player_id not in self.players or to_player_id not in self.players:
            return None

        trade_id = f"{from_player_id}_{to_player_id}_{datetime.now().timestamp()}"

        trade = TradeOffer(
            from_player_id=from_player_id,
            to_player_id=to_player_id,
            offer_money=offer.get('money', 0),
            offer_properties=offer.get('properties', []),
            request_money=request.get('money', 0),
            request_properties=request.get('properties', [])
        )

        self.trade_offers[trade_id] = trade
        return trade_id

    def accept_trade(self, trade_id: str) -> bool:
        """Принять предложение торговли"""
        trade = self.trade_offers.get(trade_id)
        if not trade or trade.status != "pending":
            return False

        from_player = self.players.get(trade.from_player_id)
        to_player = self.players.get(trade.to_player_id)

        if not from_player or not to_player:
            return False

        # Проверить возможность торговли
        if not from_player.can_afford(trade.offer_money):
            return False
        if not to_player.can_afford(trade.request_money):
            return False

        # Обмен деньгами
        from_player.deduct_money(trade.offer_money)
        to_player.add_money(trade.offer_money)

        to_player.deduct_money(trade.request_money)
        from_player.add_money(trade.request_money)

        # Обмен недвижимостью
        for prop_id in trade.offer_properties:
            cell = self.board.get_cell(prop_id)
            if hasattr(cell, 'owner_id') and cell.owner_id == from_player.user_id:
                cell.owner_id = to_player.user_id
                if prop_id in from_player.properties:
                    from_player.properties.remove(prop_id)
                    to_player.properties.append(prop_id)

        for prop_id in trade.request_properties:
            cell = self.board.get_cell(prop_id)
            if hasattr(cell, 'owner_id') and cell.owner_id == to_player.user_id:
                cell.owner_id = from_player.user_id
                if prop_id in to_player.properties:
                    to_player.properties.remove(prop_id)
                    from_player.properties.append(prop_id)

        trade.status = "accepted"
        return True

    def build_house(self, player: Player, property_id: int) -> bool:
        """Построить дом на недвижимости"""
        if not self.board.can_build_on_property(property_id, player.user_id):
            return False

        cell = self.board.get_cell(property_id)
        if not isinstance(cell, PropertyCell):
            return False

        if not player.can_afford(cell.house_price):
            return False

        if player.deduct_money(cell.house_price):
            return cell.build_house()

        return False

    def declare_bankruptcy(self, player: Player, creditor_id: Optional[int] = None):
        """Объявить банкротство"""
        player.status = PlayerStatus.BANKRUPT

        if creditor_id and creditor_id in self.players:
            # Передать активы кредитору
            creditor = self.players[creditor_id]

            for prop_id in player.properties:
                cell = self.board.get_cell(prop_id)
                cell.owner_id = creditor_id
                creditor.properties.append(prop_id)

            for station_id in player.stations:
                cell = self.board.get_cell(station_id)
                cell.owner_id = creditor_id
                creditor.stations.append(station_id)

            for util_id in player.utilities:
                cell = self.board.get_cell(util_id)
                cell.owner_id = creditor_id
                creditor.utilities.append(util_id)
        else:
            # Вернуть активы банку
            for prop_id in player.properties:
                cell = self.board.get_cell(prop_id)
                cell.owner_id = None
                cell.houses = 0
                cell.hotel = False

            for station_id in player.stations:
                cell = self.board.get_cell(station_id)
                cell.owner_id = None

            for util_id in player.utilities:
                cell = self.board.get_cell(util_id)
                cell.owner_id = None

        # Удалить игрока из порядка ходов
        if player.user_id in self.player_order:
            self.player_order.remove(player.user_id)

        # Проверить конец игры
        if len(self.player_order) == 1:
            self.state = GameState.FINISHED

    def to_dict(self) -> Dict:
        """Конвертировать игру в словарь для сохранения"""
        return {
            "game_id": self.game_id,
            "creator_id": self.creator_id,
            "created_at": self.created_at.isoformat(),
            "state": self.state.value,
            "players": {
                uid: {
                    "user_id": p.user_id,
                    "username": p.username,
                    "full_name": p.full_name,
                    "position": p.position,
                    "money": p.money,
                    "status": p.status.value,
                    "properties": p.properties,
                    "stations": p.stations,
                    "utilities": p.utilities,
                    "jail_turns": p.jail_turns,
                    "get_out_of_jail_cards": p.get_out_of_jail_cards,
                    "color": p.color
                }
                for uid, p in self.players.items()
            },
            "player_order": self.player_order,
            "current_player_index": self.current_player_index,
            "board_state": [
                {
                    "id": i,
                    "owner_id": cell.owner_id if hasattr(cell, 'owner_id') else None,
                    "houses": cell.houses if hasattr(cell, 'houses') else 0,
                    "hotel": cell.hotel if hasattr(cell, 'hotel') else False,
                    "mortgaged": cell.mortgaged if hasattr(cell, 'mortgaged') else False
                }
                for i, cell in enumerate(self.board.cells)
                if hasattr(cell, 'owner_id')
            ],
            "double_count": self.double_count,
            "free_parking_pot": self.free_parking_pot,
            "auction": {
                "property_id": self.auction.property_id,
                "current_bid": self.auction.current_bid,
                "current_bidder_id": self.auction.current_bidder_id,
                "participants": self.auction.participants,
                "active": self.auction.active
            } if self.auction else None
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'Game':
        """Восстановить игру из словаря"""
        game = cls(data["game_id"], data["creator_id"])
        game.created_at = datetime.fromisoformat(data["created_at"])
        game.state = GameState(data["state"])

        # Восстановить игроков
        game.players = {}
        for uid, p_data in data["players"].items():
            uid = int(uid)
            player = Player(
                user_id=p_data["user_id"],
                username=p_data["username"],
                full_name=p_data["full_name"]
            )
            player.position = p_data["position"]
            player.money = p_data["money"]
            player.status = PlayerStatus(p_data["status"])
            player.properties = p_data["properties"]
            player.stations = p_data["stations"]
            player.utilities = p_data["utilities"]
            player.jail_turns = p_data["jail_turns"]
            player.get_out_of_jail_cards = p_data["get_out_of_jail_cards"]
            player.color = p_data["color"]
            game.players[uid] = player

        game.player_order = data["player_order"]
        game.current_player_index = data["current_player_index"]

        # Восстановить состояние поля
        for cell_state in data["board_state"]:
            cell = game.board.get_cell(cell_state["id"])
            if hasattr(cell, 'owner_id'):
                cell.owner_id = cell_state["owner_id"]
            if hasattr(cell, 'houses'):
                cell.houses = cell_state["houses"]
            if hasattr(cell, 'hotel'):
                cell.hotel = cell_state["hotel"]
            if hasattr(cell, 'mortgaged'):
                cell.mortgaged = cell_state["mortgaged"]

        game.double_count = data["double_count"]
        game.free_parking_pot = data.get("free_parking_pot", 0)

        # Восстановить аукцион
        if data.get("auction"):
            game.auction = Auction(
                property_id=data["auction"]["property_id"],
                current_bid=data["auction"]["current_bid"],
                current_bidder_id=data["auction"]["current_bidder_id"],
                participants=data["auction"]["participants"],
                active=data["auction"]["active"]
            )
            game.state = GameState.AUCTION

        return game


