import json
import requests
import time
from merkato.exchanges.exchange_base import ExchangeBase
from merkato.constants import MARKET
import krakenex
from math import floor
import logging
from decimal import *

log = logging.getLogger(__name__)
getcontext().prec = 8

XMR_AMOUNT_PRECISION = 3
XMR_PRICE_PRECISION = 6


class KrakenExchange(ExchangeBase):
    def __init__(self, config, coin, base, password='password'):
        self.client = krakenex.API(config['public_api_key'], config['private_api_key'])
        self.limit_only = config['limit_only']
        self.retries = 5
        self.coin = coin
        self.base = base
        self.ticker = coin + 'XBT'
        self.name = 'Kraken'

    def get_all_orders(self):
        ''' Returns all open orders for the ticker XYZ (not BTC_XYZ)
            :param coin: string
        '''
        # TODO: Accept BTC_XYZ by stripping BTC_ if it exists

        orders = self.client.get_order_book(symbol=self.ticker)

        log.info("get_all_orders", orders)
        return orders


    def get_my_open_orders(self, context_formatted=False):
        ''' Returns all open orders for the authenticated user '''
                
        orders = self.client.get_open_orders(symbol=self.ticker, recvWindow=10000000)
        # orders is an array of dicts we need to transform it to an dict of dicts to conform to binance
        new_dict = {}
        for order in orders:
            id = order['orderId']
            new_dict[id] = order
            new_dict[id]['id'] = id
            if order['side'] == 'BUY':
                new_dict[id]['type'] = 'buy'
            else:
                new_dict[id]['type'] = 'sell'
            
            origQty = Decimal(float(order['origQty']))
            executedQty = Decimal(float(order['executedQty']))
            new_dict[id]['amount'] = origQty - executedQty
        return new_dict


    def get_ticker(self, coin=None):
        ''' Returns the current ticker data for the given coin. If no coin is given,
            it will return the ticker data for all coins.
            :param coin: string (of the format BTC_XYZ)
        '''
        attempts = 0
        while attempts < 4:
            try:
                result = self.client.query_public('Ticker', {'pair': self.ticker})['result']
                log.info(result)
                for ticker_data in result.values():
                    return ticker_data
            except Exception as e:
                print('Error getting trade price {}'.format(e))
                print('Trying again attempt {}'.format(attempts + 2))
                attempts += 1
        return None


    def get_24h_volume(self, coin=None):
        ''' Returns the 24 hour volume for the given coin.
            If no coin is given, returns for all coins.
            :param coin string (of the form BTC_XYZ where XYZ is the alt ticker)
        '''

        params = { "method": "get24hvolume" }
        response = requests.get(self.url, params=params)

        if not coin:
            return json.loads(response.text)

        response_json = json.loads(response.text)
        log.info(response_json[coin])

        return response_json[coin]


    def get_balances(self):
        ''' TODO Function Definition
        '''

        # also keys go unused, also coin...
        base_balance = self.client.get_asset_balance(asset=self.base, recvWindow=10000000)
        coin_balance = self.client.get_asset_balance(asset=self.coin, recvWindow=10000000)
        base = Decimal(base_balance['free']) + Decimal(base_balance['locked'])
        coin = Decimal(coin_balance['free']) + Decimal(coin_balance['locked'])

        log.info("Base balance: {}".format(base_balance))
        log.info("Coin balance: {}".format(coin_balance))

        pair_balances = {"base" : {"amount": {'balance': base},
                                   "name" : self.base},
                         "coin": {"amount": {'balance': coin},
                                  "name": self.coin},
                        }

        return pair_balances


    def get_my_trade_history(self, start=0, end=0):
        ''' TODO Function Definition
        '''
        log.info("Getting trade history...")
        # start_is_provided = start != 0 and start != ''
        # print('start', start)
        # if start_is_provided:
        #     trades = self.client.get_my_trades(symbol=self.ticker, fromId=int(start), recvWindow=10000000)
        # else:
        trades = self.client.get_my_trades(symbol=self.ticker, recvWindow=10000000)
        trades.reverse()
        return trades


    def get_last_trade_price(self):
        ''' TODO Function Definition
        '''
        ticker = self.get_ticker()
        if ticker != None:
            return ticker["c"][0]
        return 'Error'


    def get_lowest_ask(self):
        ''' TODO Function Definition
        '''
        ticker = self.get_ticker()
        if ticker != None:
            return ticker["a"][0]
        return None

    def get_highest_bid(self):
        ''' TODO Function Definition
        '''
        ticker = self.get_ticker()
        if ticker != None:
            return ticker["b"][0]
        return None

    def get_total_amount(self, order_id):
        order_info = self.client.get_order(symbol=self.ticker, orderId=order_id, recvWindow=10000000)
        return Decimal(order_info['origQty'])
