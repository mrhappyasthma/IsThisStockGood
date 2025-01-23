# IsThisStockGood

[![IsThisStockGood](https://github.com/mrhappyasthma/IsThisStockGood/actions/workflows/python-app.yml/badge.svg)](https://github.com/mrhappyasthma/IsThisStockGood/actions)

[IsThisStockGood.com](http://www.isthisstockgood.com)

This website attempts to automate much of the calculations described in Phil Town's
[Rule #1](https://www.amazon.com/gp/product/0307336840?pf_rd_p=c2945051-950f-485c-b4df-15aac5223b10&pf_rd_r=WVNPVWRWTJ9E0QSDGWTH) investing book.
(As well as his second book, [Payback Time](https://www.amazon.com/Payback-Time-Outsmarting-Getting-Investments/dp/1847940641/).)

To use the website, simply enter in a stock ticker symbol and let this site do its magic.

The data for this website is pulled from various sources such as Morningstar, Yahoo
Finance, MSN Money, etc.

If you wanted to mirror many of these calculations in a spreadsheet, you can
check out Phil Town's [PDF](https://www.ruleoneinvesting.com/ExcelFormulas.pdf)
explaining this step-by-step.

NOTE: This site is for personal investing purposes only. Any analysis on this site
should be used at your own discretion. Obviously investing always carries some risk,
but if you follow the principles in Rule #1 investing, then this site should be a
"one stop shop" for all the calculations/resources you may need.

## Stock Screening

If you want to run bulk queries for stock analysis, check out the [Rule 1 Stock Screener](https://github.com/mrhappyasthma/Rule1-StockScreener) repository.

This repository contains a script to iteratively issue a bulk fetch and populate a MySQL database with the results. It also includes some predefined SQL queries for convenience.

## Install dependencies

### Poetry

On windows:

1. Install `pipx` with `py -m pip install --user pipx`.
2. Go to the path in "WARNING: The script pipx.exe is installed in `<USER folder>\AppData\Roaming\Python\Python3x\Scripts` which is not on "PATH". Once in this path execute: `.\pipx.exe ensurepath`
3. Install poetry with: `pipx install poetry`
4. In the repo path for IsThisStockGood, run `poetry install`
5. Install the `export` command addon: `poetry self add poetry-plugin-export`

## Running the site locally.

1. Clone the repo.
2. Install python3, if you haven't already.
3. Run the following command to install the dependencies:
```
python3 -m pip install .
```
4. Run the `main.py` with:
```
python3 main.py
```

## Deploying the site

If you haven't already, install the [Google Cloud SDK](https://cloud.google.com/sdk/docs/install)

If it's your first time deploying, run:

```
gcloud init
```

If you already have an initialized repository, then simply run

```
gcloud app deploy app.yaml
```
