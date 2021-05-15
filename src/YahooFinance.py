import json
import logging
import re
from lxml import html


class YahooFinanceQuote:
  # Expects the ticker symbol as the only argument.
  # This can theoretically request multiple comma-separated symbols.
  # This could theoretically be trimmed down by using `fields=` parameter.
  URL_TEMPLATE = 'https://query1.finance.yahoo.com/v7/finance/quote?symbols={}'

  @classmethod
  def _construct_url(cls, ticker_symbol):
    return YahooFinanceQuote.URL_TEMPLATE.format(ticker_symbol)

  def __init__(self, ticker_symbol):
    self.ticker_symbol = ticker_symbol
    self.url = YahooFinanceQuote._construct_url(ticker_symbol)
    self.current_price = None

  def parse_current_price(self, content):
    data = json.loads(content)
    results = data.get('quoteResponse', {}).get('result', [])
    if results:
      self.current_price = results[0].get('regularMarketPrice', None)
    return True if self.current_price else False


class YahooFinanceAnalysis:
  URL_TEMPLATE = 'https://finance.yahoo.com/quote/{}/analysis?p={}'

  @classmethod
  def _construct_url(cls, ticker_symbol):
    return cls.URL_TEMPLATE.format(ticker_symbol, ticker_symbol)

  @classmethod
  def _isPercentage(cls, text):
    if not isinstance(text, str):
      return False
    match = re.match('(\d+(\.\d+)?%)', text)
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
    self.ticker_symbol = ticker_symbol
    self.url = YahooFinanceAnalysis._construct_url(ticker_symbol)
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