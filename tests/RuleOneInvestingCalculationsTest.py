"""Tests for the app/RuleOneInvestingCalculations.py functions."""


import os
import sys
import unittest

app_path = os.path.join(os.path.dirname(__file__), "..", 'app')
sys.path.append(app_path)

import RuleOneInvestingCalculations as RuleOne

class RuleOneInvestingCalculationsTest(unittest.TestCase):

  def test_rule_one_margin_of_safety_price(self):
    pass

  def test_calculate_future_eps(self):
    pass

  def test_calculate_future_pe(self):
    pass

  def test_calculate_estimated_future_price(self):
    future_price = RuleOne.calculate_estimated_future_price(1.25, 3)
    self.assertEqual(future_price, 3.75)

  def test_calculate_sticker_price(self):
    pass

  def test_calculate_margin_of_safety(self):
    default_margin_of_safety = RuleOne.calculate_margin_of_safety(100)
    self.assertEqual(default_margin_of_safety, 50)

    smaller_margin_of_safety = \
        RuleOne.calculate_margin_of_safety(100, margin_of_safety=0.25)
    self.assertEqual(smaller_margin_of_safety, 75)