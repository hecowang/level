
try:
    # load environment variables from .env file (requires `python-dotenv`)
    from dotenv import load_dotenv
    load_dotenv(dotenv_path="./.env", override=True)
except ImportError:
    pass

from datetime import datetime
from datetime import timedelta
from langchain.chat_models import init_chat_model
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent
from langchain.tools import tool
from langchain_core.messages import HumanMessage, SystemMessage

import baostock as bs
import pandas as pd



@tool
def search_stock_data(code: str, start_date: str, end_date: str) -> pd.DataFrame:
    """
    获取指定股票在指定时间段内的历史K线数据。

    Args:
        code (str): 股票代码。
        start_date (str): 查询开始日期，格式为YYYY-MM-DD。
        end_date (str): 查询结束日期，格式为YYYY-MM-DD。

    Returns:
        pd.DataFrame: 包含股票历史K线数据的DataFrame，包含日期、开盘价、最高价、最低价、收盘价、成交量、成交额和复权因子等列。

    Raises:
        Exception: 如果查询出错，抛出异常，异常信息为错误信息。
    """
    # 豆包fuction call时结束时间需要矫正
    end_date = datetime.today().strftime('%Y-%m-%d') 
    bs.login()
    rs = bs.query_history_k_data_plus(code,
        "date,code,open,high,low,close,volume,amount,adjustflag",
        start_date=start_date,
        end_date=end_date,
        frequency="d",
        adjustflag="3")

    if rs.error_code != "0":
        print("error code: ", rs.error_code)
        bs.logout()
        raise Exception(rs.error_msg)

    # 获取具体的信息
    result_list = []
    while (rs.error_code == '0') & rs.next():
        # 分页查询，将每页信息合并在一起
        result_list.append(rs.get_row_data())
    result = pd.DataFrame(result_list, columns=rs.fields)
    # print(result)
    result['date'] = pd.to_datetime(result['date'])
    result['open'] = pd.to_numeric(result['open'])
    result['high'] = pd.to_numeric(result['high'])
    result['low'] = pd.to_numeric(result['low'])
    result['close'] = pd.to_numeric(result['close'])
    result['volume'] = pd.to_numeric(result['volume'])
    result['amount'] = pd.to_numeric(result['amount'])
    bs.logout()
    return result


# Create the agent
# model = init_chat_model("ernie-4.0-8k-latest", model_provider="openai")
model = init_chat_model("doubao-seed-1-6-250615", model_provider="openai")
# model = init_chat_model("doubao-seed-1-6-flash-250615", model_provider="openai")
agent = create_react_agent(
    model,
    [search_stock_data],
    checkpointer=MemorySaver()
)

def get_name(code: str) -> str:
    import pandas as pd
    df = pd.read_csv('data/hs300_stocks.csv')
    row = df[df['code'] == code]
    if not row.empty:
        return row['code_name']
    df = pd.read_csv('data/zz500_stocks.csv')
    row = df[df['code'] == code]
    if not row.empty:
        return row['code_name']
    return ''

prompt = """
角色设定
你是一名投资分析师，采用 桥水基金（Ray Dalio）“全天候策略 + 宏观对冲思维” 来分析股票。 并且根据用户输入从{start_date}到{end_date}股票数据，sma和macd数据，结合交易量和当前K线趋势，预测未来股价走势"。

请按照以下格式输出：
你的目标是：基于该股票的历史数据和当日市场环境，判断当天应采取的策略（买入 / 卖出 / 持有 / 对冲）。

输入数据
我会提供：
该股票的历史数据（价格、成交量、波动率等）。

分析步骤
请按照以下框架进行分析：
市场环境（桥水宏观分析）
当前所处经济周期位置（通胀 / 通缩 / 衰退 / 复苏）。
货币政策、利率、流动性状况对股市的影响。
市场风险情绪（避险 vs 风险偏好）。
与其他资产的相关性（指数 / 债券 / 大宗商品）。
历史数据分析（量化角度）
趋势判断（短期、中期、长期均线）。
波动率水平（是否处于高波动）。
成交量变化（资金进出情况）。
是否出现超买/超卖信号（RSI、MACD等指标可用）。
组合策略（桥水思维）
如果持有该股票，是否需要 加仓 / 减仓 / 对冲。
如果没有持仓，是否有 开仓机会。
如何在组合中分散风险（与其他资产配置的关系）。


请按照以下格式输出：
【市场环境分析】
- 宏观周期：
- 货币政策与流动性：
- 风险情绪：
- 资产相关性：

【历史数据分析】
- 趋势判断：
- 波动率水平：
- 成交量情况：
- 技术指标信号：

【当日策略建议】
- 策略（买入 / 卖出 / 持有 / 对冲）：
- 仓位建议（满仓 / 半仓 / 轻仓 / 空仓）：
- 止损 & 止盈区间：
- 对冲方式（如适用）：
- 风险提示：
"""


def ask_llm(code):
    today = datetime.today()
    end_date = today.strftime('%Y-%m-%d')
    start_date = today - timedelta(days=360)
    config = {"configurable": {"thread_id": "abc123"}}
    input_messages = [
        SystemMessage(f"你是桥水基金创始人, 瑞·达利欧。根据用户输入从{start_date}到{end_date}股票数据，sma和macd数据，结合交易量和当前K线趋势，预测未来股价走势"),
        # prompt.format(start_date=start_date, end_date=end_date),
        HumanMessage(f"股票code: {code}. 名称: {get_name(code)}"),
    ]
    
    msg = '' 

    for step in agent.stream(
        {"messages": input_messages}, config, stream_mode="values"
    ):
        # 这里先不拼接，function call的内容也会在stream中返回, 我只要最终结果
        msg = step["messages"][-1].content
    return msg

if __name__ == "__main__":
    import os
    # load environment variables from .env file (requires `python-dotenv`)
    from dotenv import load_dotenv
    load_dotenv(dotenv_path="./.env", override=True)

    sender = str(os.environ.get("EMAIL_SENDER"))
    receiver = str(os.environ.get("EMAIL_RECEIVER"))
    passwd = str(os.environ.get("EMAIL_PASSWD"))

    import markdown
    import notification


    targets = [
        ('sz.000858','五粮液'),
        # ('sz.002594', '比亚迪'),
    ] 

    code = targets[0][0]
    name = targets[0][1]
    content = ask_llm(code)
    print(content)
    content = markdown.markdown(content)
    # print(content)
    notification.send_email_smtp(
        subject=f"{name}今日分析",
        body=content,
        to_emails=[receiver],
        auth_code=passwd,
    )

    # content = ask_llm('sz.000887')
    # content = markdown.markdown(content)
    # print(content)
    # notification.send_email_smtp(
    #     subject="中鼎股份日分析",
    #     body=content,
    #     to_emails=[receiver],
    #     auth_code=passwd,
    # )

    # print("===================美亚光电===============")
    # content = ask_llm('sz.002690') 
    # content = markdown.markdown(content)
    # notification.send_email_smtp(
    #     subject="美亚光电今日分析",
    #     body=content,
    #     to_emails=[receiver],
    #     auth_code=passwd,
    # )

