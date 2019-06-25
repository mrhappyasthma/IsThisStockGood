import functools
import logging
import os
import re
import webapp2
from Morningstar import MorningstarRatios
from Morningstar import MorningstarReport
from MSNMoney import MSNMoney
from google.appengine.api import urlfetch
from google.appengine.ext.webapp import template
from datetime import date

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
  return output[1:] if output[0] == ',' else output

def renderTemplate(response, templatename, templatevalues) :
    basepath = os.path.split(os.path.dirname(__file__)) #extract the base path, since we are in the "app" folder instead of the root folder
    path = os.path.join(basepath[0], 'templates/' + templatename)
    html = template.render(path, templatevalues)
    response.out.write(html)

# Handler classes
class HomepageHandler(webapp2.RequestHandler) :
    def get(self):
        if os.environ['HTTP_HOST'].endswith('.appspot.com'):  #Redirect the appspot url to the custom url
            self.response.out.write('<meta http-equiv="refresh" content="0; url=http://isthisstockgood.com" />')
        else:
            template_values = {
                'page_title' : "Is This Stock Good?",
                'current_year' : date.today().year,
            }

            renderTemplate(self.response, 'home.html', template_values)

class SearchHandler(webapp2.RequestHandler) :
    def __init__(self, request, response):
      self.initialize(request, response)
      self.rpcs = []
      self.ticker_symbol = ''
      self.ratios = None
      self.pe_ratios = None
      self.income_statement = None
      self.error = False

    def post(self):
        if os.environ['HTTP_HOST'].endswith('.appspot.com'):  #Redirect the appspot url to the custom url
            self.response.out.write('<meta http-equiv="refresh" content="0; url=http://isthisstockgood.com" />')
        else:
            self.ticker_symbol = self.request.get('ticker')
            if not self.ticker_symbol:
              return

            # Make all network request asynchronously to build their portion of
            # the json results.

            self.fetch_morningstar_ratios()
            self.fetch_income_statement()
            self.fetch_pe_ratios()
            for rpc in self.rpcs:
              rpc.wait()
            ratios = self.ratios
            if ratios:
              ratios.calculate_long_term_debt()
            income = self.income_statement
            pe_ratios = self.pe_ratios
            if not ratios or not income:
              renderTemplate(self.response, 'json/error.json', { 'error': 'Invalid ticker symbol' })
              return
            template_values = {
                'roic': ratios.roic_averages if ratios.roic_averages else [],
                'eps': ratios.eps_averages if ratios.eps_averages else [],
                'sales': ratios.sales_averages if ratios.sales_averages else [],
                'equity': ratios.equity_averages if ratios.equity_averages else [],
                'cash': ratios.free_cash_flow_averages if ratios.free_cash_flow_averages else [],
                'long_term_debt' : ratios.long_term_debt,
                'free_cash_flow' : ratios.recent_free_cash_flow,
                'debt_payoff_time' : ratios.debt_payoff_time,
                'pe_high' : pe_ratios.pe_high if pe_ratios else 'null',
                'pe_low' : pe_ratios.pe_low if pe_ratios else 'null'
            }
            renderTemplate(self.response, 'json/big_five_numbers.json', template_values)

    def fetch_income_statement(self):
      self.income_statement = \
          MorningstarReport(self.ticker_symbol, \
                            MorningstarReport.TYPE_INCOME_STATEMENT, \
                            MorningstarReport.PERIOD_QUARTERLY)
      logging.info(self.income_statement.url)
      rpc = urlfetch.create_rpc()
      self.rpcs.append(rpc)
      rpc.callback = functools.partial(self.parse_income_statement, rpc)
      urlfetch.make_fetch_call(rpc, self.income_statement.url)

    def parse_income_statement(self, rpc):
      result = rpc.get_result()
      success = self.income_statement.parse_report(result.content.split('\n'))
      if not success:
        self.income_statement = None

    def fetch_morningstar_ratios(self):
      self.ratios = MorningstarRatios(self.ticker_symbol)
      logging.info(self.ratios.key_stat_url)
      key_stat_rpc = urlfetch.create_rpc()
      self.rpcs.append(key_stat_rpc)
      key_stat_rpc.callback = functools.partial(self.parse_morningstar_ratios, key_stat_rpc)
      urlfetch.make_fetch_call(key_stat_rpc, self.ratios.key_stat_url)

      finance_rpc = urlfetch.create_rpc()
      self.rpcs.append(finance_rpc)
      finance_rpc.callback = functools.partial(self.parse_morningstar_finances, finance_rpc)
      logging.info(self.ratios.finance_url)
      urlfetch.make_fetch_call(finance_rpc, self.ratios.finance_url)

    def parse_morningstar_finances(self, rpc):
      if not self.ratios:
        return
      result = rpc.get_result()
      parsed_content = jsonpToCSV(result.content)
      success = self.ratios.parse_finances(parsed_content.split('\n'))
      if not success:
        self.ratios = None

    def parse_morningstar_ratios(self, rpc):
      if not self.ratios:
        return
      result = rpc.get_result()
      parsed_content = jsonpToCSV(result.content)
      success = self.ratios.parse_ratios(parsed_content.split('\n'))
      if not success:
        self.ratios = None

    def fetch_pe_ratios(self):
      self.pe_ratios = MSNMoney(self.ticker_symbol)
      pe_ratios_rpc = urlfetch.create_rpc()
      self.rpcs.append(pe_ratios_rpc)
      pe_ratios_rpc.callback = functools.partial(self.parse_pe_ratios, pe_ratios_rpc)
      logging.info(self.pe_ratios.url)
      urlfetch.make_fetch_call(pe_ratios_rpc, self.pe_ratios.url)

    def parse_pe_ratios(self, rpc):
      if not self.pe_ratios:
        return
      result = rpc.get_result()
      success = self.pe_ratios.parse(result.content)
      if not success:
        self.pe_ratios = None



# list of URI/Handler routing tuples
# the URI is a regular expression beginning with root '/' char
routeHandlers = [
    (r'/', HomepageHandler),
    (r'/search', SearchHandler)
]

# application object
application = webapp2.WSGIApplication(routeHandlers, debug=True)