"""This API is for fetching data from Morningstar and parsing the fields into
python data structures
"""


import csv
import urllib2


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
    success = ratios.fetch()
    return ratios if success else None

  def __init__(self, ticker_symbol):
    """Initializes the ratio with a given ticker symbol.

    Args:
      ticker_symbol: A string representing the ticker symbol.
    """
    self.ticker_symbol = ticker_symbol
    self.url = self.MORNINGSTAR_RATIOS_URL + ticker_symbol
    self.raw_data = []
    self.roic = []  # Return on invested capital
    self.equity = []  # Equity or BVPS (book value per share)
    self.free_cash_flow = []  # Free Cash Flow
    self.sales_averages = []  # Revenue
    self.eps_averages = []  # Earnings per share
    self.long_term_debt = 0
    self.recent_free_cash_flow = 0
    self.debt_payoff_time = 0

  def fetch(self):
    """Fetches the URL and populates the ratios correctly."""
    try:
      response = urllib2.urlopen(self.url)
      csv_reader = csv.reader(response)
      for row in csv_reader:
        self.raw_data.append(row)
      if not len(self.raw_data):
        return False
      self.roic = self.extract_float_data_for_key('Return on Invested Capital %')
      if not self.roic:
        return False
      self.equity = self.extract_float_data_for_key('Book Value Per Share * USD')
      if not self.equity:
        return False
      self.free_cash_flow = self.extract_float_data_for_key('Free Cash Flow USD Mil')
      if not self.free_cash_flow:
        return False
      self.recent_free_cash_flow = self.free_cash_flow[-1] * 1000000
      self.long_term_debt = self.extract_float_data_for_key('Long-Term Debt')
      if not self.long_term_debt:
        return False
      self.long_term_debt = self.long_term_debt[-1] * 1000000
      self.debt_payoff_time = self.long_term_debt / self.recent_free_cash_flow
      self.sales_averages = self.extract_averages_from_data_for_key('Revenue %')
      if not self.sales_averages:
        return False
      self.eps_averages = self.extract_averages_from_data_for_key('EPS %')
      if not self.eps_averages:
        return False
    except:
      return False
    return True

  def extract_averages_from_data_for_key(self, key):
    """Extracts a set of precomputed averages from the data given a key into
    self.raw_data.

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
    for row in self.raw_data:
      index = index + 1
      if key in row:
        break
    if index >= len(self.raw_data):
      return None
    # Grab the second-to-last element for each list since we want to skip the
    # last quarter value.
    year_over_year = float(self.raw_data[index][-2])
    average_3 = float(self.raw_data[index+1][-2])
    average_5 = float(self.raw_data[index+2][-2])
    average_10 = float(self.raw_data[index+3][-2])
    return [year_over_year, average_3, average_5, average_10]

  def extract_float_data_for_key(self, key):
    """Extracts a specific row of data given a key into self.raw_data.

    Args:
      key: A string key to index self.raw_data.

    Returns:
      Returns a list of the extracted data for the key.
    """
    for row in self.raw_data:
      if key in row:
        # Drop the first element since it's the key, and drop the last element
        # which is the TTM (trailing twelve month) and is often duplicated.
        return [float(x.replace(',', '')) for x in filter(None, row[1:-1])]
    return None