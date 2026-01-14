# 正确的涨停统计逻辑：先获取8天数据，统计每日涨停，再找共同出现的股票
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import akshare as ak

# 全局变量定义
MIN_LIMIT_UP_DAYS = 3
_market_data_cache = None


def get_today_limit_up_pool():
    """获取今天涨停股池数据"""
    try:
        today = datetime.now().strftime('%Y%m%d')
        df = ak.stock_zt_pool_em(date=today)
        print(f"成功获取今天涨停股池数据，共 {len(df)} 只股票")
        return df
    except Exception as e:
        print(f"获取今天涨停股池失败: {e}")
        return pd.DataFrame()


def get_yesterday_limit_up_pool():
    """获取昨日涨停股池数据"""
    try:
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')
        df = ak.stock_zt_pool_previous_em(date=yesterday)
        print(f"成功获取昨日涨停股池数据，共 {len(df)} 只股票")
        return df
    except Exception as e:
        print(f"获取昨日涨停股池失败: {e}")
        return pd.DataFrame()


def generate_limit_up_pool_html(today_pool, yesterday_pool):
    """生成涨停股池HTML报告"""
    today_str = datetime.now().strftime('%Y-%m-%d')
    yesterday_str = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    
    def format_time(time_str):
        """将时间格式从HHMMSS转换为HH:MM"""
        if pd.isna(time_str) or time_str == '':
            return ''
        try:
            time_str = str(time_str)
            if len(time_str) >= 4:
                return f"{time_str[:2]}:{time_str[2:4]}"
            return time_str
        except:
            return str(time_str)
    
    html = f"""
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>涨停股池数据</title>
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
                font-family: 'Microsoft YaHei', 'PingFang SC', sans-serif;
            }}
            body {{
                font-family: 'Microsoft YaHei', 'PingFang SC', sans-serif;
                background: linear-gradient(135deg, #2c3e50 0%, #34495e 100%);
                min-height: 100vh;
                padding: 20px;
            }}
            .header {{
                text-align: center;
                margin-bottom: 30px;
                color: white;
            }}
            h1 {{
                font-size: 2.5rem;
                font-weight: 700;
                margin-bottom: 10px;
                text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
            }}
            .subtitle {{
                font-size: 1.1rem;
                color: rgba(255,255,255,0.9);
            }}
            .refresh-btn {{
                display: block;
                margin: 0 auto 30px;
                padding: 12px 30px;
                background: rgba(255,255,255,0.2);
                color: white;
                border: 2px solid white;
                border-radius: 8px;
                cursor: pointer;
                font-size: 16px;
                font-weight: 600;
                transition: all 0.3s ease;
            }}
            .refresh-btn:hover {{
                background: rgba(255,255,255,0.3);
                transform: translateY(-2px);
            }}
            .container {{
                display: flex;
                flex-direction: column;
                gap: 25px;
                max-width: 95%;
                margin: 0 auto;
                width: 100%;
            }}
            .section {{
                background: white;
                border-radius: 12px;
                box-shadow: 0 8px 32px rgba(0,0,0,0.1);
                padding: 25px;
                transition: all 0.3s ease;
            }}
            .section:hover {{
                box-shadow: 0 12px 40px rgba(0,0,0,0.15);
            }}
            h2 {{
                color: #2c3e50;
                margin-bottom: 20px;
                font-size: 1.5rem;
                font-weight: 600;
                border-bottom: 3px solid #7f8c8d;
                padding-bottom: 10px;
            }}
            .table-container {{
                max-height: 600px;
                overflow-x: auto;
                overflow-y: auto;
                border-radius: 8px;
                border: 1px solid #e0e0e0;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                min-width: 1000px;
            }}
            th {{
                background: linear-gradient(135deg, #2c3e50 0%, #34495e 100%);
                color: white;
                padding: 12px 10px;
                text-align: center;
                font-weight: 600;
                position: sticky;
                top: 0;
                z-index: 10;
                font-size: 13px;
                white-space: nowrap;
            }}
            td {{
                padding: 10px;
                text-align: center;
                border-bottom: 1px solid #f0f0f0;
                color: #333;
                font-size: 13px;
            }}
            tr:hover {{
                background-color: #f8f9fa;
                transition: all 0.2s ease;
            }}
            tr:nth-child(even) {{
                background-color: #fafafa;
            }}
            .positive {{
                color: #e74c3c;
                font-weight: 600;
            }}
            .negative {{
                color: #27ae60;
                font-weight: 600;
            }}
            .highlight {{
                background: linear-gradient(135deg, #2c3e5015 0%, #34495e15 100%) !important;
            }}
            /* Scrollbar styling */
            .table-container::-webkit-scrollbar {{
                width: 8px;
            }}
            .table-container::-webkit-scrollbar-track {{
                background: #f1f1f1;
                border-radius: 4px;
            }}
            .table-container::-webkit-scrollbar-thumb {{
                background: #7f8c8d;
                border-radius: 4px;
            }}
            .table-container::-webkit-scrollbar-thumb:hover {{
                background: #5a6c7d;
                border-radius: 4px;
                transition: background 0.2s ease;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🚀 涨停股池数据</h1>
            <p class="subtitle">实时更新的涨停板行情数据</p>
        </div>
        <button class="refresh-btn" onclick="location.reload()">🔄 刷新数据</button>
        <div class="container">
            <div class="section">
                <h2>📈 今天涨停股池 - {today_str} <span style="font-size: 0.8em; color: #666;">(共 {len(today_pool)} 只)</span></h2>
                <div class="table-container">
                    <table>
                        <tr>
                            <th>序号</th>
                            <th>代码</th>
                            <th>名称</th>
                            <th>涨跌幅(%)</th>
                            <th>最新价</th>
                            <th>成交额(亿)</th>
                            <th>流通市值(亿)</th>
                            <th>总市值(亿)</th>
                            <th>换手率(%)</th>
                            <th>封板资金(亿)</th>
                            <th>首次封板时间</th>
                            <th>最后封板时间</th>
                            <th>炸板次数</th>
                            <th>涨停统计</th>
                            <th>连板数</th>
                            <th>所属行业</th>
                        </tr>
    """
    
    if not today_pool.empty:
        for _, row in today_pool.iterrows():
            change_class = 'positive' if row['涨跌幅'] > 0 else 'negative'
            html += f"""
                        <tr>
                            <td>{int(row['序号'])}</td>
                            <td>{row['代码']}</td>
                            <td>{row['名称']}</td>
                            <td class="{change_class}">{row['涨跌幅']:.2f}</td>
                            <td>{row['最新价']:.2f}</td>
                            <td>{row['成交额']/100000000:.2f}</td>
                            <td>{row['流通市值']/100000000:.2f}</td>
                            <td>{row['总市值']/100000000:.2f}</td>
                            <td>{row['换手率']:.2f}</td>
                            <td>{row['封板资金']/100000000:.2f}</td>
                            <td>{format_time(row['首次封板时间'])}</td>
                            <td>{format_time(row['最后封板时间'])}</td>
                            <td>{int(row['炸板次数'])}</td>
                            <td>{row['涨停统计']}</td>
                            <td>{int(row['连板数'])}</td>
                            <td>{row['所属行业']}</td>
                        </tr>
            """
    else:
        html += """
                        <tr>
                            <td colspan="16" style="text-align: center; padding: 20px; color: #999;">暂无数据</td>
                        </tr>
        """
    
    html += """
                    </table>
                </div>
            </div>
            <div class="section">
                <h2>📊 昨日涨停股池 - """ + yesterday_str + """ <span style="font-size: 0.8em; color: #666;">(共 """ + str(len(yesterday_pool)) + """ 只)</span></h2>
                <div class="table-container">
                    <table>
                        <tr>
                            <th>序号</th>
                            <th>代码</th>
                            <th>名称</th>
                            <th>涨跌幅(%)</th>
                            <th>最新价</th>
                            <th>涨停价</th>
                            <th>成交额(亿)</th>
                            <th>流通市值(亿)</th>
                            <th>总市值(亿)</th>
                            <th>换手率(%)</th>
                            <th>涨速(%)</th>
                            <th>振幅(%)</th>
                            <th>昨日封板时间</th>
                            <th>昨日连板数</th>
                            <th>涨停统计</th>
                            <th>所属行业</th>
                        </tr>
    """
    
    if not yesterday_pool.empty:
        for _, row in yesterday_pool.iterrows():
            change_class = 'positive' if row['涨跌幅'] > 0 else 'negative'
            html += f"""
                        <tr>
                            <td>{int(row['序号'])}</td>
                            <td>{row['代码']}</td>
                            <td>{row['名称']}</td>
                            <td class="{change_class}">{row['涨跌幅']:.2f}</td>
                            <td>{row['最新价']:.2f}</td>
                            <td>{row['涨停价']:.2f}</td>
                            <td>{row['成交额']/100000000:.2f}</td>
                            <td>{row['流通市值']/100000000:.2f}</td>
                            <td>{row['总市值']/100000000:.2f}</td>
                            <td>{row['换手率']:.2f}</td>
                            <td>{row['涨速']:.2f}</td>
                            <td>{row['振幅']:.2f}</td>
                            <td>{format_time(row['昨日封板时间'])}</td>
                            <td>{int(row['昨日连板数'])}</td>
                            <td>{row['涨停统计']}</td>
                            <td>{row['所属行业']}</td>
                        </tr>
            """
    else:
        html += """
                        <tr>
                            <td colspan="16" style="text-align: center; padding: 20px; color: #999;">暂无数据</td>
                        </tr>
        """
    
    html += """
                    </table>
                </div>
            </div>
        </div>
    </body>
</html>
    """
    
    return html


def generate_html_report(yesterday_limit_up, before_yesterday_limit_up, breakout_stocks, yesterday, before_yesterday):
    """生成HTML报告"""
    
    # 获取一进二打板策略选中的股票代码列表
    breakout_codes = set()
    if not breakout_stocks.empty:
        breakout_codes = set(breakout_stocks['股票代码'].tolist())
    
    # 创建一进二打板股票信息字典
    breakout_info = {}
    if not breakout_stocks.empty:
        for _, stock in breakout_stocks.iterrows():
            breakout_info[stock['股票代码']] = {
                '换手率(%)': stock['换手率(%)'],
                '流通盘(亿)': stock['流通盘(亿)'],
                '行业板块': stock['行业板块'],
                '封板时间': stock['封板时间'],
                '是否开板': stock['是否开板'],
                '主力净买入(万元)': stock['主力净买入(万元)']
            }
    
    html = """
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>涨停股票数据</title>
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
                font-family: 'Microsoft YaHei', 'PingFang SC', sans-serif;
            }}
            body {{
                font-family: 'Microsoft YaHei', 'PingFang SC', sans-serif;
                background: #f5f5f7;
                min-height: 100vh;
                padding: 20px;
            }}
            .header {{
                text-align: center;
                margin-bottom: 30px;
                color: #333;
            }}
            h1 {{
                font-size: 2.5rem;
                font-weight: 700;
                margin-bottom: 10px;
                color: #2c3e50;
            }}
            .subtitle {{
                font-size: 1.1rem;
                color: #666;
            }}
            .refresh-btn {{
                display: block;
                margin: 0 auto 30px;
                padding: 12px 30px;
                background: #34495e;
                color: white;
                border: none;
                border-radius: 8px;
                cursor: pointer;
                font-size: 16px;
                font-weight: 600;
                transition: all 0.3s ease;
            }}
            .refresh-btn:hover {{
                background: #2c3e50;
                transform: translateY(-2px);
            }}
            .container {{
                display: flex;
                flex-direction: column;
                gap: 25px;
                max-width: 95%;
                margin: 0 auto;
                width: 100%;
            }}
            .section {{
                background: white;
                border-radius: 12px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.08);
                padding: 25px;
                transition: all 0.3s ease;
            }}
            .section:hover {{
                box-shadow: 0 8px 20px rgba(0,0,0,0.12);
            }}
            h2 {{
                color: #2c3e50;
                margin-bottom: 20px;
                font-size: 1.5rem;
                font-weight: 600;
                border-bottom: 2px solid #e0e0e0;
                padding-bottom: 10px;
            }}
            .table-container {{
                max-height: 600px;
                overflow-x: auto;
                overflow-y: auto;
                border-radius: 8px;
                border: 1px solid #e0e0e0;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                min-width: 800px;
            }}
            th {{
                background: #f8f9fa;
                color: #2c3e50;
                padding: 10px 12px;
                text-align: left;
                font-weight: 600;
                position: sticky;
                top: 0;
                z-index: 10;
                border-bottom: 2px solid #e0e0e0;
                font-size: 13px;
                white-space: nowrap;
            }}
            td {{
                padding: 10px 12px;
                text-align: left;
                border-bottom: 1px solid #f0f0f0;
                color: #333;
                font-size: 13px;
            }}
            tr:hover {{
                background-color: #f8f9fa;
                transition: all 0.2s ease;
            }}
            tr:nth-child(even) {{
                background-color: #fafafa;
            }}
            tr.breakout-stock {{
                background: linear-gradient(135deg, #667eea15 0%, #764ba215 100%) !important;
                border-left: 4px solid #667eea;
            }}
            tr.breakout-stock:hover {{
                background: linear-gradient(135deg, #667eea25 0%, #764ba225 100%) !important;
            }}
            tr.breakout-stock td {{
                font-weight: 600;
            }}
            .breakout-tag {{
                display: inline-block;
                padding: 4px 8px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border-radius: 4px;
                font-size: 0.85em;
                font-weight: 600;
            }}
            /* Scrollbar styling */
            .table-container::-webkit-scrollbar {{
                width: 8px;
            }}
            .table-container::-webkit-scrollbar-track {{
                background: #f1f1f1;
                border-radius: 4px;
            }}
            .table-container::-webkit-scrollbar-thumb {{
                background: #bdc3c7;
                border-radius: 4px;
            }}
            .table-container::-webkit-scrollbar-thumb:hover {{
                background: #7f8c8d;
                border-radius: 4px;
                transition: background 0.2s ease;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>A股涨停股票数据</h1>
            <p class="subtitle">实时更新的涨停板数据统计 <span style="font-size: 0.9em; color: #667eea; font-weight: 600;">(一进二打板策略选中 {breakout_count} 只)</span></p>
        </div>
        <button class="refresh-btn" onclick="location.reload()">🔄 刷新数据</button>
        <div class="container">
            <div class="section">
                <h2>📈 最近一个交易日涨停股票 - {yesterday_str} <span style="font-size: 0.8em; color: #666;">(共 {yesterday_count} 只)</span></h2>
                <div class="table-container">
                    <table>
                        <tr>
                            <th>股票代码</th>
                            <th>股票名称</th>
                            <th>收盘价</th>
                            <th>涨跌幅(%)</th>
                            <th>成交量</th>
                            <th>成交额(万元)</th>
                            <th>换手率(%)</th>
                            <th>流通盘(亿)</th>
                            <th>行业板块</th>
                            <th>封板时间</th>
                            <th>是否开板</th>
                            <th>主力净买入(万元)</th>
                        </tr>
        """.format(breakout_count=len(breakout_codes), yesterday_str=yesterday.strftime('%Y-%m-%d') if yesterday else '日期获取失败', yesterday_count=len(yesterday_limit_up))
    
    # 获取股票名称映射
    stocks = get_all_securities()
    stock_name_map = dict(zip(stocks['code'], stocks['name']))
    
    # 为昨天的股票获取换手率和流通盘数据
    yesterday_stock_info = {}
    for stock in yesterday_limit_up:
        stock_code = stock['股票代码']
        try:
            turnover_data = get_valuation(stock_code, end_date=yesterday, count=1, fields=['turnover_ratio', 'circulating_market_cap'])
            if not turnover_data.empty:
                turnover_ratio = turnover_data['turnover_ratio'].iloc[0]
                market_cap = turnover_data['circulating_market_cap'].iloc[0] / 100000000
                yesterday_stock_info[stock_code] = {
                    '换手率(%)': turnover_ratio,
                    '流通盘(亿)': round(market_cap, 2)
                }
        except Exception as e:
            print(f"获取股票 {stock_code} 数据时出错: {e}")
            yesterday_stock_info[stock_code] = {
                '换手率(%)': '-',
                '流通盘(亿)': '-'
            }
    
    # 为前天的股票获取换手率和流通盘数据
    before_yesterday_stock_info = {}
    for stock in before_yesterday_limit_up:
        stock_code = stock['股票代码']
        try:
            turnover_data = get_valuation(stock_code, end_date=before_yesterday, count=1, fields=['turnover_ratio', 'circulating_market_cap'])
            if not turnover_data.empty:
                turnover_ratio = turnover_data['turnover_ratio'].iloc[0]
                market_cap = turnover_data['circulating_market_cap'].iloc[0] / 100000000
                before_yesterday_stock_info[stock_code] = {
                    '换手率(%)': turnover_ratio,
                    '流通盘(亿)': round(market_cap, 2)
                }
        except Exception as e:
            print(f"获取股票 {stock_code} 数据时出错: {e}")
            before_yesterday_stock_info[stock_code] = {
                '换手率(%)': '-',
                '流通盘(亿)': '-'
            }
    
    # 添加最近一个交易日的数据
    for stock in yesterday_limit_up:
        stock_code = stock['股票代码']
        is_breakout = stock_code in breakout_codes
        row_class = 'class="breakout-stock"' if is_breakout else ''
        breakout_tag = '<span class="breakout-tag">一进二</span>' if is_breakout else ''
        
        if is_breakout and stock_code in breakout_info:
            info = breakout_info[stock_code]
            html += f"""
                    <tr {row_class}>
                        <td>{stock_code}</td>
                        <td>{stock_name_map.get(stock_code, '')} {breakout_tag}</td>
                        <td>{stock['收盘价']}</td>
                        <td>{stock['涨跌幅(%)']}</td>
                        <td>{stock['成交量']}</td>
                        <td>{stock['成交额(万元)']}</td>
                        <td>{info['换手率(%)']}</td>
                        <td>{info['流通盘(亿)']}</td>
                        <td>{info['行业板块']}</td>
                        <td>{info['封板时间']}</td>
                        <td>{info['是否开板']}</td>
                        <td>{info['主力净买入(万元)']}</td>
                    </tr>
            """
        else:
            stock_info = yesterday_stock_info.get(stock_code, {'换手率(%)': '-', '流通盘(亿)': '-'})
            html += f"""
                    <tr {row_class}>
                        <td>{stock_code}</td>
                        <td>{stock_name_map.get(stock_code, '')} {breakout_tag}</td>
                        <td>{stock['收盘价']}</td>
                        <td>{stock['涨跌幅(%)']}</td>
                        <td>{stock['成交量']}</td>
                        <td>{stock['成交额(万元)']}</td>
                        <td>{stock_info['换手率(%)']}</td>
                        <td>{stock_info['流通盘(亿)']}</td>
                        <td>-</td>
                        <td>-</td>
                        <td>-</td>
                        <td>-</td>
                    </tr>
            """
        
    html += """
                </table>
            </div>
        </div>
            <div class="section">
                <h2>📊 前天涨停股票 - {before_yesterday_str} <span style="font-size: 0.8em; color: #666;">(共 {before_yesterday_count} 只)</span></h2>
                <div class="table-container">
                    <table>
                        <tr>
                            <th>股票代码</th>
                            <th>股票名称</th>
                            <th>收盘价</th>
                            <th>涨跌幅(%)</th>
                            <th>成交量</th>
                            <th>成交额(万元)</th>
                            <th>换手率(%)</th>
                            <th>流通盘(亿)</th>
                            <th>行业板块</th>
                            <th>封板时间</th>
                            <th>是否开板</th>
                            <th>主力净买入(万元)</th>
                        </tr>
        """.format(before_yesterday_str=before_yesterday.strftime('%Y-%m-%d') if before_yesterday else '日期获取失败', before_yesterday_count=len(before_yesterday_limit_up))
        
        # 添加前天的数据
    for stock in before_yesterday_limit_up:
        stock_code = stock['股票代码']
        is_breakout = stock_code in breakout_codes
        row_class = 'class="breakout-stock"' if is_breakout else ''
        breakout_tag = '<span class="breakout-tag">一进二</span>' if is_breakout else ''
        
        if is_breakout and stock_code in breakout_info:
            info = breakout_info[stock_code]
            html += f"""
                    <tr {row_class}>
                        <td>{stock_code}</td>
                        <td>{stock_name_map.get(stock_code, '')} {breakout_tag}</td>
                        <td>{stock['收盘价']}</td>
                        <td>{stock['涨跌幅(%)']}</td>
                        <td>{stock['成交量']}</td>
                        <td>{stock['成交额(万元)']}</td>
                        <td>{info['换手率(%)']}</td>
                        <td>{info['流通盘(亿)']}</td>
                        <td>{info['行业板块']}</td>
                        <td>{info['封板时间']}</td>
                        <td>{info['是否开板']}</td>
                        <td>{info['主力净买入(万元)']}</td>
                    </tr>
            """
        else:
            stock_info = before_yesterday_stock_info.get(stock_code, {'换手率(%)': '-', '流通盘(亿)': '-'})
            html += f"""
                    <tr {row_class}>
                        <td>{stock_code}</td>
                        <td>{stock_name_map.get(stock_code, '')} {breakout_tag}</td>
                        <td>{stock['收盘价']}</td>
                        <td>{stock['涨跌幅(%)']}</td>
                        <td>{stock['成交量']}</td>
                        <td>{stock['成交额(万元)']}</td>
                        <td>{stock_info['换手率(%)']}</td>
                        <td>{stock_info['流通盘(亿)']}</td>
                        <td>-</td>
                        <td>-</td>
                        <td>-</td>
                        <td>-</td>
                    </tr>
            """
        
    html += """
                    </table>
                </div>
            </div>
        </div>
    </body>
</html>
        """
        
    return html

if __name__ == "__main__":
    # 获取今天和昨天的涨停股池数据
    print("=" * 60)
    print("开始获取涨停股池数据...")
    print("=" * 60)
    
    # 获取今天涨停股池
    print("\n正在获取今天涨停股池...")
    today_pool = get_today_limit_up_pool()
    
    # 获取昨日涨停股池
    print("\n正在获取昨日涨停股池...")
    yesterday_pool = get_yesterday_limit_up_pool()
    
    # 显示今天涨停股池数据
    if not today_pool.empty:
        print("\n" + "=" * 60)
        print("今天涨停股池数据预览:")
        print("=" * 60)
        print(today_pool.to_string())
    else:
        print("\n今天涨停股池数据为空或获取失败")
    
    # 显示昨日涨停股池数据
    if not yesterday_pool.empty:
        print("\n" + "=" * 60)
        print("昨日涨停股池数据预览:")
        print("=" * 60)
        print(yesterday_pool.to_string())
    else:
        print("\n昨日涨停股池数据为空或获取失败")
    
    # 生成HTML报告
    print("\n" + "=" * 60)
    print("正在生成HTML报告...")
    print("=" * 60)
    
    html_content = generate_limit_up_pool_html(today_pool, yesterday_pool)
    
    # 保存HTML文件
    html_file_path = "limit_up_pool_report.html"
    with open(html_file_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"\nHTML报告已生成: {html_file_path}")
    print("请在浏览器中打开该文件查看涨停股池数据")
    
    print("\n" + "=" * 60)
    print("数据获取完成！")
    print("=" * 60)
