"""This API is for fetching data from StockRow and parsing the fields into
python data structures
"""

import json
import logging
import src.RuleOneInvestingCalculations as RuleOne
import traceback

# Stockrow does not seem to update their ticker symbols very promptly. This can be used
# as a temporary mapping to allow strocks to continue to work after a rename.
def _temporary_ticker_mapping(ticker_symbol):
  mapping = {
      'META' : 'FB'
  }
  return mapping.get(ticker_symbol.upper(), ticker_symbol)

class StockRowKeyStats:
  """An object wrapping the key stats data from stockrow.com"""

  STOCKROW_KEY_STATS_URL = 'https://stockrow.com/api/companies/{}/new_key_stats.json'

  def __init__(self, ticker_symbol):
    """Initializes the ratio with a given ticker symbol.

    Args:
      ticker_symbol: A string representing the ticker symbol.
    """
    self.ticker_symbol = _temporary_ticker_mapping(ticker_symbol)
    self.key_stat_url = self.STOCKROW_KEY_STATS_URL.format(self.ticker_symbol)
    self.roic = []  # Return on invested capital
    self.roic_averages = []
    self.equity = []  # Equity or BVPS (book value per share)
    self.equity_growth_rates = []
    self.free_cash_flow = []  # Free Cash Flow
    self.free_cash_flow_growth_rates = []
    self.revenue_growth_rates = []  # Revenue
    self.eps_growth_rates = []  # Earnings per share
    self.last_year_net_income = 0
    self.total_debt = 0
    self.recent_free_cash_flow = 0
    self.debt_payoff_time = 0
    self.debt_equity_ratio = -1

  def parse_json_data(self, data):
    try:
      print(data)
      json_data = json.loads(data)
      data_dict = {}
      rows = json_data.get("fundamentals", {}).get("rows", [])
      _add_list_of_dicts_to_dict(rows, data_dict, "label")

      capital_structures = json_data.get("capital_structure", {})
      singles = capital_structures.get("singles", [])
      _add_list_of_dicts_to_dict(singles, data_dict, "label")

      sparklines = capital_structures.get("sparklines", [])
      _add_list_of_dicts_to_dict(sparklines, data_dict, "label")

      self.roic = _get_nested_values_for_key(data_dict, "ROIC")
      # Convert from decimal to percent
      self.roic = [self.roic[i] * 100 for i in range(0, len(self.roic))]
      self.roic_averages = _compute_averages_for_data(self.roic)
      if not self.roic_averages:
        logging.error('Failed to parse ROIC')

      revenue = _get_nested_values_for_key(data_dict, "Revenue")
      self.revenue_growth_rates = compute_growth_rates_for_data(revenue)
      if not self.revenue_growth_rates:
        logging.error('Failed to parse Revenue growth rates')

      eps = _get_nested_values_for_key(data_dict, "Earnings/Sh")
      self.eps_growth_rates = compute_growth_rates_for_data(eps)
      if not self.eps_growth_rates:
        logging.error('Failed to parse EPS growth rates')

      debt_equity = _get_nested_value_for_key(data_dict, "Debt to Equity (Q)")
      if not debt_equity:
        logging.error('Failed to parse Debt-to-Equity ratio.')
      else:
        self.debt_equity_ratio = debt_equity

      self.equity = _get_nested_values_for_key(data_dict, "Book Value/Sh")
      self.equity_growth_rates = compute_growth_rates_for_data(self.equity)
      if not self.equity:
        logging.error('Failed to parse BVPS.')

      self.free_cash_flow = _get_nested_values_for_key(data_dict, "FCF")
      self.free_cash_flow_growth_rates = compute_growth_rates_for_data(self.free_cash_flow)
      if not self.free_cash_flow:
        logging.error('Failed to parse Free Cash Flow.')
      else:
        self.recent_free_cash_flow = self.free_cash_flow[-1] # Data already in USD millions
        
      net_income = _get_nested_values_for_key(data_dict, "Net Income")
      if net_income and len(net_income):
        self.last_year_net_income = net_income[-1]
      
      total_debts = _get_nested_values_for_key(data_dict, "Total Debt") # Already in USD millions
      self.calculate_total_debt(total_debts)
    except ValueError:
      logging.error(traceback.format_exc())
      return False
    return True


  def calculate_total_debt(self, total_debts):
    if not len(total_debts) > 0 or not self.recent_free_cash_flow:
      self.total_debt = 0
      logging.error('Failed to parse Long Term Debt')
      self.debt_payoff_time = 0
    else:
      self.total_debt = total_debts[-1]  # Data already in USD millions
      self.debt_payoff_time = self.total_debt / self.recent_free_cash_flow


def _add_list_of_dicts_to_dict(list_of_dicts, target_dict, key_name):
  for i in range(0, len(list_of_dicts)):
    value = list_of_dicts[i]
    key = value.get(key_name, "")
    if not key:
      continue
    target_dict[key] = value


def _get_nested_values_for_key(dictionary, key):
  elements = dictionary.get(key, {}).get("values", [])
  return [x for x in elements if isinstance(x, (int, float, complex))]
 
 
def _get_nested_value_for_key(dictionary, key):
  value = dictionary.get(key, {}).get("value", None)
  return value if isinstance(value, (int, float, complex)) else None


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
    max_val = RuleOne.compound_annual_growth_rate(data[0], data[-1], last_index)
    results.append(max_val)
  return [x for x in results if x is not None]


def _average(list):
  return round(sum(list) / len(list), 2)


def _compute_averages_for_data(data):
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
    max_val = _average(data)
    results.append(max_val)
  return [x for x in results if x is not None]
