import os
import webapp2
from Morningstar import MorningstarRatios
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
    def post(self):
        if os.environ['HTTP_HOST'].endswith('.appspot.com'):  #Redirect the appspot url to the custom url
            self.response.out.write('<meta http-equiv="refresh" content="0; url=http://isthisstockgood.com" />')
        else:
            ticker_symbol = self.request.get('ticker')
            if not ticker_symbol:
              return

            m = MorningstarRatios.download_ratios(ticker_symbol)
            if not m:
              renderTemplate(self.response, 'json/error.json', { 'error': 'Invalid ticker symbol' })
              return
            template_values = {
                'roic': m.roic_averages,
                'eps': m.eps_averages,
                'sales': m.sales_averages,
                'equity': m.equity_averages,
                'cash': m.free_cash_flow_averages,
                'long_term_debt' : m.long_term_debt,
                'free_cash_flow' : m.recent_free_cash_flow,
                'debt_payoff_time' : m.debt_payoff_time
            }
            renderTemplate(self.response, 'json/big_five_numbers.json', template_values)


# list of URI/Handler routing tuples
# the URI is a regular expression beginning with root '/' char
routeHandlers = [
    (r'/', HomepageHandler),
    (r'/search', SearchHandler)
]

# application object
application = webapp2.WSGIApplication(routeHandlers, debug=True)