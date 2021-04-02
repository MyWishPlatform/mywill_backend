import logging
from requests import get

from django.db.models.query import QuerySet
from django.utils import timezone
from rest_framework.status import (
    HTTP_201_CREATED,
    HTTP_400_BAD_REQUEST,
    HTTP_500_INTERNAL_SERVER_ERROR,
)
from web3 import Web3, HTTPProvider
from web3.exceptions import TransactionNotFound

from lastwill.swaps_common.orderbook.order_limited.uniswap import load_contract
from lastwill.settings_local import (
    ETH_PROVIDER_URL,
    BSC_PROVIDER_URL,
    ETH_SWAP_CONTRACT_ADDRESS,
    BSC_SWAP_CONTRACT_ADDRESS,
    SWAP_BACKEND_URL,
)

from .models import PanamaTransaction


def create_swap(network:int, tx_hash:str):
    if not network or not tx_hash:
        return (
            'Network or tx_hash is required.',
            HTTP_400_BAD_REQUEST,
        )

    if network == 1:
        url_provider = BSC_PROVIDER_URL
        # contract_address = BSC_SWAP_CONTRACT_ADDRESS
        # TODO: fix method call to BSC contract.
        contract_address = ETH_SWAP_CONTRACT_ADDRESS
        contract_abi = 'rubic_bsc_swap_contract.json'
    elif network == 2:
        url_provider = ETH_PROVIDER_URL
        contract_address = ETH_SWAP_CONTRACT_ADDRESS
        contract_abi = 'rubic_eth_swap_contract.json'

    web3_provider = Web3(HTTPProvider(url_provider))

    try:
        contract = load_contract(
            contract_abi,
            Web3.toChecksumAddress(contract_address)
        )
        tx_receipt = web3_provider.eth.waitForTransactionReceipt(tx_hash)
        receipt = contract.events.TransferToOtherBlockchain().processReceipt(tx_receipt)

        if not receipt:
            return (
                'No info with hash: {} in events.'.format(tx_hash),
                HTTP_400_BAD_REQUEST,
            )

        print(receipt)

        event = receipt[0].args

        print(event)

        target_network = event.blockchain
        # token = contract.functions.tokenAddress().call()
        tx_hash=Web3.toHex(receipt[0]['transactionHash'])
        fee_address = contract.functions.feeAddress().call()
        fee_amount = contract.functions.feeAmountOfBlockchain(target_network).call()

        if PanamaTransaction.objects.filter(transaction_id=tx_hash).exists():
            return (
                'Swap with hash {} already exist.'.format(
                    tx_hash,
                ),
                HTTP_400_BAD_REQUEST,
            )

        new_swap = PanamaTransaction(
            type=PanamaTransaction.SWAP_RBC,
            from_network='ETH' if network == 2 else 'BSC',
            to_network='BSC' if target_network == 1 else 'ETH',
            eth_symbol='RBC',
            bsc_symbol='BRBC',
            wallet_from_address=event.user.lower(),
            wallet_to_address=event.newAddress.lower(),
            actual_from_amount=str(int(event.amount) / 10 ** 18),
            actual_to_amount=str((int(event.amount) - int(fee_amount)) / 10 ** 18),
            transaction_id=tx_hash,
            # wallet_deposit_address=receipt[0]['address'].lower(),
            # TODO: fix call to BSC contract.
            wallet_deposit_address=ETH_SWAP_CONTRACT_ADDRESS if network == 2 else BSC_SWAP_CONTRACT_ADDRESS,
            update_time=timezone.now(),
            status='DepositInProgress',
            # fee_address=fee_address,
            # fee_amount=fee_amount,
        )

        new_swap.save()

        logging.info(
            {
                'network': network,
                'source_address': event.user,
                'target_address': event.newAddress,
                'amount': event.amount,
                'tx_hash': tx_hash,
                'fee_address': fee_address,
                'fee_amount': fee_amount,
            }
        )

        return (
            'Swap with hash {} was successfully added.'.format(tx_hash),
            HTTP_201_CREATED,
        )
    except TransactionNotFound as exception_error:
        print(exception_error)

        return (
            str(exception_error),
            HTTP_400_BAD_REQUEST
        )
    except Exception as exception_error:
        return (
            str(exception_error),
            HTTP_500_INTERNAL_SERVER_ERROR,
        )

def check_swap_status(swap_tx_hash:str, backend_url:str=SWAP_BACKEND_URL):
    response = get(backend_url.format(swap_tx_hash))

    return response.json()['status']


def update_swap_status(
    swaps:QuerySet=PanamaTransaction.objects \
                   .filter(type='swap_rbc') \
                   .exclude(status='Completed')
):
    for swap in swaps:
        status = check_swap_status(swap.transaction_id)

        logging.info(status)

        # if status == 'FAIL':
        #     swap.status = swap.FAIL
        if status == 'IN_PROCESS':
            swap.update_time=timezone.now()
            swap.status = 'DepositInProgress'
        elif status == 'SUCCESS':
            swap.update_time=timezone.now()
            swap.status = 'Completed'
        swap.save()

    return 1
