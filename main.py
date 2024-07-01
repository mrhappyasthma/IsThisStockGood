from src.DataFetcher import fetchDataForTickerSymbol
from src.server import create_app


if __name__ == '__main__':
  app = create_app(fetchDataForTickerSymbol)
  app.run(host='127.0.0.1', port=8080, debug=True)
