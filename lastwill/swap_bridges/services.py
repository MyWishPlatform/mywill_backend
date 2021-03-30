from requests import get

from django.db.models.query import QuerySet
from rest_framework.status import HTTP_201_CREATED, HTTP_400_BAD_REQUEST
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

from .models import Swap


def create_swap(network:int, tx_hash:str):
    if not network or not tx_hash:
        return (
            'Network or tx_hash is required.',
            HTTP_400_BAD_REQUEST,
        )

    if network == 1:
        url_provider = BSC_PROVIDER_URL
        contract_address = BSC_SWAP_CONTRACT_ADDRESS
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
        tx_receipt = web3_provider.eth.getTransactionReceipt(tx_hash)
        receipt = contract.events.TransferToOtherBlockchain().processReceipt(tx_receipt)

        if not receipt:
            return (
                'No info with the tx_hash in events.',
                HTTP_400_BAD_REQUEST,
            )

        print(receipt)

        event = receipt[0].args

        print(event)

        target_address = event.blockchain
        token = contract.functions.tokenAddress().call()
        tx_hash=Web3.toHex(receipt[0]['transactionHash'])
        fee_address = contract.functions.feeAddress().call()
        fee_amount = contract.functions.feeAmountOfBlockchain(target_address).call()

        if Swap.objects.filter(tx_hash=tx_hash).exists():
            return (
                'Swap with the tx_hash \"{}\" already exist.'.format(
                    tx_hash,
                ),
                HTTP_400_BAD_REQUEST,
            )

        new_swap = Swap(
            source_network=network,
            target_network=target_address,
            token=token.lower(),
            source_address=event.user.lower(),
            target_address=event.newAddress.lower(),
            amount=event.amount,
            tx_hash=tx_hash,
            fee_address=fee_address,
            fee_amount=fee_amount,
        )

        new_swap.save()

        print({'network': network,
            'source_address': event.user,
            'target_address': event.newAddress,
            'amount': event.amount,
            'tx_hash': tx_hash,
            'fee_address': fee_address,
            'fee_amount': fee_amount,})

        return (
            'Swap was successfully added.',
            HTTP_201_CREATED,
        )
    except TransactionNotFound as exception_error:
        print(exception_error)

        return (exception_error, HTTP_400_BAD_REQUEST)


def check_swap_status(swap_tx_hash:str, backend_url:str=SWAP_BACKEND_URL):
    response = get(backend_url.format(swap_tx_hash))

    return response.json()['status']


def update_swap_status(
    swaps:QuerySet=Swap.objects.exclude(status=Swap.SUCCESS)
):
    for swap in swaps:
        status = check_swap_status(swap.tx_hash)

        if status == 'FAIL':
            swap.status = swap.FAIL
        elif status == 'IN PROCESS':
            swap.status = swap.PENDING
        elif status == 'SUCCESS':
            swap.status = swap.SUCCESS
        swap.save()

    return 1
