import requests
import json
import os
from web3 import Web3, HTTPProvider

COINGECKO_API = "https://api.coingecko.com"
ETHERSCAN_API = "https://api.etherscan.io/api"
ETHERSCAN_API_KEY = "D8QKZPVM9BMRWS7BY41RU9EKU2VMWT8PM5"

INFURA_URL = 'https://mainnet.infura.io/v3/519bcee159504883ad8af59830dec2bb'
WALLET_ADDRESS = '0xfCf49f25a2D1E49631d05614E2eCB45296F26258'
CONTRACT_ADDRESS = '0xAAaCFf66942df4f1e1cB32C21Af875AC971A8117'
BLOCKCHAIN_DECIMALS = 10 ** 18


def get_rbc_eth_price():
    """
    Parse exchange rate rbc to eth from coingecko.
    Return exchange rate(float type).
    """

    url = "{URL}/api/v3/simple/price?ids={id}&vs_currencies={currency}".format(
        URL=COINGECKO_API, id="rubic", currency="eth")
    response = requests.get(url)

    return response.json().get("rubic").get("eth")


def get_gas_price():
    """
    Get gas price from etherscan api.
    Return gas price for average speed(int type)
    """

    url = "{URL}?module=gastracker&action=gasoracle&apikey={apikey}".format(
        URL=ETHERSCAN_API, apikey=ETHERSCAN_API_KEY)
    response = requests.get(url)

    return int(response.json().get("result").get("ProposeGasPrice"))


def is_orderbook_profitable(exchangeRate, gasPrice, rbcValue, ethValue, isRBC):
    # profit_coeff - value in ETH showing the minimum profit for which a transaction can be carried out
    profit_coeff = 0.01
    """
    Calculate profit for active orderbook
    
    RinE = RBC*exch_rate = value RBC in ETH
    RinE - ETH = free profit
    RinE - ETH - gas = total profit
    Total: rbcValue*exchangeRate - ethValue - gasPrice
    
    Logic:
    If we have RBC we want that: user's ETH > our RBC*ExchRate
        (ETH - RBC*ER) - GP - PC > 0 
    If we have ETH we want that: user's RBC*ExchRate > our ETH
        (RBC*ER - ETH) - GP - PC > 0
    value isRBC: int =1 if we have RBC, int = -1 if we have ETH
    Finally we get: isRBC*(ethValue - rbcValue*exchangeRate) - gasPrice - profit_coeff > 0 - it's profit
    Input data: rbc/eth exchange rate, gasPrice,
        orderbook's value of eth and rbc, isRBC
    Output data: True if profit, False if not.
    """

    if isRBC*(ethValue - rbcValue*exchangeRate) - gasPrice - profit_coeff > 0:
        return True
    else:
        return False


def test_calling():
    print(get_rbc_eth_price())
    print(get_gas_price())


def get_abi_by_filename(filename):
    build_dir = os.path.join(os.getcwd(), 'lastwill/swaps_common/orderbook/')

    with open(os.path.join(build_dir, filename), 'r') as contract:
        return json.load(contract)


w3 = Web3(HTTPProvider(INFURA_URL))



print(w3.isConnected())
print(w3.eth.getBalance(WALLET_ADDRESS)/BLOCKCHAIN_DECIMALS)

abi = get_abi_by_filename("contract_abi.json")
contract = w3.eth.contract(address=CONTRACT_ADDRESS, abi=abi)

function = contract.functions.myWishBasePercent()
gas_limit = function.estimateGas({'from': CONTRACT_ADDRESS})

print(gas_limit)

#     tx_crypto_price = gas_limit * w3.eth.gasPrice / BLOCKCHAIN_DECIMALS

