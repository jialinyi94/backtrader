import numpy as np
import pandas as pd
from .porfolio_base import PortfolioSideInfoBase


class FactorStatArbPortfolio(PortfolioSideInfoBase):
    params = (
        ('lookback', 252),         # 约一年的交易日
        ('rebalance_period', 21),  # 约一个月重新平衡一次
        ('side_info_start', 29),   # 数据源的分隔符
        ('print_debug', True),     # 是否打印调试信息
    )

    def __init__(self):
        # 设置最小周期
        self.addminperiod(self.p.lookback + 1)
        super().__init__(self.p.side_info_start)
        self.side_info = self.datas[self.side_info_data_start:]

    def next(self):
        # 存储当前日期和投资组合价值
        self.dates.append(self.datas[0].datetime.date(0))
        self.portfolio_value.append(self.broker.getvalue())
        
        tester = len(self) - self.p.lookback
        if (tester > 0) and (tester % self.p.rebalance_period == 1):
            self.log(f'重新平衡投资组合，当前日期: {self.datas[0].datetime.date(0)}')
            self.rebalance_portfolio()

    def rebalance_portfolio(self):
        """重新平衡投资组合，计算特征投资组合权重"""
        # 收集历史价格数据
        price_data = {}
        for asset in self.assets:
            # 获取lookback期间的收盘价
            prices = np.array(self.close_prices[asset].get(size=self.p.lookback+1))
            price_data[asset] = prices

        # 收集历史辅助信息
        side_data = {}
        for asset in self.side_info_assets:
            # 获取lookback期间的辅助信息
            side_info = np.array(self.side_info[asset].get(size=self.p.lookback+1))
            side_data[asset] = side_info
    