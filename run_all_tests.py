#!/usr/bin/env python

"""Gathers all tests in the /tests/ subdirectory and runs them."""
import os
import unittest


def main():
  # Execute all tests.
  test_loader = unittest.TestLoader()
  tests_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'tests')
  test_suite = test_loader.discover(tests_dir, '*.py')
  test_runner = unittest.TextTestRunner()
  test_runner.run(test_suite)


if __name__ == '__main__':
  main()
