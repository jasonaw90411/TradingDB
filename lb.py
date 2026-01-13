# 正确的涨停统计逻辑：先获取8天数据，统计每日涨停，再找共同出现的股票
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import requests
import json
import akshare as ak

# 全局变量定义
MIN_LIMIT_UP_DAYS = 3  # 最小涨停天数，可根据需要调整
QIAN_WEN_API= "sk-0cf24d6cc45a4d88bf150f8b565c1ef7"
INDEX_CODE = "000001.XSHG"  # 默认使用上证指数
DEVIATION_PERIODS = [3, 10]  # 计算偏离值的时间段

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


def calculate_price_deviation(stock_list, days=DEVIATION_PERIODS, index_code=INDEX_CODE):
    """
    计算指定股票列表的3天和10日涨幅偏离值及下一个交易日的涨幅空间
    
    参数:
    - stock_list: 股票代码列表
    - days: 计算天数列表，默认使用全局变量DEVIATION_PERIODS
    - index_code: 大盘指数代码，默认使用全局变量INDEX_CODE
    
    返回:
    - DataFrame: 包含偏离值和涨幅空间的股票列表
    """
    
    print(f"计算{days}日涨幅偏离值及涨幅空间...")
    
    # 获取最近的交易日期
    latest_date = get_latest_trading_date()
    
    # 计算需要的最早日期
    max_days = max(days)
    start_date = latest_date - timedelta(days=max_days * 2)  # 留足缓冲区，考虑周末和节假日
    
    # 获取所有股票代码信息
    stocks = get_all_securities(types=['stock'], date=None)
    
    # 结果列表
    result_list = []
    
    # 遍历每个股票
    for stock_code in stock_list:
        try:
            # 获取股票数据
            df = get_price(stock_code, 
                          start_date=start_date, 
                          end_date=latest_date, 
                          frequency='daily', 
                          fields=['close', 'pre_close'])
            
            if df.empty:
                continue
                
            # 获取股票基本信息
            stock_info = stocks.loc[stock_code]
            
            # 根据股票代码判断市场并获取对应指数
            if stock_code.endswith('.XSHG'):
                # 上证股票
                index_code = '000001.XSHG'  # 上证指数
            elif stock_code.startswith('300') or stock_code.startswith('301'):
                # 创业板股票
                index_code = '399006.XSHE'  # 创业板指
            else:
                # 深证股票
                index_code = '399001.XSHE'  # 深证成指
            
            # 获取对应的大盘指数数据
            index_df = get_index_data(start_date, latest_date, index_code)
            
            if index_df.empty:
                print(f"获取股票 {stock_code} 对应指数 {index_code} 数据失败，跳过")
                continue
            
            # 最新收盘价
            latest_close = df['close'].iloc[-1]
            
            result = {
                '股票代码': stock_code,
                '股票名称': stock_info.display_name,
                '最新收盘价': latest_close
            }
            
            # 计算每个时间段的偏离值和涨幅空间
            for period in days:
                if len(df) < period + 1 or len(index_df) < period + 1:
                    continue
                    
                # 计算个股涨幅（每日涨幅之和，只累加正涨幅，下跌日忽视）
                stock_gain = sum(max(0, (df['close'].iloc[-1-i] - df['pre_close'].iloc[-1-i]) / df['pre_close'].iloc[-1-i] * 100) for i in range(period))
                
                # 计算大盘涨幅（每日涨幅之和，只累加正涨幅，下跌日忽视）
                index_gain = sum(max(0, (index_df['close'].iloc[-1-i] - index_df['pre_close'].iloc[-1-i]) / index_df['pre_close'].iloc[-1-i] * 100) for i in range(period))
                
                # 计算偏离值
                deviation = stock_gain - index_gain
                
                # 根据证监会规定的异常波动标准计算涨幅空间
                # 连续3个交易日累计±20%为异常波动
                # 连续10个交易日累计+100%/-50%为严重异常波动
                if period == 3:
                    target_gain = 20.0  # 3日目标涨幅为20%
                elif period == 10:
                    target_gain = 100.0  # 10日目标涨幅为100%
                else:
                    target_gain = deviation  # 其他周期仍使用偏离值
                
                # 计算涨幅空间
                # 涨幅空间 = 目标涨幅 - 偏离值
                gain_space = target_gain - deviation
                
                # 添加到结果
                result[f'{period}日个股涨幅(%)'] = round(stock_gain, 2)
                result[f'{period}日偏离值(%)'] = round(deviation, 2)
                result[f'{period}日涨幅空间(%)'] = round(gain_space, 2)
            
            # 只有当至少计算了一个时间段的数据时才添加到结果
            if len(result) > 3:
                result_list.append(result)
                
        except Exception as e:
            print(f"计算股票 {stock_code} 偏离值时出错: {e}")
            continue
    
    # 转换为DataFrame
    result_df = pd.DataFrame(result_list)
    
    if not result_df.empty:
        print(f"\n计算完成，共分析了 {len(result_df)} 只股票")
    else:
        print("\n没有找到符合条件的股票")
    
    return result_df


def analyze_one_to_two_breakout(include_cy=False):
    """
    一进二打板策略选股
    
    参数:
    - include_cy: 是否包含创业板
    
    返回:
    - DataFrame: 满足条件的一进二打板股票列表
    """
    
    print("=== 一进二打板策略选股 ===")
    
    # 获取股票列表
    all_stocks = get_all_stocks(include_cy)
    
    # 获取最近的交易日期（需要至少2个交易日）
    trading_dates = get_trading_dates(days=2)
    
    if not trading_dates or len(trading_dates) < 2:
        print("错误：无法获取足够的交易日期，分析终止")
        return pd.DataFrame()
    
    yesterday = trading_dates[-1]  # 最近一个交易日
    before_yesterday = trading_dates[-2]  # 前天
    
    print(f"分析时间段: 前天({before_yesterday}) 和 最近一个交易日({yesterday})")
    
    # 获取所有股票代码
    stocks = get_all_securities(types=['stock'], date=None)
    
    print(f"\n开始分析最近一个交易日的涨停股票...")
    
    # 筛选最近一个交易日的涨停股票
    yesterday_limit_up = get_daily_limit_up_stocks(yesterday, all_stocks)
    
    print(f"最近一个交易日涨停股票数量: {len(yesterday_limit_up)}")
    
    # 获取前天的涨停股票列表（用于检查是否是首板）
    before_yesterday_limit_up = get_daily_limit_up_stocks(before_yesterday, all_stocks)
    before_yesterday_limit_up_codes = [stock['股票代码'] for stock in before_yesterday_limit_up]
    
    print(f"前天涨停股票数量: {len(before_yesterday_limit_up)}")
    
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
                # 获取封板时间和是否开板信息
                seal_time = ""
                has_opening = ""
                try:
                    # 使用千问API同时获取封板时间和是否开板
                    prompt = f"根据同花顺数据告诉我({stock_info.display_name})股票在{yesterday}的涨停封板时间（格式为HH.MM，例如：xx.xx）以及当天是否有过开板（是/否）。请按照以下格式返回：封板时间,是否开板。例如：09.30,是 或 14.55,否。只需要返回格式正确的结果，不要有其他解释或格式。"
                    llm_result = call_qianwen_api(prompt)
                    if llm_result:
                        # 清理结果，确保格式正确
                        llm_result = llm_result.strip()
                        # 分割结果
                        if ',' in llm_result:
                            parts = llm_result.split(',')
                            if len(parts) >= 2:
                                # 处理封板时间
                                seal_time_part = parts[0].strip()
                                if ':' in seal_time_part:
                                    seal_time = seal_time_part.replace(':', '.')
                                else:
                                    seal_time = seal_time_part
                                
                                # 处理是否开板
                                has_opening_part = parts[1].strip()
                                # 确保结果是中文的"是"或"否"
                                if has_opening_part.lower() in ['yes', 'y', '是']:
                                    has_opening = "是"
                                elif has_opening_part.lower() in ['no', 'n', '否']:
                                    has_opening = "否"
                                else:
                                    has_opening = has_opening_part
                                
                                print(f"股票 {stock_code} 封板时间: {seal_time}, 是否开板: {has_opening}")
                            else:
                                # 如果分割后只有一个部分，可能只有封板时间
                                seal_time_part = llm_result.strip()
                                if ':' in seal_time_part:
                                    seal_time = seal_time_part.replace(':', '.')
                                else:
                                    seal_time = seal_time_part
                                has_opening = "获取失败"
                                print(f"股票 {stock_code} 封板时间: {seal_time}, 是否开板: 获取失败")
                        else:
                            # 如果没有逗号分割，可能只有封板时间
                            seal_time_part = llm_result.strip()
                            if ':' in seal_time_part:
                                seal_time = seal_time_part.replace(':', '.')
                            else:
                                seal_time = seal_time_part
                            has_opening = "获取失败"
                            print(f"股票 {stock_code} 封板时间: {seal_time}, 是否开板: 获取失败")
                    else:
                        seal_time = "获取失败"
                        has_opening = "获取失败"
                except Exception as e:
                    print(f"获取股票 {stock_code} 封板信息时出错: {e}")
                    seal_time = "获取失败"
                    has_opening = "获取失败"
                
                qualified_stocks.append({
                    '股票代码': stock_code,
                    '股票名称': stock_info.display_name,
                    '涨跌幅(%)': stock['涨跌幅(%)'],
                    '换手率(%)': turnover_ratio,
                    '流通盘(亿)': market_cap,
                    '行业板块': stock['行业板块'],
                    '封板时间': seal_time,
                    '是否开板': has_opening,
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

def filter_recent_two_days_down(stocks_df):
    """
    筛选出最近两个交易日涨幅小于等于0的股票
    
    参数:
    - stocks_df: 满足初始条件的股票DataFrame
    
    返回:
    - DataFrame: 筛选后的股票列表
    """
    
    # 日志：输入数据基本信息
    print(f"\n=== filter_recent_two_days_down 函数开始执行 ===")
    print(f"输入股票数量: {len(stocks_df)}")
    if not stocks_df.empty:
        print(f"输入股票代码列表: {list(stocks_df['股票代码'])}")
    
    if stocks_df.empty:
        print("输入DataFrame为空，直接返回")
        print(f"=== filter_recent_two_days_down 函数执行结束 ===")
        return stocks_df
    
    print(f"\n进一步筛选：最近两个交易日涨幅小于等于0的股票...")
    
    # 获取最近两个交易日的日期
    recent_trading_dates = get_trading_dates(days=2)
    if not recent_trading_dates or len(recent_trading_dates) < 2:
        print("获取交易日期失败，无法进行进一步筛选")
        print(f"=== filter_recent_two_days_down 函数执行结束 ===")
        return stocks_df
    
    # 获取最近两个交易日
    date1 = recent_trading_dates[-2]  # 倒数第二个交易日
    date2 = recent_trading_dates[-1]  # 最新交易日
    
    print(f"检查日期：{date1} 和 {date2}")
    
    # 筛选满足条件的股票
    filtered_stocks = []
    
    # 日志：处理进度
    total_stocks = len(stocks_df)
    print(f"\n开始处理 {total_stocks} 只股票...")
    
    for idx, (_, row) in enumerate(stocks_df.iterrows()):
        stock_code = row['股票代码']
        print(f"\n[{idx+1}/{total_stocks}] 处理股票: {stock_code}")
        
        try:
            # 获取最近两个交易日的股票数据，增加起始日期提前天数确保获取到足够数据
            start_date = (date1 - timedelta(days=5)).strftime('%Y-%m-%d')  # 提前5天开始获取，确保包含足够的交易日
            end_date = date2.strftime('%Y-%m-%d')
            
            print(f"  获取数据日期范围: {start_date} 至 {end_date}")
            
            df = get_price(stock_code, 
                           start_date=start_date, 
                           end_date=end_date, 
                           frequency='daily', 
                           fields=['close', 'open'])
            
            print(f"  获取到 {len(df)} 天的股票数据")
            
            if not df.empty and len(df) >= 3:  # 需要至少3天数据来计算两天的涨跌幅
                # 计算最近两个交易日的涨跌幅
                df['price_change_ratio'] = df['close'].pct_change() * 100
                
                # 获取最近两个交易日的涨跌幅
                change_date1 = df.iloc[-2]['price_change_ratio']  # 倒数第二天的涨跌幅
                change_date2 = df.iloc[-1]['price_change_ratio']  # 最新一天的涨跌幅
                
                print(f"  倒数第二个交易日({date1})涨跌幅: {change_date1:.2f}%")
                print(f"  最新交易日({date2})涨跌幅: {change_date2:.2f}%")
                
                # 检查是否满足条件
                if change_date1 <= 0 or change_date2 <= 0:
                    print(f"  ✅ 满足条件：至少有一天涨幅<=0")
                    row_copy = row.copy()
                    row_copy['最近两日涨跌幅'] = f"{change_date1:.2f}%/{change_date2:.2f}%"
                    filtered_stocks.append(row_copy)
                    print(f"  当前已筛选出 {len(filtered_stocks)} 只满足条件的股票")
                else:
                    print(f"  ❌ 不满足条件：两天涨幅都>0")
            else:
                print(f"  ❌ 数据不足：需要至少3天数据，仅获取到{len(df)}天")
        
        except Exception as e:
            print(f"  ❌ 获取股票数据时出错: {e}")
            continue
    
    # 详细的筛选结果日志
    print(f"\n=== 筛选结果统计 ===")
    print(f"输入股票总数: {total_stocks}")
    print(f"满足条件的股票数: {len(filtered_stocks)}")
    
    if filtered_stocks:
        result_df = pd.DataFrame(filtered_stocks)
        print(f"\n筛选完成，共找到 {len(result_df)} 只最近两个交易日涨幅均小于等于0的股票")
        print(f"满足条件的股票代码: {list(result_df['股票代码'])}")
    else:
        print("\n没有找到满足条件的股票")
        result_df = pd.DataFrame()
    
    print(f"=== filter_recent_two_days_down 函数执行结束 ===")
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



def call_qianwen_api(prompt, model="qwen-turbo", api_key=QIAN_WEN_API, base_url="https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"):
    """
    调用千问API获取AI响应
    
    参数:
    - prompt: 提示词文本
    - model: 模型名称，默认为ernie-3.5-turbo
    - api_key: API密钥，需要用户替换为自己的密钥
    - base_url: API端点，默认为百度文心一言的聊天接口
    
    返回:
    - str: AI生成的响应文本
    """
    
    try:
        # 设置请求头，千问Turbo需要使用Authorization头进行认证
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        # 构建请求体，千问Turbo的API格式
        payload = {
            "model": model,
            "input": {
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            },
            "parameters": {
                "temperature": 0.7,
                "max_tokens": 2048,
                "top_p": 0.95
            }
        }
        
        # 发送POST请求
        response = requests.post(base_url, headers=headers, data=json.dumps(payload))
        
        # 解析响应
        response_data = response.json()
        
        # 检查响应是否成功
        if "output" in response_data and "text" in response_data["output"]:
            return response_data["output"]["text"]
        else:
            print(f"千问API调用失败: {response_data.get('message', '未知错误')}")
            return None
            
    except Exception as e:
        print(f"调用千问API时出错: {e}")
        return None


def analyze_stock_themes(filtered_stocks_df, api_key=QIAN_WEN_API):
    """
    分析筛选后的股票，获取每只股票的核心题材
    
    参数:
    - filtered_stocks_df: filter_recent_two_days_down函数筛选后的股票DataFrame
    - api_key: 千问API密钥
    
    返回:
    - DataFrame: 添加了核心题材信息的股票DataFrame
    """
    
    if filtered_stocks_df.empty:
        print("没有筛选出符合条件的股票，无法进行题材分析")
        return filtered_stocks_df
    
    
    # 创建结果DataFrame的副本
    result_df = filtered_stocks_df.copy()
    
    # 遍历每只股票
    for idx, row in result_df.iterrows():
        stock_code = row['股票代码']
        stock_name = row['股票名称']
        
        # 构建提示词
        prompt = f"请分析股票{stock_code}({stock_name})的核心题材，参考东方财富和同花顺的概念题材热度索引，只列出2-3个最核心、其中第一个题材应该是最近影响他涨停原因的题材，不要有其他解释。格式为：题材1,题材2,题材3"
        
        # 调用千问API
        themes = call_qianwen_api(prompt, api_key=api_key)
        
        if themes:

            # 替换行业板块列为核心题材
            result_df.at[idx, '行业板块'] = themes
        else:
            print(f"  获取核心题材失败")
            result_df.at[idx, '行业板块'] = '获取失败'
    
    print(f"\n=== 股票核心题材分析完成 ===")
    return result_df



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
    
    # 获取股票列表
    all_stocks = get_all_stocks(include_cy=False)
    
    # 获取最近的交易日期（需要至少2个交易日）
    trading_dates = get_trading_dates(days=2)
    
    if not trading_dates or len(trading_dates) < 2:
        print("错误：无法获取足够的交易日期，分析终止")
    else:
        yesterday = trading_dates[-1]  # 最近一个交易日
        before_yesterday = trading_dates[-2]  # 前天
        
        print(f"分析时间段: 前天({before_yesterday}) 和 最近一个交易日({yesterday})")
        
        # 获取最近一个交易日的涨停股票
        yesterday_limit_up = get_daily_limit_up_stocks(yesterday, all_stocks)
        print(f"最近一个交易日涨停股票数量: {len(yesterday_limit_up)}")
        
        # 获取前天的涨停股票
        before_yesterday_limit_up = get_daily_limit_up_stocks(before_yesterday, all_stocks)
        print(f"前天涨停股票数量: {len(before_yesterday_limit_up)}")
        
        # 生成HTML报告
        html_content = generate_html_report(yesterday_limit_up, before_yesterday_limit_up, yesterday, before_yesterday)
        
        # 保存HTML文件
        html_file_path = "d:\\量化\\trading\\1进2\\zt_stocks_report.html"
        with open(html_file_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"\nHTML报告已生成: {html_file_path}")
        print("请在浏览器中打开该文件查看涨停股票数据")
    
    # 分析一进二打板股票
    result_df = analyze_one_to_two_breakout(include_cy=False)
    
    # 分析股票核心题材
    result_df_with_themes = analyze_stock_themes(result_df)
    
    # 显示结果
    display_results(result_df_with_themes)
    
    print(f"\n分析完成！找到 {len(result_df_with_themes)} 只符合条件的一进二打板股票。")
    
    # 如果有核心题材信息，额外显示
    if not result_df_with_themes.empty and '核心题材' in result_df_with_themes.columns:
        print("\n=== 股票核心题材信息 ===")
        for idx, row in result_df_with_themes.iterrows():
            print(f"{row['股票代码']} {row['股票名称']}: {row['核心题材']}")
