# web_server.py
from aiohttp import web
import json
import asyncio
import os
import logging
from datetime import datetime
import traceback

import config
from arbitrage.pair_analyzer import ArbitragePairAnalyzer

logger = logging.getLogger('main')

class WebDashboard:
    """
    Клас для веб-інтерфейсу моніторингу бота
    """
    def __init__(self, host=config.WEB_SERVER_HOST, port=config.WEB_SERVER_PORT):
        self.host = host
        self.port = port
        self.app = web.Application()
        self.site = None
        self.runner = None
        
        # Налаштовуємо маршрути
        self.app.router.add_get('/', self.index_handler)
        self.app.router.add_get('/api/status', self.status_handler)
        self.app.router.add_get('/api/opportunities', self.opportunities_handler)
        self.app.router.add_get('/api/stats', self.stats_handler)
        
        # Додаємо обробку статичних файлів
        self.app.router.add_static('/static/', path=os.path.join(os.path.dirname(__file__), 'static'), name='static')
        
    async def start(self):
        """
        Запускає веб-сервер
        """
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, self.host, self.port)
        await self.site.start()
        
        logger.info(f"Web server started at http://{self.host}:{self.port}")
        
    async def stop(self):
        """
        Зупиняє веб-сервер
        """
        if self.site:
            await self.site.stop()
            
        if self.runner:
            await self.runner.cleanup()
            
        logger.info("Web server stopped")
        
    async def index_handler(self, request):
        """
        Головна сторінка з інформацією про стан бота
        """
        try:
            # Базовий HTML-шаблон
            html = f"""
            <!DOCTYPE html>
            <html lang="uk">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>{config.APP_NAME} - Панель керування</title>
                <style>
                    body {{
                        font-family: Arial, sans-serif;
                        line-height: 1.6;
                        margin: 0;
                        padding: 20px;
                        color: #333;
                        background-color: #f4f7f9;
                    }}
                    .container {{
                        max-width: 1200px;
                        margin: 0 auto;
                    }}
                    header {{
                        background-color: #2c3e50;
                        color: white;
                        padding: 10px 20px;
                        border-radius: 4px;
                        margin-bottom: 20px;
                    }}
                    header h1 {{
                        margin: 0;
                    }}
                    .card {{
                        background-color: white;
                        border-radius: 4px;
                        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
                        padding: 20px;
                        margin-bottom: 20px;
                    }}
                    .status-indicator {{
                        display: inline-block;
                        width: 12px;
                        height: 12px;
                        border-radius: 50%;
                        margin-right: 5px;
                    }}
                    .status-active {{
                        background-color: #2ecc71;
                    }}
                    .status-inactive {{
                        background-color: #e74c3c;
                    }}
                    table {{
                        width: 100%;
                        border-collapse: collapse;
                    }}
                    th, td {{
                        padding: 10px;
                        text-align: left;
                        border-bottom: 1px solid #ddd;
                    }}
                    th {{
                        background-color: #f2f2f2;
                    }}
                    .profit-high {{
                        color: #2ecc71;
                        font-weight: bold;
                    }}
                    .profit-medium {{
                        color: #f39c12;
                        font-weight: bold;
                    }}
                    .profit-low {{
                        color: #3498db;
                    }}
                    .footer {{
                        text-align: center;
                        margin-top: 40px;
                        color: #7f8c8d;
                        font-size: 0.9em;
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <header>
                        <h1>{config.APP_NAME} v{config.VERSION}</h1>
                    </header>
                    
                    <div class="card" id="status-card">
                        <h2>Статус системи</h2>
                        <div id="status-content">Завантаження...</div>
                    </div>
                    
                    <div class="card">
                        <h2>Поточні арбітражні можливості</h2>
                        <div id="opportunities-content">Завантаження...</div>
                    </div>
                    
                    <div class="card">
                        <h2>Статистика</h2>
                        <div id="stats-content">Завантаження...</div>
                    </div>
                    
                    <div class="footer">
                        &copy; {datetime.now().year} {config.APP_NAME} - Криптоарбітражний бот
                    </div>
                </div>
                
                <script>
                    // Функція для форматування дати
                    function formatDate(dateString) {{
                        const date = new Date(dateString);
                        return date.toLocaleString('uk-UA');
                    }}
                    
                    // Функція для форматування прибутку
                    function formatProfit(profit) {{
                        const profitNum = parseFloat(profit);
                        let profitClass = 'profit-low';
                        
                        if (profitNum >= 1.5) {{
                            profitClass = 'profit-high';
                        }} else if (profitNum >= 0.8) {{
                            profitClass = 'profit-medium';
                        }}
                        
                        return `<span class="${{profitClass}}">${{profitNum.toFixed(2)}}%</span>`;
                    }}
                    
                    // Завантаження даних про статус
                    fetch('/api/status')
                        .then(response => response.json())
                        .then(data => {{
                            let statusHtml = '';
                            
                            if (data.error) {{
                                statusHtml = `<p>Помилка: ${{data.error}}</p>`;
                            }} else {{
                                const statusClass = data.running ? 'status-active' : 'status-inactive';
                                const statusText = data.running ? 'Активний' : 'Зупинено';
                                
                                statusHtml = `
                                    <p><span class="status-indicator ${{statusClass}}"></span> <strong>Стан:</strong> ${{statusText}}</p>
                                    <p><strong>Остання перевірка:</strong> ${{formatDate(data.last_check)}}</p>
                                    <p><strong>Інтервал перевірки:</strong> ${{data.check_interval}}с ${{data.is_peak_time ? '(пікові години)' : ''}}</p>
                                    <p><strong>Знайдено можливостей:</strong> ${{data.opportunities_found}}</p>
                                `;
                            }}
                            
                            document.getElementById('status-content').innerHTML = statusHtml;
                        })
                        .catch(error => {{
                            document.getElementById('status-content').innerHTML = `<p>Помилка при завантаженні даних: ${{error}}</p>`;
                        }});
                    
                    // Завантаження даних про можливості
                    fetch('/api/opportunities')
                        .then(response => response.json())
                        .then(data => {{
                            let opportunitiesHtml = '';
                            
                            if (data.error) {{
                                opportunitiesHtml = `<p>Помилка: ${{data.error}}</p>`;
                            }} else if (data.opportunities && data.opportunities.length > 0) {{
                                opportunitiesHtml = `
                                    <table>
                                        <thead>
                                            <tr>
                                                <th>Тип</th>
                                                <th>Пара/Шлях</th>
                                                <th>Біржі</th>
                                                <th>Прибуток</th>
                                                <th>Чистий прибуток</th>
                                                <th>Час</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                `;
                                
                                data.opportunities.forEach(opp => {{
                                    let pairInfo = '';
                                    let exchangeInfo = '';
                                    
                                    if (opp.opportunity_type === 'triangular') {{
                                        pairInfo = opp.path ? opp.path.join(' → ') : 'невідомо';
                                        exchangeInfo = opp.buy_exchange;
                                    }} else {{
                                        pairInfo = opp.symbol;
                                        exchangeInfo = `${{opp.buy_exchange}} → ${{opp.sell_exchange}}`;
                                    }}
                                    
                                    opportunitiesHtml += `
                                        <tr>
                                            <td>${{opp.opportunity_type === 'triangular' ? 'Трикутний' : 'Крос-біржовий'}}</td>
                                            <td>${{pairInfo}}</td>
                                            <td>${{exchangeInfo}}</td>
                                            <td>${{formatProfit(opp.profit_percent)}}</td>
                                            <td>${{formatProfit(opp.net_profit_percent)}}</td>
                                            <td>${{formatDate(opp.timestamp)}}</td>
                                        </tr>
                                    `;
                                }});
                                
                                opportunitiesHtml += `
                                        </tbody>
                                    </table>
                                `;
                            }} else {{
                                opportunitiesHtml = `<p>На даний момент не знайдено арбітражних можливостей.</p>`;
                            }}
                            
                            document.getElementById('opportunities-content').innerHTML = opportunitiesHtml;
                        })
                        .catch(error => {{
                            document.getElementById('opportunities-content').innerHTML = `<p>Помилка при завантаженні даних: ${{error}}</p>`;
                        }});
                    
                    // Завантаження статистичних даних
                    fetch('/api/stats')
                        .then(response => response.json())
                        .then(data => {{
                            let statsHtml = '';
                            
                            if (data.error) {{
                                statsHtml = `<p>Помилка: ${{data.error}}</p>`;
                            }} else if (data.total_opportunities > 0) {{
                                statsHtml = `
                                    <p><strong>Всього можливостей:</strong> ${{data.total_opportunities}}</p>
                                    <p><strong>Середній чистий прибуток:</strong> ${{formatProfit(data.avg_profit)}}</p>
                                    <p><strong>Крос-біржових можливостей:</strong> ${{data.cross_count}}</p>
                                    <p><strong>Трикутних можливостей:</strong> ${{data.triangular_count}}</p>
                                    
                                    <h3>Найкращі крос-біржові пари</h3>
                                `;
                                
                                if (data.top_cross && data.top_cross.length > 0) {{
                                    statsHtml += `
                                        <table>
                                            <thead>
                                                <tr>
                                                    <th>Пара</th>
                                                    <th>Біржі</th>
                                                    <th>Середній прибуток</th>
                                                    <th>Кількість</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                    `;
                                    
                                    data.top_cross.forEach(stats => {{
                                        statsHtml += `
                                            <tr>
                                                <td>${{stats.symbol}}</td>
                                                <td>${{stats.buy_exchange}} → ${{stats.sell_exchange}}</td>
                                                <td>${{formatProfit(stats.avg_net_profit)}}</td>
                                                <td>${{stats.count}}</td>
                                            </tr>
                                        `;
                                    }});
                                    
                                    statsHtml += `
                                            </tbody>
                                        </table>
                                    `;
                                }} else {{
                                    statsHtml += `<p>Немає даних про крос-біржові пари.</p>`;
                                }}
                                
                                statsHtml += `<h3>Найкращі трикутні шляхи</h3>`;
                                
                                if (data.top_triangular && data.top_triangular.length > 0) {{
                                    statsHtml += `
                                        <table>
                                            <thead>
                                                <tr>
                                                    <th>Біржа</th>
                                                    <th>Шлях</th>
                                                    <th>Середній прибуток</th>
                                                    <th>Кількість</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                    `;
                                    
                                    data.top_triangular.forEach(stats => {{
                                        const pathStr = stats.path ? stats.path.join(' → ') : 'невідомо';
                                        
                                        statsHtml += `
                                            <tr>
                                                <td>${{stats.exchange}}</td>
                                                <td>${{pathStr}}</td>
                                                <td>${{formatProfit(stats.avg_net_profit)}}</td>
                                                <td>${{stats.count}}</td>
                                            </tr>
                                        `;
                                    }});
                                    
                                    statsHtml += `
                                            </tbody>
                                        </table>
                                    `;
                                }} else {{
                                    statsHtml += `<p>Немає даних про трикутні шляхи.</p>`;
                                }}
                            }} else {{
                                statsHtml = `<p>Поки що немає даних для статистики.</p>`;
                            }}
                            
                            document.getElementById('stats-content').innerHTML = statsHtml;
                        })
                        .catch(error => {{
                            document.getElementById('stats-content').innerHTML = `<p>Помилка при завантаженні даних: ${{error}}</p>`;
                        }});
                        
                    // Оновлення даних кожні 30 секунд
                    setInterval(() => {{
                        fetch('/api/status')
                            .then(response => response.json())
                            .then(data => {{
                                // ... оновлення статусу
                            }})
                            .catch(error => console.error('Помилка при оновленні статусу:', error));
                            
                        fetch('/api/opportunities')
                            .then(response => response.json())
                            .then(data => {{
                                // ... оновлення можливостей
                            }})
                            .catch(error => console.error('Помилка при оновленні можливостей:', error));
                    }}, 30000);
                </script>
            </body>
            </html>
            """
            
            return web.Response(text=html, content_type='text/html')
        except Exception as e:
            logger.error(f"Помилка при обробці index_handler: {e}")
            traceback.print_exc()
            return web.json_response({"error": str(e)})
    
    async def status_handler(self, request):
        """
        API для отримання поточного статусу бота
        """
        try:
            if os.path.exists("status.json"):
                with open("status.json", "r") as f:
                    status_data = json.load(f)
                return web.json_response(status_data)
            else:
                return web.json_response({"error": "Файл статусу не знайдено"})
        except Exception as e:
            logger.error(f"Помилка при обробці status_handler: {e}")
            return web.json_response({"error": str(e)})
    
    async def opportunities_handler(self, request):
        """
        API для отримання поточних арбітражних можливостей
        """
        try:
            if os.path.exists("status.json"):
                with open("status.json", "r") as f:
                    status_data = json.load(f)
                
                opportunities = status_data.get("top_opportunities", [])
                return web.json_response({"opportunities": opportunities})
            else:
                return web.json_response({"error": "Файл статусу не знайдено"})
        except Exception as e:
            logger.error(f"Помилка при обробці opportunities_handler: {e}")
            return web.json_response({"error": str(e)})
    
    async def stats_handler(self, request):
        """
        API для отримання статистики арбітражу
        """
        try:
            analyzer = ArbitragePairAnalyzer()
            
            # Загальна статистика
            total_opportunities = sum(stats.get('count', 0) for stats in analyzer.pair_stats.values())
            
            if total_opportunities > 0:
                avg_profit = sum(stats.get('total_net_profit', 0) for stats in analyzer.pair_stats.values()) / total_opportunities
                
                # Статистика за типами
                cross_count = sum(1 for stats in analyzer.pair_stats.values() if stats.get('opportunity_type') == 'cross')
                triangular_count = sum(1 for stats in analyzer.pair_stats.values() if stats.get('opportunity_type') == 'triangular')
                
                # Найкращі пари/шляхи
                top_cross = analyzer.get_top_pairs(5, "cross")
                top_triangular = analyzer.get_top_pairs(5, "triangular")
                
                return web.json_response({
                    "total_opportunities": total_opportunities,
                    "avg_profit": avg_profit,
                    "cross_count": cross_count,
                    "triangular_count": triangular_count,
                    "top_cross": top_cross,
                    "top_triangular": top_triangular
                })
            else:
                return web.json_response({
                    "total_opportunities": 0,
                    "error": "Немає даних для статистики"
                })
        except Exception as e:
            logger.error(f"Помилка при обробці stats_handler: {e}")
            return web.json_response({"error": str(e)})

# Функція для запуску веб-сервера
async def start_web_server():
    """
    Запускає веб-сервер для моніторингу
    """
    if config.WEB_SERVER_ENABLED:
        dashboard = WebDashboard()
        await dashboard.start()
        return dashboard
    return None
