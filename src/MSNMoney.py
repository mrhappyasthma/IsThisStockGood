import json

class MSNMoney:
  TICKER_URL = 'https://services.bingapis.com/contentservices-finance.csautosuggest/api/v1/Query?query={}&market=en-us'
  KEY_RATIOS_URL = 'https://services.bingapis.com/contentservices-finance.financedataservice/api/v1/KeyRatios?stockId={}'
  KEY_RATIOS_YEAR_SPAN = 5

  def __init__(self, ticker_symbol):
    self.ticker_symbol = ticker_symbol.replace('.', '')
    self.pe_high = None
    self.pe_low = None

  def get_ticker_autocomplete_url(self):
    return self.TICKER_URL.format(self.ticker_symbol)

  def get_key_ratios_url(self, stock_id):
    return self.KEY_RATIOS_URL.format(stock_id)

  def extract_stock_id(self, content):
    data = json.loads(content)
    for ticker in data.get('data', {}).get('stocks', []):
        js = json.loads(ticker)
        if js.get('RT00S', '').upper() == self.ticker_symbol.upper():
            return js.get('SecId', '')

  def parse_pe_ratios(self, content):
    return self._parse_pe_ratios(json.loads(content))

  def _parse_pe_ratios(self, data):
    recent_pe_ratios = [
      year.get('priceToEarningsRatio', None)
      for year in data.get('companyMetrics', [])
      if year.get('fiscalPeriodType', '') == 'Annual'
      and 'priceToEarningsRatio' in year
    ][-self.KEY_RATIOS_YEAR_SPAN:]
    if len(recent_pe_ratios) != self.KEY_RATIOS_YEAR_SPAN:
      return False
    try:
      self.pe_high = max(recent_pe_ratios)
      self.pe_low = min(recent_pe_ratios)
    except ValueError:
        return False
    return True
