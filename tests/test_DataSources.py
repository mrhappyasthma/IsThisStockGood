from isthisstockgood.CompanyInfo import CompanyInfo
from isthisstockgood.DataFetcher import DataFetcher


def test_msn_money():
    test_ticker = 'MSFT'
    test_name = 'Microsoft Corp'

    data = get_msn_money_data(test_ticker)

    assert data.ticker_symbol == test_ticker
    assert data.name == test_name
    assert data.description != ''
    assert data.industry != ''
    assert data.current_price > 0.0
    assert data.average_volume > 0
    assert data.market_cap > 0.0
    assert data.shares_outstanding > 0
    assert data.pe_high > 0.0
    assert data.pe_low > 0.0
    assert data.roic != []
    assert data.roic_averages != []
    assert data.equity != []
    assert data.equity_growth_rates != []
    assert data.free_cash_flow != []
    assert data.free_cash_flow_growth_rates != []
    assert data.revenue != []
    assert data.revenue_growth_rates != []
    assert data.eps != []
    assert data.eps_growth_rates != []
    assert data.debt_equity_ratio > 0.0
    assert data.last_year_net_income > 0.0
    assert data.total_debt >= 0.0

def test_future_growth_rate():
    test_ticker = 'MSFT'
    test_name = 'Microsoft Corp'

    data = get_growth_rate(test_ticker)

    assert data.ticker_symbol == test_ticker
    assert float(data.five_year_growth_rate) > 0.0

def get_msn_money_data(ticker):
    data_fetcher = DataFetcher(ticker)

    # Make all network request asynchronously to build their portion of
    # the json results.
    data_fetcher.fetch_msn_money_data()

    # Wait for each RPC result before proceeding.
    for rpc in data_fetcher.rpcs:
      rpc.result()

    return CompanyInfo(**vars(data_fetcher.msn_money))

def get_growth_rate(ticker):
    data_fetcher = DataFetcher(ticker)

    # Make all network request asynchronously to build their portion of
    # the json results.
    data_fetcher.fetch_zacks_analysis()

    # Wait for each RPC result before proceeding.
    for rpc in data_fetcher.rpcs:
      rpc.result()

    return data_fetcher.zacks_analysis
