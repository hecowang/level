import backtrader as bt
import logging

logger = logging.getLogger("app")

debug = False
win_prob = 0

class MacdCross(bt.SignalStrategy):
    params = dict(fastperiod=12, slowperiod=26, signalperiod=9, hold_days=21)  # MACD参数和持有天数

    def __init__(self):
        self.macd = bt.ind.MACD(
            period_me1=self.params.fastperiod,
            period_me2=self.params.slowperiod,
            period_signal=self.params.signalperiod
        )
        self.crossover = bt.ind.CrossOver(self.macd.macd, self.macd.signal)  # 计算MACD与信号线交叉
        self.bar_executed = [] 

        self.signal_add(bt.SIGNAL_LONG, self.crossover)
        self.order = None
        self.win = 0
        self.loss = 0
        self.buy_count = 0
        self.trade_profits = []
        self.trade_profits_ratio = []
        self.last_trade_size = 0

    def log(self, txt, dt=None):
        ''' Logging function for this strategy'''
        if debug:
            dt = dt or self.datas[0].datetime.date(0)
            logger.info(f"{dt.isoformat()}, {txt}")
        else:
            logger.debug(txt)

    def next(self):
         """ 在每根K线执行交易检查 """
         if self.crossover[0] > 0:  # MACD上穿信号线，触发买入信号
             self.bar_executed.append(len(self))
             self.log(f"📈 MACD({self.params.fastperiod},{self.params.slowperiod},{self.params.signalperiod}) 上穿信号线，触发买入信号.")
             self.buy_count += 1

         if self.crossover[0] < 0:  # MACD下穿信号线，触发卖出信号
            self.log(f"📉 MACD({self.params.fastperiod},{self.params.slowperiod},{self.params.signalperiod}) 下穿信号线，触发卖出信号.")
            self.bar_executed = self.bar_executed[1:]

         if len(self.bar_executed) > 0 and len(self) >= self.bar_executed[0] + self.params.hold_days:
             self.log(f"⏳ 第{len(self)-self.bar_executed[0]}个周期, 卖出.")
             self.bar_executed = self.bar_executed[1:]
             self.sell()

    def notify_order(self, order):
        """ 监听订单状态变化 """
        # self.log(f"🤖 订单状态变更：{bt.Order.Status[order.status]}")
        if order.status in [order.Submitted, order.Accepted]:
            return
        if order.status in [order.Completed]:
           self.log(f"{'买入' if order.isbuy() else '卖出'} {order.executed.size} @ {order.executed.price} | {self.position.size}")
           self.last_trade_size = abs(order.executed.size)

    def notify_trade(self, trade):
        """ 监听交易完成，输出盈亏 """
        if trade.isclosed:
            self.log(f"🎉 盈利: {trade.pnlcomm:.2f}" if trade.pnlcomm > 0 else f"💔 亏损: {trade.pnlcomm:.2f}")
            if trade.pnlcomm > 0:
                self.win += 1
            else:
                self.loss += 1
            self.trade_profits.append(trade.pnlcomm)
            # print(trade.pnlcomm, trade.price, self.last_trade_size)
            self.trade_profits_ratio.append(trade.pnlcomm / (trade.price * self.last_trade_size) if trade.price != 0 else 0)

    def stop(self):
        """ 回测结束，输出最终净值 """
        final_value = self.broker.getvalue()
        start_value = self.broker.startingcash
        trade_count = len(self.trade_profits)
        if trade_count == 0:
            self.log("😭 没有任何交易！")
            trade_count = 1
        # print(self.trade_profits)
        total_profit = sum(self.trade_profits)
        avg_profit_ratio = sum(self.trade_profits_ratio) / trade_count if trade_count != 0 else 0

        self.log("=" * 30)
        self.log(f"📊 回测结束 - 期末资金: {final_value:.2f}")
        self.log(f"💰 期初资金: {start_value:.2f}")
        self.log(f"🚀 策略净利润: {total_profit:.2f}")
        self.log(f"🙋‍♂️ : {trade_count}")
        self.log(f"🌟 平均收益率 {avg_profit_ratio:.2f}")
        self.log(f"🚀 平均利润: {total_profit / trade_count:.2f}")
        self.log("=" * 30)
        if self.win + self.loss == 0:
            self.win = 1
        self.log(f"👍 胜率: {self.win / (self.win+self.loss)}")
        global win_prob
        win_prob = self.win / (self.win+self.loss)

def parse_args(pargs=None):
    import argparse
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description='macdcross')
    parser.add_argument('--strat', required=False, action='store', default='',
                        help=('Arguments for the strategy'))
    parser.add_argument('--feed', required=False, action='store', default='',
                        help=('Input data'))
    return parser.parse_args(pargs)


def runstrat(data, plot=False, args={}):
    """
    运行MACD策略回测
    
    Args:
        data: 股票数据DataFrame
        plot: 是否绘图
        args: 策略参数字典，可包含：
            - fastperiod: 快线周期（默认12）
            - slowperiod: 慢线周期（默认26）
            - signalperiod: 信号线周期（默认9）
            - hold_days: 持有天数（默认21）
    
    Returns:
        (avg_profit, avg_profit_ratio, win_prob): 平均收益、平均收益率、胜率
    """
    cerebro = bt.Cerebro()

    data0 = bt.feeds.PandasData(
        dataname=data,
        datetime='date',
        open='open',
        high='high',
        low='low',
        close='close',
        volume='volume',
    )
    cerebro.adddata(data0)

    # 从args中获取参数，如果没有则使用默认值
    fastperiod = args.get('fastperiod', 12)
    slowperiod = args.get('slowperiod', 26)
    signalperiod = args.get('signalperiod', 9)
    hold_days = args.get('hold_days', 21)
    
    # 将参数传递给策略
    cerebro.addstrategy(MacdCross, fastperiod=fastperiod, slowperiod=slowperiod, signalperiod=signalperiod, hold_days=hold_days)
    cerebro.broker.setcommission(commission=0.0005)
    cerebro.broker.setcash(50000.0)
    cerebro.addsizer(bt.sizers.FixedSize, stake=200)

    results = cerebro.run()
    strat = results[0]

    final_value = cerebro.broker.getvalue()
    profit = final_value - cerebro.broker.startingcash

    # 手动提取交易盈亏（推荐在策略中记录 self.trades = []）
    # if hasattr(strat, 'trade_profits'):
    trade_profits = strat.trade_profits
    trade_profits_ratio = strat.trade_profits_ratio

    # 计算平均收益和胜率
    num_trades = len(trade_profits)
    avg_profit = sum(trade_profits) / num_trades if num_trades > 0 else 0
    win_prob = sum(1 for p in trade_profits if p > 0) / num_trades if num_trades > 0 else 0
    avg_profit_ratio = sum(trade_profits_ratio) / num_trades if num_trades > 0 else 0

    if plot:
        cerebro.plot()
    return avg_profit, avg_profit_ratio, win_prob


if __name__ == '__main__':
    import pandas as pd
    import sys
    args = parse_args()
    feed = args.feed
    df = pd.read_csv(feed, parse_dates=['date'])
    debug = True
    runstrat(df, True, args)
