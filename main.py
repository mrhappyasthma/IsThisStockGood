from isthisstockgood.DataFetcher import fetchDataForTickerSymbol
from isthisstockgood.server import create_app

# Expose `app` object at the module level, as expected by App Engine
app = create_app(fetchDataForTickerSymbol)

if __name__ == '__main__':
  app.run(host='127.0.0.1', port=8080, debug=True)
