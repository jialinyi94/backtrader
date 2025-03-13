import yfinance as yf
import backtrader as bt
import pyfolio as pf
from backtrader.strategies import EigenPortfolio
import matplotlib.pyplot as plt


def get_dow30_tickers():
    """获取道琼斯30指数成分股列表"""
    # 截至2023年的道琼斯30指数成分股
    dow30 = [
        'AAPL', 'AMGN', 'AXP', 'BA', 'CAT', 'CRM', 'CSCO', 'CVX', 'DIS', 'DOW',
        'GS', 'HD', 'HON', 'IBM', 'INTC', 'JNJ', 'JPM', 'KO', 'MCD', 'MMM',
        'MRK', 'MSFT', 'NKE', 'PG', 'TRV', 'UNH', 'V', 'VZ', 'WBA', 'WMT'
    ]
    return dow30


def download_data(tickers, start_date, end_date):
    """下载股票数据"""
    print(f"下载 {len(tickers)} 只股票的数据...")
    data = yf.download(tickers, start=start_date, end=end_date)
    print("数据下载完成!")
    return data


def prepare_backtrader_data(data, tickers):
    """准备Backtrader数据源"""
    data = data.swaplevel(0, 1, axis=1)
    datas = []
    for ticker in tickers:
        # 提取单个股票的数据
        stock_data = data[ticker].dropna()
        
        # 创建Backtrader数据源
        data_feed = bt.feeds.PandasData(
            dataname=stock_data,
            name=ticker,
        )
        datas.append(data_feed)
    
    return datas


def run_backtest(datas, initial_cash=100000.0, plot=True):
    """运行回测"""
    # 创建Cerebro引擎
    cerebro = bt.Cerebro()
    
    # 添加策略
    cerebro.addstrategy(EigenPortfolio, 
                        lookback=252,           # 一年的交易日
                        rebalance_period=21,    # 每月重新平衡
                        top_eigen=5,            # 使用前5个主成分
                        weighting_scheme='variance')  # 根据方差分配权重
    
    # 添加数据
    for data in datas:
        cerebro.adddata(data)
    
    # 设置初始资金
    cerebro.broker.setcash(initial_cash)
    
    # 设置佣金
    cerebro.broker.setcommission(commission=0.001)  # 0.1%
    
    # # 允许做空
    # cerebro.broker.set_shortcash(True)
    
    # 添加分析器
    cerebro.addanalyzer(bt.analyzers.PyFolio, _name='pyfolio')
    
    # 运行回测
    print('初始投资组合价值: %.2f' % cerebro.broker.getvalue())
    results = cerebro.run()
    print('最终投资组合价值: %.2f' % cerebro.broker.getvalue())
    
    return results

def plot_results(results):
    """绘制回测结果"""
    # 获取分析结果
    strat = results[0]
    pyfoliozer = strat.analyzers.getbyname('pyfolio')
    returns, positions, transactions, gross_lev = pyfoliozer.get_pf_items()

    pf.create_full_tear_sheet(
        returns,
        positions=positions,
        transactions=transactions,
        round_trips=True
    )

    plt.show()


if __name__ == '__main__':
    # 设置回测参数
    start_date = '2019-03-20'
    end_date = '2023-01-01'
    initial_cash = 100000.0
    
    # 获取道琼斯30指数成分股
    tickers = get_dow30_tickers()
    
    # 下载数据
    data = download_data(tickers, start_date, end_date)
    
    # 准备Backtrader数据源
    datas = prepare_backtrader_data(data, tickers)
    
    # 运行回测
    results = run_backtest(datas, initial_cash=initial_cash, plot=True)

    # 绘制回测结果
    plot_results(results)

