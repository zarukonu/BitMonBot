# check_pairs.py
import asyncio
import logging
import sys
from datetime import datetime
import json
import os

import config
from exchange_api.factory import ExchangeFactory

# Налаштування логування
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('check_pairs')

async def check_pairs_availability():
    """
    Перевіряє доступність валютних пар на біржах
    """
    try:
        exchange_names = ['binance', 'kucoin', 'kraken']
        pairs_to_check = config.ALL_PAIRS
        
        logger.info(f"Перевірка доступності {len(pairs_to_check)} пар на {len(exchange_names)} біржах")
        
        exchanges = {}
        for name in exchange_names:
            try:
                exchanges[name] = ExchangeFactory.create(name)
                logger.info(f"Ініціалізовано біржу {name}")
            except Exception as e:
                logger.error(f"Помилка при ініціалізації біржі {name}: {e}")
        
        # Перевіряємо доступність пар на біржах
        results = {}
        for exchange_name, exchange in exchanges.items():
            exchange_results = {}
            for pair in pairs_to_check:
                try:
                    ticker = await exchange.get_ticker(pair)
                    if ticker and 'bid' in ticker and 'ask' in ticker:
                        bid = ticker['bid']
                        ask = ticker['ask']
                        if bid is not None and ask is not None:
                            exchange_results[pair] = {
                                'bid': bid,
                                'ask': ask,
                                'available': True
                            }
                        else:
                            exchange_results[pair] = {
                                'bid': bid,
                                'ask': ask,
                                'available': False,
                                'reason': 'Bid or ask is None'
                            }
                    else:
                        exchange_results[pair] = {
                            'available': False,
                            'reason': 'Invalid ticker data'
                        }
                except Exception as e:
                    exchange_results[pair] = {
                        'available': False,
                        'reason': str(e)
                    }
            
            results[exchange_name] = exchange_results
            
            # Підрахунок доступних пар
            available_pairs = [pair for pair, data in exchange_results.items() if data['available']]
            logger.info(f"Біржа {exchange_name}: Доступно {len(available_pairs)}/{len(pairs_to_check)} пар")
            
            # Виведення доступних пар
            if available_pairs:
                logger.info(f"Біржа {exchange_name}: Доступні пари: {', '.join(available_pairs)}")
                
            # Виведення недоступних пар
            unavailable_pairs = [pair for pair, data in exchange_results.items() if not data['available']]
            if unavailable_pairs:
                logger.info(f"Біржа {exchange_name}: Недоступні пари: {', '.join(unavailable_pairs)}")
                for pair in unavailable_pairs:
                    logger.info(f"  {pair}: {exchange_results[pair]['reason']}")
        
        # Виведення пар, доступних на всіх біржах
        pairs_available_everywhere = []
        for pair in pairs_to_check:
            available_on_all = all(
                pair in results[exchange] and results[exchange][pair]['available'] 
                for exchange in exchange_names
            )
            if available_on_all:
                pairs_available_everywhere.append(pair)
        
        logger.info(f"Пари, доступні на всіх біржах ({len(pairs_available_everywhere)}/{len(pairs_to_check)}): {', '.join(pairs_available_everywhere)}")
        
        # Виведення пар, доступних щонайменше на двох біржах
        pairs_available_on_two = []
        for pair in pairs_to_check:
            count = sum(
                1 for exchange in exchange_names 
                if pair in results[exchange] and results[exchange][pair]['available']
            )
            if count >= 2:
                pairs_available_on_two.append(pair)
        
        logger.info(f"Пари, доступні щонайменше на двох біржах ({len(pairs_available_on_two)}/{len(pairs_to_check)}): {', '.join(pairs_available_on_two)}")
        
        # Збереження результатів у JSON файл
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"data/pairs_check_{timestamp}.json"
        os.makedirs("data", exist_ok=True)
        
        with open(filename, "w") as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "results": results,
                "pairs_available_everywhere": pairs_available_everywhere,
                "pairs_available_on_two": pairs_available_on_two
            }, f, indent=2)
            
        logger.info(f"Результати збережено у файл {filename}")
        
        # Виведення рекомендацій
        print("\n=== РЕКОМЕНДАЦІЇ ===")
        if len(pairs_available_on_two) < len(pairs_to_check):
            print(f"Деякі пари недоступні щонайменше на двох біржах. Рекомендується оновити config.py:")
            print("PAIRS = [")
            for pair in pairs_available_on_two:
                print(f'    "{pair}",')
            print("]")
    
    except Exception as e:
        logger.error(f"Помилка при перевірці пар: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Закриваємо з'єднання з біржами
        for name, exchange in exchanges.items():
            try:
                await exchange.close()
                logger.info(f"Закрито з'єднання з біржею {name}")
            except Exception as e:
                logger.error(f"Помилка при закритті з'єднання з біржею {name}: {e}")

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(check_pairs_availability())
    loop.close()
