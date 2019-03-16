import functools
import logging
import os
import re
import webapp2
from Morningstar import MorningstarRatios
from Morningstar import MorningstarReport
from google.appengine.api import urlfetch
from google.appengine.ext.webapp import template
from datetime import date

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
            for rpc in self.rpcs:
              rpc.wait()
            ratios = self.ratios
            income = self.income_statement
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
      logging.info(self.ratios.url)
      rpc = urlfetch.create_rpc()
      self.rpcs.append(rpc)
      rpc.callback = functools.partial(self.parse_morningstar_ratios, rpc)
      urlfetch.make_fetch_call(rpc, self.ratios.url)

    def parse_morningstar_ratios(self, rpc):
      result = rpc.get_result()
      success = self.ratios.parse_ratios(result.content.split('\n'))
      if not success:
        self.ratios = None





# list of URI/Handler routing tuples
# the URI is a regular expression beginning with root '/' char
routeHandlers = [
    (r'/', HomepageHandler),
    (r'/search', SearchHandler)
]

# application object
application = webapp2.WSGIApplication(routeHandlers, debug=True)