"""This API is for fetching data from Morningstar and parsing the fields into
python data structures
"""


import csv
import logging
import src.RuleOneInvestingCalculations as RuleOne
import traceback


class MorningstarRatios:
  """An object holding """

  MORNINGSTAR_RATIOS_URL = 'https://financials.morningstar.com/finan/financials/get{}Part.html?&t={}&region=usa&culture=en-US&cur=&order=asc'

  def __init__(self, ticker_symbol):
    """Initializes the ratio with a given ticker symbol.

    Args:
      ticker_symbol: A string representing the ticker symbol.
    """
    self.ticker_symbol = ticker_symbol
    self.key_stat_url = self.MORNINGSTAR_RATIOS_URL.format('KeyStat', ticker_symbol)
    self.finance_url = self.MORNINGSTAR_RATIOS_URL.format('Finance', ticker_symbol)
    self.finance_data = []
    self.ratios_data = []
    self.roic = []  # Return on invested capital
    self.roic_averages = []
    self.equity = []  # Equity or BVPS (book value per share)
    self.equity_growth_rates = []
    self.free_cash_flow = []  # Free Cash Flow
    self.free_cash_flow_growth_rates = []
    self.sales_growth_rate_averages = []  # Revenue
    self.eps_growth_rate_averages = []  # Earnings per share
    self.ttm_eps = 0
    self.ttm_net_income = 0
    self.long_term_debt = 0
    self.recent_free_cash_flow = 0
    self.debt_payoff_time = 0
    self.debt_equity_ratio = -1

  def parse_finances(self, data):
    try:
      csv_reader = csv.reader(data)
      for row in csv_reader:
        if row:
          self.finance_data.append(row)
      if not len(self.finance_data):
        logging.error('No Morningstar finance data')
        return False
      self.equity = extract_float_data_for_key(self.finance_data, 'Book Value Per Share * USD')
      self.equity_growth_rates = compute_growth_rates_for_data(self.equity)
      if not self.equity:
        logging.error('Failed to parse BVPS.')
      self.free_cash_flow = extract_float_data_for_key(self.finance_data, 'Free Cash Flow USD Mil')
      self.free_cash_flow_growth_rates = compute_growth_rates_for_data(self.free_cash_flow)
      if not self.free_cash_flow:
        logging.error('Failed to parse Free Cash Flow.')
      else:
        self.recent_free_cash_flow = self.free_cash_flow[-1] * 1000000 # In USD millions
      net_income = extract_float_data_for_key(self.finance_data, 'Net Income USD Mil', include_ttm=True)
      if not net_income:
        logging.error('Failed to parse Net Income')
      else:
        self.ttm_net_income = net_income[-1] * 1000000  # In USD millions
      eps = extract_float_data_for_key(self.finance_data, 'Earnings Per Share USD', include_ttm=True)
      if not eps:
        logging.error('Failed to parse Earnings Per Share from finances')
      else:
        self.ttm_eps = eps[-1]

    except Exception as e:
      logging.error(traceback.format_exc())
      return False
    return True

  def parse_ratios(self, data):
    """Parse the ratios data and calculates the ratios correctly."""
    try:
      csv_reader = csv.reader(data)
      for row in csv_reader:
        if row:
          self.ratios_data.append(row)
      if not len(self.ratios_data):
        logging.error('No Morningstar rtios data')
        return False
      self.roic = extract_float_data_for_key(self.ratios_data, 'Return on Invested Capital %')
      self.roic_averages = compute_averages_for_data(self.roic)
      if not self.roic_averages:
        logging.error('Failed to parse ROIC')
      self.long_term_debt = extract_float_data_for_key(self.ratios_data, 'Long-Term Debt')
      self.sales_growth_rate_averages = extract_averages_from_data_for_key(self.ratios_data, 'Revenue %')
      if not self.sales_growth_rate_averages:
        logging.error('Failed to parse Sales Averages')
      self.eps_growth_rate_averages = extract_averages_from_data_for_key(self.ratios_data, 'EPS %')
      if not self.eps_growth_rate_averages:
        logging.error('Failed to parse EPS averages.')
      debt_equity = extract_float_data_for_key(self.ratios_data, 'Debt/Equity')
      if not debt_equity or not len(debt_equity):
        logging.error('Failed to parse Debt-to-Equity ratio.')
      else:
        self.debt_equity_ratio = debt_equity[-1]
    except Exception as e:
      logging.error(traceback.format_exc())
      return False
    return True

  def calculate_long_term_debt(self):
    if not self.long_term_debt or not self.recent_free_cash_flow:
      self.long_term_debt = 0
      logging.error('Failed to parse Long Term Debt')
      self.debt_payoff_time = 0
    else:
      self.long_term_debt = self.long_term_debt[-1] * 1000000
      self.debt_payoff_time = self.long_term_debt / self.recent_free_cash_flow


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
    results.append(average_5)
  if len(data) > 6:
    last_index = len(data) - 1
    max = RuleOne.compound_annual_growth_rate(data[0], data[-1], last_index)
    results.append(max)
  return [x for x in results if x is not None]


def _average(list):
  return round(sum(list) / len(list), 2)


def compute_averages_for_data(data):
  """Calculates yearly averages from a set of yearly data. Assumes no TTM entry at the end."""
  if data is None or len(data) < 2:
    return None
  results = []
  results.append(round(data[-1], 2))
  if len(data) >= 3:
    three_year = _average(data[-3:])
    results.append(three_year)
  if len(data) >= 5:
    five_year = _average(data[-5:])
    results.append(five_year)
  if len(data) >= 6:
    max = _average(data)
    results.append(max)
  return [x for x in results if x is not None]