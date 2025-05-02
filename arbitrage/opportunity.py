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
        Форматує арбітражну можливість для відправки в Telegram з емодзі
        """
        # Визначаємо емодзі для заголовка залежно від % прибутку
        if self.profit_percent >= 5.0:
            header_emoji = "🔥💰🔥"  # Дуже прибуткова можливість
        elif self.profit_percent >= 2.0:
            header_emoji = "💰💰"    # Хороша можливість
        else:
            header_emoji = "💰"      # Звичайна можливість
            
        # Форматуємо повідомлення
        return (
            f"<b>{header_emoji} АРБІТРАЖНА МОЖЛИВІСТЬ {header_emoji}</b>\n\n"
            f"<b>📊 Прибуток:</b> <code>+{self.profit_percent:.2f}%</code>\n"
            f"<b>🪙 Пара:</b> <code>{self.symbol}</code>\n\n"
            f"<b>🔄 Операція:</b>\n"
            f"<b>📈 Купити на:</b> <code>{self.buy_exchange}</code>\n"
            f"<b>💲 Ціна купівлі:</b> <code>{self.buy_price:.8f}</code>\n\n"
            f"<b>📉 Продати на:</b> <code>{self.sell_exchange}</code>\n"
            f"<b>💲 Ціна продажу:</b> <code>{self.sell_price:.8f}</code>\n\n"
            f"<b>⏱️ Час:</b> <code>{self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}</code>"
        )
