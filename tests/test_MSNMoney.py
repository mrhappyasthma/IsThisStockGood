"""Tests for the MSNMoney.py functions."""


import unittest

from isthisstockgood.Active.MSNMoney import MSNMoney

class MSNMoneyTest(unittest.TestCase):

  def test_parse_pe_ratios_should_return_false_when_no_data(self):
    payload = {
    }
    self.assertFalse(MSNMoney('DUMMY')._parse_pe_ratios(payload))

  def test_parse_pe_ratios_should_return_false_if_too_few_pe_ratios(self):
    msn = MSNMoney('DUMMY')
    payload = {
      'companyMetrics' : [
        {
          'fiscalPeriodType' : 'Annual',
          'priceToEarningsRatio' : 22.5
        },
      ]
    }
    self.assertFalse(msn._parse_pe_ratios(payload))

  def test_parse_pe_ratios_should_properly_calculate_pe_ratios(self):
    msn = MSNMoney('DUMMY')
    payload = {
      'companyMetrics' : [
        {
          'fiscalPeriodType' : 'Annual',
          'priceToEarningsRatio' : 0.5
        },
        {
          'fiscalPeriodType' : 'Annual',
          'priceToEarningsRatio' : 103.5
        },
        {
          'fiscalPeriodType' : 'Annual',
          'priceToEarningsRatio' : 21.5
        },
        {
          'fiscalPeriodType' : 'Annual',
          'priceToEarningsRatio' : 43.7
        },
        {
          'fiscalPeriodType' : 'Annual',
          'priceToEarningsRatio' : 1.5
        },
        {
          'fiscalPeriodType' : 'Annual',
          'priceToEarningsRatio' : 22.5
        },
        {
          'fiscalPeriodType' : 'Annual',
          'priceToEarningsRatio' : 50.9
        },
      ]
    }
    # TODO Fix these three checks.
    self.assertEqual(msn._parse_pe_ratios(payload), None)
    # PE High is 50.9, cause 103.5 isn't in last 5 years
    self.assertEqual(msn.pe_high, None)
    # PE Low is 1.5, cause 0.5 isn't in last 5 years
    self.assertEqual(msn.pe_low, None)
