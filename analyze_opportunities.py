# analyze_opportunities.py
import json
import os
import sys
from datetime import datetime, timedelta
import glob

def analyze_opportunities(days_ago=0, min_profit=None, symbol=None):
    """
    Аналізує арбітражні можливості з JSON-файлів
    
    Args:
        days_ago (int): Кількість днів назад для аналізу (0 = сьогодні)
        min_profit (float): Мінімальний поріг прибутку для аналізу
        symbol (str): Фільтр за символом
    """
    try:
        # Визначаємо дату для аналізу
        target_date = datetime.now() - timedelta(days=days_ago)
        date_str = target_date.strftime('%Y%m%d')
        
        # Знаходимо всі файли з можливостями за вказану дату
        files = glob.glob(f"data/opportunities_{date_str}_*.json")
        
        if not files:
            print(f"Не знайдено файлів з можливостями за {target_date.strftime('%Y-%m-%d')}")
            return
        
        all_opportunities = []
        
        # Завантажуємо дані з кожного файлу
        for file_path in files:
            try:
                with open(file_path, "r") as f:
                    data = json.load(f)
                    timestamp = data.get("timestamp")
                    opportunities = data.get("opportunities", [])
                    
                    # Додаємо часову мітку до кожної можливості
                    for opp in opportunities:
                        opp["file_timestamp"] = timestamp
                    
                    all_opportunities.extend(opportunities)
            except Exception as e:
                print(f"Помилка при читанні файлу {file_path}: {e}")
        
        if not all_opportunities:
            print("Не знайдено жодної можливості для аналізу")
            return
        
        # Фільтруємо за символом, якщо вказано
        if symbol:
            all_opportunities = [opp for opp in all_opportunities if symbol.upper() in opp.get("symbol", "").upper()]
            if not all_opportunities:
                print(f"Не знайдено можливостей для символу {symbol}")
                return
        
        # Фільтруємо за мінімальним прибутком, якщо вказано
        if min_profit is not None:
            all_opportunities = [opp for opp in all_opportunities if opp.get("net_profit_percent", 0) >= min_profit]
            if not all_opportunities:
                print(f"Не знайдено можливостей з чистим прибутком >= {min_profit}%")
                return
        
        # Сортуємо за чистим прибутком
        all_opportunities.sort(key=lambda x: x.get("net_profit_percent", 0), reverse=True)
        
        # Виводимо статистику
        print(f"===== АНАЛІЗ АРБІТРАЖНИХ МОЖЛИВОСТЕЙ =====")
        print(f"Дата: {target_date.strftime('%Y-%m-%d')}")
        print(f"Кількість файлів: {len(files)}")
        print(f"Всього можливостей: {len(all_opportunities)}")
        
        # Групуємо за символами
        symbols = {}
        for opp in all_opportunities:
            symbol = opp.get("symbol", "невідомо")
            if symbol not in symbols:
                symbols[symbol] = []
            symbols[symbol].append(opp)
        
        print(f"\n== Статистика за символами ==")
        for symbol, opps in sorted(symbols.items(), key=lambda x: len(x[1]), reverse=True):
            max_profit = max([opp.get("net_profit_percent", 0) for opp in opps])
            avg_profit = sum([opp.get("net_profit_percent", 0) for opp in opps]) / len(opps)
            print(f"{symbol}: {len(opps)} можливостей, макс. прибуток {max_profit:.4f}%, сер. прибуток {avg_profit:.4f}%")
        
        # Виводимо топ-10 можливостей за чистим прибутком
        print(f"\n== Топ-10 можливостей за чистим прибутком ==")
        for i, opp in enumerate(all_opportunities[:10], 1):
            symbol = opp.get("symbol", "невідомо")
            buy_exchange = opp.get("buy_exchange", "невідомо")
            sell_exchange = opp.get("sell_exchange", "невідомо")
            profit = opp.get("profit_percent", 0)
            net_profit = opp.get("net_profit_percent", 0)
            timestamp = datetime.fromisoformat(opp.get("file_timestamp", "").replace("Z", "+00:00"))
            
            print(f"{i}. {symbol}: {buy_exchange} → {sell_exchange}, "
                  f"Брутто: {profit:.4f}%, Нетто: {net_profit:.4f}%, "
                  f"Час: {timestamp.strftime('%H:%M:%S')}")
        
        # Перевіряємо, чи є можливості з прибутком > 0.5%
        profitable_opps = [opp for opp in all_opportunities if opp.get("net_profit_percent", 0) >= 0.5]
        if profitable_opps:
            print(f"\n== Можливості з чистим прибутком >= 0.5% ==")
            for i, opp in enumerate(profitable_opps[:10], 1):
                symbol = opp.get("symbol", "невідомо")
                buy_exchange = opp.get("buy_exchange", "невідомо")
                sell_exchange = opp.get("sell_exchange", "невідомо")
                profit = opp.get("profit_percent", 0)
                net_profit = opp.get("net_profit_percent", 0)
                
                print(f"{i}. {symbol}: {buy_exchange} → {sell_exchange}, "
                      f"Брутто: {profit:.4f}%, Нетто: {net_profit:.4f}%")
        else:
            print(f"\nНе знайдено можливостей з чистим прибутком >= 0.5%")
    
    except Exception as e:
        print(f"Помилка при аналізі можливостей: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Парсимо аргументи командного рядка
    days_ago = 0
    min_profit = None
    symbol = None
    
    if len(sys.argv) > 1:
        try:
            days_ago = int(sys.argv[1])
        except ValueError:
            print(f"Помилка: перший аргумент має бути числом (кількість днів назад)")
            sys.exit(1)
    
    if len(sys.argv) > 2:
        try:
            min_profit = float(sys.argv[2])
        except ValueError:
            symbol = sys.argv[2]
    
    if len(sys.argv) > 3:
        symbol = sys.argv[3]
    
    analyze_opportunities(days_ago, min_profit, symbol)
