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


class YahooFinanceQuoteSummaryModule(Enum):
    assetProfile = 1
    incomeStatementHistory = 2
    incomeStatementHistoryQuarterly = 3
    balanceSheetHistory = 4
    balanceSheetHistoryQuarterly = 5
    cashFlowStatementHistory = 6
    cashFlowStatementHistoryQuarterly = 7
    defaultKeyStatistics = 8
    financialData = 9
    calendarEvents = 10
    secFilings = 11
    recommendationTrend = 12
    upgradeDowngradeHistory = 13
    institutionOwnership = 14
    fundOwnership = 15
    majorDirectHolders = 16,
    majorHoldersBreakdown = 17
    insiderTransactions = 18
    insiderHolders = 19
    netSharePurchaseActivity = 20
    earnings = 21
    earningsHistory = 22
    earningsTrend = 23
    industryTrend = 24
    indexTrend = 26
    sectorTrend = 27


## (unofficial) API documentation: https://observablehq.com/@stroked/yahoofinance
class YahooFinanceQuoteSummary:
  # Expects the ticker symbol as the first format string, and a comma-separated list
  # of `QuotesummaryModules` strings for the second argument.
  _URL_TEMPLATE = 'https://query1.finance.yahoo.com/v10/finance/quoteSummary/{}?modules={}'
  _CRUMB_URL = 'https://query1.finance.yahoo.com/v1/test/getcrumb'

  # A list of modules that can be used inside of `QUOTE_SUMMARY_URL_TEMPLATE`.
  # These should be passed as a comma-separated list.
  _MODULES = {
    YahooFinanceQuoteSummaryModule.assetProfile: "assetProfile",  # Company info/background
    YahooFinanceQuoteSummaryModule.incomeStatementHistory: "incomeStatementHistory",
    YahooFinanceQuoteSummaryModule.incomeStatementHistoryQuarterly: "incomeStatementHistoryQuarterly",
    YahooFinanceQuoteSummaryModule.balanceSheetHistory: "balanceSheetHistory",  # Current cash/equivalents
    YahooFinanceQuoteSummaryModule.balanceSheetHistoryQuarterly: "balanceSheetHistoryQuarterly",
    YahooFinanceQuoteSummaryModule.cashFlowStatementHistory: "cashFlowStatementHistory",
    YahooFinanceQuoteSummaryModule.cashFlowStatementHistoryQuarterly: "cashFlowStatementHistoryQuarterly",
    YahooFinanceQuoteSummaryModule.defaultKeyStatistics: "defaultKeyStatistics",
    YahooFinanceQuoteSummaryModule.financialData: "financialData",
    YahooFinanceQuoteSummaryModule.calendarEvents: "calendarEvents",  # Contains ex-dividend date
    YahooFinanceQuoteSummaryModule.secFilings: "secFilings",  # SEC filing links
    YahooFinanceQuoteSummaryModule.recommendationTrend: "recommendationTrend",
    YahooFinanceQuoteSummaryModule.upgradeDowngradeHistory: "upgradeDowngradeHistory",
    YahooFinanceQuoteSummaryModule.institutionOwnership: "institutionOwnership",
    YahooFinanceQuoteSummaryModule.fundOwnership: "fundOwnership",
    YahooFinanceQuoteSummaryModule.majorDirectHolders: "majorDirectHolders",
    YahooFinanceQuoteSummaryModule.majorHoldersBreakdown: "majorHoldersBreakdown",
    YahooFinanceQuoteSummaryModule.insiderTransactions: "insiderTransactions",
    YahooFinanceQuoteSummaryModule.insiderHolders: "insiderHolders",
    YahooFinanceQuoteSummaryModule.netSharePurchaseActivity: "netSharePurchaseActivity",
    YahooFinanceQuoteSummaryModule.earnings: "earnings",
    YahooFinanceQuoteSummaryModule.earningsHistory: "earningsHistory",
    YahooFinanceQuoteSummaryModule.earningsTrend: "earningsTrend",
    YahooFinanceQuoteSummaryModule.industryTrend: "industryTrend",
    YahooFinanceQuoteSummaryModule.indexTrend: "indexTrend",
    YahooFinanceQuoteSummaryModule.sectorTrend: "sectorTrend"
  }

  @classmethod
  def _construct_url(cls, ticker_symbol, modules):
    modulesString = cls._construct_modules_string(modules)
    return cls._URL_TEMPLATE.format(ticker_symbol, modulesString)

  # A helper method to return a formatted modules string.
  @classmethod
  def _construct_modules_string(cls, modules):
    modulesString = modules[0]
    for module in modules[1:]:
      modulesString = modulesString + ',' + module
    return modulesString

  # Accepts the ticker symbol followed by a list of
  # `YahooFinanceQuoteSummaryModule` enum values.
  def __init__(self, ticker_symbol, modules):
    self.ticker_symbol = ticker_symbol
    self.modules = [self._MODULES[module] for module in modules]
    self.url = YahooFinanceQuoteSummary._construct_url(ticker_symbol, self.modules)
    self.module_data = {}
    self.crumb = None

  def parse_modules(self, content):
    """Parses all the of the module responses from the json into a top-level dictionary."""
    data = json.loads(content)
    results = data.get('quoteSummary', {}).get('result', None)
    if not results:
      logging.error('Could not parse response for url: ' + self.url)
      return False
    for module in self.modules:
      for result in results:
        if module in result:
          self.module_data[module] = result[module]
          break
    return True

  def get_balance_sheet_history(self, key):
    history = []
    for stmt in self.module_data.get('balanceSheetHistory', {}).get('balanceSheetStatements', []):
      history.append(stmt.get(key).get('raw'))
    return history

  def get_income_statement_history(self, key):
    history = []
    for stmt in self.module_data.get('incomeStatementHistory', {}).get('incomeStatementHistory', []):
      history.append(stmt.get(key).get('raw'))
    return history
