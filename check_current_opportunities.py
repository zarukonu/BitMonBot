# check_current_opportunities.py
import os
import json
from datetime import datetime

def check_current_opportunities():
    """
    Перевіряє поточний стан арбітражних можливостей
    """
    try:
        # Перевіряємо файл статусу
        if os.path.exists("status.json"):
            with open("status.json", "r") as f:
                status = json.load(f)
                
            last_check = datetime.fromisoformat(status.get("last_check", "").replace("Z", "+00:00"))
            now = datetime.now()
            seconds_ago = (now - last_check).total_seconds()
            
            print(f"===== ПОТОЧНИЙ СТАН АРБІТРАЖНИХ МОЖЛИВОСТЕЙ =====")
            print(f"Остання перевірка: {last_check.strftime('%Y-%m-%d %H:%M:%S')} ({int(seconds_ago)} секунд тому)")
            print(f"Знайдено можливостей: {status.get('opportunities_found', 0)}")
            print(f"Крос-біржових: {status.get('cross_opportunities', 0)}")
            print(f"Трикутних: {status.get('triangular_opportunities', 0)}")
            print(f"Бот запущено: {'Так' if status.get('running', False) else 'Ні'}")
            print(f"Врахування комісій: {'Ввімкнено' if status.get('include_fees', False) else 'Вимкнено'}")
            
            # Виводимо топ-можливості
            opportunities = status.get("top_opportunities", [])
            if opportunities:
                print(f"\n== Поточні знайдені можливості ({len(opportunities)}) ==")
                for i, opp in enumerate(opportunities, 1):
                    if opp.get("opportunity_type") == "triangular":
                        path = " → ".join(opp.get("path", []))
                        print(f"{i}. ТРИКУТНА: {path} на {opp.get('buy_exchange')}")
                    else:
                        print(f"{i}. КРОС-БІРЖОВА: {opp.get('symbol')} - "
                              f"{opp.get('buy_exchange')} → {opp.get('sell_exchange')}")
                    
                    print(f"   Прибуток (брутто): {opp.get('profit_percent', 0):.4f}%")
                    if "net_profit_percent" in opp:
                        print(f"   Прибуток (нетто): {opp.get('net_profit_percent', 0):.4f}%")
                    print()
            else:
                print("\nНе знайдено жодної арбітражної можливості в останньому циклі.")
            
            # Перевіряємо лог всіх можливостей
            print("\n== Перевірка логу всіх можливостей ==")
            all_opps_log = "logs/all_opportunities.log"
            if os.path.exists(all_opps_log):
                # Читаємо останні 10 рядків
                with open(all_opps_log, "r") as f:
                    lines = f.readlines()
                    last_lines = lines[-20:]  # Останні 20 рядків
                    
                    if not last_lines:
                        print("Лог порожній.")
                    else:
                        # Знаходимо останню секцію звіту
                        report_indices = [i for i, line in enumerate(last_lines) if "===== ЗВІТ ПРО ВСІ МОЖЛИВОСТІ" in line]
                        if report_indices:
                            last_report_index = report_indices[-1]
                            report_lines = last_lines[last_report_index:]
                            print("".join(report_lines))
                        else:
                            print("Не знайдено повного звіту в останніх рядках логу.")
            else:
                print(f"Файл {all_opps_log} не існує. Можливо, ще не було знайдено жодної можливості.")
                
            # Перевіряємо дані за останню годину
            print("\n== Дані за останню годину ==")
            current_hour = datetime.now().strftime('%Y%m%d_%H')
            recent_files = [f for f in os.listdir("data") if f.startswith(f"opportunities_{current_hour}")]
            
            if recent_files:
                print(f"Знайдено {len(recent_files)} файлів з даними за останню годину.")
                
                # Беремо останній файл
                latest_file = sorted(recent_files)[-1]
                with open(os.path.join("data", latest_file), "r") as f:
                    data = json.load(f)
                    
                opportunities = data.get("opportunities", [])
                if opportunities:
                    print(f"Останній файл містить {len(opportunities)} можливостей.")
                    
                    # Фільтруємо можливості з прибутком > 0.2%
                    profitable = [o for o in opportunities if o.get("net_profit_percent", 0) > 0.2]
                    if profitable:
                        print(f"Знайдено {len(profitable)} можливостей з чистим прибутком > 0.2%:")
                        
                        # Сортуємо за прибутком
                        profitable.sort(key=lambda x: x.get("net_profit_percent", 0), reverse=True)
                        
                        # Виводимо топ-5
                        for i, opp in enumerate(profitable[:5], 1):
                            print(f"{i}. {opp.get('symbol')}: {opp.get('buy_exchange')} → {opp.get('sell_exchange')}, "
                                  f"Нетто: {opp.get('net_profit_percent', 0):.4f}%")
                    else:
                        print("Не знайдено можливостей з чистим прибутком > 0.2%")
                else:
                    print("Файл не містить можливостей.")
            else:
                print("Не знайдено файлів з даними за останню годину.")
        else:
            print("Файл status.json не знайдено. Бот може не бути запущеним.")
    
    except Exception as e:
        print(f"Помилка при перевірці поточного стану: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_current_opportunities()
