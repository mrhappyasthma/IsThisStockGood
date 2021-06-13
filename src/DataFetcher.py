import src.RuleOneInvestingCalculations as RuleOne
from requests_futures.sessions import FuturesSession
from src.Morningstar import MorningstarRatios
from src.MSNMoney import MSNMoney
from src.YahooFinance import YahooFinanceAnalysis
from src.YahooFinance import YahooFinanceQuote

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
        'ttm_net_income',
        'margin_of_safety_price',
        'current_price'
  """
  if not ticker:
    return None

  data_fetcher = DataFetcher()
  data_fetcher.ticker_symbol = ticker

  # Make all network request asynchronously to build their portion of
  # the json results.
  data_fetcher.fetch_morningstar_ratios()
  data_fetcher.fetch_pe_ratios()
  data_fetcher.fetch_yahoo_finance_analysis()
  data_fetcher.fetch_yahoo_finance_quote()

  # Wait for each RPC result before proceeding.
  for rpc in data_fetcher.rpcs:
    rpc.result()

  ratios = data_fetcher.ratios
  if ratios:
    ratios.calculate_long_term_debt()
  pe_ratios = data_fetcher.pe_ratios
  yahoo_finance_analysis = data_fetcher.yahoo_finance_analysis
  yahoo_finance_quote = data_fetcher.yahoo_finance_quote
  if not ratios:
    return None
  margin_of_safety_price = _calculateMarginOfSafetyPrice(ratios, pe_ratios, yahoo_finance_analysis)
  payback_time = _calculatePaybackTime(ratios, yahoo_finance_quote, yahoo_finance_analysis)
  template_values = {
    'roic': ratios.roic_averages if ratios.roic_averages else [],
    'eps': ratios.eps_growth_rate_averages if ratios.eps_growth_rate_averages else [],
    'sales': ratios.sales_growth_rate_averages if ratios.sales_growth_rate_averages else [],
    'equity': ratios.equity_growth_rates if ratios.equity_growth_rates else [],
    'cash': ratios.free_cash_flow_growth_rates if ratios.free_cash_flow_growth_rates else [],
    'long_term_debt' : ratios.long_term_debt,
    'free_cash_flow' : ratios.recent_free_cash_flow,
    'debt_payoff_time' : ratios.debt_payoff_time,
    'debt_equity_ratio' : ratios.debt_equity_ratio if ratios.debt_equity_ratio >= 0 else -1,
    'ttm_net_income' : ratios.ttm_net_income if ratios.ttm_net_income else 'null',
    'margin_of_safety_price' : margin_of_safety_price if margin_of_safety_price else 'null',
    'current_price' : yahoo_finance_quote.current_price if yahoo_finance_quote and yahoo_finance_quote.current_price else 'null',
    'payback_time' : payback_time if payback_time else 'null'
  }
  return template_values


def _jsonpToCSV(s):
  # Handle a weird edge case where morningstar may return
  # the string '{"componentData":null}'
  if s == '{"componentData":null}':
    return ''

  arr = []
  ignore = False
  printing = False
  s = s.replace(',', '')
  s = s.replace('\/', '/')
  s = s.replace('&amp', '&')
  s = s.replace('&nbsp;', ' ')
  s = s.replace('</tr>', '\n')
  for c in s:
    if c == '<':
      ignore = True
      printing = False
      continue
    elif c == '>':
      ignore = False
      printing = False
      continue
    elif not ignore:
      if not printing:
        printing = True
        arr.append(',')
      arr.append(c)
  output = ''.join(arr)
  output = output.replace('\n,', '\n')
  output = output.replace(',\n', '\n')
  output = output.replace(' ,', ' ')
  output = output.replace('&mdash;', '')
  if len(output) == 0:
    return ''
  return output[1:] if output[0] == ',' else output


def _calculateMarginOfSafetyPrice(ratios, pe_ratios, yahoo_finance_analysis):
  if not ratios or not pe_ratios or not yahoo_finance_analysis:
    return None

  if not yahoo_finance_analysis.five_year_growth_rate or not ratios.equity_growth_rates:
    return None
  growth_rate = min(float(yahoo_finance_analysis.five_year_growth_rate),
                    float(ratios.equity_growth_rates[-1]))
  # Divide the growth rate by 100 to convert from percent to decimal.
  growth_rate = growth_rate / 100.0

  if not ratios.ttm_eps or not pe_ratios.pe_low or not pe_ratios.pe_high:
    return None
  margin_of_safety_price = RuleOne.margin_of_safety_price(float(ratios.ttm_eps), growth_rate,
                                                          float(pe_ratios.pe_low), float(pe_ratios.pe_high))
  return margin_of_safety_price


def _calculatePaybackTime(ratios, yahoo_finance_quote, yahoo_finance_analysis):
  if not ratios or not yahoo_finance_quote or not yahoo_finance_analysis:
    return None

  if not yahoo_finance_analysis.five_year_growth_rate or not ratios.equity_growth_rates:
    return None
  growth_rate = min(float(yahoo_finance_analysis.five_year_growth_rate),
                    float(ratios.equity_growth_rates[-1]))
  # Divide the growth rate by 100 to convert from percent to decimal.
  growth_rate = growth_rate / 100.0

  if not ratios.ttm_net_income or not yahoo_finance_quote.market_cap:
    return None
  payback_time = RuleOne.payback_time(yahoo_finance_quote.market_cap, ratios.ttm_net_income, growth_rate)
  return payback_time


class DataFetcher():
  """A helper class that syncronizes all of the async data fetches."""
  def __init__(self,):
    self.rpcs = []
    self.ticker_symbol = ''
    self.ratios = None
    self.pe_ratios = None
    self.yahoo_finance_analysis = None
    self.yahoo_finance_quote = None
    self.error = False


  def fetch_morningstar_ratios(self):
    self.ratios = MorningstarRatios(self.ticker_symbol)
    session = FuturesSession()
    key_stat_rpc = session.get(self.ratios.key_stat_url, hooks={
       'response': self.parse_morningstar_ratios,
    })
    self.rpcs.append(key_stat_rpc)

    finance_rpc = session.get(self.ratios.finance_url, hooks={
       'response': self.parse_morningstar_finances,
    })
    self.rpcs.append(finance_rpc)

  # Called asynchronously upon completion of the URL fetch from
  # `fetch_morningstar_ratios`.
  def parse_morningstar_finances(self, response, *args, **kwargs):
    if not self.ratios:
      return
    parsed_content = _jsonpToCSV(response.text)
    success = self.ratios.parse_finances(parsed_content.split('\n'))
    if not success:
      self.ratios = None

  # Called asynchronously upon completion of the URL fetch from
  # `fetch_morningstar_ratios`.
  def parse_morningstar_ratios(self, response, *args, **kwargs):
    if not self.ratios:
      return
    parsed_content = _jsonpToCSV(response.text)
    success = self.ratios.parse_ratios(parsed_content.split('\n'))
    if not success:
      self.ratios = None

  def fetch_pe_ratios(self):
    self.pe_ratios = MSNMoney(self.ticker_symbol)
    session = FuturesSession()
    rpc = session.get(self.pe_ratios.url, allow_redirects=True, hooks={
       'response': self.parse_pe_ratios,
    })
    self.rpcs.append(rpc)

  # Called asynchronously upon completion of the URL fetch from
  # `fetch_pe_ratios`.
  def parse_pe_ratios(self, response, *args, **kwargs):
    if response.status_code != 200:
      return
    if not self.pe_ratios:
      return
    result = response.text
    success = self.pe_ratios.parse(result)
    if not success:
      self.pe_ratios = None

  def fetch_yahoo_finance_analysis(self):
    self.yahoo_finance_analysis = YahooFinanceAnalysis(self.ticker_symbol)
    session = FuturesSession()
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
    session = FuturesSession()
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