import requests
from web3 import Web3, HTTPProvider
from web3.types import Wei, HexBytes, ChecksumAddress, ENS, Address, \
    TxParams
import logging
from typing import Union, Optional
from django.db.models.query import QuerySet
from django.db.models import Q
from gql import Client, gql
from gql.transport.aiohttp import AIOHTTPTransport
from gql.transport.requests import RequestsHTTPTransport
from .models import OrderBookSwaps
from .working_with_uniswap import (
    approve,
    is_approved,
    eth_to_token_swap_output,
    get_eth_balance,
    get_eth_token_output_price,
    get_rbc_balance,
    get_token_eth_output_price,
    token_to_eth_swap_output,
    AddressLike,
    Wei
)


ETHERSCAN_API = "https://api.etherscan.io/api"
ETHERSCAN_API_KEY = "D8QKZPVM9BMRWS7BY41RU9EKU2VMWT8PM5"
UNISWAP_API = "https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v2"
UNISWAP_RBC_ETH_CONTRACT_ADDRESS = "0x10db37f4d9b3bc32AE8303B46E6166F7e9652d28"

INFURA_URL = 'https://mainnet.infura.io/v3/519bcee159504883ad8af59830dec2bb'
WALLET_ADDRESS = '0xfCf49f25a2D1E49631d05614E2eCB45296F26258'
OLD_MAINNET_CONTRACT_ADDRESS = '0xAAaCFf66942df4f1e1cB32C21Af875AC971A8117'
NEW_KOVAN_ADDRESS = "0xB09fe422dE371a86D7148d6ED9DBD499287cc95c"
RUBIC_ADDRESS = "0xA4EED63db85311E22dF4473f87CcfC3DaDCFA3E3"
ETH_ADDRESS = "0x0000000000000000000000000000000000000000"
BLOCKCHAIN_DECIMALS = 10 ** 18
MIN_BALANCE_PARAM = 1
MAX_SLIPPAGE = 0.1
PRIVATE_KEY = "0x00"
UNISWAP_ROUTER02_ADDRESS = "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D"

LIQUIDITY_PULL_ADDRESS = 'fill_me'
GAS_FEE = 'fill_me'
PROFIT_RATIO = 0.1
UNISWAP_API = 'https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v2'


# connect to infura
w3 = Web3(HTTPProvider(INFURA_URL))


# def get_rbc_eth_ratio_uniswap():
#     """
#         Parse exchange rate rbc to eth from uniswap.
#         Return exchange rate(float type).
#     """
#
#     # Select your transport with a defined url endpoint
#     transport = AIOHTTPTransport(url=UNISWAP_API)
#
#     # Create a GraphQL client using the defined transport
#     client = Client(transport=transport, fetch_schema_from_transport=True)
#
#     # Provide a GraphQL query
#     query = gql(
#         """
#         {
#             token(id: "0xa4eed63db85311e22df4473f87ccfc3dadcfa3e3"){
#                name
#                symbol
#                decimals
#                derivedETH
#                tradeVolumeUSD
#                totalLiquidity
#             }
#         }
#     """
#     )
#
#     # Execute the query on the transport
#     result = client.execute(query)
#     return float(result.get("token").get("derivedETH"))


def get_gas_price():
    """
    Get gas price from etherscan api.
    Return gas price for average speed(int type)
    """

    url = "{URL}?module=gastracker&action=gasoracle&apikey={apikey}".format(
        URL=ETHERSCAN_API, apikey=ETHERSCAN_API_KEY)
    response = requests.get(url)

    return int(response.json().get("result").get("ProposeGasPrice"))


def is_orderbook_profitable(exchange_rate, gas_fee, rbc_value, eth_value, is_rbc):
    # profit_coeff - value in ETH showing the minimum profit for which a transaction can be carried out
    profit_coeff = 0.1
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

    if is_rbc*(eth_value - rbc_value * exchange_rate) - gas_fee - profit_coeff > 0:
        return True
    else:
        return False


def _get_active_orders():
    """
        Returns active ETH <> RBC and RBC <> ETH orders.
    """
    return OrderBookSwaps.active_rbc_eth_orders.all()


def _get_matching_orders(queryset: QuerySet, matching_eth_value=5):
    """
        Returns ETH <> RBC and RBC <> ETH orders filtered by
        the amount of ETH.
    """
    return queryset.filter(
        Q(base_address=ETH_ADDRESS, base_limit__lte=matching_eth_value) | \
        Q(quote_address=ETH_ADDRESS, quote_limit__lte=matching_eth_value)
    )


def main():
    """
        Fill me.
    """
    active_eth_rbc_orders = _get_matching_orders(_get_active_orders())

    # eth_currency_quote = ''
    # rbc_currency_quote = ''

    # eth_current_balance = get_eth_balance(LIQUIDITY_PULL_ADDRESS)
    # rbc_current_balance = get_rbc_balance(LIQUIDITY_PULL_ADDRESS)


    if active_eth_rbc_orders.exists():
        print(
            'Matching orders have been found is: {}.'.format(
                active_eth_rbc_orders.count()
            )
        )
        logging.info(f'Matching orders have been found is: ')
        for counter, order in enumerate(active_eth_rbc_orders):
            rbc_eth_ratio = _get_rbc_eth_ratio()

            if order.base_address == RBC_ADDRESS and \
               order.quote_address == ETH_ADDRESS:
                if _check_profitability(
                    exchange_rate=rbc_eth_ratio,
                    gas_fee=0,
                    rbc_value=float(order.base_limit),
                    eth_value=float(order.quote_limit),
                    is_rbc=True):
                    print(f'{counter}. YEP!')
                    continue
                print(f'{counter}. NOUP...')
                ...
            else:
                if _check_profitability(
                    exchange_rate=rbc_eth_ratio,
                    gas_fee=0,
                    rbc_value=float(order.base_limit),
                    eth_value=float(order.quote_limit),
                    is_rbc=False):
                    print(f'{counter}. YEP!')
                    continue
                print(f'{counter}. NOUP...')
                ...
            # Проверка сделки на доходность.
            # - Получаем текущий курс RBC в ETH c UniSwap'а.
            # - Если сделка выгодна по текущему курсу обмениваемого токена, то
            # скрываем сделку и отправляем ее на исполнение.
            #   # - Проверяем доступный остаток средств для закрытия сделки.
            #   #   - Если доступного остатка на кошельке обмениваемого токена
            #   #     не достаточно для совершения сделки, то проверяем
            #   #     доступный остаток исходного токена, для обмена
            #   #   - Если средств RBC и ETH недоставточно, то записываем в
            #   #     logging.warning ссобщение о недостаточности средств (и для
            #   #     обмена между собой) и выходим из функции со статусом 0.
            # - Если сделка НЕ выгодна по текущему курсу обмениваемого токена,
            # то пропускаем (удаляем из плученного пула?).

    print('No active "ETH <> RBC" or "RBC <> ETH" orders yet.')
    logging.info('No active "ETH <> RBC" or "RBC <> ETH" orders yet.')

    return 0


def _hide_order(order: QuerySet):
    """
        Changes order visiblity to False.
    """
    order.is_displayed=False
    order.save()

    return 1


def _set_done_status_order(order: QuerySet):
    """
        Changes order visibility to True and state to 'done'.
    """
    # order.contract_state='done'
    order.state=OrderBookSwaps.STATE_DONE
    order.is_displayed=True
    order.save()

    return 1


def _get_rbc_eth_ratio():
    """
        Parse exchange rate rbc to eth from UniSwap.
        Return exchange rate: float.
    """

    # Select your transport with a defined url endpoint
    # transport = AIOHTTPTransport(url=UNISWAP_API)
    transport = RequestsHTTPTransport(url=UNISWAP_API)

    # Create a GraphQL client using the defined transport
    client = Client(transport=transport, fetch_schema_from_transport=True)

    # Provide a GraphQL query
    query = gql(
        """
        {
            token(id: "%s"){
               name
               symbol
               decimals
               derivedETH
               tradeVolumeUSD
               totalLiquidity
            }
        }
        """ % RBC_ADDRESS
    )

    # Execute the query on the transport
    result = client.execute(query)

    return float(result.get("token").get("derivedETH"))


def _check_profitability(
    exchange_rate:float,
    gas_fee:float,
    rbc_value:float,
    eth_value:float,
    is_rbc:bool=True
):
    # profit_coeff - value in ETH showing the minimum profit for which a transaction can be carried out
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
    if not is_rbc:
        is_rbc = -1
    else:
        is_rbc = int(is_rbc)

    profitability = is_rbc * (eth_value - rbc_value * exchange_rate) - \
                    gas_fee - PROFIT_RATIO

    if profitability > 0:
        return True
    else:
        return False


def confirm_orderbook(orderbook_id):
    """
    make transaction
    """
    # TODO add logic to make transaction with contract
    pass


def swap_token_on_uniswap(input_token: AddressLike,
                          output_token: AddressLike,
                          qty: Union[int, Wei],
                          recipient: AddressLike = None
                          ) -> HexBytes:
    """
        Make a trade by defining the qty of the output token.
        Input is address of swapped tokens and exact amount of output token.
    """
    # TODO: now it works only for ETH->TOKEN and TOKEN->ETH swaps
    #  needed to add TOKEN->TOKEN swap ability
    if not is_approved(RUBIC_ADDRESS):
        approve(RUBIC_ADDRESS)

    if input_token == Web3.toChecksumAddress(ETH_ADDRESS):
        balance = get_eth_balance(WALLET_ADDRESS)
        need = get_eth_token_output_price(token_address=output_token, quantity_in_wei=qty)
        print("balance: ", balance, " need: ", need)
        if balance < need:

            # TODO: add logging "not enough eth token"
            pass
        else:
            return eth_to_token_swap_output(output_token, qty, recipient)

    elif output_token == Web3.toChecksumAddress(ETH_ADDRESS):

        # balance = get_rbc_balance(WALLET_ADDRESS)
        # need = get_token_eth_output_price(output_token, qty)
        # if balance < need:
        #     # TODO: add logging "not enough eth token"
        #     pass
        # else:
        qty = Wei(qty)
        return token_to_eth_swap_output(input_token, qty)


# # TODO add celery to this func
# def orderbook_main():
#     """
#     main func to get profit from orderbooks
#     """
#     # get active orderbooks type=dict(queryset_eth_rbc,queryset_rbc_eth)
#     active_orderbooks = get_active_orderbook()
#
#     # get rbc/eth ratio
#     exchange_rate = get_rbc_eth_ratio_uniswap()
#
#     # get params for calculate gasFee = gasPrice*gasLimit
#     gas_price = get_gas_price()
#     gas_limit = get_gas_limit()
#     gas_fee = gas_price * gas_limit
#
#     # check active ETH->RBC orderbooks for profit
#     for orderbook in active_orderbooks.get("orderbooks_eth_rbc"):
#         is_rbc = 1
#         eth_value = orderbook.base_limit
#         rbc_value = orderbook.quote_limit
#         profit = is_orderbook_profitable(exchange_rate, gas_fee, rbc_value, eth_value, is_rbc)
#         if profit:
#             change_orderbook_status(orderbook.id)
#             if is_enough_token_on_wallet(rbc_value, eth_value, is_rbc, gas_fee):
#                 confirm_orderbook(orderbook.id)
#             else:
#                 if swap_token_on_uniswap(token_give_name="RBC", token_give_value=rbc_value, token_send_name="ETH"):
#                     # next need to check that orderbook profit for us yet
#                     if is_orderbook_profitable(exchange_rate, gas_fee, rbc_value, eth_value, is_rbc):
#                         confirm_orderbook(orderbook.id)
#
#     # check active RBC->ETH orderbooks for profit
#     for orderbook in active_orderbooks.get("orderbooks_rbc_eth"):
#         is_rbc = -1
#         eth_value = orderbook.quote_amount_contributed
#         rbc_value = orderbook.base_amount_contributed
#         profit = is_orderbook_profitable(exchange_rate, gas_price*gas_limit, rbc_value, eth_value, is_rbc)
#         if profit:
#             change_orderbook_status(orderbook.id)
#             if is_enough_token_on_wallet(rbc_value, eth_value, is_rbc, gas_fee):
#                 confirm_orderbook(orderbook.id)
#             else:
#                 # TODO add logic if it not enough ETH on wallet (not high priority task)
#                 pass


# run test
gg = int(320*BLOCKCHAIN_DECIMALS)
RBC = Web3.toChecksumAddress(RUBIC_ADDRESS)
print(RBC)
ETH = Web3.toChecksumAddress(ETH_ADDRESS)
print(ETH)
swap_token_on_uniswap(ETH, RBC, qty=gg)
