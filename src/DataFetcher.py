import random
import logging
import src.RuleOneInvestingCalculations as RuleOne
from requests_futures.sessions import FuturesSession
from src.Active.MSNMoney import MSNMoney
from src.Active.YahooFinance import YahooFinanceAnalysis
from src.Active.YahooFinanceChart import YahooFinanceChart
from threading import Lock

logger = logging.getLogger("IsThisStockGood")


def fetchDataForTickerSymbol(ticker):
  """Fetches and parses all of the financial data for the `ticker`.

    Args:
      ticker: The ticker symbol string.

    Returns:
      Returns a dictionary of all the processed financial data. If
      there's an error, return None.

      Keys include:
        'roic',
        'eps',
        'sales',
        'equity',
        'cash',
        'long_term_debt',
        'free_cash_flow',
        'debt_payoff_time',
        'debt_equity_ratio',
        'margin_of_safety_price',
        'current_price'
  """
  if not ticker:
    return None

  data_fetcher = DataFetcher()
  data_fetcher.ticker_symbol = ticker

  # Make all network request asynchronously to build their portion of
  # the json results.
  data_fetcher.fetch_msn_money_data()
  data_fetcher.fetch_yahoo_finance_analysis()
  data_fetcher.fetch_yahoo_finance_chart()


  # Wait for each RPC result before proceeding.
  for rpc in data_fetcher.rpcs:
    rpc.result()

  msn_money = data_fetcher.msn_money
  yahoo_finance_chart = data_fetcher.yahoo_finance_chart
  yahoo_finance_analysis = data_fetcher.yahoo_finance_analysis
  if not msn_money or not yahoo_finance_chart or not yahoo_finance_analysis:
    return None
  # TODO: Use TTM EPS instead of most recent year
  margin_of_safety_price, sticker_price = \
      _calculateMarginOfSafetyPrice(msn_money.equity_growth_rates[-1], msn_money.pe_low, msn_money.pe_high, msn_money.eps[-1], yahoo_finance_analysis.five_year_growth_rate)
  payback_time = -9999999 #_calculatePaybackTime(msn_money, yahoo_finance_quote, yahoo_finance_analysis)
  template_values = {
    'ticker' : ticker,
    'name' : msn_money.name if msn_money and msn_money.name else 'null',
    'description': msn_money.description if msn_money and msn_money.description else 'null',
    'roic': msn_money.roic_averages if msn_money and msn_money.roic_averages else [],
    'eps': msn_money.eps_growth_rates if msn_money and msn_money.eps_growth_rates else [],
    'sales': msn_money.revenue_growth_rates if msn_money and msn_money.revenue_growth_rates else [],
    'equity': msn_money.equity_growth_rates if msn_money and msn_money.equity_growth_rates else [],
    'cash': msn_money.free_cash_flow_growth_rates if msn_money and msn_money.free_cash_flow_growth_rates else [],
    # TODO: Figure out how to get long-term debt instead of total debt
    'total_debt' : -9999999, #msn_money.total_debt,
    'free_cash_flow' : -9999999, #msn_money.recent_free_cash_flow,
    'debt_payoff_time' : -9999999, #: msn_money.debt_payoff_time,
    'debt_equity_ratio' : msn_money.debt_equity_ratio if msn_money and msn_money.debt_equity_ratio >= 0 else -1,
    'margin_of_safety_price' : margin_of_safety_price if margin_of_safety_price else 'null',
    'current_price' : yahoo_finance_chart.current_price if yahoo_finance_chart and yahoo_finance_chart.current_price else 'null',
    'sticker_price' : sticker_price if sticker_price else 'null',
    'payback_time' : payback_time if payback_time else 'null',
    'average_volume' : -9999999 #yahoo_finance_quote.average_volume if yahoo_finance_quote and yahoo_finance_quote.average_volume else 'null'
  }
  return template_values


def _calculate_growth_rate_decimal(analyst_growth_rate, current_growth_rate):
  growth_rate = min(float(analyst_growth_rate), float(current_growth_rate))
  # Divide the growth rate by 100 to convert from percent to decimal.
  return growth_rate / 100.0


def _calculateMarginOfSafetyPrice(one_year_equity_growth_rate, pe_low, pe_high, ttm_eps, analyst_five_year_growth_rate):
  if not one_year_equity_growth_rate or not pe_low or not pe_high or not ttm_eps or not analyst_five_year_growth_rate:
    return None, None

  print(f"growthrate: {one_year_equity_growth_rate} pelow: {pe_low} pehigh: {pe_high} ttm_eps: {ttm_eps} analyst: {analyst_five_year_growth_rate}", flush=True)
  growth_rate = _calculate_growth_rate_decimal(analyst_five_year_growth_rate, one_year_equity_growth_rate)
  margin_of_safety_price, sticker_price = \
      RuleOne.margin_of_safety_price(float(ttm_eps), growth_rate, float(pe_low), float(pe_high))
  return margin_of_safety_price, sticker_price


# TODO: Figure out how to get TTM net income instead of previous year net income.
def _calculatePaybackTime(one_year_equity_growth_rate, last_year_net_income, market_cap, analyst_five_year_growth_rate):
  if not one_year_equity_growth_rate or not last_year_net_income or not market_cap or not analyst_five_year_growth_rate:
    return None

  growth_rate = _calculate_growth_rate_decimal(analyst_five_year_growth_rate, one_year_equity_growth_rate)
  payback_time = RuleOne.payback_time(market_cap, last_year_net_income, growth_rate)
  return payback_time


class DataFetcher():
  """A helper class that syncronizes all of the async data fetches."""

  USER_AGENT_LIST = [
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.1.1 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:77.0) Gecko/20100101 Firefox/77.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.97 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:77.0) Gecko/20100101 Firefox/77.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.97 Safari/537.36',
  ]

  def __init__(self,):
    self.lock = Lock()
    self.rpcs = []
    self.ticker_symbol = ''
    self.msn_money = None
    self.yahoo_finance_chart = None
    self.error = False

  def _create_session(self):
    session = FuturesSession()
    session.headers.update({
      'User-Agent' : random.choice(DataFetcher.USER_AGENT_LIST)
    })
    return session

  def fetch_msn_money_data(self):
    """
    Fetching PE Ratios to calculate Sticker Price and Safety Margin Price. As well as
    the "Big 5" growth rate numbers.
    First we need to get an internal MSN stock id for a ticker and then fetch the data.
    """
    self.msn_money = MSNMoney(self.ticker_symbol)
    session = self._create_session()
    rpc = session.get(self.msn_money.get_ticker_autocomplete_url(), allow_redirects=True, hooks={
       'response': self.continue_fetching_msn_money_data,
    })
    self.rpcs.append(rpc)

  def continue_fetching_msn_money_data(self, response, *args, **kwargs):
    """
    After msn_stock_id was fetched in fetch_msn_money_data method
    we can now get the financials.
    """
    msn_stock_id = self.msn_money.extract_stock_id(response.text)
    session = self._create_session()
    rpc = session.get(self.msn_money.get_key_ratios_url(msn_stock_id), allow_redirects=True, hooks={
       'response': self.parse_msn_money_data,
    })
    self.rpcs.append(rpc)

  # Called asynchronously upon completion of the URL fetch from
  # `fetch_msn_money_data` and `continue_fetching_msn_money_data`.
  def parse_msn_money_data(self, response, *args, **kwargs):
    if response.status_code != 200:
      return
    if not self.msn_money:
      return
    result = response.text
    success = self.msn_money.parse_data(result)
    if not success:
      self.pe_ratios = None

  def fetch_yahoo_finance_analysis(self):
    self.yahoo_finance_analysis = YahooFinanceAnalysis(self.ticker_symbol)
    session = self._create_session()
    rpc = session.get(self.yahoo_finance_analysis.url, allow_redirects=True, hooks={
       'response': self.parse_yahoo_finance_analysis,
    })
    self.rpcs.append(rpc)

  # Called asynchronously upon completion of the URL fetch from
  # `fetch_yahoo_finance_analysis`.
  def parse_yahoo_finance_analysis(self, response, *args, **kwargs):
    if response.status_code != 200:
      return
    if not self.yahoo_finance_analysis:
      return
    result = response.text
    success = self.yahoo_finance_analysis.parse_analyst_five_year_growth_rate(result)
    if not success:
      self.yahoo_finance_analysis = None

  def fetch_yahoo_finance_chart(self):
    self.yahoo_finance_chart = YahooFinanceChart(self.ticker_symbol)
    session = self._create_session()
    rpc = session.get(self.yahoo_finance_chart.url, allow_redirects=True, hooks={
       'response': self.parse_yahoo_finance_chart,
    })
    self.rpcs.append(rpc)

  # Called asynchronously upon completion of the URL fetch from
  # `fetch_yahoo_finance_analysis`.
  def parse_yahoo_finance_chart(self, response, *args, **kwargs):
    if response.status_code != 200:
      return
    if not self.yahoo_finance_chart:
      return
    result = response.text
    success = self.yahoo_finance_chart.parse_chart(result)
    if not success:
      self.yahoo_finance_chart = None
