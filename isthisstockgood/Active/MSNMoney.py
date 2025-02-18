import json
import isthisstockgood.RuleOneInvestingCalculations as RuleOne



class MSNMoney:
  # This key appears to be fixed? So we can use it for now /shrug
  _API_KEY = '0QfOX3Vn51YCzitbLaRkTTBadtWpgTN8NZLW0C1SEM'
  TICKER_URL = 'https://services.bingapis.com/contentservices-finance.csautosuggest/api/v1/Query?query={}&market=en-us'
  KEY_RATIOS_URL = 'https://services.bingapis.com/contentservices-finance.financedataservice/api/v1/KeyRatios?stockId={}'
  ANNUAL_STATEMENTS_URL = 'https://assets.msn.com/service/Finance/Equities?apikey={}&ids={}&wrapodata=false'
  QUOTES_URL = 'https://assets.msn.com/service/Finance/Quotes?apikey={}&ids={}&wrapodata=false'
  KEY_RATIOS_YEAR_SPAN = 5

  def __init__(self, ticker_symbol):
    self.ticker_symbol = ticker_symbol.replace('.', '')
    self.name = ''
    self.description = ''
    self.industry = ''
    self.current_price = ''
    self.average_volume = ''
    self.market_cap = ''
    self.shares_outstanding = ''
    self.pe_high = None
    self.pe_low = None
    self.roic = []  # Return on invested capital
    self.roic_averages = []
    self.equity = []  # Equity or BVPS (book value per share)
    self.equity_growth_rates = []
    self.free_cash_flow = []  # Free Cash Flow
    self.free_cash_flow_growth_rates = []
    self.revenue = []
    self.revenue_growth_rates = []  # Revenue
    self.eps = []
    self.eps_growth_rates = []  # Earnings per share
    self.debt_equity_ratio = -1
    self.last_year_net_income = 0
    self.total_debt = 0


  def get_ticker_autocomplete_url(self):
    return self.TICKER_URL.format(self.ticker_symbol)

  def get_key_ratios_url(self, stock_id):
    return self.KEY_RATIOS_URL.format(stock_id)
  
  def get_quotes_url(self, stock_id):
    return self.QUOTES_URL.format(self._API_KEY, stock_id)
  
  def get_annual_statements_url(self, stock_id):
    return self.ANNUAL_STATEMENTS_URL.format(self._API_KEY, stock_id)

  def extract_stock_id(self, content):
    data = json.loads(content)
    for ticker in data.get('data', {}).get('stocks', []):
      js = json.loads(ticker)
      if js.get('RT00S', '').upper() == self.ticker_symbol.upper():
        self.description = js.get('Description', '')
        return js.get('SecId', '')


  def parse_quotes_data(self, content):
    json_content = json.loads(content);
    if not json_content or len(json_content) < 1:
      return
    data = json_content[0]
    self.current_price = data.get('price', '')
    self.average_volume = data.get('averageVolume', '')
    self.market_cap = data.get('marketCap', '')
  
  
  def parse_annual_report_data(self, content):
    json_content = json.loads(content);
    if not json_content or len(json_content) < 1:
      return
    data = json_content[0]
    annual_statements = data.get('analysis', {}).get('annualStatements', {})
    if not annual_statements or len(annual_statements) < 1:
      return
    most_recent_statement = annual_statements[max(annual_statements.keys())]
    if not most_recent_statement:
      return
    self.total_debt = float(most_recent_statement.get('longTermDebt', 0))
    self.shares_outstanding = float(most_recent_statement.get('sharesOutstanding', 0))
    

  def parse_ratios_data(self, content):
    json_content = json.loads(content);
    yearly_data, quarterly_data = self._parse_company_metrics(json_content)
    if not yearly_data or not quarterly_data:
      return False
    
    self.name = json_content.get('displayName', '')
    self.industry = json_content.get('industry', '')
    
    # PE Ratios
    self._parse_pe_ratios(yearly_data)
    
    # "Big 5" numbers -- compound growth rates / averages
    self._parse_eps_growth_rate(yearly_data)
    self._parse_free_cash_flow_growth_rate(yearly_data)
    self._parse_equity_growth_rate(yearly_data)
    self._parse_revenue_growth_rate(yearly_data)
    self._parse_roic_average(yearly_data)
    
    # Debt
    self._parse_debt_to_equity(quarterly_data)

    # Quarterly EPS for MOSP valuation
    self.quarterly_eps = _extract_data_for_key(quarterly_data, "earningsPerShare")

    # For Payback Time valuation:
    # "EPS is calculated by dividing a company's net income
    # by the total number of outstanding shares."
    # - https://www.investopedia.com/terms/e/eps.asp
    ttm_eps = sum(self.quarterly_eps[-4:])
    self.last_year_net_income =  ttm_eps * self.shares_outstanding
    
    return True


  def _parse_company_metrics(self, json_data):
      yearly_data = []
      quarterly_data = []
      for metrics in json_data.get('companyMetrics', []):
        time_period = metrics.get('fiscalPeriodType', '')
        if time_period == 'Annual':  # Ignore quarterly data since we don't use it yet.
          yearly_data.append(metrics)
        elif 'Q' in time_period:
          quarterly_data.append(metrics)
      return yearly_data, quarterly_data


  def _parse_pe_ratios(self, yearly_data):
    recent_pe_ratios = _extract_data_for_key(yearly_data, "priceToEarningsRatio")[-self.KEY_RATIOS_YEAR_SPAN:]
    if len(recent_pe_ratios) != self.KEY_RATIOS_YEAR_SPAN:
      return
    try:
      self.pe_high = max(recent_pe_ratios)
      self.pe_low = min(recent_pe_ratios)
    except ValueError:
        return

  def _parse_eps_growth_rate(self, yearly_data):
    self.eps = _extract_data_for_key(yearly_data, "earningsPerShare")
    self.eps_growth_rates = _compute_growth_rates_for_data(self.eps)
    

  def _parse_free_cash_flow_growth_rate(self, yearly_data):
    self.free_cash_flow = _extract_data_for_key(yearly_data, "freeCashFlowPerShare")
    self.free_cash_flow_growth_rates = _compute_growth_rates_for_data(self.free_cash_flow)


  def _parse_equity_growth_rate(self, yearly_data):  # i.e. Book Value Per Share
    self.equity = _extract_data_for_key(yearly_data, "bookValuePerShare")
    self.equity_growth_rates = _compute_growth_rates_for_data(self.equity)  


  def _parse_revenue_growth_rate(self, yearly_data):  # i.e. Sales
    self.revenue = _extract_data_for_key(yearly_data, "revenuePerShare")
    self.revenue_growth_rates = _compute_growth_rates_for_data(self.revenue)      


  def _parse_roic_average(self, yearly_data):
    # NOTE: ROIC is already expressed as a percentage, so just take the average over a timespan.
    self.roic = _extract_data_for_key(yearly_data, "roic")
    self.roic_averages = _compute_averages_for_data(self.revenue)  
    
  
  def _parse_debt_to_equity(self, quarterly_data):
    # NOTE: ROIC is already expressed as a percentage, so just take the average over a timespan.
    debt_to_equity_ratios = _extract_data_for_key(quarterly_data, "debtToEquityRatio")
    self.debt_equity_ratio = debt_to_equity_ratios[-1] / 100  # Most recent quarter


def _extract_data_for_key(yearly_data, key):
  """Extracts a specific metric from the yearly data array with a given key."""
  metrics = []
  for year in yearly_data:
    if key in year:
      metrics.append(year[key])
  return metrics


def _compute_growth_rates_for_data(data):
  """Computes the compound annual growth rate between 1, 3, 5, and maximum year periods."""
  if data is None or len(data) < 2:
    return None
  results = []
  year_over_year = RuleOne.compound_annual_growth_rate(data[-2], data[-1], 1)
  results.append(year_over_year)
  if len(data) > 3:
    growth_rate_3 = RuleOne.compound_annual_growth_rate(data[-4], data[-1], 3)
    results.append(growth_rate_3)
  if len(data) > 5:
    growth_rate_5 = RuleOne.compound_annual_growth_rate(data[-6], data[-1], 5)
    results.append(growth_rate_5)
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
