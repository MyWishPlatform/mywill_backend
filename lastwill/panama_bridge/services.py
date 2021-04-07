import logging
from decimal import Decimal
from requests import get

# from django.db.models.query import QuerySet
from django.utils import timezone
from rest_framework.status import (
    HTTP_201_CREATED,
    HTTP_400_BAD_REQUEST,
    HTTP_500_INTERNAL_SERVER_ERROR,
)
from web3 import Web3, HTTPProvider
# from web3.exceptions import TransactionNotFound

from lastwill.consts import NET_DECIMALS
from lastwill.swaps_common.orderbook.order_limited.uniswap import load_contract
from lastwill.settings_local import (
    # ETH_PROVIDER_URL,
    # BSC_PROVIDER_URL,
    ETH_SWAP_CONTRACT_ADDRESS,
    BSC_SWAP_CONTRACT_ADDRESS,
    SWAP_BACKEND_URL,
)

from .models import PanamaTransaction

RBC_DECIMALS = NET_DECIMALS.get('RBC', 10 ** 18)


# def create_swap(network:int, tx_hash:str):
def create_swap(
    from_network:int,
    tx_id:str,
    from_amount:str,
    wallet_address:str
):
    # {
    #    "type": "swap_rbc",
    #    "fromNetwork": int (1 - BSC / 2 - ETH),
    #    "transaction_id": str,
    #    "fromAmount": str,
    #    "walletFromAddress": str
    # }
    if not from_network or not tx_id or not from_amount:
        return (
            'Network or tx_hash or from_amount is required.',
            HTTP_400_BAD_REQUEST,
        )

    if PanamaTransaction.objects.filter(transaction_id=tx_id).exists():
        return (
            'Swap with hash {} already exist.'.format(tx_id),
            HTTP_400_BAD_REQUEST,
        )


    networks = {
        'BSC': {
            'blockchain_id': 1,
            'title': 'BSC',
            'contract_address': BSC_SWAP_CONTRACT_ADDRESS,
            'contract_abi': 'rubic_bsc_swap_contract.json',
        },
        'ETH': {
            'blockchain_id': 2,
            'title': 'ETH',
            'contract_address': ETH_SWAP_CONTRACT_ADDRESS,
            'contract_abi': 'rubic_eth_swap_contract.json',
        }
    }

    network = networks.get('BSC' if from_network == 1 else 'ETH')

    try:
        contract = load_contract(
            network.get('contract_abi'),
            # Web3.toChecksumAddress(network.get('contract_address'))
            Web3.toChecksumAddress(ETH_SWAP_CONTRACT_ADDRESS)
        )
        from_network = network.get('blockchain_id')

        if from_network == 1:
            to_network = 2
        elif from_network == 2:
            to_network = 1

        # to_network = 1 if network.get('blockchain_id') == 1 else 2
        # fee_address = contract.functions.feeAddress().call()
        fee_amount = contract.functions.feeAmountOfBlockchain(to_network).call()
        actual_from_amount = int(Decimal(from_amount) * RBC_DECIMALS)
        actual_to_amount = (actual_from_amount - int(fee_amount)) / RBC_DECIMALS
        wallet_deposit_address = ETH_SWAP_CONTRACT_ADDRESS if network == 2 else BSC_SWAP_CONTRACT_ADDRESS

        new_swap = PanamaTransaction(
            type=PanamaTransaction.SWAP_RBC,
            from_network=network.get('title'),
            to_network='BSC' if from_network == 2 else 'ETH',
            eth_symbol='RBC',
            bsc_symbol='BRBC',
            wallet_from_address=wallet_address.lower(),
            wallet_to_address=wallet_address.lower(),
            actual_from_amount=Decimal(actual_from_amount / RBC_DECIMALS),
            actual_to_amount=Decimal(actual_to_amount),
            transaction_id=tx_id,
            wallet_deposit_address=wallet_deposit_address,
            update_time=timezone.now(),
            status='DepositInProgress',
        )

        new_swap.save()

        logging.info(
            """Swap with hash {transaction_id} was successfully added.
               The swap body:
               Type: {type},
               Transaction id: {transaction_id},
               From network: {from_network},
               To network: {to_network},
               ETH symbol: {eth_symbol},
               BSC symbol: {bsc_symbol},
               From wallet address: {wallet_from_address},
               To wallet address: {wallet_to_address},
               From actual amount: {actual_from_amount},
               To actual amount: {actual_to_amount},
               Deposit wallet address: {wallet_deposit_address},
               Updated at: {update_time},
               Status: {status}
            """.format(
                type=new_swap.type,
                transaction_id=new_swap.transaction_id,
                from_network=new_swap.from_network,
                to_network=new_swap.to_network,
                eth_symbol=new_swap.eth_symbol,
                bsc_symbol=new_swap.bsc_symbol,
                wallet_from_address=new_swap.wallet_from_address,
                wallet_to_address=new_swap.wallet_to_address,
                actual_from_amount=new_swap.actual_from_amount,
                actual_to_amount=new_swap.actual_to_amount,
                wallet_deposit_address=new_swap.wallet_deposit_address,
                update_time=new_swap.update_time,
                status=new_swap.status,
            )
        )

        return (
            'Swap with hash {} was successfully added.'.format(tx_id),
            HTTP_201_CREATED,
        )

    # if not network or not tx_hash or not from_amount:
    #     return (
    #         'Network or tx_hash or from_amount is required.',
    #         HTTP_400_BAD_REQUEST,
    #     )

    # if network == 1:
    #     url_provider = BSC_PROVIDER_URL
    #     # contract_address = BSC_SWAP_CONTRACT_ADDRESS
    #     # TODO: fix method call to BSC contract.
    #     contract_address = ETH_SWAP_CONTRACT_ADDRESS
    #     contract_abi = 'rubic_bsc_swap_contract.json'
    # elif network == 2:
    #     url_provider = ETH_PROVIDER_URL
    #     contract_address = ETH_SWAP_CONTRACT_ADDRESS
    #     contract_abi = 'rubic_eth_swap_contract.json'

    # web3_provider = Web3(HTTPProvider(url_provider))

    # try:
    #     contract = load_contract(
    #         contract_abi,
    #         Web3.toChecksumAddress(contract_address)
    #     )
    #     tx_receipt = web3_provider.eth.waitForTransactionReceipt(tx_hash)
    #     receipt = contract.events.TransferToOtherBlockchain().processReceipt(tx_receipt)

    #     if not receipt:
    #         return (
    #             'No info with hash: {} in events.'.format(tx_hash),
    #             HTTP_400_BAD_REQUEST,
    #         )

    #     print(receipt)

    #     event = receipt[0].args

    #     print(event)

    #     target_network = event.blockchain
    #     # token = contract.functions.tokenAddress().call()
    #     tx_hash=Web3.toHex(receipt[0]['transactionHash'])
    #     fee_address = contract.functions.feeAddress().call()
    #     fee_amount = contract.functions.feeAmountOfBlockchain(target_network).call()

    #     if PanamaTransaction.objects.filter(transaction_id=tx_hash).exists():
    #         return (
    #             'Swap with hash {} already exist.'.format(
    #                 tx_hash,
    #             ),
    #             HTTP_400_BAD_REQUEST,
    #         )

    #     new_swap = PanamaTransaction(
    #         type=PanamaTransaction.SWAP_RBC,
    #         from_network='ETH' if network == 2 else 'BSC',
    #         to_network='BSC' if target_network == 1 else 'ETH',
    #         eth_symbol='RBC',
    #         bsc_symbol='BRBC',
    #         wallet_from_address=event.user.lower(),
    #         wallet_to_address=event.newAddress.lower(),
    #         actual_from_amount=str(int(event.amount) / RBC_DECIMALS),
    #         actual_to_amount=str((int(event.amount) - int(fee_amount)) / RBC_DECIMALS),
    #         transaction_id=tx_hash,
    #         # wallet_deposit_address=receipt[0]['address'].lower(),
    #         # TODO: fix call to BSC contract.
    #         wallet_deposit_address=ETH_SWAP_CONTRACT_ADDRESS if network == 2 else BSC_SWAP_CONTRACT_ADDRESS,
    #         update_time=timezone.now(),
    #         status='DepositInProgress',
    #         # fee_address=fee_address,
    #         # fee_amount=fee_amount,
    #     )

    #     new_swap.save()

    #     logging.info(
    #         {
    #             'network': network,
    #             'source_address': event.user,
    #             'target_address': event.newAddress,
    #             'amount': event.amount,
    #             'tx_hash': tx_hash,
    #             'fee_address': fee_address,
    #             'fee_amount': fee_amount,
    #         }
    #     )

    #     return (
    #         'Swap with hash {} was successfully added.'.format(tx_hash),
    #         HTTP_201_CREATED,
    #     )
    # except TransactionNotFound as exception_error:
    #     print(exception_error)

    #     return (
    #         str(exception_error),
    #         HTTP_400_BAD_REQUEST
    #     )
    except Exception as exception_error:
        return (
            str(exception_error),
            HTTP_500_INTERNAL_SERVER_ERROR,
        )


def check_swap_status(swap_tx_hash:str, backend_url:str=SWAP_BACKEND_URL):
    response = get(backend_url.format(swap_tx_hash))

    return response.json()['status']


def update_swap_status():
    swaps = PanamaTransaction.objects \
            .filter(type=PanamaTransaction.SWAP_RBC) \
            .exclude(status='Completed')

    for swap in swaps:
        status = check_swap_status(swap.transaction_id)

        # logging.info(status)

        # if status == 'FAIL':
        #     swap.status = swap.FAIL
        if status == 'IN_PROCESS':
            swap.update_time=timezone.now()
            swap.status = 'DepositInProgress'
        elif status == 'SUCCESS':
            swap.update_time=timezone.now()
            swap.status = 'Completed'

        swap.save()

        logging.info(
            'Swap with hash {} was updated status to {} at {}.'.format(
                swap.transaction_id,
                swap.status,
                swap.update_time,
            )
        )

    return 1
