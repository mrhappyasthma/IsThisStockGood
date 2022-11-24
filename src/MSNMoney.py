import json

class MSNMoney:
  TICKER_URL = 'https://services.bingapis.com/contentservices-finance.csautosuggest/api/v1/Query?query={}&market=en-us'
  BASE_URL = 'https://services.bingapis.com/contentservices-finance.financedataservice/api/v1/KeyRatios?stockId={}'

  def __init__(self, ticker_symbol):
    self.ticker_symbol = ticker_symbol.replace('.', '')
    self.pe_high = None
    self.pe_low = None

  def get_ticker_autocomplete_url(self):
    return self.TICKER_URL.format(self.ticker_symbol)

  def get_financials_url(self, stock_id):
    return self.BASE_URL.format(stock_id)

  def extract_stock_id(self, content):
    data = json.loads(content)
    for ticker in data['data']['stocks']:
        js = json.loads(ticker)
        if js['RT00S'] == self.ticker_symbol:
            return js['SecId']

  def parse(self, content):
    data = json.loads(content)
    recent_pe_ratios = [
      year['priceToEarningsRatio']
      for year in data['companyMetrics']
      if year['fiscalPeriodType'] == 'Annual'
      and 'priceToEarningsRatio' in year
    ][-5:]
    try:
      self.pe_high = max(recent_pe_ratios)
      self.pe_low = min(recent_pe_ratios)
    except ValueError:
        return False
    return True
