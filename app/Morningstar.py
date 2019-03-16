"""This API is for fetching data from Morningstar and parsing the fields into
python data structures
"""


import csv
import logging
import RuleOneInvestingCalculations as RuleOne
import traceback
import urllib2

class MorningstarReport:
  BASE_URL = 'http://financials.morningstar.com/ajax/ReportProcess4CSV.html?t={}&reportType={}&period={}&dataType=A&order={}&number={}'

  TYPE_INCOME_STATEMENT = 'is'
  TYPE_CASH_FLOW = 'cf'
  TYPE_BALANCE_SHEET = 'bs'

  PERIOD_ANNUAL = '12'
  PERIOD_QUARTERLY = '3'

  ORDER_ASCENDING = 'asc'
  ORDER_DESCENDING = 'desc'

  UNIT_NONE = '1'
  UNIT_THOUSANDS = '2'
  UNIT_MILLIONS = '3'
  UNIT_BILLIONS = '4'


  @classmethod
  def construct_url(cls, ticker_symbol, type, period, order=ORDER_ASCENDING, unit=UNIT_MILLIONS):
    url = MorningstarReport.BASE_URL.format(ticker_symbol, type, period, order, unit)
    return url

  @classmethod
  def download_report(cls, ticker_symbol, type, period):
    report = cls(ticker_symbol, type, period)
    success = report.fetch_report()
    return report if success else None

  def __init__(self, ticker_symbol, type, period):
    self.ticker_symbol = ticker_symbol
    self.type = type
    self.period = period
    self.raw_data = []
    self.net_income = []
    self.ttm_net_income = -1
    self.url = MorningstarReport.construct_url(ticker_symbol, type, period)

  def fetch_report(self):
    try:
      logging.info(self.url)
      response = urllib2.urlopen(self.url)
      csv_reader = csv.reader(response)
      for row in csv_reader:
        self.raw_data.append(row)
      self.net_income = extract_float_data_for_key(self.raw_data, 'Net income', True)
      if not self.net_income:
        logging.error('Cannot parse net_income.')
      else:
        self.ttm_net_income = self.net_income[-1]
    except Exception as e:
      logging.error(traceback.format_exc())
      return False
    return True

class MorningstarRatios:
  """An object holding """

  MORNINGSTAR_RATIOS_URL = 'http://financials.morningstar.com/ajax/exportKR2CSV.html?t='

  @classmethod
  def download_ratios(cls, ticker_symbol):
    """Initializes the ratio with a given ticker symbol and fetches the data.

    Args:
      ticker_symbol: A string representing the ticker symbol.

    Returns:
      Returns a fully initialized MorningstarRatios object, or None if the URL
      fetch failed.
    """
    ratios = cls(ticker_symbol)
    success = ratios.fetch_ratios()
    return ratios if success else None

  def __init__(self, ticker_symbol):
    """Initializes the ratio with a given ticker symbol.

    Args:
      ticker_symbol: A string representing the ticker symbol.
    """
    self.ticker_symbol = ticker_symbol
    self.ratios_url = self.MORNINGSTAR_RATIOS_URL + ticker_symbol
    self.raw_data = []
    self.roic = []  # Return on invested capital
    self.roic_averages = []
    self.equity = []  # Equity or BVPS (book value per share)
    self.equity_averages = []
    self.free_cash_flow = []  # Free Cash Flow
    self.free_cash_flow_averages = []
    self.sales_averages = []  # Revenue
    self.eps_averages = []  # Earnings per share
    self.long_term_debt = 0
    self.recent_free_cash_flow = 0
    self.debt_payoff_time = 0

  def fetch_ratios(self):
    """Downloads the ratios URL and populates the ratios correctly."""
    try:
      logging.info(self.ratios_url)
      response = urllib2.urlopen(self.ratios_url)
      csv_reader = csv.reader(response)
      for row in csv_reader:
        self.raw_data.append(row)
      if not len(self.raw_data):
        logging.error('No Morningstar data')
        return False
      self.roic = extract_float_data_for_key(self.raw_data, 'Return on Invested Capital %')
      self.roic_averages = compute_growth_rates_for_data(self.roic)
      if not self.roic_averages:
        logging.error('Failed to parse ROIC')
      self.equity = extract_float_data_for_key(self.raw_data, 'Book Value Per Share * USD')
      self.equity_averages = compute_growth_rates_for_data(self.equity)
      if not self.equity:
        logging.error('Failed to parse BVPS.')
      self.free_cash_flow = extract_float_data_for_key(self.raw_data, 'Free Cash Flow USD Mil')
      self.free_cash_flow_averages = compute_growth_rates_for_data(self.free_cash_flow)
      if not self.free_cash_flow:
        logging.error('Failed to parse Free Cash Flow.')
      else:
        self.recent_free_cash_flow = self.free_cash_flow[-1] * 1000000
      self.long_term_debt = extract_float_data_for_key(self.raw_data, 'Long-Term Debt')
      if not self.long_term_debt or not self.recent_free_cash_flow:
        self.long_term_debt = 0
        logging.error('Failed to parse Long Term Debt')
        self.debt_payoff_time = 0
      else:
        self.long_term_debt = self.long_term_debt[-1] * 1000000
        self.debt_payoff_time = self.long_term_debt / self.recent_free_cash_flow
      self.sales_averages = extract_averages_from_data_for_key(self.raw_data, 'Revenue %')
      if not self.sales_averages:
        logging.error('Failed to parse Sales Averages')
      self.eps_averages = extract_averages_from_data_for_key(self.raw_data, 'EPS %')
      if not self.eps_averages:
        logging.error('Failed to parse EPS averages.')
    except Exception as e:
      logging.error(traceback.format_exc())
      return False
    return True


def extract_averages_from_data_for_key(raw_data, key):
  """Extracts a set of precomputed averages from the data given a key into
  raw_data.

  Args:
    key: A string key to index self.raw_data.

  Returns:
    Returns a list of the 10-year, 5-year, 3-year, and year-over-year
    averages.
  """
  # Determine the row where the data starts. The format for the averages are:
  #   n -> Key
  #   n+1 -> Year over Year
  #   n+2 -> 3-Year Average
  #   n+3 -> 5-Year Average
  #   n+4 -> 10-Year Average
  index = 0
  for row in raw_data:
    index = index + 1
    if key in row:
      break
  if index >= len(raw_data):
    return None
  # Grab the second-to-last element for each list since we want to skip the
  # last quarter value.
  year_over_year = float(raw_data[index][-2]) if raw_data[index][-2] else None
  average_3 = float(raw_data[index+1][-2]) if raw_data[index+1][-2] else None
  average_5 = float(raw_data[index+2][-2]) if raw_data[index+2][-2] else None
  average_10 = float(raw_data[index+3][-2]) if raw_data[index+3][-2] else None
  return [x for x in [year_over_year, average_3, average_5, average_10] if x is not None]


def extract_float_data_for_key(raw_data, key, include_ttm=False):
  """Extracts a specific row of data given a key into self.raw_data.

  Args:
  key: A string key to index self.raw_data.

  Returns:
    Returns a list of the extracted data for the key.
  """
  for row in raw_data:
    if key in row:
      # Drop the first element since it's the key, and drop the last element
      # which is the TTM (trailing twelve month) and is often duplicated.
      if include_ttm:
        return [float(x.replace(',', '')) for x in filter(None, row[1:])]
      else:
        return [float(x.replace(',', '')) for x in filter(None, row[1:-1])]
  return None


def compute_growth_rates_for_data(data):
  if data is None or len(data) < 2:
    return None
  results = []
  year_over_year = RuleOne.compound_annual_growth_rate(data[-2], data[-1], 1)
  results.append(year_over_year)
  if len(data) > 3:
    average_3 = RuleOne.compound_annual_growth_rate(data[-4], data[-1], 3)
    results.append(average_3)
  if len(data) > 5:
    average_5 = RuleOne.compound_annual_growth_rate(data[-6], data[-1], 5)
    results.append(average_3)
  if len(data) > 6:
    last_index = len(data) - 1
    max = RuleOne.compound_annual_growth_rate(data[0], data[-1], last_index)
    results.append(max)
  return [x for x in results if x is not None]