"""Tests for the DataFetcher.py functions."""


import os
import sys
import unittest

app_path = os.path.join(os.path.dirname(__file__), "..", 'src')
sys.path.append(app_path)

from src.YahooFinance import YahooFinanceQuoteSummary, YahooFinanceQuoteSummaryModule
from src.DataFetcher import DataFetcher
from src.StockRow import StockRowKeyStats

class DataFetcherTest(unittest.TestCase):

  def test_roic_should_return_1_3_from_yahoo_and_the_rest_from_stockrow(self):
    df = DataFetcher()
    df.stockrow_key_stats = StockRowKeyStats('DUMMY')
    df.stockrow_key_stats.roic_averages = [11, 22, 33, 44, 55, 66, 77]
    modules = [
        YahooFinanceQuoteSummaryModule.incomeStatementHistory,
        YahooFinanceQuoteSummaryModule.balanceSheetHistory
    ]
    df.yahoo_finance_quote_summary = YahooFinanceQuoteSummary('DUMMY', modules)
    df.yahoo_finance_quote_summary.module_data = {
      'incomeStatementHistory' : {
        'incomeStatementHistory' : [
          {
              'netIncome' : { 'raw' : 1 },
          },
          {
              'netIncome' : { 'raw' : 2 },
          },
          {
              'netIncome' : { 'raw' : 3 },
          }
        ]
      },
      'balanceSheetHistory' : {
          'balanceSheetStatements' : [
              {
                  'cash' : { 'raw' : 2},
                  'longTermDebt' : { 'raw' : 2},
                  'totalStockholderEquity' : { 'raw' : 10 }
              },
              {
                  'cash' : { 'raw' : 2},
                  'longTermDebt' : { 'raw' : 2},
                  'totalStockholderEquity' : { 'raw' : 10 }
              },
              {
                  'cash' : { 'raw' : 2},
                  'longTermDebt' : { 'raw' : 2},
                  'totalStockholderEquity' : { 'raw' : 10 }
              }
          ]
      }
    }
    roic_avgs = df.get_roic_averages()
    self.assertEqual(roic_avgs[0], 10.0)
    self.assertEqual(roic_avgs[1], 20.0)
    self.assertEqual(roic_avgs[2], 33)
    self.assertEqual(roic_avgs[3], 77)

  def test_roic_should_return_1_from_yahoo_and_the_rest_from_stockrow(self):
    df = DataFetcher()
    df.stockrow_key_stats = StockRowKeyStats('DUMMY')
    df.stockrow_key_stats.roic_averages = [11, 22, 33, 44, 55, 66, 77]
    modules = [
        YahooFinanceQuoteSummaryModule.incomeStatementHistory,
        YahooFinanceQuoteSummaryModule.balanceSheetHistory
    ]
    df.yahoo_finance_quote_summary = YahooFinanceQuoteSummary('DUMMY', modules)
    df.yahoo_finance_quote_summary.module_data = {
      'incomeStatementHistory' : {
        'incomeStatementHistory' : [
          {
              'netIncome' : { 'raw' : 1 },
          },
        ]
      },
      'balanceSheetHistory' : {
          'balanceSheetStatements' : [
              {
                  'cash' : { 'raw' : 2},
                  'longTermDebt' : { 'raw' : 2},
                  'totalStockholderEquity' : { 'raw' : 10 }
              },
          ]
      }
    }
    roic_avgs = df.get_roic_averages()
    self.assertEqual(roic_avgs[0], 10.0)
    self.assertEqual(roic_avgs[1], 22)
    self.assertEqual(roic_avgs[2], 33)
    self.assertEqual(roic_avgs[3], 77)

  def test_roic_should_return_all_from_stockrow_if_nothing_in_yahoo(self):
    df = DataFetcher()
    df.stockrow_key_stats = StockRowKeyStats('DUMMY')
    df.stockrow_key_stats.roic_averages = [11, 22, 33, 44, 55, 66, 77]
    roic_avgs = df.get_roic_averages()
    self.assertEqual(roic_avgs[0], 11)
    self.assertEqual(roic_avgs[1], 22)
    self.assertEqual(roic_avgs[2], 33)
    self.assertEqual(roic_avgs[3], 77)

  def test_roic_should_return_all_it_has_from_stockrow_if_nothing_in_yahoo(self):
    df = DataFetcher()
    df.stockrow_key_stats = StockRowKeyStats('DUMMY')
    df.stockrow_key_stats.roic_averages = [11, 22]
    roic_avgs = df.get_roic_averages()
    self.assertEqual(len(roic_avgs), 2)
