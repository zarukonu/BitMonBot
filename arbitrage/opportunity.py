# arbitrage/opportunity.py
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional, List

@dataclass
class ArbitrageOpportunity:
    """
    Клас для представлення арбітражної можливості
    """
    symbol: str  # Валютна пара або шлях
    buy_exchange: str  # Біржа для купівлі
    sell_exchange: str  # Біржа для продажу
    buy_price: float  # Ціна купівлі
    sell_price: float  # Ціна продажу
    profit_percent: float  # Відсоток прибутку (без урахування комісій)
    buy_fee: float = 0.0  # Комісія біржі для купівлі (%)
    sell_fee: float = 0.0  # Комісія біржі для продажу (%)
    net_profit_percent: Optional[float] = None  # Чистий прибуток з урахуванням комісій (%)
    timestamp: datetime = datetime.now()  # Час виявлення
    buy_fee_type: str = ""  # Тип комісії для купівлі (maker/taker)
    sell_fee_type: str = ""  # Тип комісії для продажу (maker/taker)
    opportunity_type: str = "cross"  # Тип можливості: "cross" (крос-біржовий) або "triangular" (трикутний)
    path: Optional[List[str]] = None  # Шлях для трикутного арбітражу
    estimated_fees: float = 0.0  # Оцінка загальних комісій
    
    def __post_init__(self):
        """
        Автоматично розраховуємо чистий прибуток, якщо він не вказаний
        """
        if self.net_profit_percent is None and (self.buy_fee > 0 or self.sell_fee > 0):
            # Розрахунок чистого прибутку з урахуванням комісій
            # Купуємо за buy_price, платимо комісію buy_fee
            # Продаємо за sell_price, платимо комісію sell_fee
            buy_with_fee = self.buy_price * (1 + self.buy_fee / 100)
            sell_with_fee = self.sell_price * (1 - self.sell_fee / 100)
            self.net_profit_percent = (sell_with_fee - buy_with_fee) / buy_with_fee * 100
    
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
            'timestamp': self.timestamp.isoformat(),
            'opportunity_type': self.opportunity_type
        }
        
        if self.path:
            result['path'] = self.path
            
        if self.buy_fee > 0 or self.sell_fee > 0:
            result.update({
                'buy_fee': self.buy_fee,
                'buy_fee_type': self.buy_fee_type,
                'sell_fee': self.sell_fee,
                'sell_fee_type': self.sell_fee_type,
                'net_profit_percent': self.net_profit_percent
            })
            
        return result
    
    def to_message(self) -> str:
        """
        Форматує арбітражну можливість для відправки в Telegram
        """
        # Додаємо емодзі в залежності від розміру прибутку
        if self.net_profit_percent is not None:
            profit_value = self.net_profit_percent
        else:
            profit_value = self.profit_percent
            
        if profit_value >= 5.0:
            emoji = "🔥"  # Дуже високий прибуток
        elif profit_value >= 2.0:
            emoji = "💰"  # Високий прибуток
        elif profit_value >= 1.0:
            emoji = "📈"  # Середній прибуток
        else:
            emoji = "🔍"  # Низький прибуток
            
        # Додаємо емодзі криптовалюти, якщо вони доступні
        if self.opportunity_type == "cross":
            coin_symbol = self.symbol.split('/')[0]
            coin_emoji = self._get_coin_emoji(coin_symbol)
            
            message = (
                f"<b>{emoji} {coin_emoji} Крос-біржова можливість ({self.profit_percent:.2f}%)</b>\n\n"
                f"<b>Пара:</b> {self.symbol}\n"
                f"<b>Купити на:</b> {self.buy_exchange} за {self.buy_price:.8f}\n"
                f"<b>Продати на:</b> {self.sell_exchange} за {self.sell_price:.8f}\n"
            )
        else:  # triangular
            # Для трикутного арбітражу використовуємо емодзі першої валюти в шляху
            if self.path and len(self.path) > 0:
                coin_symbol = self.path[0]
                coin_emoji = self._get_coin_emoji(coin_symbol)
                path_str = " → ".join(self.path)
                
                message = (
                    f"<b>{emoji} {coin_emoji} Трикутна можливість ({self.profit_percent:.2f}%)</b>\n\n"
                    f"<b>Біржа:</b> {self.buy_exchange}\n"
                    f"<b>Шлях:</b> {path_str}\n"
                    f"<b>Початкова ціна:</b> {self.buy_price:.8f}\n"
                    f"<b>Кінцева ціна:</b> {self.sell_price:.8f}\n"
                )
            else:
                coin_emoji = "🪙"
                message = (
                    f"<b>{emoji} {coin_emoji} Трикутна можливість ({self.profit_percent:.2f}%)</b>\n\n"
                    f"<b>Біржа:</b> {self.buy_exchange}\n"
                    f"<b>Початкова ціна:</b> {self.buy_price:.8f}\n"
                    f"<b>Кінцева ціна:</b> {self.sell_price:.8f}\n"
                )
        
        # Додаємо інформацію про комісії та чистий прибуток, якщо вони доступні
        if self.buy_fee > 0 or self.sell_fee > 0:
            message += (
                f"<b>Комісія купівлі ({self.buy_fee_type}):</b> {self.buy_fee:.2f}%\n"
                f"<b>Комісія продажу ({self.sell_fee_type}):</b> {self.sell_fee:.2f}%\n"
                f"<b>Прибуток (брутто):</b> {self.profit_percent:.2f}%\n"
                f"<b>Прибуток (нетто):</b> {self.net_profit_percent:.2f}%\n"
            )
        else:
            message += f"<b>Прибуток:</b> {self.profit_percent:.2f}%\n"
            
        message += f"<b>Час:</b> {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
        
        return message
        
    def _get_coin_emoji(self, coin_symbol: str) -> str:
        """
        Повертає емодзі для криптовалюти
        """
        coin_emojis = {
            "BTC": "₿",
            "ETH": "Ξ",
            "XRP": "✖",
            "BNB": "🔶",
            "SOL": "☀️",
            "TRX": "♦️",
            "HBAR": "♓",
            "NEAR": "🔺",
            "ATOM": "⚛️",
            "ADA": "🔷",
            "AVAX": "🔺",
            "USDT": "💵",
            "USDC": "💲"
        }
        
        return coin_emojis.get(coin_symbol, "🪙")  # Якщо емодзі не знайдено, повертаємо загальний емодзі монети
