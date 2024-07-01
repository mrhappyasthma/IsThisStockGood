from enum import Enum
import json
import logging
import re
from lxml import html

class YahooFinanceAnalysis:
  URL_TEMPLATE = 'https://finance.yahoo.com/quote/{}/analysis?p={}'

  @classmethod
  def _construct_url(cls, ticker_symbol):
    return cls.URL_TEMPLATE.format(ticker_symbol, ticker_symbol)

  @classmethod
  def _isPercentage(cls, text):
    if not isinstance(text, str):
      return False
    match = re.match(r'(\d+(\.\d+)?%)', text)
    return match != None

  @classmethod
  def _parseNextPercentage(cls, iterator):
    try:
      node = None
      while node is None or not cls._isPercentage(node.text):
        node = next(iterator)
      return node.text
    except:  # End of iteration
      return None

  def __init__(self, ticker_symbol):
    self.ticker_symbol = ticker_symbol.replace('.', '-')
    self.url = YahooFinanceAnalysis._construct_url(self.ticker_symbol)
    self.five_year_growth_rate = None

  def parse_analyst_five_year_growth_rate(self, content):
    tree = html.fromstring(bytes(content, encoding='utf8'))
    tree_iterator = tree.iter()
    for element in tree_iterator:
      text = element.text
      if text == 'Next 5 Years (per annum)':
        percentage = YahooFinanceAnalysis._parseNextPercentage(tree_iterator)
        self.five_year_growth_rate = percentage.rstrip("%") if percentage else None
    return True if self.five_year_growth_rate else False
