from datetime import datetime
from datetime import timedelta
import pandas as pd
import os
import asyncio

import app.services.macd as macd
import app.services.notification as notification
from app.services.llm_agent import ask_llm
from app.services.database import get_index_stocks, get_stock_daily_data_from_db
from app.utils.logger import logger
from app.utils.main_board_checker import is_main_board

try:
    # load environment variables from .env file (requires `python-dotenv`)
    from dotenv import load_dotenv
    load_dotenv(override=True)
except ImportError:
    pass

stocks = {
    "HS300": "hs300",
    "ZZ500": "zz500"
}

def format_email_content(content: list[tuple]) -> str:
    """
    Description: 
       content is a list of tuple, each tuple contains 4 elements: code, name, profit, win_prob.
       format the content to html table format.
    Args:
        content (list[tuple]): [stock code, stock name, profit, win prob] 
    Returns:
        str: html content for email.
    """
    if not content:
        return "<p>暂无选股结果。</p>"

    html = """
    <html>
    <body>
    <h3>今日MACD量化选股结果：</h3>
    <table border="1" cellpadding="6" cellspacing="0" style="border-collapse: collapse; font-family: Arial, sans-serif;">
        <tr style="background-color: #f2f2f2;">
            <th>代码</th>
            <th>名称</th>
            <th>回测收益</th>
            <th>回测收益率</th>
            <th>胜率</th>
        </tr>
    """

    for code, name, avg_profit, avg_profit_ratio, win_prob in content:
        html += f"""
        <tr>
            <td>{code}</td>
            <td>{name}</td>
            <td>{avg_profit:.2f}</td>
            <td>{avg_profit_ratio:.2f}</td>
            <td>{win_prob:.2f}</td>
        </tr>
        """

    html += """
    </table>
    <p>以上为今日MACD策略回测结果，请注意风险控制。</p>
    </body>
    </html>
    """

    return html

def calculate_macd(df, fastperiod=12, slowperiod=26, signalperiod=9):
    """计算MACD指标"""
    df = df.copy()
    # 计算EMA
    ema_fast = df['close'].ewm(span=fastperiod, adjust=False).mean()
    ema_slow = df['close'].ewm(span=slowperiod, adjust=False).mean()
    
    # MACD线
    df['MACD'] = ema_fast - ema_slow
    
    # 信号线
    df['Signal'] = df['MACD'].ewm(span=signalperiod, adjust=False).mean()
    
    # 柱状图
    df['Histogram'] = df['MACD'] - df['Signal']
    
    return df


def detect_macd_golden_cross(df, fastperiod=12, slowperiod=26, signalperiod=9):
    """检测MACD金叉（MACD线上穿信号线）"""
    df = calculate_macd(df, fastperiod, slowperiod, signalperiod)

    prev_macd = df['MACD'].shift(1)
    prev_signal = df['Signal'].shift(1)

    df['Crossover'] = (df['MACD'] > df['Signal']) & (prev_macd <= prev_signal)
    return df


async def detect_macd_golden_cross_from_db(stock_list, start_date, end_date, detect_days=7, 
                                          fastperiod=12, slowperiod=26, signalperiod=9):
    """
    从数据库读取股票数据并检测MACD金叉
    
    Args:
        stock_list: 股票列表，每个元素包含 code, name 等字段
        start_date: 开始日期
        end_date: 结束日期
        detect_days: 检测天数
        fastperiod: MACD快线周期（默认12）
        slowperiod: MACD慢线周期（默认26）
        signalperiod: 信号线周期（默认9）
    
    Returns:
        DataFrame: 包含MACD金叉信息的DataFrame
    """
    
    golden_cross = {
        "Code": [],
        "Name": [],
        "Last Cross Date": []
    }
    

    for stock in stock_list:
        code = stock.get('code')
        name = stock.get('name', code)
        
        if not code:
            continue
        
        # 从数据库读取股票交易数据
        stock_data = await get_stock_daily_data_from_db(code, start_date, end_date)
        
        if not stock_data:
            continue
        
        # 转换为DataFrame
        data = pd.DataFrame(stock_data)
        # 确保date列是datetime类型
        data['date'] = pd.to_datetime(data['date'])
        # 确保数值列是数值类型
        for col in ['open', 'high', 'low', 'close', 'volume', 'amount']:
            if col in data.columns:
                data[col] = pd.to_numeric(data[col], errors='coerce')
        
        # 检测MACD金叉
        cross_points = detect_macd_golden_cross(data, fastperiod, slowperiod, signalperiod)
        cross_points = cross_points[cross_points['Crossover'] == True]
        
        if cross_points.empty:
            continue
        
        # 取最近一次金叉的日期
        last_cross_date = cross_points['date'].iloc[-1]
        
        # 如果最近的金叉在过去 detect_days 天内
        if last_cross_date >= data['date'].iloc[-detect_days]:
            golden_cross['Code'].append(code)
            golden_cross['Name'].append(name)
            golden_cross['Last Cross Date'].append(last_cross_date)
    
    return pd.DataFrame(golden_cross)


async def do_search():
    """
    执行MACD选股任务，从数据库读取股票数据
    """
    logger.info("Starting MACD Detector")
    end_date    = datetime.today()
    start_date  = end_date - timedelta(days=365)
    start_date  = start_date.strftime("%Y-%m-%d")
    end_date    = end_date.strftime("%Y-%m-%d")
    
    stock_to_ask_llm = []
    content = []

    for stock_cls, index_type in stocks.items():
        logger.info(f"Begin detect {stock_cls} MACD golden crosses...")
        
        # 从数据库获取股票列表
        stock_list = await get_index_stocks(index_type)
        
        if not stock_list:
            logger.warning(f"未找到 {stock_cls} 成分股数据")
            continue
        
        # 从数据库读取数据并检测MACD金叉
        golden_cross_df = await detect_macd_golden_cross_from_db(stock_list, start_date, end_date, 7)
        
        # 保存MACD金叉结果
        os.makedirs('data', exist_ok=True)
        golden_cross_df.to_csv('data/macd_golden_cross.csv', index=False, encoding='utf-8')
        
        logger.info("Detect MACD golden crosses done.")
        logger.info("Do MACD Backtrade analysis...")

        # 对每个MACD金叉股票进行回测
        for _, row in golden_cross_df.iterrows():
            code = row['Code']
            stock_name = row.get('Name', code)

            if not is_main_board(code):
                logger.info(f"股票 {code} {stock_name} 不是主板股票，跳过")
                continue
            
            # 从数据库读取股票交易数据
            stock_data = await get_stock_daily_data_from_db(code, start_date, end_date)
            
            if not stock_data:
                logger.warning(f"股票 {code} 没有交易数据，跳过")
                continue
            
            # 转换为DataFrame
            data = pd.DataFrame(stock_data)
            # 确保date列是datetime类型
            data['date'] = pd.to_datetime(data['date'])
            # 确保数值列是数值类型
            for col in ['open', 'high', 'low', 'close', 'volume', 'amount']:
                if col in data.columns:
                    data[col] = pd.to_numeric(data[col], errors='coerce')
            
            # 运行MACD回测策略  
            avg_profit, avg_profit_ratio, win_prob = macd.runstrat(data)
            
            if avg_profit_ratio >= 0.02 and win_prob >= 0.5:
                logger.info(f"macd 🎉 盈利: {code} {stock_name}. avg profit={avg_profit:.2f}. " + \
                    f"avg profit ratio = {avg_profit_ratio:.2f}. win probability={win_prob:.2f}")
                content.append((code, stock_name, avg_profit, avg_profit_ratio, win_prob))
                stock_to_ask_llm.append((code, stock_name, avg_profit, avg_profit_ratio, win_prob))

        logger.info("MACD Backtrade analysis done.")
        logger.info(f"Finish {stock_cls}")
        logger.info("....................................")

    notification.send_mail(f"{end_date} MACD分析结果", format_email_content(content))
    logger.info("Email sent.")
    return content

    ## for code, name, _, _, _ in stock_to_ask_llm:
    ##     content = [] 
    ##     content.append(f"\n## code: {code}, name: {name}. \n")
    ##     content.append(ask_llm(code))
    ##     content = markdown.markdown('\n'.join(content))
    ##     send_mail(f"{end_date} {code} {name} AI分析结果", content)
    #logger.info("Done. And good luck!")


async def run_search_macd_gold_task():
    """
    异步任务函数，用于在后台运行MACD选股任务
    """
    try:
        logger.info("开始执行MACD选股任务...")
        content = await do_search()
        logger.info("MACD选股任务执行完成, content: %s", content)
    except Exception as e:
        logger.error(f"MACD选股任务执行失败: {str(e)}", exc_info=True)
        raise
    return content


if __name__ == "__main__":
    asyncio.run(do_search())
