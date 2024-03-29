import logging

import requests
from hexbytes import HexBytes
from web3 import HTTPProvider, Web3

# from networks.models import Network
# from contracts.services import (
# get_infura_provider,
# get_abi_by_filename,
# )
from lastwill.swaps_common.orderbook.order_limited.uniswap import \
    get_abi_by_filename

from .models import PanamaTransaction

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
INFURA_URL_GOERLI_TESTNET = 'https://goerli.infura.io/v3/519bcee159504883ad8af59830dec2bb'
LOG_ZERO_TOPIC_HASH = '103fed9db65eac19c4d870f49ab7520fe03b99f1838e5996caf47e9e43308392'


def get_infura_provider(provider_url):
    return Web3(HTTPProvider(provider_url))


def update_pol_eth_status(debug=False):
    # get active POL->ETH transaction
    polygon_transactions = PanamaTransaction.objects.filter(
        type=PanamaTransaction.SWAP_POLYGON,
        from_network=POLYGON_NETWORK,
        to_network=ETHEREUM_NETWORK,
        status__iexact=ETH_POL_STATUS,
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
        # pol_provider = get_infura_provider(provider_url=POL_PR_URL)
        # pol_provider = get_infura_provider(provider_url=POL_TEST_PR_URL)
        pol_provider = get_infura_provider(provider_url=POL_PR_URL if debug else POL_TEST_PR_URL)
    except Exception as exception_error:
        logging.error("""
            Get provider.
            Error message:
            {error_message}
            """.format(error_massage=exception_error.__str__()))

        return 0

    for transaction in polygon_transactions:
        try:

            receipt = pol_provider.eth.getTransactionReceipt(transaction.transaction_id)

            # if TESTNET:
            #     url = POLYGON_API_URL_TESTNET + str(receipt.blockNumber)
            # else:
            #     url = POLYGON_API_URL + str(receipt.blockNumber)
            # url = POLYGON_API_URL + str(receipt.blockNumber)
            # url = POLYGON_API_URL_TESTNET + str(receipt.blockNumber)
            url = '{url}{block_number}'.format(url=POLYGON_API_URL if debug else POLYGON_API_URL_TESTNET,
                                               block_bumber=str(receipt.blockNumber))

            response = requests.get(url)

            if response.json().get('message') == RESPONSE_MSG:
                transaction.status = WAITING_FOR_DEPOSIT_STATUS
                transaction.save()

            logging.info('Polygon -> Ethereum updating on {tx_id}'.format(tx_id=transaction.transaction_id))
        except Exception as exception_error:
            logging.error("""
                Polygon -> Ethereum error on {tx_id}.
                Error description:
                {error_message}
                """.format(tx_id=transaction.transaction_id, error_message=exception_error.__str__()))

            continue


def second_get_pol_eth_status(debug=False):
    # get second part of active POL->ETH transaction
    polygon_transactions = PanamaTransaction.objects.filter(
        type=PanamaTransaction.SWAP_POLYGON,
        from_network=POLYGON_NETWORK,
        to_network=ETHEREUM_NETWORK,
        status__iexact=WITHDRAW_IN_PROGRESS,
    ) \
    .exclude(
        second_transaction_id='',
    )

    if not polygon_transactions:
        return 0

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

    # w3 = get_infura_provider(provider_url=INFURA_URL)
    w3 = get_infura_provider(provider_url=INFURA_URL if debug else INFURA_URL_GOERLI_TESTNET)

    # check updating for active transaction
    for transaction in polygon_transactions:

        try:
            receipt = w3.eth.getTransactionReceipt(transaction.second_transaction_id)

            if receipt.status:
                transaction.status = ETH_POL_STATUS_COMPLETED
                transaction.save()

            logging.info('Polygon -> Ethereum second part updating on {}.'.format(transaction.second_transaction_id))
        except Exception as exception_error:
            logging.error("""
                Polygon -> Ethereum second part error on {tx_id}.
                Error description:
                {error_message}
                """.format(
                tx_id=transaction.second_transaction_id,
                error_message=exception_error.__str__(),
            ))

            continue


def update_eth_pol_status(debug=False):
    # get active ETH->POL transaction

    polygon_transactions = PanamaTransaction.objects.filter(
        type=PanamaTransaction.SWAP_POLYGON,
        from_network=ETHEREUM_NETWORK,
        to_network=POLYGON_NETWORK,
        status__iexact=ETH_POL_STATUS,
    )

    if not polygon_transactions:
        return 0

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
    # w3 = get_infura_provider(provider_url=INFURA_URL)
    # w3 = get_infura_provider(provider_url=INFURA_URL_GOERLI_TESTNET)
    w3 = get_infura_provider(provider_url=INFURA_URL if debug else INFURA_URL_GOERLI_TESTNET)

    # network = Network.displayed_objects.get(
    #     title=POLYGON_NETWORK,
    #     testnet=TESTNET,
    # )
    # try:
    #     pol_provider = get_infura_provider(provider_url=network.provider_url)
    # except Exception:
    #     return 0
    # pol_provider = get_infura_provider(provider_url=POL_PR_URL)
    # pol_provider = get_infura_provider(provider_url=POL_TEST_PR_URL)
    pol_provider = get_infura_provider(provider_url=POL_PR_URL if debug else POL_TEST_PR_URL)

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
                if log.topics[0] == HexBytes(LOG_ZERO_TOPIC_HASH):
                    eth_counter = int(bytes.hex(log.topics[1]), 16)

            # magic counters check
            if eth_counter:
                if polygon_counter >= eth_counter:
                    transaction.status = ETH_POL_STATUS_COMPLETED
                    transaction.save()

            logging.info('Ethereum -> Polygon second part updating on {}.'.format(transaction.second_transaction_id))
        except Exception as exception_error:
            logging.error("""
                Ethereum-> Polygon error on {tx_id}.
                Error description:
                {error_message}
                """.format(
                tx_id=transaction.second_transaction_id,
                error_message=exception_error.__str__(),
            ))

            continue
