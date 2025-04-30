# arbitrage/opportunity.py
from dataclasses import dataclass
from datetime import datetime
from typing import Dict

@dataclass
class ArbitrageOpportunity:
    """
    Клас для представлення арбітражної можливості
    """
    symbol: str  # Валютна пара
    buy_exchange: str  # Біржа для купівлі
    sell_exchange: str  # Біржа для продажу
    buy_price: float  # Ціна купівлі
    sell_price: float  # Ціна продажу
    profit_percent: float  # Відсоток прибутку
    timestamp: datetime = datetime.now()  # Час виявлення
    
    def to_dict(self) -> Dict:
        """
        Перетворення об'єкта в словник
        """
        return {
            'symbol': self.symbol,
            'buy_exchange': self.buy_exchange,
            'sell_exchange': self.sell_exchange,
            'buy_price': self.buy_price,
            'sell_price': self.sell_price,
            'profit_percent': self.profit_percent,
            'timestamp': self.timestamp.isoformat()
        }
    
    def to_message(self) -> str:
        """
        Форматує арбітражну можливість для відправки в Telegram
        """
        return (
            f"<b>🔍 Арбітражна можливість ({self.profit_percent:.2f}%)</b>\n\n"
            f"<b>Пара:</b> {self.symbol}\n"
            f"<b>Купити на:</b> {self.buy_exchange} за {self.buy_price:.8f}\n"
            f"<b>Продати на:</b> {self.sell_exchange} за {self.sell_price:.8f}\n"
            f"<b>Прибуток:</b> {self.profit_percent:.2f}%\n"
            f"<b>Час:</b> {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
        )
