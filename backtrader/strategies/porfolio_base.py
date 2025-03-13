import backtrader as bt
from backtrader.order import Order
from backtrader.trade import Trade


class PortfolioBase(bt.Strategy):
    def __init__(self):
        # 存储每个数据源的收盘价
        self.close_prices = {}
        self.assets = []
        
        # 初始化每个数据源
        for i, data in enumerate(self.datas):
            # 获取资产名称
            asset_name = data._name
            self.assets.append(asset_name)
            # 存储收盘价引用
            self.close_prices[asset_name] = data.close
        
        # 初始化投资组合权重
        self.weights = {asset: 0.0 for asset in self.assets}
        
        # 存储每日投资组合价值
        self.portfolio_value = []
        self.dates = []

    def log(self, txt: str, dt=None):
        """Logging function for this strategy

        Parameters
        ----------
        txt : str
            string to log
        dt : optional
            datetime by default None
        """
        if self.p.print_debug:
            dt = dt or self.datas[0].datetime.date(0)
            print(f'{dt.isoformat()}: {txt}')

    def adjust_positions(self):
        """Rebalance the portfolio based on the current weights"""
        # 获取当前投资组合总价值
        portfolio_value = self.broker.getvalue()
        
        # 平仓所有现有头寸
        for data in self.datas:
            self.close(data=data)
        
        # 根据新的权重分配资金
        for i, data in enumerate(self.datas):
            asset_name = data._name
            weight = self.weights[asset_name]
            
            if abs(weight) > 0.01:  # 忽略非常小的权重
                # 计算目标头寸规模
                price = data.close[0]
                target_value = portfolio_value * weight
                size = int(target_value / price)
                
                # 开仓(可以做多或做空)
                if size > 0:
                    self.log(f'买入 {asset_name}: {size} 股，价格: {price:.2f}')
                    self.buy(data=data, size=size)
                elif size < 0:
                    self.log(f'卖空 {asset_name}: {abs(size)} 股，价格: {price:.2f}')
                    self.sell(data=data, size=abs(size))

    def notify_order(self, order: Order):
        if order.status in [order.Submitted, order.Accepted]:
            # Buy/Sell order submitted/accepted to/by broker - Nothing to do
            return

        # Check if an order has been completed
        # Attention: broker could reject order if not enough cash
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(
                    'BUY EXECUTED, Price: %.2f, Cost: %.2f, Comm %.2f' %
                    (order.executed.price,
                     order.executed.value,
                     order.executed.comm))

                self.buyprice = order.executed.price
                self.buycomm = order.executed.comm
            else:  # Sell
                self.log('SELL EXECUTED, Price: %.2f, Cost: %.2f, Comm %.2f' %
                         (order.executed.price,
                          order.executed.value,
                          order.executed.comm))

            self.bar_executed = len(self)

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled/Margin/Rejected')

        self.order = None

    def notify_trade(self, trade: Trade):
        if not trade.isclosed:
            return

        self.log('OPERATION PROFIT, GROSS %.2f, NET %.2f' %
                 (trade.pnl, trade.pnlcomm))
