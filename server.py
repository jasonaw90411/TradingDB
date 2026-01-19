from flask import Flask, jsonify, send_from_directory
import pandas as pd
import akshare as ak
from datetime import datetime
import threading
import time

app = Flask(__name__)

# 全局变量缓存新闻数据
news_cache = {
    'cls_news': None,
    'ths_news': None,
    'last_update': None
}

# 全局变量缓存市场热点数据
hot_rank_cache = {
    'hot_search_data': None,
    'hot_rank_data': None,
    'last_update': None
}

# 缓存时间（秒）
NEWS_CACHE_DURATION = 300  # 新闻5分钟
HOT_RANK_CACHE_DURATION = 600  # 市场热点10分钟

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

def get_hot_search_data():
    """获取百度热搜股票数据"""
    try:
        today_str = datetime.now().strftime('%Y%m%d')
        print(f"尝试获取百度热搜股票数据，日期: {today_str}")
        
        try:
            hot_today_df = ak.stock_hot_search_baidu(symbol="A股", date=today_str, time="今日")
            print(f"成功获取百度热搜股票数据（今日），共 {len(hot_today_df)} 条记录")
        except Exception as e:
            print(f"获取今日热搜数据失败: {e}")
            hot_today_df = pd.DataFrame()
        
        try:
            hot_hour_df = ak.stock_hot_search_baidu(symbol="A股", date=today_str, time="1小时")
            print(f"成功获取百度热搜股票数据（1小时），共 {len(hot_hour_df)} 条记录")
        except Exception as e:
            print(f"获取1小时热搜数据失败: {e}")
            hot_hour_df = pd.DataFrame()
        
        return {"今日": hot_today_df, "1小时": hot_hour_df}
    except Exception as e:
        print(f"获取百度热搜股票数据失败: {e}")
        return {"今日": pd.DataFrame(), "1小时": pd.DataFrame()}

def get_hot_rank_em():
    """获取东方财富热度榜数据"""
    try:
        hot_rank_df = ak.stock_hot_rank_em()
        print(f"成功获取东方财富热度榜数据，共 {len(hot_rank_df)} 条记录")
        return hot_rank_df
    except Exception as e:
        print(f"获取东方财富热度榜数据失败: {e}")
        return pd.DataFrame()

def update_news_cache():
    """更新新闻缓存"""
    print("开始更新新闻缓存...")
    news_cache['cls_news'] = get_cls_news()
    news_cache['ths_news'] = get_ths_news()
    news_cache['last_update'] = datetime.now()
    print(f"新闻缓存更新完成，时间: {news_cache['last_update']}")

def update_hot_rank_cache():
    """更新市场热点缓存"""
    print("开始更新市场热点缓存...")
    hot_rank_cache['hot_search_data'] = get_hot_search_data()
    hot_rank_cache['hot_rank_data'] = get_hot_rank_em()
    hot_rank_cache['last_update'] = datetime.now()
    print(f"市场热点缓存更新完成，时间: {hot_rank_cache['last_update']}")

def background_update():
    """后台线程定期更新数据"""
    news_update_time = time.time()
    hot_rank_update_time = time.time()
    
    while True:
        current_time = time.time()
        
        # 更新新闻（每5分钟）
        if current_time - news_update_time >= NEWS_CACHE_DURATION:
            try:
                update_news_cache()
                news_update_time = current_time
            except Exception as e:
                print(f"后台更新新闻失败: {e}")
        
        # 更新市场热点（每10分钟）
        if current_time - hot_rank_update_time >= HOT_RANK_CACHE_DURATION:
            try:
                update_hot_rank_cache()
                hot_rank_update_time = current_time
            except Exception as e:
                print(f"后台更新市场热点失败: {e}")
        
        time.sleep(10)  # 每10秒检查一次

@app.route('/')
def index():
    """返回主页"""
    return send_from_directory('.', 'limit_up_pool_report.html')

@app.route('/api/news')
def api_news():
    """返回新闻数据API"""
    icons = ['📰', '📊', '💹', '📈', '💼', '🏢', '💡', '⚡', '🔔', '📢']
    news_items = []
    
    # 添加财联社新闻
    if news_cache['cls_news'] is not None and not news_cache['cls_news'].empty:
        for idx, row in news_cache['cls_news'].iterrows():
            title = str(row.get('标题', ''))
            time_str = str(row.get('发布时间', ''))
            icon = icons[idx % len(icons)]
            news_items.append({
                'icon': icon,
                'source': '财联社',
                'time': time_str,
                'title': title
            })
    
    # 添加同花顺新闻
    if news_cache['ths_news'] is not None and not news_cache['ths_news'].empty:
        start_idx = len(news_items)
        for idx, row in news_cache['ths_news'].iterrows():
            title = str(row.get('标题', ''))
            time_str = str(row.get('发布时间', ''))
            icon = icons[(start_idx + idx) % len(icons)]
            news_items.append({
                'icon': icon,
                'source': '同花顺',
                'time': time_str,
                'title': title
            })
    
    return jsonify({
        'news': news_items,
        'last_update': news_cache['last_update'].isoformat() if news_cache['last_update'] else None
    })

@app.route('/api/hot-rank')
def api_hot_rank():
    """返回市场热点数据API"""
    hot_search_data = hot_rank_cache.get('hot_search_data')
    hot_rank_data = hot_rank_cache.get('hot_rank_data')
    
    # 处理百度热搜数据
    hot_search_items = []
    if hot_search_data:
        if '今日' in hot_search_data and not hot_search_data['今日'].empty:
            for idx, row in hot_search_data['今日'].head(20).iterrows():
                name_code = row.get('名称/代码', '')
                change_pct = row.get('涨跌幅', '0%')
                hot_value = row.get('综合热度', 0)
                
                stock_code = ''
                stock_name = ''
                if '(' in name_code and ')' in name_code:
                    stock_name = name_code.split('(')[0].strip()
                    stock_code = name_code.split('(')[1].split(')')[0].strip()
                else:
                    stock_name = name_code
                
                hot_search_items.append({
                    'rank': idx + 1,
                    'code': stock_code,
                    'name': stock_name,
                    'change': change_pct,
                    'heat': str(hot_value) if pd.notna(hot_value) else '0'
                })
    
    # 处理东方财富热度榜数据
    hot_rank_items = []
    if hot_rank_data is not None and not hot_rank_data.empty:
        for idx, row in hot_rank_data.head(20).iterrows():
            hot_rank_items.append({
                'rank': int(row.get('当前排名', idx + 1)),
                'code': str(row.get('代码', '')),
                'name': str(row.get('股票名称', '')),
                'price': float(row.get('最新价', 0)) if pd.notna(row.get('最新价')) else 0,
                'change': float(row.get('涨跌幅', 0)) if pd.notna(row.get('涨跌幅')) else 0,
                'volume': float(row.get('成交量', 0)) if pd.notna(row.get('成交量')) else 0
            })
    
    return jsonify({
        'hot_search': hot_search_items,
        'hot_rank': hot_rank_items,
        'last_update': hot_rank_cache['last_update'].isoformat() if hot_rank_cache['last_update'] else None
    })

if __name__ == '__main__':
    # 启动时先更新一次数据
    update_news_cache()
    update_hot_rank_cache()
    
    # 启动后台更新线程
    update_thread = threading.Thread(target=background_update, daemon=True)
    update_thread.start()
    
    # 启动Flask服务器
    print("服务器启动中...")
    print("请访问: http://localhost:5000")
    app.run(host='0.0.0.0', port=5000, debug=False)
