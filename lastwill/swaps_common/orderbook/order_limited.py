import requests

COINGECKO_API = "https://api.coingecko.com"
ETHERSCAN_API = "https://api.etherscan.io/api"
ETHERSCAN_API_KEY = "D8QKZPVM9BMRWS7BY41RU9EKU2VMWT8PM5"


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



# test calling
print(get_rbc_eth_price())
print(get_gas_price())