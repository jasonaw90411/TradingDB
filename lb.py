# 正确的涨停统计逻辑：先获取8天数据，统计每日涨停，再找共同出现的股票
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import akshare as ak

# 全局变量定义
MIN_LIMIT_UP_DAYS = 3

# Akshare 原生函数
def get_all_securities(types=None, date=None):
    """获取所有股票代码（纯akshare实现）"""
    try:
        return ak.stock_info_a_code_name()
    except Exception as e:
        print(f"获取股票列表时出错: {e}")
        return pd.DataFrame()

def get_price(stock_code, start_date, end_date, frequency='daily', fields=None):
    """获取股票价格数据（纯akshare实现）"""
    try:
        # akshare直接使用股票代码，不需要转换格式
        symbol = stock_code
        
        # 获取历史行情数据
        df = ak.stock_zh_a_hist(symbol=symbol, period="daily", 
                                start_date=start_date.replace('-', ''), 
                                end_date=end_date.replace('-', ''), 
                                adjust="qfq")
        
        return df
    except Exception as e:
        print(f"获取股票 {stock_code} 价格数据时出错: {e}")
        return pd.DataFrame()

def get_concepts(stock_code, date=None):
    """获取股票概念板块（纯akshare实现）"""
    try:
        # 尝试获取股票概念信息
        try:
            concept_df = ak.stock_board_concept_cons_em(symbol=stock_code)
            if not concept_df.empty:
                return concept_df
        except Exception as e:
            print(f"获取股票 {stock_code} 概念板块时出错: {e}")
        
        # 如果概念板块接口失败，尝试获取行业板块信息
        try:
            industry_df = ak.stock_board_industry_cons_em(symbol=stock_code)
            if not industry_df.empty:
                return industry_df
        except Exception as e:
            print(f"获取股票 {stock_code} 行业板块时出错: {e}")
        
        # 如果所有接口都失败，返回空DataFrame
        return pd.DataFrame()
    except Exception as e:
        print(f"获取股票 {stock_code} 板块信息时出错: {e}")
        return pd.DataFrame()

def get_valuation(stock_code, end_date=None, count=1, fields=None):
    """获取股票估值数据（纯akshare实现）"""
    try:
        # akshare直接使用股票代码，不需要转换格式
        symbol = stock_code
        
        # 获取股票实时数据
        df = ak.stock_zh_a_spot_em()
        
        if df.empty:
            return pd.DataFrame()
        
        # 筛选指定股票
        stock_data = df[df['代码'] == symbol]
        
        if stock_data.empty:
            return pd.DataFrame()
        
        # 转换为DataFrame
        result = pd.DataFrame()
        
        # 添加换手率
        if 'turnover_ratio' in fields or fields is None:
            result['turnover_ratio'] = [stock_data.iloc[0].get('换手率', 0)]
        
        # 添加流通市值
        if 'circulating_market_cap' in fields or fields is None:
            result['circulating_market_cap'] = [stock_data.iloc[0].get('流通市值', 0)]
        
        return result
    except Exception as e:
        print(f"获取股票 {stock_code} 估值数据时出错: {e}")
        return pd.DataFrame()

def get_money_flow(stock_code, end_date=None, count=1, fields=None):
    """获取资金流向数据（纯akshare实现）"""
    try:
        # akshare直接使用股票代码，不需要转换格式
        symbol = stock_code
        
        # 获取个股资金流向
        df = ak.stock_individual_fund_flow(stock=symbol, market="sh" if stock_code.startswith('6') else "sz")
        
        if df.empty:
            return pd.DataFrame()
        
        # 重命名列
        df = df.rename(columns={
            '日期': 'date',
            '主力净流入': 'net_amount_main'
        })
        
        # 设置日期索引
        df['date'] = pd.to_datetime(df['date'])
        df = df.set_index('date')
        
        # 选择需要的字段
        if fields:
            available_fields = [f for f in fields if f in df.columns]
            if available_fields:
                df = df[available_fields]
        
        # 只返回指定数量的数据
        if count and len(df) > count:
            df = df.tail(count)
        
        return df
    except Exception as e:
        print(f"获取股票 {stock_code} 资金流向数据时出错: {e}")
        return pd.DataFrame()

def get_latest_trading_date():
    """
    获取最近一个交易日
    如果今天是交易日且已过交易时间（15:00后），返回今天
    否则返回前一个交易日
    """
    from datetime import datetime
    today = datetime.now().date()
    current_time = datetime.now().time()
    
    # 检查是否是周末
    weekday = today.weekday()
    if weekday >= 5:  # 周六(5)或周日(6)
        # 返回上周五
        days_to_friday = weekday - 4
        return today - timedelta(days=days_to_friday)
    
    # 检查是否是工作日且已过交易时间（15:00）
    if current_time.hour >= 15:
        return today
    else:
        # 如果还没收盘，返回前一个交易日
        if weekday == 0:  # 周一
            return today - timedelta(days=3)  # 上周五
        else:
            return today - timedelta(days=1)

def get_trading_dates(end_date=None, days=8):
    """获取最近的交易日期（不依赖聚宽API）"""
    
    try:
        # 如果没有提供结束日期，使用最近一个交易日
        if end_date is None:
            end_date = get_latest_trading_date()
        
        trading_dates = []
        current_date = end_date
        
        # 循环获取指定数量的交易日
        while len(trading_dates) < days:
            # 检查是否是工作日
            if current_date.weekday() < 5:  # 周一到周五
                trading_dates.append(current_date)
            
            # 往前推一天
            current_date -= timedelta(days=1)
        
        # 按日期升序排列（最早的日期在前，最晚的日期在后）
        return sorted(trading_dates)
    except Exception as e:
        print(f"获取交易日期时出错: {e}")
        return []

def get_daily_limit_up_stocks(date, stock_list, min_price_change=9.8):
    """获取指定日期的涨停股票（使用akshare API）"""
    
    try:
        # 将日期转换为YYYYMMDD格式
        date_str = date.strftime('%Y%m%d')
        
        # 使用akshare获取涨停股票数据
        zt_stocks = ak.stock_zt_pool_em(date=date_str)
        
        if zt_stocks.empty:
            return []
        
        limit_up_stocks = []
        
        for _, row in zt_stocks.iterrows():
            stock_code = row['代码']
            
            # 只处理指定股票列表中的股票
            if stock_code not in stock_list:
                continue
            
            # 获取概念板块信息
            concept_names = []
            try:
                concept_df = get_concepts(stock_code)
                if not concept_df.empty:
                    # 处理概念板块数据
                    if '概念板块' in concept_df.columns:
                        concept_names = concept_df['概念板块'].tolist()
                    elif '板块名称' in concept_df.columns:
                        concept_names = concept_df['板块名称'].tolist()
            except Exception as e:
                print(f"获取股票 {stock_code} 概念板块失败: {str(e)}")
            
            # 构造涨停股票信息
            limit_up_stocks.append({
                '股票代码': stock_code,
                '交易日期': date.strftime('%Y-%m-%d'),
                '前收盘价': round(row.get('前收盘价', row.get('昨收', 0)), 2),
                '收盘价': round(row.get('最新价', row.get('现价', 0)), 2),
                '涨跌幅(%)': round(row.get('涨跌幅', 0), 2),
                '成交量': row.get('成交量', 0),
                '成交额(万元)': round(row.get('成交额', 0) / 10000, 1),
                '行业板块': ','.join(concept_names) if concept_names else '获取失败'
            })
        
        return limit_up_stocks
    except Exception as e:
        print(f"获取涨停股票数据时出错: {e}")
        return []


def get_index_data(start_date, end_date, index_code="000001.XSHG"):
    """
    获取指定日期范围内的大盘指数数据（纯akshare实现）
    
    参数:
    - start_date: 开始日期 (datetime/date对象或字符串)
    - end_date: 结束日期 (datetime/date对象或字符串)
    - index_code: 指数代码，默认上证指数
    
    返回:
    - DataFrame: 指数数据，包含日期和收盘价
    """
    
    try:
        # 如果输入是datetime或date对象，转换为字符串
        if hasattr(start_date, 'strftime'):
            start_date_str = start_date.strftime('%Y-%m-%d')
        else:
            start_date_str = start_date
            
        if hasattr(end_date, 'strftime'):
            end_date_str = end_date.strftime('%Y-%m-%d')
        else:
            end_date_str = end_date
        
        # akshare直接使用指数代码，不需要转换格式
        symbol = index_code
        
        # 使用akshare获取指数数据
        df = ak.index_zh_a_hist(symbol=symbol, period="daily", 
                                start_date=start_date_str.replace('-', ''), 
                                end_date=end_date_str.replace('-', ''))
        
        if df.empty:
            return pd.DataFrame()
        
        # 重命名列
        df = df.rename(columns={
            '日期': 'date',
            '收盘': 'close',
            '开盘': 'open'
        })
        
        # 设置日期索引
        df['date'] = pd.to_datetime(df['date'])
        df = df.set_index('date')
        
        # 添加前收盘价
        df['pre_close'] = df['close'].shift(1)
        
        # 选择需要的字段
        df = df[['close', 'pre_close']]
        
        return df
    except Exception as e:
        print(f"获取指数数据时出错: {e}")
        return pd.DataFrame()

def get_all_stocks(include_cy=False):
    """获取所有股票代码（纯akshare实现，排除科创板和ST股票）"""
    
    try:
        # 获取所有股票代码
        stocks = get_all_securities()
        
        if stocks.empty:
            return []
        
        # 筛选股票：根据参数决定是否包含创业板
        sh_stocks = stocks[stocks['code'].str.startswith('6')]['code'].tolist()  # 上证
        sz_main_stocks = stocks[stocks['code'].str.startswith('0')]['code'].tolist()  # 深证主板和中小板
        
        all_stocks_pre = sh_stocks + sz_main_stocks
        
        # 如果包含创业板，添加创业板股票
        if include_cy:
            cy_stocks = stocks[stocks['code'].str.startswith('3')]['code'].tolist()  # 创业板
            all_stocks_pre.extend(cy_stocks)
        
        # 排除科创板(68开头)，创业板根据参数决定
        if include_cy:
            all_stocks = [code for code in all_stocks_pre if not code.startswith('68')]
        else:
            all_stocks = [code for code in all_stocks_pre if not code.startswith('68') and not code.startswith('3')]
        
        # 过滤ST和*ST股票
        filtered_stocks = []
        for stock_code in all_stocks:
            stock_name = stocks.loc[stocks['code'] == stock_code, 'name'].values[0]
            # 检查股票名称是否包含'ST'或'*ST'
            if 'ST' not in stock_name and '*ST' not in stock_name:
                filtered_stocks.append(stock_code)
        
        all_stocks = filtered_stocks
        return all_stocks
    except Exception as e:
        print(f"获取股票列表时出错: {e}")
        return []


def analyze_one_to_two_breakout(yesterday_limit_up, before_yesterday_limit_up, stocks):
    """
    一进二打板策略选股
    
    参数:
    - yesterday_limit_up: 昨天涨停股票列表
    - before_yesterday_limit_up: 前天涨停股票列表
    - stocks: 所有股票信息DataFrame
    
    返回:
    - DataFrame: 满足条件的一进二打板股票列表
    """
    
    print("=== 一进二打板策略选股 ===")
    
    print(f"最近一个交易日涨停股票数量: {len(yesterday_limit_up)}")
    print(f"前天涨停股票数量: {len(before_yesterday_limit_up)}")
    
    # 获取前天的涨停股票列表（用于检查是否是首板）
    before_yesterday_limit_up_codes = [stock['股票代码'] for stock in before_yesterday_limit_up]
    
    # 筛选符合条件的首板股票
    qualified_stocks = []
    
    for stock in yesterday_limit_up:
        stock_code = stock['股票代码']
        
        try:
            # 筛选条件1：今天是涨停首板，前天没有涨停
            if stock_code in before_yesterday_limit_up_codes:
                print(f"股票 {stock_code} 前天已涨停，不是首板，已过滤")
                continue
            
            # 获取股票基本信息
            stock_info = stocks.loc[stock_code]
            
            # 获取换手率数据
            turnover_ratio = 0.0
            turnover_data = get_valuation(stock_code, end_date=yesterday, count=1, fields=['turnover_ratio'])
            if not turnover_data.empty:
                turnover_ratio = turnover_data['turnover_ratio'].iloc[0]
            
            # 获取流通盘数据
            market_cap = 0.0
            market_cap_data = get_valuation(stock_code, end_date=yesterday, count=1, fields=['circulating_market_cap'])
            if not market_cap_data.empty:
                market_cap = market_cap_data['circulating_market_cap'].iloc[0]
                
            
            # 获取主力净买入数据
            main_force_net_buy = 0.0
            main_df = get_money_flow(stock_code, end_date=yesterday, count=2, fields=['net_amount_main'])
            if main_df.empty:
                main_df = get_money_flow(stock_code, end_date=yesterday, count=1, fields=['net_amount_main'])
                
            # ====================== 【改动3：肉眼可见，取值逻辑加固，兼容所有情况】 ======================
            # 原版：只有一层判断
            # 新版：判断非空+判断字段存在，双重保险，绝对不会触发KeyError/IndexError
            if not main_df.empty and 'net_amount_main' in main_df.columns:
                # 你的原版取值语句，完全保留，一个字符没改
                main_force_net_buy = main_df['net_amount_main'].iloc[0]

            
            # 筛选流通盘大于20亿的股票
            if market_cap > 20:
                qualified_stocks.append({
                    '股票代码': stock_code,
                    '股票名称': stock_info.display_name,
                    '涨跌幅(%)': stock['涨跌幅(%)'],
                    '换手率(%)': turnover_ratio,
                    '流通盘(亿)': market_cap,
                    '行业板块': stock['行业板块'],
                    '封板时间': '获取失败',
                    '是否开板': '获取失败',
                    '主力净买入(万元)': main_force_net_buy
                })
            else:
                print(f"股票 {stock_code} 流通盘 {market_cap} 亿，小于20亿，已过滤")
            
        except Exception as e:
            print(f"分析股票 {stock_code} 时出错: {e}")
            continue
    
    print(f"\n筛选完成，共找到 {len(qualified_stocks)} 只涨停股票")
    
    # 转换为DataFrame
    result_df = pd.DataFrame(qualified_stocks)
    
    if len(result_df) > 0:
        # 按主力净买入从大到小排序
        result_df = result_df.sort_values('主力净买入(万元)', ascending=False)
    
    return result_df

def display_results(stocks_df, days=None, min_rise_days=None):
    """显示一进二打板策略选股结果"""
    
    if stocks_df.empty:
        print("没有找到满足条件的股票")
        return
    
    print(f"\n=== 一进二打板策略选股结果 ===")
    print(f"共找到 {len(stocks_df)} 只符合条件的涨停股票\n")
    
    # 复制数据
    df_stocks = stocks_df.copy()
    
    # 添加序号列
    df_stocks.insert(0, '序号', range(1, len(df_stocks) + 1))
    
    # 选择需要显示的列
    display_columns = ['序号', '股票代码', '股票名称', '换手率(%)', '流通盘(亿)', '行业板块', '涨跌幅(%)', '封板时间', '是否开板', '主力净买入(万元)']
    
    # 如果有核心题材列，添加到显示列表中
    if '核心题材' in df_stocks.columns:
        display_columns.append('核心题材')
    
    # 设置显示选项
    pd.set_option('display.unicode.ambiguous_as_wide', True)
    pd.set_option('display.unicode.east_asian_width', True)
    pd.set_option('display.width', 1200)
    pd.set_option('display.max_columns', None)
    pd.set_option('display.max_colwidth', 30)  # 增加最大列宽
    pd.set_option('display.colheader_justify', 'center')
    
    # 打印结果
    print(df_stocks[display_columns].to_string(index=False, col_space=10))
    
    # 恢复默认设置
    pd.reset_option('display.unicode.ambiguous_as_wide')
    pd.reset_option('display.unicode.east_asian_width')
    pd.reset_option('display.width')
    pd.reset_option('display.max_columns')
    pd.reset_option('display.max_colwidth')
    pd.reset_option('display.colheader_justify')



def generate_html_report(yesterday_limit_up, before_yesterday_limit_up, yesterday, before_yesterday):
    """生成HTML报告"""
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
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(600px, 1fr));
                gap: 25px;
                max-width: 1400px;
                margin: 0 auto;
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
                overflow-y: auto;
                border-radius: 8px;
                border: 1px solid #e0e0e0;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
            }}
            th {{
                background: #f8f9fa;
                color: #2c3e50;
                padding: 12px 15px;
                text-align: left;
                font-weight: 600;
                position: sticky;
                top: 0;
                z-index: 10;
                border-bottom: 2px solid #e0e0e0;
            }}
            td {{
                padding: 12px 15px;
                text-align: left;
                border-bottom: 1px solid #f0f0f0;
                color: #333;
            }}
            tr:hover {{
                background-color: #f8f9fa;
                transition: all 0.2s ease;
            }}
            tr:nth-child(even) {{
                background-color: #fafafa;
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
            <p class="subtitle">实时更新的涨停板数据统计</p>
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
                        </tr>
        """.format(yesterday_str=yesterday.strftime('%Y-%m-%d') if yesterday else '日期获取失败', yesterday_count=len(yesterday_limit_up))
        
    # 获取股票名称映射
    stocks = get_all_securities()
    stock_name_map = dict(zip(stocks['code'], stocks['name']))
    
    # 添加最近一个交易日的数据
    for stock in yesterday_limit_up:
        html += f"""
                    <tr>
                        <td>{stock['股票代码']}</td>
                        <td>{stock_name_map.get(stock['股票代码'], '')}</td>
                        <td>{stock['收盘价']}</td>
                        <td>{stock['涨跌幅(%)']}</td>
                        <td>{stock['成交量']}</td>
                        <td>{stock['成交额(万元)']}</td>
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
                        </tr>
        """.format(before_yesterday_str=before_yesterday.strftime('%Y-%m-%d') if before_yesterday else '日期获取失败', before_yesterday_count=len(before_yesterday_limit_up))
        
        # 添加前天的数据
    for stock in before_yesterday_limit_up:
        html += f"""
                    <tr>
                        <td>{stock['股票代码']}</td>
                        <td>{stock_name_map.get(stock['股票代码'], '')}</td>
                        <td>{stock['收盘价']}</td>
                        <td>{stock['涨跌幅(%)']}</td>
                        <td>{stock['成交量']}</td>
                        <td>{stock['成交额(万元)']}</td>
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
    # 运行分析
    print("开始一进二打板策略选股...")
    
    # 获取最近的交易日期（需要至少2个交易日）
    trading_dates = get_trading_dates(days=2)
    
    if not trading_dates or len(trading_dates) < 2:
        print("错误：无法获取足够的交易日期，分析终止")
    else:
        yesterday = trading_dates[-1]  # 最近一个交易日
        before_yesterday = trading_dates[-2]  # 前天
        
        print(f"分析时间段: 前天({before_yesterday}) 和 最近一个交易日({yesterday})")
        
        # 获取股票列表
        all_stocks = get_all_stocks(include_cy=False)
        
        # 获取最近一个交易日的涨停股票
        yesterday_limit_up = get_daily_limit_up_stocks(yesterday, all_stocks)
        print(f"最近一个交易日涨停股票数量: {len(yesterday_limit_up)}")
        
        # 获取前天的涨停股票
        before_yesterday_limit_up = get_daily_limit_up_stocks(before_yesterday, all_stocks)
        print(f"前天涨停股票数量: {len(before_yesterday_limit_up)}")
        
        # 生成HTML报告
        html_content = generate_html_report(yesterday_limit_up, before_yesterday_limit_up, yesterday, before_yesterday)
        
        # 保存HTML文件
        html_file_path = "zt_stocks_report.html"
        with open(html_file_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"\nHTML报告已生成: {html_file_path}")
        print("请在浏览器中打开该文件查看涨停股票数据")
    
    # 分析一进二打板股票
    result_df = analyze_one_to_two_breakout(include_cy=False)
    
    # 显示结果
    display_results(result_df)
    
    print(f"\n分析完成！找到 {len(result_df)} 只符合条件的一进二打板股票。")
