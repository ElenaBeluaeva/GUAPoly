"""
Менеджер торговли для Монополии
"""

import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta  # ← Добавьте timedelta здесь


class TradeOffer:
    """Предложение торговли"""

    def __init__(self, trade_id: str, from_player_id: int, to_player_id: int,
                 offer: Dict[str, Any], request: Dict[str, Any]):
        self.trade_id = trade_id
        self.from_player_id = from_player_id
        self.to_player_id = to_player_id
        self.offer = offer  # {money: int, properties: List[int]}
        self.request = request  # {money: int, properties: List[int]}
        self.status = "pending"  # pending, accepted, rejected, expired
        self.created_at = datetime.now()
        self.expires_at = datetime.now() + timedelta(minutes=5)  # 5 минут на ответ

    def __repr__(self):
        return f"TradeOffer(id={self.trade_id}, from={self.from_player_id}, to={self.to_player_id}, status={self.status})"


class TradeManager:
    """Менеджер торговли"""

    def __init__(self):
        self.active_trades: Dict[str, TradeOffer] = {}
        self.trade_history: List[TradeOffer] = []

    def create_trade(self, from_player_id: int, to_player_id: int,
                     offer: Dict[str, Any], request: Dict[str, Any]) -> Optional[str]:
        """Создать новое предложение торговли"""
        try:
            # Генерируем уникальный ID
            timestamp = int(time.time())
            trade_id = f"trade_{from_player_id}_{to_player_id}_{timestamp}"

            # Создаем предложение
            trade = TradeOffer(
                trade_id=trade_id,
                from_player_id=from_player_id,
                to_player_id=to_player_id,
                offer=offer,
                request=request
            )

            # Сохраняем в активные предложения
            self.active_trades[trade_id] = trade

            print(f"✅ Создано торговое предложение {trade_id}")  # ← ИЗМЕНИТЕ ЗДЕСЬ
            return trade_id

        except Exception as e:
            print(f"❌ Ошибка создания торговли: {e}")  # ← ИЗМЕНИТЕ ЗДЕСЬ
            import traceback
            traceback.print_exc()
            return None

    def get_trade(self, trade_id: str) -> Optional[TradeOffer]:
        """Получить предложение по ID"""
        return self.active_trades.get(trade_id)

    def accept_trade(self, trade_id: str, player_id: int) -> Dict[str, Any]:
        """Принять предложение торговли"""
        trade = self.get_trade(trade_id)

        if not trade:
            return {"success": False, "error": "Предложение не найдено"}

        if trade.to_player_id != player_id:
            return {"success": False, "error": "Вы не можете принять это предложение"}

        if trade.status != "pending":
            return {"success": False, "error": "Предложение уже обработано"}

        if datetime.now() > trade.expires_at:
            trade.status = "expired"
            del self.active_trades[trade_id]
            self.trade_history.append(trade)
            return {"success": False, "error": "Время предложения истекло"}

        # Принимаем предложение
        trade.status = "accepted"
        trade.processed_at = datetime.now()

        # Перемещаем в историю
        self.trade_history.append(trade)
        if trade_id in self.active_trades:
            del self.active_trades[trade_id]

        return {"success": True, "message": "Сделка принята!"}

    def reject_trade(self, trade_id: str, player_id: int) -> Dict[str, Any]:
        """Отклонить предложение торговли"""
        trade = self.get_trade(trade_id)

        if not trade:
            return {"success": False, "error": "Предложение не найдено"}

        if trade.to_player_id != player_id:
            return {"success": False, "error": "Вы не можете отклонить это предложение"}

        if trade.status != "pending":
            return {"success": False, "error": "Предложение уже обработано"}

        # Отклоняем предложение
        trade.status = "rejected"
        trade.processed_at = datetime.now()

        # Перемещаем в историю
        self.trade_history.append(trade)
        if trade_id in self.active_trades:
            del self.active_trades[trade_id]

        return {"success": True, "message": "Предложение отклонено"}

    def cancel_trade(self, trade_id: str, player_id: int) -> Dict[str, Any]:
        """Отменить свое предложение"""
        trade = self.get_trade(trade_id)

        if not trade:
            return {"success": False, "error": "Предложение не найдено"}

        if trade.from_player_id != player_id:
            return {"success": False, "error": "Вы не можете отменить это предложение"}

        if trade.status != "pending":
            return {"success": False, "error": "Предложение уже обработано"}

        # Отменяем предложение
        trade.status = "cancelled"

        # Перемещаем в историю
        self.trade_history.append(trade)
        if trade_id in self.active_trades:
            del self.active_trades[trade_id]

        return {"success": True, "message": "Предложение отменено"}

    def cleanup_expired_trades(self):
        """Очистить истекшие предложения"""
        now = datetime.now()
        expired_trades = []

        for trade_id, trade in list(self.active_trades.items()):
            if now > trade.expires_at and trade.status == "pending":
                trade.status = "expired"
                expired_trades.append(trade)
                del self.active_trades[trade_id]

        # Добавляем истекшие в историю
        self.trade_history.extend(expired_trades)

    def get_player_trades(self, player_id: int) -> Dict[str, List[TradeOffer]]:
        """Получить все предложения игрока"""
        incoming = []
        outgoing = []

        for trade in self.active_trades.values():
            if trade.status != "pending":
                continue

            if trade.to_player_id == player_id:
                incoming.append(trade)
            elif trade.from_player_id == player_id:
                outgoing.append(trade)

        return {
            "incoming": incoming,
            "outgoing": outgoing
        }

    def format_trade_details(self, trade: TradeOffer) -> str:
        """Форматировать детали торговли"""
        if not trade:
            return "Предложение не найдено"

        status_texts = {
            "pending": "⏳ Ожидает ответа",
            "accepted": "✅ Принято",
            "rejected": "❌ Отклонено",
            "expired": "⌛ Истекло",
            "cancelled": "🚫 Отменено"
        }

        details = f"🤝 *Предложение #{trade.trade_id[:8]}*\n\n"
        details += f"📅 Создано: {trade.created_at.strftime('%H:%M:%S')}\n"
        details += f"⏳ Истекает: {trade.expires_at.strftime('%H:%M')}\n"
        details += f"📊 Статус: {status_texts.get(trade.status, trade.status)}\n\n"

        return details