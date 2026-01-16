# 正确的涨停统计逻辑：先获取8天数据，统计每日涨停，再找共同出现的股票
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import akshare as ak
import requests
import json 

# 全局变量定义
MIN_LIMIT_UP_DAYS = 3
_market_data_cache = None
ALI_QIAN_WEN = "sk-0cf24d6cc45a4d88bf150f8b565c1ef7"


def get_cls_news():
    """获取财联社电报数据"""
    try:
        df = ak.stock_info_global_cls(symbol="全部")
        print(f"成功获取财联社电报数据，共 {len(df)} 条")
        return df
    except Exception as e:
        print(f"获取财联社电报失败: {e}")
        return pd.DataFrame()


def get_ths_news():
    """获取同花顺财经直播数据"""
    try:
        df = ak.stock_info_global_ths()
        print(f"成功获取同花顺财经直播数据，共 {len(df)} 条")
        return df
    except Exception as e:
        print(f"获取同花顺财经直播失败: {e}")
        return pd.DataFrame()


def get_ths_limit_up_analysis():
    """获取同花顺涨停异动解读数据"""
    try:
        df = ak.stock_zt_pool_em(date=datetime.now().strftime('%Y%m%d'))
        print(f"成功获取同花顺涨停异动解读数据，共 {len(df)} 条")
        return df
    except Exception as e:
        print(f"获取同花顺涨停异动解读失败: {e}")
        return pd.DataFrame()


def get_stock_concepts(stock_code):
    """获取股票的概念板块信息"""
    try:
        df = ak.stock_board_concept_cons_em(symbol=stock_code)
        if not df.empty:
            concepts = df['板块名称'].tolist()
            return concepts[:5]
        return []
    except Exception as e:
        print(f"获取股票{stock_code}概念板块失败: {e}")
        return []


def analyze_limit_up_detailed(stock_name, stock_code, zt_pool_data=None):
    """使用LLM详细分析涨停原因和概念"""
    try:
        if zt_pool_data is None or zt_pool_data.empty:
            zt_pool_data = get_ths_limit_up_analysis()
        
        stock_info = ""
        if not zt_pool_data.empty:
            stock_row = zt_pool_data[(zt_pool_data['名称'] == stock_name) | (zt_pool_data['代码'] == stock_code)]
            if not stock_row.empty:
                stock_info = stock_row.iloc[0].to_dict()
        
        concepts = get_stock_concepts(stock_code)
        concept_str = "、".join(concepts) if concepts else "未知"
        
        prompt = f"""请分析股票{stock_name}({stock_code})的涨停原因。

        股票信息：{stock_info}
        所属概念板块：{concept_str}

        依据所属概念板块+同花顺涨停解读总结，要求：
        1.仅输出涨停核心热点概念和原因，直接说结果不要有无任何多余文字描述
        2.极致简洁,不超过30字,无标点,无废话"""

        url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"
        headers = {
            "Authorization": f"Bearer {ALI_QIAN_WEN}",
            "Content-Type": "application/json"
        }
        data = {
            "model": "qwen-turbo",
            "input": {
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            },
            "parameters": {
                "max_tokens": 50,
                "temperature": 0,
                "top_p": 0.9
            }
        }
        
        response = requests.post(url, headers=headers, json=data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            reason = result['output']['text'].strip()
            if len(reason) > 20:
                reason = reason[:20]
            print(f"股票{stock_name}涨停原因分析: {reason}")
            return reason, concept_str
        else:
            print(f"LLM调用失败: {response.status_code} - {response.text}")
            return "分析失败", concept_str
            
    except Exception as e:
        print(f"LLM分析涨停原因失败: {e}")
        return "分析失败", ""


def analyze_limit_up_reason_with_llm(stock_name, stock_code, zt_pool_data=None):
    """使用阿里千文turbo模型分析涨停原因"""
    try:
        if zt_pool_data is None or zt_pool_data.empty:
            zt_pool_data = get_ths_limit_up_analysis()
        
        stock_info = ""
        if not zt_pool_data.empty:
            stock_row = zt_pool_data[(zt_pool_data['名称'] == stock_name) | (zt_pool_data['代码'] == stock_code)]
            if not stock_row.empty:
                stock_info = stock_row.iloc[0].to_dict()
        
        prompt = f"""请分析股票{stock_name}({stock_code})的涨停原因。

        股票信息：{stock_info}

        依据所属概念板块+同花顺涨停解读总结，要求：
        1.仅输出涨停核心热点概念和原因，直接说结果不要有无任何多余文字描述
        2.极致简洁,不超过30字,无标点,无废话"""

        url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"
        headers = {
            "Authorization": f"Bearer {ALI_QIAN_WEN}",
            "Content-Type": "application/json"
        }
        data = {
            "model": "qwen-turbo",
            "input": {
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            },
            "parameters": {
                "max_tokens": 50,
                "temperature": 0,    # 重中之重：0=绝对精准输出，不脑补、不废话、不发散
                "top_p": 0.9       # 0.9=90%概率质量，1=100%概率质量        
            }
        }
        
        response = requests.post(url, headers=headers, json=data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            reason = result['output']['text'].strip()
            if len(reason) > 20:
                reason = reason[:20]
            print(f"股票{stock_name}涨停原因分析: {reason}")
            return reason
        else:
            print(f"LLM调用失败: {response.status_code} - {response.text}")
            return "分析失败"
            
    except ImportError:
        print("未安装requests库，请先安装: pip install requests")
        return "未安装requests"
    except Exception as e:
        print(f"LLM分析涨停原因失败: {e}")
        return "分析失败"


def analyze_limit_up_statistics(today_pool):
    """分析涨停股池统计数据"""
    if today_pool.empty:
        return {
            'industry_stats': {},
            'industry_stocks': {},
            'concept_stats': {},
            'board_stats': {'首版': 0, '二板': 0, '三板及以上': 0}
        }
    
    # 行业统计
    industry_stats = today_pool['所属行业'].value_counts().to_dict()
    
    # 行业股票列表
    industry_stocks = {}
    for industry in today_pool['所属行业'].unique():
        stocks_in_industry = today_pool[today_pool['所属行业'] == industry][['名称', '代码']]
        stock_list = [f"{row['名称']}({row['代码']})" for _, row in stocks_in_industry.iterrows()]
        industry_stocks[industry] = stock_list
    
    # 概念统计（从涨停原因中提取）
    concept_stats = {}
    for reason in today_pool['涨停原因']:
        if pd.notna(reason) and reason != '未知' and reason != '分析失败':
            concept_stats[reason] = concept_stats.get(reason, 0) + 1
    
    # 连板统计
    board_stats = {'首版': 0, '二板': 0, '三板及以上': 0}
    for lianban in today_pool['连板数']:
        if lianban == 1:
            board_stats['首版'] += 1
        elif lianban == 2:
            board_stats['二板'] += 1
        elif lianban >= 3:
            board_stats['三板及以上'] += 1
    
    return {
        'industry_stats': industry_stats,
        'industry_stocks': industry_stocks,
        'concept_stats': concept_stats,
        'board_stats': board_stats
    }


def get_today_limit_up_pool():
    """获取今天涨停股池数据"""
    try:
        today = datetime.now().strftime('%Y%m%d')
        df = ak.stock_zt_pool_em(date=today)
        print(f"成功获取今天涨停股池数据，共 {len(df)} 只股票")
        
        if not df.empty:
            print("\n开始分析涨停原因...")
            zt_pool_data = get_ths_limit_up_analysis()
            
            limit_up_reasons = []
            for idx, row in df.iterrows():
                stock_name = row.get('名称', '')
                stock_code = row.get('代码', '')
                
                if stock_name and stock_code:
                    reason = analyze_limit_up_reason_with_llm(stock_name, stock_code, zt_pool_data)
                    limit_up_reasons.append(reason)
                else:
                    limit_up_reasons.append("未知")
            
            df['涨停原因'] = limit_up_reasons
            print(f"涨停原因分析完成，共分析 {len(limit_up_reasons)} 只股票")
        
        return df
    except Exception as e:
        print(f"获取今天涨停股池失败: {e}")
        return pd.DataFrame()


def get_stock_url(stock_code):
    """根据股票代码生成东方财富跳转URL"""
    if not stock_code:
        return "#"
    
    stock_code_str = str(stock_code)
    
    if stock_code_str.startswith('6'):
        return f"https://quote.eastmoney.com/sh{stock_code_str}.html"
    elif stock_code_str.startswith('0') or stock_code_str.startswith('3'):
        return f"https://quote.eastmoney.com/sz{stock_code_str}.html"
    elif stock_code_str.startswith('8'):
        return f"https://quote.eastmoney.com/{stock_code_str}.html"
    else:
        return f"https://quote.eastmoney.com/{stock_code_str}.html"


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


def get_board_concept_info():
    """获取概念板块信息数据"""
    try:
        df = ak.stock_board_concept_name_em()
        print(f"成功获取概念板块信息数据，共 {len(df)} 个板块")
        return df
    except Exception as e:
        print(f"获取概念板块信息失败: {e}")
        return pd.DataFrame()


def get_board_industry_info():
    """获取行业板块信息数据"""
    try:
        df = ak.stock_board_industry_summary_ths()
        print(f"成功获取行业板块信息数据，共 {len(df)} 个板块")
        return df
    except Exception as e:
        print(f"获取行业板块信息失败: {e}")
        return pd.DataFrame()


def get_capital_flow_data():
    """获取资金流向数据"""
    try:
        # 获取即时资金流向
        realtime_df = ak.stock_fund_flow_concept(symbol="即时")
        print(f"成功获取即时资金流向数据，共 {len(realtime_df)} 个概念板块")
        
        # 获取3日排行
        day3_df = ak.stock_fund_flow_concept(symbol="3日排行")
        print(f"成功获取3日资金流向排行，共 {len(day3_df)} 个概念板块")
        
        # 获取5日排行
        day5_df = ak.stock_fund_flow_concept(symbol="5日排行")
        print(f"成功获取5日资金流向排行，共 {len(day5_df)} 个概念板块")
        
        # 获取10日排行
        day10_df = ak.stock_fund_flow_concept(symbol="10日排行")
        print(f"成功获取10日资金流向排行，共 {len(day10_df)} 个概念板块")
        
        # 获取20日排行
        day20_df = ak.stock_fund_flow_concept(symbol="20日排行")
        print(f"成功获取20日资金流向排行，共 {len(day20_df)} 个概念板块")
        
        return {
            "即时": realtime_df,
            "3日": day3_df,
            "5日": day5_df,
            "10日": day10_df,
            "20日": day20_df
        }
    except Exception as e:
        print(f"获取资金流向数据失败: {e}")
        return {}

def get_industry_flow_data():
    """获取行业资金流向数据"""
    try:
        # 获取即时资金流向
        realtime_df = ak.stock_fund_flow_industry(symbol="即时")
        print(f"成功获取即时行业资金流向数据，共 {len(realtime_df)} 个行业")
        
        # 获取3日排行
        day3_df = ak.stock_fund_flow_industry(symbol="3日排行")
        print(f"成功获取3日行业资金流向排行，共 {len(day3_df)} 个行业")
        
        # 获取5日排行
        day5_df = ak.stock_fund_flow_industry(symbol="5日排行")
        print(f"成功获取5日行业资金流向排行，共 {len(day5_df)} 个行业")
        
        # 获取10日排行
        day10_df = ak.stock_fund_flow_industry(symbol="10日排行")
        print(f"成功获取10日行业资金流向排行，共 {len(day10_df)} 个行业")
        
        # 获取20日排行
        day20_df = ak.stock_fund_flow_industry(symbol="20日排行")
        print(f"成功获取20日行业资金流向排行，共 {len(day20_df)} 个行业")
        
        return {
            "即时": realtime_df,
            "3日": day3_df,
            "5日": day5_df,
            "10日": day10_df,
            "20日": day20_df
        }
    except Exception as e:
        print(f"获取行业资金流向数据失败: {e}")
        return {}

def get_yyb_lhb_data(yyb_code="210204000015668"):
    """获取营业部龙虎榜数据"""
    try:
        lhb_df = ak.stock_lhb_yyb_detail_em(symbol=yyb_code)
        print(f"成功获取营业部龙虎榜数据，共 {len(lhb_df)} 条记录")
        return lhb_df
    except Exception as e:
        print(f"获取营业部龙虎榜数据失败: {e}")
        return pd.DataFrame()



def generate_limit_up_pool_html(today_pool, yesterday_pool, board_info, industry_info, capital_flow_data=None, industry_flow_data=None, yyb_lhb_data=None, cls_news=None, ths_news=None):
    # 获取股票市场活跃度数据
    try:
        market_activity = ak.stock_market_activity_legu()
        print(f"成功获取股票市场活跃度数据")
    except Exception as e:
        print(f"获取股票市场活跃度数据失败: {e}")
        market_activity = pd.DataFrame()
    
    # 如果没有提供新闻数据，则获取
    if cls_news is None:
        cls_news = get_cls_news()
    if ths_news is None:
        ths_news = get_ths_news()
    
    # 生成新闻HTML
    news_html = ""
    news_items = []
    icons = ['📰', '📊', '💹', '📈', '💼', '🏢', '💡', '⚡', '🔔', '📢']
    
    # 添加财联社新闻
    if not cls_news.empty:
        for idx, row in cls_news.iterrows():
            title = str(row.get('标题', ''))
            time_str = str(row.get('发布时间', ''))
            icon = icons[idx % len(icons)]
            news_items.append(f"<span class='news-item'>{icon} [财联社 {time_str}] {title}</span>")
    
    # 添加同花顺新闻
    if not ths_news.empty:
        start_idx = len(news_items)
        for idx, row in ths_news.iterrows():
            title = str(row.get('标题', ''))
            time_str = str(row.get('发布时间', ''))
            icon = icons[(start_idx + idx) % len(icons)]
            news_items.append(f"<span class='news-item'>{icon} [同花顺 {time_str}] {title}</span>")
    
    # 如果有新闻，则使用新闻数据
    if news_items:
        # 重复新闻以实现无缝滚动
        news_html = '\n                    '.join(news_items + news_items)
    else:
        # 默认新闻
        default_news = [
            "📈 沪指今日收涨0.5%，创业板指涨1.2%",
            "💰 北向资金净流入50亿元，连续3日净买入",
            "🚀 新能源板块强势领涨，多股涨停",
            "📊 央行今日开展1000亿元逆回购操作",
            "🔥 科技股持续活跃，人工智能概念受关注"
        ]
        news_html = '\n                    '.join([f"<span class='news-item'>{news}</span>" for news in default_news * 2])
    
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
                padding: 0;
                display: flex;
                margin: 0;
            }}
            .news-ticker {{
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                height: 55px;
                background: linear-gradient(90deg, #1a252f 0%, #2c3e50 100%);
                color: white;
                display: flex;
                align-items: center;
                overflow: hidden;
                z-index: 1000;
                border-bottom: 2px solid rgba(255, 255, 255, 0.1);
            }}
            .news-label {{
                background: #e74c3c;
                color: white;
                padding: 0 20px;
                height: 100%;
                display: flex;
                align-items: center;
                font-weight: 600;
                font-size: 16px;
                white-space: nowrap;
                z-index: 10;
            }}
            .news-content {{
                flex: 1;
                overflow: hidden;
                position: relative;
                height: 100%;
                display: flex;
                align-items: center;
            }}
            .news-scroll {{
                display: flex;
                animation: scroll 280s linear infinite;
                white-space: nowrap;
            }}
            .news-scroll:hover {{
                animation-play-state: paused;
            }}
            .news-item {{
                display: inline-block;
                padding: 0 40px;
                font-size: 16px;
                color: rgba(255, 255, 255, 0.95);
            }}
            .news-item a {{
                color: rgba(255, 255, 255, 0.9);
                text-decoration: none;
                transition: color 0.3s ease;
            }}
            .news-item a:hover {{
                color: #3498db;
            }}
            @keyframes scroll {{
                0% {{
                    transform: translateX(0);
                }}
                100% {{
                    transform: translateX(-50%);
                }}
            }}
            .sidebar {{
                width: 250px;
                background: rgba(0, 0, 0, 0.3);
                backdrop-filter: blur(10px);
                padding: 30px 20px;
                display: flex;
                flex-direction: column;
                position: fixed;
                height: 100vh;
                overflow-y: auto;
                border-right: 1px solid rgba(255, 255, 255, 0.1);
                top: 55px;
            }}
            .sidebar-title {{
                color: white;
                font-size: 1.8rem;
                font-weight: 700;
                margin-bottom: 30px;
                text-align: center;
                padding-bottom: 20px;
                border-bottom: 2px solid rgba(255, 255, 255, 0.2);
            }}
            .nav-menu {{
                display: flex;
                flex-direction: column;
                gap: 10px;
            }}
            .nav-item {{
                padding: 15px 20px;
                color: rgba(255, 255, 255, 0.8);
                text-decoration: none;
                border-radius: 8px;
                transition: all 0.3s ease;
                font-size: 1rem;
                font-weight: 500;
                cursor: pointer;
            }}
            .nav-item:hover {{
                background: rgba(255, 255, 255, 0.15);
                color: white;
                transform: translateX(5px);
            }}
            .nav-item.active {{
                background: rgba(255, 255, 255, 0.2);
                color: white;
                font-weight: 600;
            }}
            .main-content {{
                flex: 1;
                margin-left: 250px;
                padding: 20px;
                margin-top: 55px;
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
                gap: 40px;
                max-width: 100%;
                margin: 0 auto;
                width: 100%;
            }}
            .section {{
                background: white;
                border-radius: 0;
                box-shadow: none;
                border-bottom: 2px solid #e0e0e0;
                padding: 25px 0;
                transition: all 0.3s ease;
            }}
            .section:hover {{
                box-shadow: none;
            }}
            h2 {{
                color: #2c3e50;
                margin-bottom: 20px;
                font-size: 1.5rem;
                font-weight: 600;
                border-bottom: 3px solid #a3b3b4;
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
            .market-activity-container {{
                margin-top: 20px;
            }}
            .activity-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 15px;
                margin-top: 20px;
            }}
            .activity-card {{
                background: white;
                border-radius: 12px;
                padding: 15px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.08);
                text-align: center;
                transition: all 0.3s ease;
                border-left: 4px solid;
            }}
            .activity-card:hover {{
                transform: translateY(-5px);
                box-shadow: 0 8px 20px rgba(0,0,0,0.12);
            }}
            .activity-card.positive {{
                border-left-color: #27ae60;
            }}
            .activity-card.negative {{
                border-left-color: #e74c3c;
            }}
            .activity-card.neutral {{
                border-left-color: #95a5a6;
            }}
            .activity-icon {{
                font-size: 2rem;
                margin-bottom: 8px;
            }}
            .activity-title {{
                font-size: 0.9rem;
                color: #666;
                margin-bottom: 8px;
                font-weight: 600;
            }}
            .activity-value {{
                 font-size: 1.8rem;
                 font-weight: 700;
                 color: #2c3e50;
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
                background: #a3b3b4;
                border-radius: 4px;
            }}
            .table-container::-webkit-scrollbar-thumb:hover {{
                background: #5a6c7d;
                border-radius: 4px;
                transition: background 0.2s ease;
            }}
            
            /* Chart styling */
            .chart-container {{
                display: flex;
                justify-content: space-around;
                flex-wrap: wrap;
                gap: 30px;
                margin-top: 30px;
            }}
            .chart-card {{
                background: white;
                border-radius: 12px;
                padding: 25px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.08);
                width: 450px;
                text-align: center;
            }}
            .chart-title {{
                font-size: 1.3rem;
                color: #2c3e50;
                margin-bottom: 20px;
                font-weight: 600;
            }}
            .chart-canvas {{
                width: 100% !important;
                height: 300px !important;
            }}
            .lianban-section {{
                margin-bottom: 30px;
                background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
            }}
            .lianban-cards {{
                display: flex;
                gap: 10px;
                flex-wrap: nowrap;
                width: 100%;
            }}
            .lianban-card {{
                flex: 1;
                min-width: 0;
                max-width: none;
                background: white;
                border-radius: 0;
                box-shadow: none;
                padding: 20px;
                transition: all 0.3s ease;
            }}
            .lianban-card:hover {{
                box-shadow: 0 4px 8px rgba(0,0,0,0.1);
            }}
            .lianban-title {{
                font-size: 1.8rem;
                font-weight: 700;
                color: #e74c3c;
                margin-bottom: 5px;
            }}
            .lianban-count {{
                font-size: 0.9rem;
                color: #666;
                margin-bottom: 15px;
            }}
            .lianban-divider {{
                height: 2px;
                background: #a3b3b4;
                margin: 10px 0;
            }}
            .lianban-stocks {{
                display: flex;
                flex-direction: column;
                gap: 10px;
            }}
            .lianban-stock-item {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 10px;
                background: #f8f9fa;
                border-radius: 6px;
                transition: all 0.2s ease;
            }}
            .lianban-stock-item:hover {{
                background: #e9ecef;
            }}
            .stock-code {{
                font-weight: 600;
                color: #2c3e50;
                font-size: 0.9rem;
            }}
            .stock-name {{
                flex: 1;
                text-align: center;
                font-weight: 500;
                color: #333;
                font-size: 0.95rem;
            }}
            .stock-change {{
                font-weight: 600;
                font-size: 0.9rem;
                padding: 4px 8px;
                border-radius: 4px;
            }}
            .stock-change.positive {{
                color: #e74c3c;
            }}
            .stock-change.negative {{
                color: #27ae60;
            }}
            @media (max-width: 1200px) {{
                .lianban-card {{
                    flex: 1 1 calc(50% - 20px);
                }}
            }}
            @media (max-width: 768px) {{
                .lianban-card {{
                    flex: 1 1 100%;
                }}
            }}
        </style>
        <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.8/dist/chart.umd.min.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-datalabels@2.2.0/dist/chartjs-plugin-datalabels.min.js"></script>
        <script>
            function showPage(pageId) {{
                var limitUpPage = document.getElementById('limit-up-page');
                var boardInfoPage = document.getElementById('board-info-page');
                var capitalFlowPage = document.getElementById('capital-flow-page');
                var chenXiaoqunPage = document.getElementById('chen-xiaoqun-page');
                var navItems = document.querySelectorAll('.nav-item');
                var headerTitle = document.querySelector('h1');
                var headerSubtitle = document.querySelector('.subtitle');
                
                if (pageId === 'limit-up') {{
                    limitUpPage.style.display = 'block';
                    boardInfoPage.style.display = 'none';
                    capitalFlowPage.style.display = 'none';
                    chenXiaoqunPage.style.display = 'none';
                    navItems[0].classList.remove('active');
                    navItems[1].classList.remove('active');
                    navItems[2].classList.add('active');
                    navItems[3].classList.remove('active');
                    headerTitle.textContent = '🚀 涨停股池数据';
                    headerSubtitle.textContent = '实时更新的涨停板行情数据';
                    initLimitUpCharts();
                }} else if (pageId === 'board-info') {{
                    limitUpPage.style.display = 'none';
                    boardInfoPage.style.display = 'block';
                    capitalFlowPage.style.display = 'none';
                    chenXiaoqunPage.style.display = 'none';
                    navItems[0].classList.remove('active');
                    navItems[1].classList.add('active');
                    navItems[2].classList.remove('active');
                    navItems[3].classList.remove('active');
                    headerTitle.textContent = '📊 概念板块信息';
                    headerSubtitle.textContent = '实时更新的概念板块行情数据';
                    initCharts();
                }} else if (pageId === 'capital-flow') {{
                    limitUpPage.style.display = 'none';
                    boardInfoPage.style.display = 'none';
                    capitalFlowPage.style.display = 'block';
                    chenXiaoqunPage.style.display = 'none';
                    navItems[0].classList.add('active');
                    navItems[1].classList.remove('active');
                    navItems[2].classList.remove('active');
                    navItems[3].classList.remove('active');
                    headerTitle.textContent = '💰 资金流向数据';
                    headerSubtitle.textContent = '实时更新的资金流向统计数据';
                }} else if (pageId === 'chen-xiaoqun') {{
                    limitUpPage.style.display = 'none';
                    boardInfoPage.style.display = 'none';
                    capitalFlowPage.style.display = 'none';
                    chenXiaoqunPage.style.display = 'block';
                    navItems[0].classList.remove('active');
                    navItems[1].classList.remove('active');
                    navItems[2].classList.remove('active');
                    navItems[3].classList.add('active');
                    headerTitle.textContent = '👤 陈小群追踪';
                    headerSubtitle.textContent = '知名游资陈小群龙虎榜追踪';
                }}
            }}
            
            function exportToCSV() {{
                const table = document.querySelector('#limit-up-page table');
                if (!table) {{
                    alert('未找到数据表');
                    return;
                }}
                
                let csv = [];
                const rows = table.querySelectorAll('tr');
                
                for (let i = 0; i < rows.length; i++) {{
                    const row = [], cols = rows[i].querySelectorAll('td, th');
                    
                    for (let j = 0; j < cols.length; j++) {{
                        let text = cols[j].innerText.replace(/,/g, '，').replace(/\\n/g, ' ');
                        row.push('"' + text + '"');
                    }}
                    
                    csv.push(row.join(','));
                }}
                
                const csvFile = new Blob([csv.join('\\n')], {{ type: 'text/csv;charset=utf-8;' }});
                const downloadLink = document.createElement('a');
                downloadLink.download = '涨停股池_' + new Date().toISOString().slice(0, 10) + '.csv';
                downloadLink.href = window.URL.createObjectURL(csvFile);
                downloadLink.style.display = 'none';
                document.body.appendChild(downloadLink);
                downloadLink.click();
                document.body.removeChild(downloadLink);
            }}
            
            function refreshCurrentPage() {{
                const activeNavItem = document.querySelector('.nav-item.active');
                if (activeNavItem) {{
                    const pageId = activeNavItem.onclick.toString().match(/'([^']+)'/)[1];
                    showPage(pageId);
                    updateRefreshTime();
                    if (pageId === 'limit-up') {{
                        initLimitUpCharts();
                    }}
                }}
            }}
            
            function updateRefreshTime() {{
                const now = new Date();
                const timeStr = now.toLocaleString('zh-CN', {{
                    year: 'numeric',
                    month: '2-digit',
                    day: '2-digit',
                    hour: '2-digit',
                    minute: '2-digit',
                    second: '2-digit'
                }});
                const refreshTimeElements = document.querySelectorAll('.refresh-time');
                refreshTimeElements.forEach(element => {{
                    element.textContent = '最后刷新: ' + timeStr;
                }});
            }}
            
            window.onload = function() {{
                updateRefreshTime();
                startAutoRefresh();
                initLimitUpCharts();
            }}
            
            function startAutoRefresh() {{
                setInterval(function() {{
                    console.log('15分钟自动刷新页面以更新新闻...');
                    location.reload();
                }}, 15 * 60 * 1000);
            }}

            function initCharts() {{
            // 上涨下跌饼图
            const upDownCtx = document.getElementById('upDownChart').getContext('2d');
            new Chart(upDownCtx, {{
                type: 'doughnut',
                plugins: [ChartDataLabels],
                    data: {{
                        labels: ['上涨', '下跌', '平盘'],
                        datasets: [{{
                            data: [{market_activity.loc[market_activity['item'] == '上涨', 'value'].iloc[0] if not market_activity.empty and '上涨' in market_activity['item'].values else 0}, {market_activity.loc[market_activity['item'] == '下跌', 'value'].iloc[0] if not market_activity.empty and '下跌' in market_activity['item'].values else 0}, {market_activity.loc[market_activity['item'] == '平盘', 'value'].iloc[0] if not market_activity.empty and '平盘' in market_activity['item'].values else 0}],
                            backgroundColor: ['#f5cac3', '#84a98c', '#cad2c5'],
                            borderWidth: 0
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {{
                            legend: {{
                                position: 'bottom',
                                labels: {{
                                    font: {{
                                        size: 12
                                    }}
                                }}
                            }},
                            title: {{
                                display: true,
                                text: '市场赚钱效应',
                                font: {{
                                    size: 12,
                                    weight: 'bold'
                                }}
                            }},
                            tooltip: {{
                                callbacks: {{
                                    label: function(context) {{
                                        return context.label + ': ' + context.raw;
                                    }}
                                }}
                            }},
                            datalabels: {{
                                display: true,
                                color: '#ffffff',
                                font: {{
                                    size: 12,
                                    weight: 'bold'
                                }},
                                formatter: function(value, context) {{
                                    return value;
                                }}
                            }}
                        }}
                    }}
                }});
                
                // 涨停跌停饼图
            const limitCtx = document.getElementById('limitChart').getContext('2d');
            new Chart(limitCtx, {{
                type: 'doughnut',
                plugins: [ChartDataLabels],
                    data: {{
                        labels: ['真实涨停', '一字涨停', '真实跌停', '一字跌停'],
                        datasets: [{{
                            data: [{market_activity.loc[market_activity['item'] == '真实涨停', 'value'].iloc[0] if not market_activity.empty and '真实涨停' in market_activity['item'].values else 0}, {market_activity.loc[market_activity['item'] == '涨停', 'value'].iloc[0] - (market_activity.loc[market_activity['item'] == '真实涨停', 'value'].iloc[0] if not market_activity.empty and '真实涨停' in market_activity['item'].values else 0) if not market_activity.empty and '涨停' in market_activity['item'].values else 0}, {market_activity.loc[market_activity['item'] == '真实跌停', 'value'].iloc[0] if not market_activity.empty and '真实跌停' in market_activity['item'].values else 0}, {market_activity.loc[market_activity['item'] == '跌停', 'value'].iloc[0] - (market_activity.loc[market_activity['item'] == '真实跌停', 'value'].iloc[0] if not market_activity.empty and '真实跌停' in market_activity['item'].values else 0) if not market_activity.empty and '跌停' in market_activity['item'].values else 0}],
                            backgroundColor: ['#f28482', '#e5989b', '#84a98c', '#52796f'],
                            borderWidth: 0
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {{
                            legend: {{
                                position: 'bottom',
                                labels: {{
                                    font: {{
                                        size: 12
                                    }}
                                }}
                            }},
                            title: {{
                                display: true,
                                text: '涨停跌停分布（总数=真实+一字）',
                                font: {{
                                    size: 14,
                                    weight: 'bold'
                                }}
                            }},
                            tooltip: {{
                                callbacks: {{
                                    label: function(context) {{
                                        return context.label + ': ' + context.raw;
                                    }}
                                }}
                            }},
                            datalabels: {{
                                display: true,
                                color: '#ffffff',
                                font: {{
                                    size: 12,
                                    weight: 'bold'
                                }},
                                formatter: function(value, context) {{
                                    return value;
                                }}
                            }}
                        }}
                    }}
                }});
            }}
            
            function initLimitUpCharts() {{
                const industryData = {json.dumps(analyze_limit_up_statistics(today_pool)['industry_stats'], ensure_ascii=False)};
                const industryStocks = {json.dumps(analyze_limit_up_statistics(today_pool)['industry_stocks'], ensure_ascii=False)};
                const boardData = {json.dumps(analyze_limit_up_statistics(today_pool)['board_stats'], ensure_ascii=False)};
                
                // 行业分布饼图
                const industryCtx = document.getElementById('industryChart');
                if (industryCtx) {{
                    const industryLabels = Object.keys(industryData).slice(0, 10);
                    const industryValues = industryLabels.map(k => industryData[k]);
                    const colors = ['#e74c3c', '#3498db', '#2ecc71', '#f39c12', '#9b59b6', '#1abc9c', '#e67e22', '#34495e', '#16a085', '#c0392b'];
                    
                    new Chart(industryCtx, {{
                        type: 'pie',
                        data: {{
                            labels: industryLabels,
                            datasets: [{{
                                data: industryValues,
                                backgroundColor: colors,
                                borderWidth: 2,
                                borderColor: '#fff'
                            }}]
                        }},
                        options: {{
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: {{
                                legend: {{
                                    position: 'right',
                                    labels: {{
                                        font: {{ size: 11 }},
                                        padding: 8
                                    }}
                                }},
                                tooltip: {{
                                    callbacks: {{
                                        label: function(context) {{
                                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                            const percentage = ((context.raw / total) * 100).toFixed(1);
                                            const industryName = context.label;
                                            const stocks = industryStocks[industryName] || [];
                                            let stockText = stocks.length > 0 ? '\\n股票: ' + stocks.join(', ') : '';
                                            return context.label + ': ' + context.raw + '只 (' + percentage + '%)' + stockText;
                                        }}
                                    }}
                                }}
                            }}
                        }}
                    }});
                }}
                
                // 连板统计饼图
                const boardCtx = document.getElementById('boardChart');
                if (boardCtx) {{
                    const boardLabels = Object.keys(boardData);
                    const boardValues = boardLabels.map(k => boardData[k]);
                    const boardColors = ['#2ecc71', '#f39c12', '#e74c3c'];
                    
                    new Chart(boardCtx, {{
                        type: 'doughnut',
                        data: {{
                            labels: boardLabels,
                            datasets: [{{
                                data: boardValues,
                                backgroundColor: boardColors,
                                borderWidth: 3,
                                borderColor: '#fff'
                            }}]
                        }},
                        options: {{
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: {{
                                legend: {{
                                    position: 'bottom',
                                    labels: {{
                                        font: {{ size: 14, weight: 'bold' }},
                                        padding: 15
                                    }}
                                }},
                                tooltip: {{
                                    callbacks: {{
                                        label: function(context) {{
                                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                            const percentage = ((context.raw / total) * 100).toFixed(1);
                                            return context.label + ': ' + context.raw + '只 (' + percentage + '%)';
                                        }}
                                    }}
                                }}
                            }}
                        }}
                    }});
                }}
            }}
        </script>
    </head>
    <body>
        <div class="news-ticker">
            <div class="news-label">📰 财经快讯</div>
            <div class="news-content">
                <div class="news-scroll" id="newsScroll">
                    """ + news_html + """
                </div>
            </div>
        </div>
        <div class="sidebar">
            <div class="sidebar-title">📊 复盘助手</div>
            <div class="nav-menu">
                <div class="nav-item" onclick="showPage('capital-flow')">💰 资金流向</div>
                <div class="nav-item" onclick="showPage('board-info')">📊 板块信息</div>
                <div class="nav-item active" onclick="showPage('limit-up')">📈 涨停股池数据</div>
                <div class="nav-item" onclick="showPage('chen-xiaoqun')">👤 陈小群追踪</div>
            </div>
        </div>
        <div class="main-content">
            <div class="header">
                <h1>🚀 涨停股池数据</h1>
                <p class="subtitle">实时更新的涨停板行情数据</p>
                <p class="refresh-time" style="color: rgba(255,255,255,0.7); font-size: 0.9em; margin-top: 5px;"></p>
            </div>
            <button class="refresh-btn" onclick="refreshCurrentPage()">🔄 刷新数据</button>
            <div class="container">
            <div id="limit-up-page" class="page-content">
            
    """
    
    # 添加连板分类区域
    if not today_pool.empty:
        # 提取连板数大于1的股票
        lianban_stocks = today_pool[today_pool['连板数'] > 1]
        
        if not lianban_stocks.empty:
            # 按连板数分组
            lianban_groups = lianban_stocks.groupby('连板数')
            
            html += """
            <div class="lianban-section">
                <div class="lianban-cards">
            """
            
            for lianban_num, group in sorted(lianban_groups):
                # 为每个连板数分配不同底色（低饱和度）
                colors = ['#e3ddd7', '#d7e3de', '#d7e1e3', '#ded7e3']
                color_idx = (lianban_num - 2) % len(colors)
                bg_color = colors[color_idx]
                
                stocks_list = []
                for _, row in group.iterrows():
                    stocks_list.append(f"""
                        <div class="lianban-stock-item">
                            <div class="stock-code">{row['代码']}</div>
                            <div class="stock-name">{row['名称']}</div>
                            <div class="stock-change {'positive' if row['涨跌幅'] > 0 else 'negative'}">{row['涨跌幅']:.2f}%</div>
                        </div>
                    """)
                
                html += f"""
                    <div class="lianban-card" style="background-color: {bg_color};">
                        <div class="lianban-title">{lianban_num}连板</div>
                        <div class="lianban-divider"></div>
                        <div class="lianban-count">共 {len(group)} 只</div>
                        <div class="lianban-stocks">
                            {''.join(stocks_list)}
                        </div>
                    </div>
                """
            
            html += """
                </div>
            </div>
            """
    
    html += """
            <div class="section">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                    <h2 style="margin-bottom: 0;">📈 今日涨停股池 - """ + today_str + """ <span style="font-size: 0.8em; color: #666;">(共 """ + str(len(today_pool)) + """ 只)</span></h2>
                    <button onclick="exportToCSV()" style="padding: 8px 16px; background: #27ae60; color: white; border: none; border-radius: 5px; cursor: pointer; font-size: 14px; font-weight: 600; transition: all 0.3s ease;">📥 导出CSV</button>
                </div>
                
                <div class="charts-section" style="display: flex; gap: 20px; margin-bottom: 30px; flex-wrap: wrap;">
                    <div class="chart-card" style="flex: 1; min-width: 300px; background: #f8f9fa; border-radius: 10px; padding: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                        <h3 style="text-align: center; color: #2c3e50; margin-bottom: 15px; font-size: 1.2rem;">📊 行业分布</h3>
                        <div style="position: relative; height: 300px;">
                            <canvas id="industryChart"></canvas>
                        </div>
                    </div>
                    
                    <div class="chart-card" style="flex: 1; min-width: 300px; background: #f8f9fa; border-radius: 10px; padding: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                        <h3 style="text-align: center; color: #2c3e50; margin-bottom: 15px; font-size: 1.2rem;">📈 连板统计</h3>
                        <div style="position: relative; height: 300px;">
                            <canvas id="boardChart"></canvas>
                        </div>
                    </div>
                </div>
                
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
                            <th>换手率(%)</th>
                            <th>封板资金(亿)</th>
                            <th>首次封板时间</th>
                            <th>最后封板时间</th>
                            <th>炸板次数</th>
                            <th>涨停统计</th>
                            <th>连板数</th>
                            <th>所属行业</th>
                            <th>涨停原因</th>
                        </tr>
    """
    
    if not today_pool.empty:
        for _, row in today_pool.iterrows():
            change_class = 'positive' if row['涨跌幅'] > 0 else 'negative'
            limit_up_reason = row.get('涨停原因', '未知')
            stock_url = get_stock_url(row['代码'])
            html += f"""
                        <tr>
                            <td>{int(row['序号'])}</td>
                            <td>{row['代码']}</td>
                            <td><a href="{stock_url}" target="_blank" style="color: #3498db; text-decoration: none; font-weight: 500;">{row['名称']}</a></td>
                            <td class="{change_class}">{row['涨跌幅']:.2f}</td>
                            <td>{row['最新价']:.2f}</td>
                            <td>{row['成交额']/100000000:.2f}</td>
                            <td>{row['流通市值']/100000000:.2f}</td>
                            <td>{row['换手率']:.2f}</td>
                            <td>{row['封板资金']/100000000:.2f}</td>
                            <td>{format_time(row['首次封板时间'])}</td>
                            <td>{format_time(row['最后封板时间'])}</td>
                            <td>{int(row['炸板次数'])}</td>
                            <td>{row['涨停统计']}</td>
                            <td>{int(row['连板数'])}</td>
                            <td>{row['所属行业']}</td>
                            <td style="color: #e74c3c; font-weight: 500;">{limit_up_reason}</td>
                        </tr>
            """
    else:
        html += """
                        <tr>
                            <td colspan="17" style="text-align: center; padding: 20px; color: #999;">暂无数据</td>
                        </tr>
        """
    
    html += """
                    </table>
                </div>
            </div>
            </div>
            <div id="capital-flow-page" class="page-content" style="display: none;">
            <div class="section">
                <h2>📊 概念资金流排行</h2>
                <div style="display: flex; gap: 10px; width: 100%; overflow-x: auto;">
                    <div style="flex: 1; min-width: 0;">
                        <h3>即时排行</h3>
                        <div class="table-container" style="width: 100%;">
                            <table>
                                <tr>
                                    <th style="width: 12%;">排名</th>
                                    <th style="width: 48%;">概念板块</th>
                                    <th style="width: 12%;">净额(亿)</th>
                                    <th style="width: 12%;">阶段涨跌幅</th>
                                    <th style="width: 16%;">主力净流入占比(%)</th>
                                </tr>
                                """
    if capital_flow_data and "即时" in capital_flow_data and not capital_flow_data["即时"].empty:
        sorted_df = capital_flow_data["即时"].sort_values(by="净额", ascending=False).head(20)
        for idx, row in sorted_df.iterrows():
            change_pct = row.get('行业-涨跌幅', '0%')
            if isinstance(change_pct, str) and '%' in change_pct:
                change_value = float(change_pct.replace('%', ''))
                display_pct = change_pct
            else:
                change_value = float(change_pct) if pd.notna(change_pct) else 0
                display_pct = f"{change_value:.2f}%"
            
            inflow = row.get('流入资金', 0)
            outflow = row.get('流出资金', 0)
            net_amount = row.get('净额', 0)
            if inflow + outflow != 0:
                net_flow_ratio = (net_amount / (inflow + outflow)) * 100
            else:
                net_flow_ratio = 0
            net_flow_class = 'positive' if net_flow_ratio > 0 else 'negative'
            
            html += f"""
                                <tr>
                                    <td>{idx + 1}</td>
                                    <td>{row['行业']}</td>
                                    <td class="{'positive' if row['净额'] > 0 else 'negative'}">{row['净额']:.2f}</td>
                                    <td class="{'positive' if change_value > 0 else 'negative'}">{display_pct}</td>
                                    <td class="{net_flow_class}">{net_flow_ratio:.2f}</td>
                                </tr>
            """
    else:
        html += """
                                <tr>
                                    <td colspan="5" style="text-align: center; padding: 20px; color: #999;">暂无数据</td>
                                </tr>
        """
    html += """
                            </table>
                        </div>
                    </div>
                    
                    <div style="flex: 1; min-width: 0;">
                        <h3>3日排行</h3>
                        <div class="table-container" style="width: 100%;">
                            <table>
                                <tr>
                                    <th style="width: 12%;">排名</th>
                                    <th style="width: 48%;">概念板块</th>
                                    <th style="width: 12%;">净额(亿)</th>
                                    <th style="width: 12%;">阶段涨跌幅</th>
                                    <th style="width: 16%;">主力净流入占比(%)</th>
                                </tr>
                                """
    if capital_flow_data and "3日" in capital_flow_data and not capital_flow_data["3日"].empty:
        # 按净流入降序排列
        sorted_df = capital_flow_data["3日"].sort_values(by="净额", ascending=False).head(20)
        for idx, row in sorted_df.iterrows():
            change_pct = row.get('阶段涨跌幅', '0%')
            if isinstance(change_pct, str) and '%' in change_pct:
                change_value = float(change_pct.replace('%', ''))
            else:
                change_value = float(change_pct) if pd.notna(change_pct) else 0
            
            inflow = row.get('流入资金', 0)
            outflow = row.get('流出资金', 0)
            net_amount = row.get('净额', 0)
            if inflow + outflow != 0:
                net_flow_ratio = (net_amount / (inflow + outflow)) * 100
            else:
                net_flow_ratio = 0
            net_flow_class = 'positive' if net_flow_ratio > 0 else 'negative'
            
            html += f"""
                                <tr>
                                    <td>{idx + 1}</td>
                                    <td>{row['行业']}</td>
                                    <td class="{'positive' if row['净额'] > 0 else 'negative'}">{row['净额']:.2f}</td>
                                    <td class="{'positive' if change_value > 0 else 'negative'}">{change_pct}</td>
                                    <td class="{net_flow_class}">{net_flow_ratio:.2f}</td>
                                </tr>
            """
    else:
        html += """
                                <tr>
                                    <td colspan="5" style="text-align: center; padding: 20px; color: #999;">暂无数据</td>
                                </tr>
        """
    html += """
                            </table>
                        </div>
                    </div>
                    
                    <div style="flex: 1;">
                        <h3>5日排行</h3>
                        <div class="table-container" style="width: 100%;">
                            <table>
                                <tr>
                                    <th style="width: 12%;">排名</th>
                                    <th style="width: 48%;">概念板块</th>
                                    <th style="width: 12%;">净额(亿)</th>
                                    <th style="width: 12%;">阶段涨跌幅</th>
                                    <th style="width: 16%;">主力净流入占比(%)</th>
                                </tr>
                                """
    if capital_flow_data and "5日" in capital_flow_data and not capital_flow_data["5日"].empty:
        # 按净流入降序排列
        sorted_df = capital_flow_data["5日"].sort_values(by="净额", ascending=False).head(20)
        for idx, row in sorted_df.iterrows():
            change_pct = row.get('阶段涨跌幅', '0%')
            if isinstance(change_pct, str) and '%' in change_pct:
                change_value = float(change_pct.replace('%', ''))
            else:
                change_value = float(change_pct) if pd.notna(change_pct) else 0
            
            inflow = row.get('流入资金', 0)
            outflow = row.get('流出资金', 0)
            net_amount = row.get('净额', 0)
            if inflow + outflow != 0:
                net_flow_ratio = (net_amount / (inflow + outflow)) * 100
            else:
                net_flow_ratio = 0
            net_flow_class = 'positive' if net_flow_ratio > 0 else 'negative'
            
            html += f"""
                                <tr>
                                    <td>{idx + 1}</td>
                                    <td>{row['行业']}</td>
                                    <td class="{'positive' if row['净额'] > 0 else 'negative'}">{row['净额']:.2f}</td>
                                    <td class="{'positive' if change_value > 0 else 'negative'}">{change_pct}</td>
                                    <td class="{net_flow_class}">{net_flow_ratio:.2f}</td>
                                </tr>
            """
    else:
        html += """
                                <tr>
                                    <td colspan="5" style="text-align: center; padding: 20px; color: #999;">暂无数据</td>
                                </tr>
        """
    html += """
                            </table>
                        </div>
                    </div>
                    
                    <div style="flex: 1; min-width: 0;">
                        <h3>10日排行</h3>
                        <div class="table-container" style="width: 100%;">
                            <table>
                                <tr>
                                    <th style="width: 12%;">排名</th>
                                    <th style="width: 48%;">概念板块</th>
                                    <th style="width: 12%;">净额(亿)</th>
                                    <th style="width: 12%;">阶段涨跌幅</th>
                                    <th style="width: 16%;">主力净流入占比(%)</th>
                                </tr>
                                """
    if capital_flow_data and "10日" in capital_flow_data and not capital_flow_data["10日"].empty:
        # 按净流入降序排列
        sorted_df = capital_flow_data["10日"].sort_values(by="净额", ascending=False).head(20)
        for idx, row in sorted_df.iterrows():
            change_pct = row.get('阶段涨跌幅', '0%')
            if isinstance(change_pct, str) and '%' in change_pct:
                change_value = float(change_pct.replace('%', ''))
            else:
                change_value = float(change_pct) if pd.notna(change_pct) else 0
            
            inflow = row.get('流入资金', 0)
            outflow = row.get('流出资金', 0)
            net_amount = row.get('净额', 0)
            if inflow + outflow != 0:
                net_flow_ratio = (net_amount / (inflow + outflow)) * 100
            else:
                net_flow_ratio = 0
            net_flow_class = 'positive' if net_flow_ratio > 0 else 'negative'
            
            html += f"""
                                <tr>
                                    <td>{idx + 1}</td>
                                    <td>{row['行业']}</td>
                                    <td class="{'positive' if row['净额'] > 0 else 'negative'}">{row['净额']:.2f}</td>
                                    <td class="{'positive' if change_value > 0 else 'negative'}">{change_pct}</td>
                                    <td class="{net_flow_class}">{net_flow_ratio:.2f}</td>
                                </tr>
            """
    else:
        html += """
                                <tr>
                                    <td colspan="5" style="text-align: center; padding: 20px; color: #999;">暂无数据</td>
                                </tr>
        """
    html += """
                            </table>
                        </div>
                    </div>
                    
                    <div style="flex: 1;">
                        <h3>20日排行</h3>
                        <div class="table-container" style="width: 100%;">
                            <table>
                                <tr>
                                    <th style="width: 12%;">排名</th>
                                    <th style="width: 48%;">概念板块</th>
                                    <th style="width: 12%;">净额(亿)</th>
                                    <th style="width: 12%;">阶段涨跌幅</th>
                                    <th style="width: 16%;">主力净流入占比(%)</th>
                                </tr>
                                """
    if capital_flow_data and "20日" in capital_flow_data and not capital_flow_data["20日"].empty:
        # 按净流入降序排列
        sorted_df = capital_flow_data["20日"].sort_values(by="净额", ascending=False).head(20)
        for idx, row in sorted_df.iterrows():
            change_pct = row.get('阶段涨跌幅', '0%')
            if isinstance(change_pct, str) and '%' in change_pct:
                change_value = float(change_pct.replace('%', ''))
            else:
                change_value = float(change_pct) if pd.notna(change_pct) else 0
            
            inflow = row.get('流入资金', 0)
            outflow = row.get('流出资金', 0)
            net_amount = row.get('净额', 0)
            if inflow + outflow != 0:
                net_flow_ratio = (net_amount / (inflow + outflow)) * 100
            else:
                net_flow_ratio = 0
            net_flow_class = 'positive' if net_flow_ratio > 0 else 'negative'
            
            html += f"""
                                <tr>
                                    <td>{idx + 1}</td>
                                    <td>{row['行业']}</td>
                                    <td class="{'positive' if row['净额'] > 0 else 'negative'}">{row['净额']:.2f}</td>
                                    <td class="{'positive' if change_value > 0 else 'negative'}">{change_pct}</td>
                                    <td class="{net_flow_class}">{net_flow_ratio:.2f}</td>
                                </tr>
            """
    else:
        html += """
                                <tr>
                                    <td colspan="4" style="text-align: center; padding: 20px; color: #999;">暂无数据</td>
                                </tr>
        """
    html += """
                            </table>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="section">
                <h2>📊 行业资金流排行</h2>
                <div style="display: flex; gap: 10px; width: 100%; overflow-x: auto;">
                    <div style="flex: 1; min-width: 0;">
                        <h3>即时排行</h3>
                        <div class="table-container" style="width: 100%;">
                            <table>
                                <tr>
                                    <th style="width: 12%;">排名</th>
                                    <th style="width: 48%;">行业板块</th>
                                    <th style="width: 12%;">净额(亿)</th>
                                    <th style="width: 12%;">阶段涨跌幅</th>
                                    <th style="width: 16%;">主力净流入占比(%)</th>
                                </tr>
                                """
    if industry_flow_data and "即时" in industry_flow_data and not industry_flow_data["即时"].empty:
        sorted_df = industry_flow_data["即时"].sort_values(by="净额", ascending=False).head(20)
        for idx, row in sorted_df.iterrows():
            change_pct = row.get('行业-涨跌幅', '0%')
            if isinstance(change_pct, str) and '%' in change_pct:
                change_value = float(change_pct.replace('%', ''))
                display_pct = change_pct
            else:
                change_value = float(change_pct) if pd.notna(change_pct) else 0
                display_pct = f"{change_value:.2f}%"
            
            inflow = row.get('流入资金', 0)
            outflow = row.get('流出资金', 0)
            net_amount = row.get('净额', 0)
            if inflow + outflow != 0:
                net_flow_ratio = (net_amount / (inflow + outflow)) * 100
            else:
                net_flow_ratio = 0
            net_flow_class = 'positive' if net_flow_ratio > 0 else 'negative'
            
            html += f"""
                                <tr>
                                    <td>{idx + 1}</td>
                                    <td>{row['行业']}</td>
                                    <td class="{'positive' if row['净额'] > 0 else 'negative'}">{row['净额']:.2f}</td>
                                    <td class="{'positive' if change_value > 0 else 'negative'}">{display_pct}</td>
                                    <td class="{net_flow_class}">{net_flow_ratio:.2f}</td>
                                </tr>
            """
    else:
        html += """
                                <tr>
                                    <td colspan="4" style="text-align: center; padding: 20px; color: #999;">暂无数据</td>
                                </tr>
        """
    html += """
                            </table>
                        </div>
                    </div>
                    
                    <div style="flex: 1; min-width: 0;">
                        <h3>3日排行</h3>
                        <div class="table-container" style="width: 100%;">
                            <table>
                                <tr>
                                    <th style="width: 12%;">排名</th>
                                    <th style="width: 48%;">行业板块</th>
                                    <th style="width: 12%;">净额(亿)</th>
                                    <th style="width: 12%;">阶段涨跌幅</th>
                                    <th style="width: 16%;">主力净流入占比(%)</th>
                                </tr>
                                """
    if industry_flow_data and "3日" in industry_flow_data and not industry_flow_data["3日"].empty:
        # 按净流入降序排列
        sorted_df = industry_flow_data["3日"].sort_values(by="净额", ascending=False).head(20)
        for idx, row in sorted_df.iterrows():
            change_pct = row.get('阶段涨跌幅', '0%')
            if isinstance(change_pct, str) and '%' in change_pct:
                change_value = float(change_pct.replace('%', ''))
            else:
                change_value = float(change_pct) if pd.notna(change_pct) else 0
            
            inflow = row.get('流入资金', 0)
            outflow = row.get('流出资金', 0)
            net_amount = row.get('净额', 0)
            if inflow + outflow != 0:
                net_flow_ratio = (net_amount / (inflow + outflow)) * 100
            else:
                net_flow_ratio = 0
            net_flow_class = 'positive' if net_flow_ratio > 0 else 'negative'
            
            html += f"""
                                <tr>
                                    <td>{idx + 1}</td>
                                    <td>{row['行业']}</td>
                                    <td class="{'positive' if row['净额'] > 0 else 'negative'}">{row['净额']:.2f}</td>
                                    <td class="{'positive' if change_value > 0 else 'negative'}">{change_pct}</td>
                                    <td class="{net_flow_class}">{net_flow_ratio:.2f}</td>
                                </tr>
            """
    else:
        html += """
                                <tr>
                                    <td colspan="5" style="text-align: center; padding: 20px; color: #999;">暂无数据</td>
                                </tr>
        """
    html += """
                            </table>
                        </div>
                    </div>
                    
                    <div style="flex: 1; min-width: 0;">
                        <h3>5日排行</h3>
                        <div class="table-container" style="width: 100%;">
                            <table>
                                <tr>
                                    <th style="width: 12%;">排名</th>
                                    <th style="width: 48%;">行业板块</th>
                                    <th style="width: 12%;">净额(亿)</th>
                                    <th style="width: 12%;">阶段涨跌幅</th>
                                    <th style="width: 16%;">主力净流入占比(%)</th>
                                </tr>
                                """
    if industry_flow_data and "5日" in industry_flow_data and not industry_flow_data["5日"].empty:
        # 按净流入降序排列
        sorted_df = industry_flow_data["5日"].sort_values(by="净额", ascending=False).head(20)
        for idx, row in sorted_df.iterrows():
            change_pct = row.get('阶段涨跌幅', '0%')
            if isinstance(change_pct, str) and '%' in change_pct:
                change_value = float(change_pct.replace('%', ''))
            else:
                change_value = float(change_pct) if pd.notna(change_pct) else 0
            
            inflow = row.get('流入资金', 0)
            outflow = row.get('流出资金', 0)
            net_amount = row.get('净额', 0)
            if inflow + outflow != 0:
                net_flow_ratio = (net_amount / (inflow + outflow)) * 100
            else:
                net_flow_ratio = 0
            net_flow_class = 'positive' if net_flow_ratio > 0 else 'negative'
            
            html += f"""
                                <tr>
                                    <td>{idx + 1}</td>
                                    <td>{row['行业']}</td>
                                    <td class="{'positive' if row['净额'] > 0 else 'negative'}">{row['净额']:.2f}</td>
                                    <td class="{'positive' if change_value > 0 else 'negative'}">{change_pct}</td>
                                    <td class="{net_flow_class}">{net_flow_ratio:.2f}</td>
                                </tr>
            """
    else:
        html += """
                                <tr>
                                    <td colspan="5" style="text-align: center; padding: 20px; color: #999;">暂无数据</td>
                                </tr>
        """
    html += """
                            </table>
                        </div>
                    </div>
                    
                    <div style="flex: 1; min-width: 0;">
                        <h3>10日排行</h3>
                        <div class="table-container" style="width: 100%;">
                            <table>
                                <tr>
                                    <th style="width: 12%;">排名</th>
                                    <th style="width: 48%;">行业板块</th>
                                    <th style="width: 12%;">净额(亿)</th>
                                    <th style="width: 12%;">阶段涨跌幅</th>
                                    <th style="width: 16%;">主力净流入占比(%)</th>
                                </tr>
                                """
    if industry_flow_data and "10日" in industry_flow_data and not industry_flow_data["10日"].empty:
        # 按净流入降序排列
        sorted_df = industry_flow_data["10日"].sort_values(by="净额", ascending=False).head(20)
        for idx, row in sorted_df.iterrows():
            change_pct = row.get('阶段涨跌幅', '0%')
            if isinstance(change_pct, str) and '%' in change_pct:
                change_value = float(change_pct.replace('%', ''))
            else:
                change_value = float(change_pct) if pd.notna(change_pct) else 0
            
            inflow = row.get('流入资金', 0)
            outflow = row.get('流出资金', 0)
            net_amount = row.get('净额', 0)
            if inflow + outflow != 0:
                net_flow_ratio = (net_amount / (inflow + outflow)) * 100
            else:
                net_flow_ratio = 0
            net_flow_class = 'positive' if net_flow_ratio > 0 else 'negative'
            
            html += f"""
                                <tr>
                                    <td>{idx + 1}</td>
                                    <td>{row['行业']}</td>
                                    <td class="{'positive' if row['净额'] > 0 else 'negative'}">{row['净额']:.2f}</td>
                                    <td class="{'positive' if change_value > 0 else 'negative'}">{change_pct}</td>
                                    <td class="{net_flow_class}">{net_flow_ratio:.2f}</td>
                                </tr>
            """
    else:
        html += """
                                <tr>
                                    <td colspan="5" style="text-align: center; padding: 20px; color: #999;">暂无数据</td>
                                </tr>
        """
    html += """
                            </table>
                        </div>
                    </div>
                    
                    <div style="flex: 1; min-width: 0;">
                        <h3>20日排行</h3>
                        <div class="table-container" style="width: 100%;">
                            <table>
                                <tr>
                                    <th style="width: 12%;">排名</th>
                                    <th style="width: 48%;">行业板块</th>
                                    <th style="width: 12%;">净额(亿)</th>
                                    <th style="width: 12%;">阶段涨跌幅</th>
                                    <th style="width: 16%;">主力净流入占比(%)</th>
                                </tr>
                                """
    if industry_flow_data and "20日" in industry_flow_data and not industry_flow_data["20日"].empty:
        # 按净流入降序排列
        sorted_df = industry_flow_data["20日"].sort_values(by="净额", ascending=False).head(20)
        for idx, row in sorted_df.iterrows():
            change_pct = row.get('阶段涨跌幅', '0%')
            if isinstance(change_pct, str) and '%' in change_pct:
                change_value = float(change_pct.replace('%', ''))
            else:
                change_value = float(change_pct) if pd.notna(change_pct) else 0
            
            inflow = row.get('流入资金', 0)
            outflow = row.get('流出资金', 0)
            net_amount = row.get('净额', 0)
            if inflow + outflow != 0:
                net_flow_ratio = (net_amount / (inflow + outflow)) * 100
            else:
                net_flow_ratio = 0
            net_flow_class = 'positive' if net_flow_ratio > 0 else 'negative'
            
            html += f"""
                                <tr>
                                    <td>{idx + 1}</td>
                                    <td>{row['行业']}</td>
                                    <td class="{'positive' if row['净额'] > 0 else 'negative'}">{row['净额']:.2f}</td>
                                    <td class="{'positive' if change_value > 0 else 'negative'}">{change_pct}</td>
                                    <td class="{net_flow_class}">{net_flow_ratio:.2f}</td>
                                </tr>
            """
    else:
        html += """
                                <tr>
                                    <td colspan="4" style="text-align: center; padding: 20px; color: #999;">暂无数据</td>
                                </tr>
        """
    html += """
                            </table>
                        </div>
                    </div>
                </div>
            </div>
            </div>
            <div id="board-info-page" class="page-content" style="display: none;">
            <div class="section">
                <h2>� 市场赚钱效应 <span style="font-size: 0.8em; color: #666;">实时统计</span></h2>
                <div class="market-activity-container">
                    <div class="activity-grid">
                        <div class="activity-card positive">
                            <div class="activity-icon">📈</div>
                            <div class="activity-title">上涨家数</div>
                            <div class="activity-value">""" + str(market_activity.loc[market_activity['item'] == '上涨', 'value'].iloc[0] if not market_activity.empty and '上涨' in market_activity['item'].values else '0') + """</div>
                        </div>
                        <div class="activity-card positive">
                            <div class="activity-icon">🔥</div>
                            <div class="activity-title">涨停家数</div>
                            <div class="activity-value">""" + str(market_activity.loc[market_activity['item'] == '涨停', 'value'].iloc[0] if not market_activity.empty and '涨停' in market_activity['item'].values else '0') + """</div>
                        </div>
                        <div class="activity-card positive">
                            <div class="activity-icon">💎</div>
                            <div class="activity-title">真实涨停</div>
                            <div class="activity-value">""" + str(market_activity.loc[market_activity['item'] == '真实涨停', 'value'].iloc[0] if not market_activity.empty and '真实涨停' in market_activity['item'].values else '0') + """</div>
                        </div>
                        <div class="activity-card negative">
                            <div class="activity-icon">📉</div>
                            <div class="activity-title">下跌家数</div>
                            <div class="activity-value">""" + str(market_activity.loc[market_activity['item'] == '下跌', 'value'].iloc[0] if not market_activity.empty and '下跌' in market_activity['item'].values else '0') + """</div>
                        </div>
                        <div class="activity-card negative">
                            <div class="activity-icon">💧</div>
                            <div class="activity-title">跌停家数</div>
                            <div class="activity-value">""" + str(market_activity.loc[market_activity['item'] == '跌停', 'value'].iloc[0] if not market_activity.empty and '跌停' in market_activity['item'].values else '0') + """</div>
                        </div>
                        <div class="activity-card negative">
                            <div class="activity-icon">💣</div>
                            <div class="activity-title">真实跌停</div>
                            <div class="activity-value">""" + str(market_activity.loc[market_activity['item'] == '真实跌停', 'value'].iloc[0] if not market_activity.empty and '真实跌停' in market_activity['item'].values else '0') + """</div>
                        </div>
                        <div class="activity-card neutral">
                            <div class="activity-icon">📊</div>
                            <div class="activity-title">市场活跃度</div>
                            <div class="activity-value">""" + str(market_activity.loc[market_activity['item'] == '活跃度', 'value'].iloc[0] if not market_activity.empty and '活跃度' in market_activity['item'].values else '0%') + """</div>
                        </div>
                        <div class="activity-card neutral">
                            <div class="activity-icon">⏸️</div>
                            <div class="activity-title">平盘家数</div>
                            <div class="activity-value">""" + str(market_activity.loc[market_activity['item'] == '平盘', 'value'].iloc[0] if not market_activity.empty and '平盘' in market_activity['item'].values else '0') + """</div>
                        </div>
                        <div class="activity-card neutral">
                            <div class="activity-icon">🚫</div>
                            <div class="activity-title">停牌家数</div>
                            <div class="activity-value">""" + str(market_activity.loc[market_activity['item'] == '停牌', 'value'].iloc[0] if not market_activity.empty and '停牌' in market_activity['item'].values else '0') + """</div>
                        </div>
                    </div>
                </div>
            </div>
            <div class="section">
                <h2>📊 市场分布饼图 <span style="font-size: 0.8em; color: #666;">可视化分析</span></h2>
                <div class="chart-container">
                    <div class="chart-card">
                        <div class="chart-title">上涨下跌分布</div>
                        <canvas id="upDownChart" class="chart-canvas"></canvas>
                    </div>
                    <div class="chart-card">
                        <div class="chart-title">涨停跌停分布</div>
                        <canvas id="limitChart" class="chart-canvas"></canvas>
                    </div>
                </div>
            </div>
            <div class="section">
                <h2>�� 板块信息 <span style="font-size: 0.8em; color: #666;">概念与行业</span></h2>
                <div style="display: flex; gap: 20px; width: 100%;">
                    <div style="flex: 1; margin-right: 10px;">
                        <h3>概念板块 (共 """ + str(len(board_info)) + """ 个)</h3>
                        <div class="table-container" style="width: 100%;">
                            <table>
                                <tr>
                                    <th>排名</th>
                                    <th>板块名称</th>
                                    <th>板块代码</th>
                                    <th>最新价</th>
                                    <th>涨跌幅(%)</th>
                                    <th>总市值(亿)</th>
                                    <th>换手率(%)</th>
                                    <th>上涨家数</th>
                                    <th>下跌家数</th>
                                    <th>领涨股票</th>
                                    <th>领涨股票-涨跌幅(%)</th>
                                </tr>
    """
    
    if not board_info.empty:
        for _, row in board_info.iterrows():
            change_class = 'positive' if row['涨跌幅'] > 0 else 'negative'
            html += f"""
                                <tr>
                                    <td>{int(row['排名'])}</td>
                                    <td>{row['板块名称']}</td>
                                    <td>{row['板块代码']}</td>
                                    <td>{row['最新价']:.2f}</td>
                                    <td class="{change_class}">{row['涨跌幅']:.2f}</td>
                                    <td>{row['总市值']/100000000:.2f}</td>
                                    <td>{row['换手率']:.2f}</td>
                                    <td>{int(row['上涨家数'])}</td>
                                    <td>{int(row['下跌家数'])}</td>
                                    <td>{row['领涨股票']}</td>
                                    <td class="{change_class}">{row['领涨股票-涨跌幅']:.2f}</td>
                                </tr>
            """
    else:
        html += """
                                <tr>
                                    <td colspan="11" style="text-align: center; padding: 20px; color: #999;">暂无数据</td>
                                </tr>
        """
    
    html += """
                            </table>
                        </div>
                    </div>
                    <div style="flex: 1; margin-left: 10px;">
                        <h3>行业板块 (共 """ + str(len(industry_info)) + """ 个)</h3>
                        <div class="table-container" style="width: 100%;">
                            <table>
                                <tr>
                                    <th>排名</th>
                                    <th>板块名称</th>
                                    <th>涨跌幅(%)</th>
                                    <th>总成交量(万手)</th>
                                    <th>总成交额(亿元)</th>
                                    <th>净流入(亿元)</th>
                                    <th>上涨家数</th>
                                    <th>下跌家数</th>
                                    <th>均价</th>
                                    <th>领涨股</th>
                                    <th>领涨股-最新价</th>
                                    <th>领涨股-涨跌幅(%)</th>
                                </tr>
    """
    
    if not industry_info.empty:
        for _, row in industry_info.iterrows():
            change_class = 'positive' if row['涨跌幅'] > 0 else 'negative'
            html += f"""
                                <tr>
                                    <td>{int(row['序号'])}</td>
                                    <td>{row['板块']}</td>
                                    <td class="{change_class}">{row['涨跌幅']:.2f}</td>
                                    <td>{row['总成交量']:.2f}</td>
                                    <td>{row['总成交额']:.2f}</td>
                                    <td>{row['净流入']:.2f}</td>
                                    <td>{int(row['上涨家数'])}</td>
                                    <td>{int(row['下跌家数'])}</td>
                                    <td>{row['均价']:.2f}</td>
                                    <td>{row['领涨股']}</td>
                                    <td>{row['领涨股-最新价']:.2f}</td>
                                    <td class="{change_class}">{row['领涨股-涨跌幅']:.2f}</td>
                                </tr>
            """
    else:
        html += """
                                <tr>
                                    <td colspan="12" style="text-align: center; padding: 20px; color: #999;">暂无数据</td>
                                </tr>
        """
    
    html += """
                            </table>
                        </div>
                    </div>
                </div>
            </div>
            </div>
            <div id="chen-xiaoqun-page" class="page-content" style="display: none;">
            <div class="section">
                <h2>👤 陈小群龙虎榜追踪</h2>
                <div class="table-container">
                    <table>
                        <tr>
                            <th>序号</th>
                            <th>股票代码</th>
                            <th>股票名称</th>
                            <th>交易日期</th>
                            <th>涨跌幅(%)</th>
                            <th>买入金额(万)</th>
                            <th>卖出金额(万)</th>
                            <th>净额(万)</th>
                            <th>上榜原因</th>
                        </tr>
                        """
    if not yyb_lhb_data.empty:
        for _, row in yyb_lhb_data.iterrows():
            change_class = 'positive' if row['涨跌幅'] > 0 else 'negative'
            net_class = 'positive' if row['净额'] > 0 else 'negative'
            html += f"""
                        <tr>
                            <td>{int(row['序号'])}</td>
                            <td>{row['股票代码']}</td>
                            <td>{row['股票名称']}</td>
                            <td>{row['交易日期']}</td>
                            <td class="{change_class}">{row['涨跌幅']:.2f}</td>
                            <td>{row['买入金额']/10000:.2f}</td>
                            <td>{row['卖出金额']/10000:.2f}</td>
                            <td class="{net_class}">{row['净额']/10000:.2f}</td>
                            <td>{row['上榜原因']}</td>
                        </tr>
            """
    else:
        html += """
                        <tr>
                            <td colspan="9" style="text-align: center; padding: 40px; color: #999;">暂无数据</td>
                        </tr>
        """
    html += """
                    </table>
                </div>
            </div>
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
    
    # 获取概念板块信息
    print("\n正在获取概念板块信息...")
    board_info = get_board_concept_info()
    
    # 获取行业板块信息
    print("\n正在获取行业板块信息...")
    industry_info = get_board_industry_info()
    
    # 获取资金流向数据
    print("\n正在获取资金流向数据...")
    capital_flow_data = get_capital_flow_data()
    
    # 获取行业资金流向数据
    print("\n正在获取行业资金流向数据...")
    industry_flow_data = get_industry_flow_data()
    
    # 获取营业部龙虎榜数据
    print("\n正在获取营业部龙虎榜数据...")
    yyb_lhb_data = get_yyb_lhb_data(yyb_code="10030463")
    
    # 获取财联社新闻数据
    print("\n正在获取财联社新闻数据...")
    cls_news = get_cls_news()
    
    # 获取同花顺新闻数据
    print("\n正在获取同花顺新闻数据...")
    ths_news = get_ths_news()
    
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
    
    html_content = generate_limit_up_pool_html(today_pool, yesterday_pool, board_info, industry_info, capital_flow_data, industry_flow_data, yyb_lhb_data, cls_news, ths_news)
    
    # 保存HTML文件
    html_file_path = "limit_up_pool_report.html"
    with open(html_file_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"\nHTML报告已生成: {html_file_path}")
    print("请在浏览器中打开该文件查看涨停股池数据")
    
    print("\n" + "=" * 60)
    print("数据获取完成！")
    print("=" * 60)
