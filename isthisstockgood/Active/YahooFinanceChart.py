import json


class YahooFinanceChart:
  # Expects the ticker symbol as the only argument.
  URL_TEMPLATE = 'https://query1.finance.yahoo.com/v8/finance/chart/{}'

  @classmethod
  def _construct_url(cls, ticker_symbol):
    return YahooFinanceChart.URL_TEMPLATE.format(ticker_symbol)

  def __init__(self, ticker_symbol):
    self.ticker_symbol = ticker_symbol.replace('.', '-')  # URL expects dashes
    self.url = YahooFinanceChart._construct_url(self.ticker_symbol)
    self.current_price = None

  def parse_chart(self, content):
    data = json.loads(content)
    results = data.get('chart', {}).get('result', [])
    if not results:
      return False
    success = self._parse_current_price(results)
    return success

  def _parse_current_price(self, results):
    if results:
      self.current_price = results[0].get('meta', {}).get('regularMarketPrice', None)
    return True if self.current_price else False
