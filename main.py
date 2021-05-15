import functools
import logging
import os
import re
import src.RuleOneInvestingCalculations as RuleOne
from datetime import date
from flask import Flask, request, render_template
from requests_futures.sessions import FuturesSession
from src.Morningstar import MorningstarRatios
from src.MSNMoney import MSNMoney
from src.YahooFinance import YahooFinanceAnalysis
from src.YahooFinance import YahooFinanceQuote


app = Flask(__name__)

def jsonpToCSV(s):
  arr = []
  ignore = False
  printing = False
  s = s.replace(',', '')
  s = s.replace('\/', '/')
  s = s.replace('&amp', '&')
  s = s.replace('&nbsp;', ' ')
  s = s.replace('</tr>', '\n')
  for c in s:
    if c == '<':
      ignore = True
      printing = False
      continue
    elif c == '>':
      ignore = False
      printing = False
      continue
    elif not ignore:
      if not printing:
        printing = True
        arr.append(',')
      arr.append(c)
  output = ''.join(arr)
  output = output.replace('\n,', '\n')
  output = output.replace(',\n', '\n')
  output = output.replace(' ,', ' ')
  output = output.replace('&mdash;', '')
  if len(output) == 0:
    return ''
  return output[1:] if output[0] == ',' else output


def calculateMarginOfSafetyPrice(ratios, pe_ratios, yahoo_finance_analysis):
  if not ratios or not pe_ratios or not yahoo_finance_analysis:
    return None

  if not yahoo_finance_analysis.five_year_growth_rate or not ratios.equity_averages:
    return None
  growth_rate = min(float(yahoo_finance_analysis.five_year_growth_rate),
                    float(ratios.equity_averages[-1]))
  # Divide the growth rate by 100 to convert from percent to decimal.
  growth_rate = growth_rate / 100.0

  if not ratios.ttm_eps or not pe_ratios.pe_low or not pe_ratios.pe_high:
    return None
  margin_of_safety_price = RuleOne.margin_of_safety_price(float(ratios.ttm_eps), growth_rate,
                                                          float(pe_ratios.pe_low), float(pe_ratios.pe_high))
  return margin_of_safety_price


@app.route('/')
def homepage():
  if request.environ['HTTP_HOST'].endswith('.appspot.com'):  #Redirect the appspot url to the custom url
    return '<meta http-equiv="refresh" content="0; url=https://isthisstockgood.com" />'

  template_values = {
    'page_title' : "Is This Stock Good?",
    'current_year' : date.today().year,
  }
  return render_template('home.html', **template_values)

@app.route('/search', methods=['POST'])
def search():
  if request.environ['HTTP_HOST'].endswith('.appspot.com'):  #Redirect the appspot url to the custom url
    return '<meta http-equiv="refresh" content="0; url=http://isthisstockgood.com" />'

  search_handler = SearchHandler()
  search_handler.ticker_symbol = request.values.get('ticker')
  if not search_handler.ticker_symbol:
    return render_template('json/error.json', **{'error' : 'Invalid ticker symbol'})

  # Make all network request asynchronously to build their portion of
  # the json results.

  search_handler.fetch_morningstar_ratios()
  search_handler.fetch_pe_ratios()
  search_handler.fetch_yahoo_finance_analysis()
  search_handler.fetch_yahoo_finance_quote()
  for rpc in search_handler.rpcs:
    # Wait for each RPC result before proceeding.
    rpc.result()
  ratios = search_handler.ratios
  if ratios:
    ratios.calculate_long_term_debt()
  pe_ratios = search_handler.pe_ratios
  yahoo_finance_analysis = search_handler.yahoo_finance_analysis
  yahoo_finance_quote = search_handler.yahoo_finance_quote
  if not ratios:
    return render_template('json/error.json', **{'error' : 'Invalid ticker symbol'})
  margin_of_safety_price = calculateMarginOfSafetyPrice(ratios, pe_ratios, yahoo_finance_analysis)
  template_values = {
    'roic': ratios.roic_averages if ratios.roic_averages else [],
    'eps': ratios.eps_averages if ratios.eps_averages else [],
    'sales': ratios.sales_averages if ratios.sales_averages else [],
    'equity': ratios.equity_averages if ratios.equity_averages else [],
    'cash': ratios.free_cash_flow_averages if ratios.free_cash_flow_averages else [],
    'long_term_debt' : ratios.long_term_debt,
    'free_cash_flow' : ratios.recent_free_cash_flow,
    'debt_payoff_time' : ratios.debt_payoff_time,
    'debt_equity_ratio' : ratios.debt_equity_ratio if ratios.debt_equity_ratio >= 0 else -1,
    'ttm_net_income' : ratios.ttm_net_income if ratios.ttm_net_income else 'null',
    'margin_of_safety_price' : margin_of_safety_price if margin_of_safety_price else 'null',
    'current_price' : yahoo_finance_quote.current_price if yahoo_finance_quote.current_price else 'null'
  }
  return render_template('json/big_five_numbers.json', **template_values)


class SearchHandler():
  def __init__(self,):
    self.rpcs = []
    self.ticker_symbol = ''
    self.ratios = None
    self.pe_ratios = None
    self.yahoo_finance_analysis = None
    self.yahoo_finance_quote = None
    self.error = False

  def fetch_morningstar_ratios(self):
    self.ratios = MorningstarRatios(self.ticker_symbol)
    logging.info(self.ratios.key_stat_url)
    session = FuturesSession()
    key_stat_rpc = session.get(self.ratios.key_stat_url, hooks={
       'response': self.parse_morningstar_ratios,
    })
    self.rpcs.append(key_stat_rpc)

    logging.info(self.ratios.finance_url)
    finance_rpc = session.get(self.ratios.finance_url, hooks={
       'response': self.parse_morningstar_finances,
    })
    self.rpcs.append(finance_rpc)

  # Called asynchronously upon completion of the URL fetch from
  # `fetch_morningstar_ratios`.
  def parse_morningstar_finances(self, response, *args, **kwargs):
    if not self.ratios:
      return
    parsed_content = jsonpToCSV(response.text)
    success = self.ratios.parse_finances(parsed_content.split('\n'))
    if not success:
      self.ratios = None

  # Called asynchronously upon completion of the URL fetch from
  # `fetch_morningstar_ratios`.
  def parse_morningstar_ratios(self, response, *args, **kwargs):
    if not self.ratios:
      return
    parsed_content = jsonpToCSV(response.text)
    success = self.ratios.parse_ratios(parsed_content.split('\n'))
    if not success:
      self.ratios = None

  def fetch_pe_ratios(self):
    self.pe_ratios = MSNMoney(self.ticker_symbol)
    session = FuturesSession()
    rpc = session.get(self.pe_ratios.url, allow_redirects=True, hooks={
       'response': self.parse_pe_ratios,
    })
    self.rpcs.append(rpc)

  # Called asynchronously upon completion of the URL fetch from
  # `fetch_pe_ratios`.
  def parse_pe_ratios(self, response, *args, **kwargs):
    if response.status_code != 200:
      return
    if not self.pe_ratios:
      return
    result = response.text
    success = self.pe_ratios.parse(result)
    if not success:
      self.pe_ratios = None

  def fetch_yahoo_finance_analysis(self):
    self.yahoo_finance_analysis = YahooFinanceAnalysis(self.ticker_symbol)
    session = FuturesSession()
    rpc = session.get(self.yahoo_finance_analysis.url, allow_redirects=True, hooks={
       'response': self.parse_yahoo_finance_analysis,
    })
    self.rpcs.append(rpc)

  # Called asynchronously upon completion of the URL fetch from
  # `fetch_yahoo_finance_analysis`.
  def parse_yahoo_finance_analysis(self, response, *args, **kwargs):
    if response.status_code != 200:
      return
    if not self.yahoo_finance_analysis:
      return
    result = response.text
    success = self.yahoo_finance_analysis.parse_analyst_five_year_growth_rate(result)
    if not success:
      self.yahoo_finance_analysis = None

  def fetch_yahoo_finance_quote(self):
    self.yahoo_finance_quote = YahooFinanceQuote(self.ticker_symbol)
    session = FuturesSession()
    rpc = session.get(self.yahoo_finance_quote.url, allow_redirects=True, hooks={
       'response': self.parse_yahoo_finance_quote,
    })
    self.rpcs.append(rpc)

  # Called asynchronously upon completion of the URL fetch from
  # `fetch_yahoo_finance_quote`.
  def parse_yahoo_finance_quote(self, response, *args, **kwargs):
    if response.status_code != 200:
      return
    if not self.yahoo_finance_quote:
      return
    result = response.text
    success = self.yahoo_finance_quote.parse_current_price(result)
    if not success:
      self.yahoo_finance_quote = None


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)