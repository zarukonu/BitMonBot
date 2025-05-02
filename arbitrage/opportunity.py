# arbitrage/opportunity.py
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

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
    profit_percent: float  # Відсоток прибутку (без врахування комісій)
    timestamp: datetime = datetime.now()  # Час виявлення
    
    # Нові поля
    opportunity_type: str = "cross"  # Тип арбітражу: "cross" або "triangular"
    estimated_fees: float = 0.0  # Оцінка комісій у відсотках
    net_profit_percent: float = 0.0  # Чистий прибуток після комісій
    estimated_execution_time: int = 0  # Оцінка часу виконання в секундах
    path: Optional[List[str]] = None  # Шлях для трикутного арбітражу
    volume_limitation: Optional[float] = None  # Обмеження обсягу для арбітражу
    
    def __post_init__(self):
        """
        Автоматично розраховує чистий прибуток при створенні об'єкта
        """
        self.calculate_net_profit()
    
    def calculate_net_profit(self):
        """
        Розрахувати чистий прибуток після врахування комісій
        """
        self.net_profit_percent = self.profit_percent - self.estimated_fees
        return self.net_profit_percent
    
    def to_dict(self) -> Dict:
        """
        Перетворення об'єкта в словник
        """
        result = {
            'symbol': self.symbol,
            'buy_exchange': self.buy_exchange,
            'sell_exchange': self.sell_exchange,
            'buy_price': self.buy_price,
            'sell_price': self.sell_price,
            'profit_percent': self.profit_percent,
            'estimated_fees': self.estimated_fees,
            'net_profit_percent': self.net_profit_percent,
            'timestamp': self.timestamp.isoformat(),
            'opportunity_type': self.opportunity_type
        }
        
        if self.path:
            result['path'] = self.path
            
        if self.volume_limitation:
            result['volume_limitation'] = self.volume_limitation
            
        return result
    
    def to_message(self) -> str:
        """
        Форматує арбітражну можливість для відправки в Telegram
        """
        # Визначаємо емодзі залежно від прибутку
        profit_emoji = "🔥" if self.net_profit_percent > 1.5 else "💰" if self.net_profit_percent > 0.8 else "💸"
        
        if self.opportunity_type == "cross":
            return (
                f"<b>{profit_emoji} Крос-біржова можливість ({self.net_profit_percent:.2f}% після комісій)</b>\n\n"
                f"<b>Пара:</b> {self.symbol}\n"
                f"<b>Купити на:</b> {self.buy_exchange} за {self.buy_price:.8f}\n"
                f"<b>Продати на:</b> {self.sell_exchange} за {self.sell_price:.8f}\n"
                f"<b>Прибуток:</b> {self.profit_percent:.2f}% (комісії: {self.estimated_fees:.2f}%)\n"
                f"<b>Час:</b> {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
            )
        elif self.opportunity_type == "triangular":
            # Форматуємо шлях для трикутного арбітражу
            path_str = " → ".join(self.path) if self.path else "Невідомий шлях"
            
            return (
                f"<b>{profit_emoji} Трикутна можливість ({self.net_profit_percent:.2f}% після комісій)</b>\n\n"
                f"<b>Біржа:</b> {self.buy_exchange}\n"
                f"<b>Шлях:</b> {path_str}\n"
                f"<b>Прибуток:</b> {self.profit_percent:.2f}% (комісії: {self.estimated_fees:.2f}%)\n"
                f"<b>Час:</b> {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
            )
        else:
            return (
                f"<b>{profit_emoji} Арбітражна можливість ({self.net_profit_percent:.2f}% після комісій)</b>\n\n"
                f"<b>Пара:</b> {self.symbol}\n"
                f"<b>Купити на:</b> {self.buy_exchange} за {self.buy_price:.8f}\n"
                f"<b>Продати на:</b> {self.sell_exchange} за {self.sell_price:.8f}\n"
                f"<b>Прибуток:</b> {self.profit_percent:.2f}% (комісії: {self.estimated_fees:.2f}%)\n"
                f"<b>Час:</b> {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
            )
