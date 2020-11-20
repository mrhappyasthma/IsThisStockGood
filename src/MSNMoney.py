import logging
from lxml import html

def isfloat(value):
  if value is None:
    return False
  try:
    float(value)
    return True
  except ValueError:
    return False

class MSNMoney:
  BASE_URL = 'https://www.msn.com/en-us/money/stockdetails/analysis?symbol={}'
  PE_HIGH_KEY = 'P/E Ratio 5-Year High'
  PE_LOW_KEY = 'P/E Ratio 5-Year Low'

  @classmethod
  def construct_url(cls, ticker_symbol,):
    url = MSNMoney.BASE_URL.format(ticker_symbol)
    return url

  def __init__(self, ticker_symbol):
    self.ticker_symbol = ticker_symbol
    self.pe_high = None
    self.pe_low = None
    self.url = MSNMoney.construct_url(ticker_symbol)

  def nextFloatFromIterator(self, iterator):
    node = None
    while node is None or not isfloat(node.text):
      node = next(iterator)
    return node.text

  def parse(self, content):
    tree = html.fromstring(content)
    tree_iterator = tree.iter()
    for element in tree_iterator:
      text = element.text
      if text == MSNMoney.PE_HIGH_KEY:
        self.pe_high = self.nextFloatFromIterator(tree_iterator)
      if text == MSNMoney.PE_LOW_KEY:
        self.pe_low = self.nextFloatFromIterator(tree_iterator)
    if self.pe_high is not None and self.pe_low is not None:
      return True
    return False