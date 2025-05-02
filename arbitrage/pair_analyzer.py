# arbitrage/pair_analyzer.py
import logging
from typing import Dict, List, Optional, Tuple
import json
import os
from datetime import datetime, timedelta
import asyncio

from arbitrage.opportunity import ArbitrageOpportunity
import config

logger = logging.getLogger('arbitrage')

class ArbitragePairAnalyzer:
    """
    Аналізує історичні дані для виявлення найприбутковіших пар для арбітражу
    """
    def __init__(self, storage_path="status/pair_stats.json"):
        self.storage_path = storage_path
        self.pair_stats = {}
        self.last_update = datetime.now()
        
        # Створюємо директорію для зберігання статистики, якщо вона не існує
        os.makedirs(os.path.dirname(storage_path), exist_ok=True)
        
        # Завантажуємо існуючу статистику, якщо вона є
        self._load_stats()
        
    def _load_stats(self):
        """
        Завантажує статистику пар з файлу
        """
        try:
            if os.path.exists(self.storage_path):
                with open(self.storage_path, 'r') as f:
                    data = json.load(f)
                    self.pair_stats = data.get('pair_stats', {})
                    
                    # Перетворення рядка дати в об'єкт datetime
                    last_update_str = data.get('last_update')
                    if last_update_str:
                        self.last_update = datetime.fromisoformat(last_update_str)
        except Exception as e:
            logger.error(f"Помилка при завантаженні статистики пар: {e}")
            self.pair_stats = {}
            
    def _save_stats(self):
        """
        Зберігає статистику пар у файл
        """
        try:
            data = {
                'pair_stats': self.pair_stats,
                'last_update': self.last_update.isoformat()
            }
            
            with open(self.storage_path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Помилка при збереженні статистики пар: {e}")
            
    async def update_stats(self, opportunities: List[ArbitrageOpportunity]):
        """
        Оновлює статистику на основі нових можливостей
        
        Args:
            opportunities (List[ArbitrageOpportunity]): Список арбітражних можливостей
        """
        current_time = datetime.now()
        
        # Оновлюємо статистику для кожної можливості
        for opp in opportunities:
            if opp.opportunity_type == "cross":
                # Для крос-біржового арбітражу
                key = f"{opp.symbol}-{opp.buy_exchange}-{opp.sell_exchange}"
                self._update_pair_stat(key, opp)
            elif opp.opportunity_type == "triangular":
                # Для трикутного арбітражу
                if opp.path:
                    key = f"tri-{opp.buy_exchange}-{'-'.join(opp.path)}"
                    self._update_pair_stat(key, opp)
        
        # Оновлюємо час останнього оновлення
        self.last_update = current_time
        
        # Зберігаємо статистику кожні 10 хвилин
        if (current_time - self.last_update) > timedelta(minutes=10):
            self._save_stats()
    
    def _update_pair_stat(self, key: str, opportunity: ArbitrageOpportunity):
        """
        Оновлює статистику для конкретної пари або шляху
        
        Args:
            key (str): Ключ для ідентифікації пари або шляху
            opportunity (ArbitrageOpportunity): Арбітражна можливість
        """
        if key not in self.pair_stats:
            self.pair_stats[key] = {
                'count': 0,
                'total_profit': 0.0,
                'total_net_profit': 0.0,
                'max_profit': 0.0,
                'min_profit': float('inf'),
                'avg_profit': 0.0,
                'avg_net_profit': 0.0,
                'opportunity_type': opportunity.opportunity_type,
                'first_seen': opportunity.timestamp.isoformat(),
                'last_seen': opportunity.timestamp.isoformat()
            }
            
        # Оновлюємо статистику
        stats = self.pair_stats[key]
        stats['count'] += 1
        stats['total_profit'] += opportunity.profit_percent
        stats['total_net_profit'] += opportunity.net_profit_percent
        stats['max_profit'] = max(stats['max_profit'], opportunity.net_profit_percent)
        stats['min_profit'] = min(stats['min_profit'], opportunity.net_profit_percent)
        stats['avg_profit'] = stats['total_profit'] / stats['count']
        stats['avg_net_profit'] = stats['total_net_profit'] / stats['count']
        stats['last_seen'] = opportunity.timestamp.isoformat()
        
        # Для крос-біржового арбітражу зберігаємо додаткову інформацію
        if opportunity.opportunity_type == "cross":
            stats['symbol'] = opportunity.symbol
            stats['buy_exchange'] = opportunity.buy_exchange
            stats['sell_exchange'] = opportunity.sell_exchange
        # Для трикутного арбітражу
        elif opportunity.opportunity_type == "triangular" and opportunity.path:
            stats['path'] = opportunity.path
            stats['exchange'] = opportunity.buy_exchange
            
    def get_top_pairs(self, limit: int = 5, opportunity_type: Optional[str] = None) -> List[Dict]:
        """
        Повертає найприбутковіші пари
        
        Args:
            limit (int, optional): Кількість пар для повернення. За замовчуванням 5.
            opportunity_type (Optional[str], optional): Тип можливості ("cross" або "triangular").
                Якщо None, поверне обидва типи.
                
        Returns:
            List[Dict]: Список словників зі статистикою найприбутковіших пар
        """
        filtered_stats = []
        
        for key, stats in self.pair_stats.items():
            # Фільтруємо за типом можливості, якщо вказано
            if opportunity_type and stats.get('opportunity_type') != opportunity_type:
                continue
                
            filtered_stats.append(stats)
        
        # Сортуємо за середнім чистим прибутком
        sorted_stats = sorted(filtered_stats, key=lambda x: x.get('avg_net_profit', 0), reverse=True)
        
        # Повертаємо обмежену кількість результатів
        return sorted_stats[:limit]
