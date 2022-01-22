from web3 import Web3
from pyuniswap.pyuniswap import Token
import time
import json
from datetime import datetime
import threading
from sys import exit
import logging.config
import os
NORMAL_ROTER = "0x10ed43c718714eb63d5aa57b78b54704e256024e".lower()
Trini_Limit_low = 600
logging.config.dictConfig({
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s %(message)s"
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "INFO",
            "formatter": "default",
            "stream": "ext://sys.stdout"
        },
        "file": {
            "class": "logging.FileHandler",
            "level": "INFO",
            "formatter": "default",
            "filename": "bot.log.log",
            "mode": "a",
            "encoding": "utf-8"
        }
    },
    "root": {
        "level": "INFO",
        "handlers": [
            "console",
            "file"
        ]
    }
})
LOGGER = logging.getLogger()


def show_log(msg):
    LOGGER.info(msg)


class MEMPOOL:
    def __init__(self):
        f = open('config.json')
        data = json.load(f)
        self.provider = data['provider']
        self.w3 = None
        self.provider_wss = data['provider_wss']
        self.wallet_address = data['address']
        self.private_key = data['private_key']
        self.trailing_stop = int(data["trailing_stop"])
        self.new_token = data["new_token_address"]
        self.new_token_presale = data["new_token_server"].lower()
        if(self.new_token_presale == NORMAL_ROTER.lower()):
            show_log("Please change presale address.")
            os._exit(1)
        self.slippage = int(data["slippage"]) / 100
        gas_price_count = int(data["gas_price"])
        self.gas_price = 1000000000 * gas_price_count
        self.gas_limit = int(data["gas_limit"])
        self.amount = data["amount"] * pow(10, 18)
        self.find_token_flag = False

    def connect_wallet(self):
        show_log('Connect wallet...')
        # trini_token = Token('0x3f7494957a403c4a484b66c1c6d0807de2660d2f', self.provider)
        # trini_token.connect_wallet(self.wallet_address, self.private_key)
        # if int(trini_token.balance()) < Trini_Limit_low:
        #     show_log("You need 600 TRINI Tokens to use bot.")
        #     os._exit(1)
        self.current_token = Token(self.new_token, self.provider)
        self.current_token.connect_wallet(self.wallet_address, self.private_key)  # craete token
        self.current_token.set_gaslimit(self.gas_limit)
        if self.current_token.is_connected():
            show_log('Wallet Connected')
            self.w3 = self.current_token.web3
            self.ws_web3 = Web3(Web3.WebsocketProvider(self.provider_wss))
            show_log("WSS is connected : {}".format(self.ws_web3.isConnected()))

    def handle_event(self, event):
        try:
            if not self.find_token_flag:
                tx = self.w3.toHex(event)
                transaction = self.w3.eth.getTransaction(tx)
                address = transaction.to
                if (address.lower() == self.new_token_presale):
                    transaction_gas_price = transaction.gasPrice
                    self.gas_price = transaction_gas_price
                    show_log('This is liquidity : {}'.format(tx))
                    self.find_token_flag = True
                    self.act()
        except:
            pass
        return

    def get_entries(self, event_filter):
        try:
            if not self.lock_filter:
                self.lock_filter = True
                new_entries = event_filter.get_new_entries()
                self.lock_filter = False
                for event in new_entries:
                    threading.Thread(target=self.handle_event, args=(event,)).start()
        except:
            pass

    def log_loop(self, event_filter):
        show_log('scanning transactions....')
        self.lock_filter = False
        while not self.find_token_flag:
            if event_filter:
                threading.Thread(target=self.get_entries, args=(event_filter,)).start()

    def buy(self,amount):  # address:token address.amount:amount for BNB with wei unit
        self.buy_price = 0
        buy_flag = False
        while not buy_flag:
            try:
                start_time = time.time()
                result = self.current_token.send_buy_transaction(self.signed_tx)
                show_log(time.time() - start_time)
                buy_flag = True
                show_log("Buy token: {}".format(result))
            except:
                pass

    def sell(self):
        balance = self.current_token.balance()
        sell_flag = False
        while not sell_flag:
            try:
                transaction_addreses = self.current_token.sell(balance, slippage=self.slippage, timeout=2100,
                                                          gas_price=self.gas_price)  # sell token as amount
                show_log("Sell transaction address {}".format(transaction_addreses))
                sell_flag = True
            except:
                pass

    def act(self):
        self.find_token_flag = True
        confirm_flag = False
        index = 0
        balance = self.current_token.balance()
        while not confirm_flag:
            if (index > 2):
                show_log("Please change parameters")
                os._exit(1)
            self.buy(self.amount)  # buy new token\
            buy_price = self.current_token.price()
            time.sleep(1)
            current_balance = self.current_token.balance()
            if (current_balance > balance):
                confirm_flag = True
            index += 1
        # wait sell moment trailing stop
        trailing_stop = buy_price * (100 - self.trailing_stop) / 100
        show_log("Trailing stop {}".format(trailing_stop))
        show_log("Buy price {}".format(buy_price))
        while True:
            current_price = self.current_token.price()
            current_trailing_stop = current_price * (100 - self.trailing_stop) / 100
            show_log("Trailing stop {}".format(current_trailing_stop))
            if current_trailing_stop > trailing_stop:
                trailing_stop = current_trailing_stop
                show_log("We are waiting sell moment")
            elif current_price > trailing_stop:
                pass
                show_log("We are waiting sell moment")
            else:
                self.sell()
                os._exit(1)
            time.sleep(1)

    def run(self):
        try:
            self.connect_wallet()
            block_filter = self.ws_web3.eth.filter("pending")
            self.signed_tx = self.current_token.buy(int(self.amount), slippage=self.slippage, timeout=2100,
                                                    gas_price= self.gas_price)  # buy token as amount
            self.log_loop(block_filter)
        except Exception as err:
            show_log('error; {}'.format(err))
if __name__ == '__main__':
    bot = MEMPOOL()
    bot.run()
