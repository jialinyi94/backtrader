#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-

import backtrader as bt
import numpy as np
import pandas as pd
from sklearn.decomposition import PCA


class EigenPortfolioStrategy(bt.Strategy):
    """
    基于特征投资组合(Eigen Portfolio)的策略
    
    参数:
        lookback (int): 用于计算协方差矩阵的历史周期
        rebalance_period (int): 重新平衡投资组合的周期(以天为单位)
        top_eigen (int): 使用的主成分数量
        weighting_scheme (str): 权重分配方案，可选值:
            - 'equal': 等权重分配给所有选定的特征投资组合
            - 'variance': 根据解释方差比例分配权重
            - 'first_only': 仅使用第一个特征投资组合
    """
    params = (
        ('lookback', 252),         # 约一年的交易日
        ('rebalance_period', 21),  # 约一个月重新平衡一次
        ('top_eigen', 3),          # 使用前3个主成分
        ('weighting_scheme', 'variance'),  # 权重分配方案
        ('print_debug', True),     # 是否打印调试信息
    )

    def log(self, txt, dt=None):
        """日志函数用于输出信息"""
        if self.p.print_debug:
            dt = dt or self.datas[0].datetime.date(0)
            print(f'{dt.isoformat()}: {txt}')

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
        
        # 初始化重新平衡计数器
        self.rebalance_count = 0
        
        # 设置最小周期
        self.addminperiod(self.p.lookback + 1)
        
        # 存储每日投资组合价值
        self.portfolio_value = []
        self.dates = []

    def next(self):
        
        # 存储当前日期和投资组合价值
        self.dates.append(self.datas[0].datetime.date(0))
        self.portfolio_value.append(self.broker.getvalue())
        
        tester = len(self) - self.p.lookback
        if (tester > 0) and (tester % self.p.rebalance_period == 1):
            self.log(f'重新平衡投资组合，当前日期: {self.datas[0].datetime.date(0)}')
            self.rebalance_count = 0
            self.rebalance_portfolio()

    def rebalance_portfolio(self):
        """重新平衡投资组合，计算特征投资组合权重"""
        # 收集历史价格数据
        price_data = {}
        for asset in self.assets:
            # 获取lookback期间的收盘价
            prices = np.array(self.close_prices[asset].get(size=self.p.lookback+1))
            price_data[asset] = prices
        
        # 创建价格DataFrame
        price_df = pd.DataFrame(price_data)
        
        # 计算日收益率
        returns_df = price_df.pct_change().dropna()
        
        # 进行主成分分析
        try:
            pca = PCA(n_components=min(self.p.top_eigen, len(self.assets)))
            pca.fit(returns_df)
            
            # 获取主成分(特征向量)
            eigenvectors = pca.components_
            
            # 获取特征值(解释方差)
            eigenvalues = pca.explained_variance_ratio_
            
            # 根据权重方案分配投资组合权重
            if self.p.weighting_scheme == 'equal':
                # 等权重分配
                portfolio_weights = np.mean(eigenvectors[:self.p.top_eigen], axis=0)
            elif self.p.weighting_scheme == 'variance':
                # 根据解释方差分配权重
                portfolio_weights = np.average(eigenvectors[:self.p.top_eigen], 
                                              axis=0, 
                                              weights=eigenvalues[:self.p.top_eigen])
            elif self.p.weighting_scheme == 'first_only':
                # 仅使用第一个特征向量
                portfolio_weights = eigenvectors[0]
            else:
                # 默认使用第一个特征向量
                portfolio_weights = eigenvectors[0]
            
            # 归一化权重，使其总和为1
            portfolio_weights = np.abs(portfolio_weights) / np.sum(np.abs(portfolio_weights))
            
            # 更新策略的权重字典
            for i, asset in enumerate(self.assets):
                self.weights[asset] = portfolio_weights[i]
            
            # 打印权重信息
            self.log(f"特征投资组合权重: {dict(zip(self.assets, np.round(portfolio_weights, 4)))}")
            self.log(f"解释方差比例: {np.round(eigenvalues[:self.p.top_eigen], 4)}")
            
            # 执行投资组合调整
            self.adjust_positions()
            
        except Exception as e:
            self.log(f"计算特征投资组合时出错: {str(e)}")
    
    def adjust_positions(self):
        """根据计算的权重调整投资组合持仓"""
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

    def notify_order(self, order):
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

    def notify_trade(self, trade):
        if not trade.isclosed:
            return

        self.log('OPERATION PROFIT, GROSS %.2f, NET %.2f' %
                 (trade.pnl, trade.pnlcomm))
