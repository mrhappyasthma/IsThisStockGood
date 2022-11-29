import random
import src.RuleOneInvestingCalculations as RuleOne
from requests_futures.sessions import FuturesSession
from src.MSNMoney import MSNMoney
from src.StockRow import StockRowKeyStats
from src.YahooFinance import YahooFinanceAnalysis
from src.YahooFinance import YahooFinanceQuote
from src.YahooFinance import YahooFinanceQuoteSummary, YahooFinanceQuoteSummaryModule
from threading import Lock

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
  data_fetcher.fetch_stockrow_key_stats()
  data_fetcher.fetch_pe_ratios()
  data_fetcher.fetch_yahoo_finance_analysis()
  data_fetcher.fetch_yahoo_finance_quote()
  data_fetcher.fetch_yahoo_finance_quote_summary()


  # Wait for each RPC result before proceeding.
  for rpc in data_fetcher.rpcs:
    rpc.result()

  key_stats = data_fetcher.stockrow_key_stats
  if not key_stats:
    return None
  pe_ratios = data_fetcher.pe_ratios
  yahoo_finance_analysis = data_fetcher.yahoo_finance_analysis
  yahoo_finance_quote = data_fetcher.yahoo_finance_quote
  margin_of_safety_price, sticker_price = _calculateMarginOfSafetyPrice(key_stats, pe_ratios, yahoo_finance_quote, yahoo_finance_analysis)
  payback_time = _calculatePaybackTime(key_stats, yahoo_finance_quote, yahoo_finance_analysis)
  template_values = {
    'ticker' : ticker,
    'name' : yahoo_finance_quote.name if yahoo_finance_quote and yahoo_finance_quote.name else 'null',
    'roic': data_fetcher.get_roic_averages(),
    'eps': key_stats.eps_growth_rates if key_stats.eps_growth_rates else [],
    'sales': key_stats.revenue_growth_rates if key_stats.revenue_growth_rates else [],
    'equity': key_stats.equity_growth_rates if key_stats.equity_growth_rates else [],
    'cash': key_stats.free_cash_flow_growth_rates if key_stats.free_cash_flow_growth_rates else [],
    # TODO: Figure out how to get long-term debt instead of total debt
    'total_debt' : key_stats.total_debt,
    'free_cash_flow' : key_stats.recent_free_cash_flow,
    'debt_payoff_time' : key_stats.debt_payoff_time,
    'debt_equity_ratio' : key_stats.debt_equity_ratio if key_stats.debt_equity_ratio >= 0 else -1,
    'margin_of_safety_price' : margin_of_safety_price if margin_of_safety_price else 'null',
    'current_price' : yahoo_finance_quote.current_price if yahoo_finance_quote and yahoo_finance_quote.current_price else 'null',
    'sticker_price' : sticker_price if sticker_price else 'null',
    'payback_time' : payback_time if payback_time else 'null',
    'average_volume' : yahoo_finance_quote.average_volume if yahoo_finance_quote and yahoo_finance_quote.average_volume else 'null'
  }
  return template_values

def _calculateMarginOfSafetyPrice(key_stats, pe_ratios, yahoo_finance_quote, yahoo_finance_analysis):
  if not key_stats or not pe_ratios or not yahoo_finance_analysis:
    return None, None

  if not yahoo_finance_analysis.five_year_growth_rate or not key_stats.equity_growth_rates:
    return None, None
  growth_rate = min(float(yahoo_finance_analysis.five_year_growth_rate),
                    float(key_stats.equity_growth_rates[-1]))
  # Divide the growth rate by 100 to convert from percent to decimal.
  growth_rate = growth_rate / 100.0

  if not yahoo_finance_quote or not yahoo_finance_quote.ttm_eps or not pe_ratios.pe_low or not pe_ratios.pe_high:
    return None, None
  margin_of_safety_price, sticker_price = \
      RuleOne.margin_of_safety_price(float(yahoo_finance_quote.ttm_eps), growth_rate,
                                     float(pe_ratios.pe_low), float(pe_ratios.pe_high))
  return margin_of_safety_price, sticker_price


def _calculatePaybackTime(key_stats, yahoo_finance_quote, yahoo_finance_analysis):
  if not key_stats or not yahoo_finance_quote or not yahoo_finance_analysis:
    return None

  if not yahoo_finance_analysis.five_year_growth_rate or not key_stats.equity_growth_rates:
    return None
  growth_rate = min(float(yahoo_finance_analysis.five_year_growth_rate),
                    float(key_stats.equity_growth_rates[-1]))
  # Divide the growth rate by 100 to convert from percent to decimal.
  growth_rate = growth_rate / 100.0

  # TODO: Figure out how to get TTM net income instead of previous year net income.
  if not key_stats.last_year_net_income or not yahoo_finance_quote.market_cap:
    return None
  payback_time = RuleOne.payback_time(yahoo_finance_quote.market_cap, key_stats.last_year_net_income, growth_rate)
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
    self.stockrow_key_stats = None
    self.pe_ratios = None
    self.yahoo_finance_analysis = None
    self.yahoo_finance_quote = None
    self.yahoo_finance_quote_summary = None
    self.error = False

  def _create_session(self):
    session = FuturesSession()
    session.headers.update({
      'User-Agent' : random.choice(DataFetcher.USER_AGENT_LIST)
    })
    return session

  def fetch_stockrow_key_stats(self):
    self.stockrow_key_stats = StockRowKeyStats(self.ticker_symbol)
    session = self._create_session()
    key_stat_rpc = session.get(self.stockrow_key_stats.key_stat_url, hooks={
       'response': self.parse_stockrow_key_stats,
    })
    self.rpcs.append(key_stat_rpc)

  # Called asynchronously upon completion of the URL fetch from
  # `fetch_stockrow_key_stats`.
  def parse_stockrow_key_stats(self, response, *args, **kwargs):
    self.lock.acquire()
    if not self.stockrow_key_stats:
      self.lock.release()
      return
    success = self.stockrow_key_stats.parse_json_data(response.content)
    if not success:
      self.stockrow_key_stats = None
    self.lock.release()

  def fetch_pe_ratios(self):
    """
    Fetching PE Ratios to calculate Sticker Price and Safety Margin Price
    First we need to get an internal MSN stock id for a ticker
    and then fetch PE Ratios.
    """
    self.pe_ratios = MSNMoney(self.ticker_symbol)
    session = self._create_session()
    rpc = session.get(self.pe_ratios.get_ticker_autocomplete_url(), allow_redirects=True, hooks={
       'response': self.continue_fetching_pe_ratios,
    })
    self.rpcs.append(rpc)

  def continue_fetching_pe_ratios(self, response, *args, **kwargs):
    """
    After msn_stock_id was fetched in fetch_pe_ratios method
    we can now get the financials
    """
    msn_stock_id = self.pe_ratios.extract_stock_id(response.text)
    session = self._create_session()
    rpc = session.get(self.pe_ratios.get_key_ratios_url(msn_stock_id), allow_redirects=True, hooks={
       'response': self.parse_pe_ratios,
    })
    self.rpcs.append(rpc)

  # Called asynchronously upon completion of the URL fetch from
  # `fetch_pe_ratios` and `continue_fetching_pe_ratios`.
  def parse_pe_ratios(self, response, *args, **kwargs):
    if response.status_code != 200:
      return
    if not self.pe_ratios:
      return
    result = response.text
    success = self.pe_ratios.parse_pe_ratios(result)
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

  def fetch_yahoo_finance_quote(self):
    self.yahoo_finance_quote = YahooFinanceQuote(self.ticker_symbol)
    session = self._create_session()
    rpc = session.get(self.yahoo_finance_quote.url, allow_redirects=True, hooks={
       'response': self.parse_yahoo_finance_quote,
    })
    self.rpcs.append(rpc)

  # Called asynchronously upon completion of the URL fetch from
  # `fetch_yahoo_finance_quote`.
  def parse_yahoo_finance_quote(self, response, *args, **kwargs):
    if response.status_code != 200:
      return
    if not self.yahoo_finance_quote:
      return
    result = response.text
    success = self.yahoo_finance_quote.parse_quote(result)
    if not success:
      self.yahoo_finance_quote = None

  def fetch_yahoo_finance_quote_summary(self):
    modules = [
        YahooFinanceQuoteSummaryModule.incomeStatementHistory,
        YahooFinanceQuoteSummaryModule.balanceSheetHistory
    ]
    self.yahoo_finance_quote_summary = YahooFinanceQuoteSummary(self.ticker_symbol, modules)
    session = self._create_session()
    rpc = session.get(self.yahoo_finance_quote_summary.url, allow_redirects=True, hooks={
       'response': self.parse_yahoo_finance_quote_summary,
    })
    self.rpcs.append(rpc)

  # Called asynchronously upon completion of the URL fetch from
  # `fetch_yahoo_finance_quote_summary`.
  def parse_yahoo_finance_quote_summary(self, response, *args, **kwargs):
    if response.status_code != 200:
      return
    if not self.yahoo_finance_quote_summary:
      return
    result = response.text
    success = self.yahoo_finance_quote_summary.parse_modules(result)
    if not success:
      self.yahoo_finance_quote_summary = None

  def get_roic_averages(self):
    """
    Calculate ROIC averages for 1,3,5 and Max years
    StockRow averages aren't accurate, so we're getting avgs for 1y and 3y from Yahoo
    by calculating these by ouselves. The rest is from StockRow to at least have some (even
    a bit inaccurate values), cause Yahoo has data for 4 years only.
    """
    roic_avgs = []
    try:
      roic_avgs.append(self.yahoo_finance_quote_summary.get_roic_average(years=1))
    except AttributeError:
      try:
        roic_avgs.append(self.stockrow_key_stats.roic_averages[0])
      except IndexError:
        return []
    try:
      roic_avgs.append(self.yahoo_finance_quote_summary.get_roic_average(years=3))
    except AttributeError:
      try:
        roic_avgs.append(self.stockrow_key_stats.roic_averages[1])
      except IndexError:
        return roic_avgs
    try:
      roic_avgs.append(self.stockrow_key_stats.roic_averages[2])
      roic_avgs.append(self.stockrow_key_stats.roic_averages[-1])
    except IndexError:
      pass
    return roic_avgs
