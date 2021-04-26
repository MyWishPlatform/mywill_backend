import logging
import requests
from hexbytes import HexBytes
from web3 import Web3, HTTPProvider

from .models import PanamaTransaction
# from networks.models import Network
# from contracts.services import (
# get_infura_provider,
# get_abi_by_filename,
# )
from lastwill.swaps_common.orderbook.order_limited.uniswap import (
    get_abi_by_filename,
)


# Consts - now there, because panama_bridge app need to refactor
ETH_POL_STATUS = 'DepositInProgress'
ETH_POL_STATUS_COMPLETED = 'Completed'
ETHEREUM_NETWORK = 'ETH'
POLYGON_NETWORK = 'POL'
POLYGON_API_URL = 'https://apis.matic.network/api/v1/matic/block-included/'
POLYGON_API_URL_TESTNET = 'https://apis.matic.network/api/v1/mumbai/block-included/'
POL_TEST_PR_URL = 'https://rpc-mumbai.maticvigil.com/'
POL_PR_URL = 'https://rpc-mainnet.maticvigil.com/'
RESPONSE_MSG = 'success'
SOME_ABI_NAME = 'some_polygon_abi.json'
SOME_ADDRESS = '0x0000000000000000000000000000000000001001'
# TESTNET = True
WAITING_FOR_DEPOSIT_STATUS = 'WaitingForDeposit'
WITHDRAW_IN_PROGRESS = 'WithdrawInProgress'
INFURA_URL = 'https://mainnet.infura.io/v3/519bcee159504883ad8af59830dec2bb'


def get_infura_provider(provider_url):
    return Web3(HTTPProvider(provider_url))


def update_pol_eth_status():
    # get active POL->ETH transaction
    polygon_transactions = PanamaTransaction.objects.filter(
        type=PanamaTransaction.SWAP_POLYGON,
        from_network=POLYGON_NETWORK,
        to_network=ETHEREUM_NETWORK,
        status__iexact=WITHDRAW_IN_PROGRESS,
    )

    # get pol provider
    # network = Network.displayed_objects.get(
    #     title=POLYGON_NETWORK,
    #     testnet=TESTNET,
    # )
    #
    # try:
    #     pol_provider = get_infura_provider(provider_url=network.provider_url)
    # except Exception:
    #     return 0
    try:
        pol_provider = get_infura_provider(provider_url=POL_PR_URL)
    except Exception:
        return 0

    for transaction in polygon_transactions:
        try:

            receipt = pol_provider.eth.getTransactionReceipt(transaction.transaction_id)

            # if TESTNET:
            #     url = POLYGON_API_URL_TESTNET + str(receipt.blockNumber)
            # else:
            #     url = POLYGON_API_URL + str(receipt.blockNumber)
            url = POLYGON_API_URL + str(receipt.blockNumber)

            response = requests.get(url)

            if response.json().get('message') == RESPONSE_MSG:
                transaction.status = WAITING_FOR_DEPOSIT_STATUS
                transaction.save()

            logging.info(f'Polygon->ethereum updating on {transaction.transaction_id}')
        except Exception:
            logging.error(f'Polygon->ethereum error on {transaction.transaction_id}')
            continue


def second_get_pol_eth_status():
    # get second part of active POL->ETH transaction
    polygon_transactions = PanamaTransaction.objects.filter(
        type=PanamaTransaction.SWAP_POLYGON,
        from_network=POLYGON_NETWORK,
        to_network=ETHEREUM_NETWORK,
        status__iexact=WAITING_FOR_DEPOSIT_STATUS,
    )

    # connect to providers
    # network = Network.displayed_objects.get(
    #     title=ETHEREUM_NETWORK,
    #     testnet=TESTNET,
    # )
    #
    # try:
    #     provider_url = network.provider_url
    # except Exception:
    #     return 0

    w3 = get_infura_provider(provider_url=INFURA_URL)

    # check updating for active transaction
    for transaction in polygon_transactions:

        try:
            receipt = w3.eth.getTransactionReceipt(transaction.second_transaction_id)
            if receipt.status:
                transaction.status = ETH_POL_STATUS_COMPLETED
                transaction.save()
            logging.info(f'Polygon->ethereum second part updating on {transaction.second_transaction_id}')
        except Exception:
            logging.error(f'Polygon->ethereum second part error on {transaction.second_transaction_id}')
            continue


def update_eth_pol_status():
    # get active ETH->POL transaction
    if not PanamaTransaction.objects.filter(
            type=PanamaTransaction.SWAP_POLYGON,
            from_network=ETHEREUM_NETWORK,
            to_network=POLYGON_NETWORK,
            status__iexact=ETH_POL_STATUS,
    ).exists():
        return 0

    polygon_transactions = PanamaTransaction.objects.filter(
        type=PanamaTransaction.SWAP_POLYGON,
        from_network=ETHEREUM_NETWORK,
        to_network=POLYGON_NETWORK,
        status__iexact=ETH_POL_STATUS,
    )

    # connect to providers
    # try:
    #     network = Network.displayed_objects.get(
    #         title=ETHEREUM_NETWORK,
    #         testnet=TESTNET,
    #     )
    # except Network.DoesNotExist:
    #     logging.error(f"Network {ETHEREUM_NETWORK} with Testnet:{TESTNET} doesn't exist")
    #     return 0

    # try:
    #     w3 = get_infura_provider(provider_url=network.provider_url)
    # except Exception:
    #     logging.error(f'Ethereum->polygon error on provider connection')
    #     return 0
    w3 = get_infura_provider(provider_url=INFURA_URL)

    # network = Network.displayed_objects.get(
    #     title=POLYGON_NETWORK,
    #     testnet=TESTNET,
    # )
    # try:
    #     pol_provider = get_infura_provider(provider_url=network.provider_url)
    # except Exception:
    #     return 0
    pol_provider = get_infura_provider(provider_url=POL_PR_URL)

    # check status for active transaction on blockchain
    for transaction in polygon_transactions:
        try:

            # get transaction receipt
            receipt = w3.eth.getTransactionReceipt(transaction.transaction_id)

            # magic code from polygon docs ------
            # load some contract
            some_abi = get_abi_by_filename(SOME_ABI_NAME)
            some_contract = pol_provider.eth.contract(
                abi=some_abi,
                address=SOME_ADDRESS,
            )

            # get pol counter (no one know what is it)
            polygon_counter = some_contract.functions.lastStateId().call()

            # get eth counter
            eth_counter = 0
            for log in receipt.logs:
                if log.topics[0] == HexBytes('103fed9db65eac19c4d870f49ab7520fe03b99f1838e5996caf47e9e43308392'):
                    eth_counter = int(bytes.hex(log.topics[1]), 16)

            # magic counters check
            if eth_counter:
                if polygon_counter >= eth_counter:
                    transaction.status = ETH_POL_STATUS_COMPLETED
                    transaction.save()

            logging.info(f'Ethereum->polygon updating on {transaction.transaction_id}')
        except Exception:
            logging.error(f'Ethereum->polygon error on {transaction.transaction_id}')
            continue
