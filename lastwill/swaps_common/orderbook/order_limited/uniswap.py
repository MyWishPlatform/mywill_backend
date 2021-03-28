import logging
import time
import json
import os
from typing import Union, Optional

from gql import Client, gql
from gql.transport.requests import RequestsHTTPTransport
from web3.contract import ContractFunction, Contract
from web3 import Web3, HTTPProvider
from web3.types import (
    Wei,
    HexBytes,
    ChecksumAddress,
    ENS,
    Address,
    TxParams,
)

from lastwill.settings_local import WALLET_ADDRESS, PRIVATE_KEY

from .consts import (
    INFURA_URL,
    MAX_SLIPPAGE,
    RUBIC_ADDRESS,
    UNISWAP_API_URL,
    UNISWAP_ROUTER02_ADDRESS,
)


AddressLike = Union[Address, ChecksumAddress, ENS]

# connect to infura
w3 = Web3(HTTPProvider(INFURA_URL))


def get_abi_by_filename(filename):
    """
    func input - filename
    func output - contract abi
    Needed for a convenient format for storing abi contracts in files
    and receiving them as variables for further interaction
    """
    build_dir = os.path.join(
        os.getcwd(), 'lastwill/swaps_common/orderbook/contracts_abi/')

    with open(os.path.join(build_dir, filename), 'r') as contract:
        return json.load(contract)


# def get_erc20_contract(token_addr: AddressLike) -> Contract:
#     # TODO: rewrite rubic contract use to erc20 contract
#     return load_contract(abi_name="erc20.json", address=token_addr)


def load_contract(abi_name: str, address: AddressLike) -> Contract:
    # TODO: refactor using this func
    return w3.eth.contract(address=address, abi=get_abi_by_filename(abi_name))


def validate_address(a: AddressLike) -> None:
    assert addr_to_str(a)


def get_eth_balance(wallet_address) -> Wei:
    """
    Get the balance of ETH in a wallet.
    """
    return w3.eth.getBalance(wallet_address)


def get_rbc_balance(wallet_address) -> Wei:
    """
    Return user rbc balance on wallet on rbc.
    """
    # TODO: rewrite func to get token status
    #  input: wallet address, token address
    contract = load_contract(
        'rubic_token.json',
        RUBIC_ADDRESS
    )

    return contract.functions.balanceOf(wallet_address).call()


def deadline() -> int:
    """
    Get a predefined deadline. 10min by default (same as the Uniswap SDK).
    """
    return int(time.time()) + 10 * 60


def addr_to_str(a: AddressLike) -> str:
    if isinstance(a, bytes):
        # Address or ChecksumAddress
        addr: str = Web3.toChecksumAddress("0x" + bytes(a).hex())

        return addr
    elif isinstance(a, str):
        if a.startswith("0x"):
            addr = Web3.toChecksumAddress(a)

            return addr


def str_to_addr(s: str) -> AddressLike:
    if s.startswith("0x"):
        return Address(bytes.fromhex(s[2:]))
    elif s.endswith(".eth"):
        return ENS(s)
    else:
        # TODO: add exception
        pass


# ------ Approval Utils -------------------------------------------------------
def approve(
    token_address: AddressLike,
    max_approval: Optional[int] = None,
    contract_address=UNISWAP_ROUTER02_ADDRESS
):
    # gg
    max_approval_hex = f"0x{64 * 'f'}"
    max_approval_int = int(max_approval_hex, 16)
    max_approval = max_approval_int if not max_approval else max_approval
    # gg

    """Give an exchange/router max approval of a token."""
    # TODO: now it works only for rubic
    #  change rubic_abi to erc20_abi
    contract = load_contract(
        'rubic_token.json',
        token_address,
    )
    function = contract.functions.approve(
        contract_address, max_approval
    )
    tx = build_and_send_tx(function)
    logging.info('Txn body: {}'.format(tx))
    logging.info('yep')

    w3.eth.waitForTransactionReceipt(tx, timeout=600)

    logging.info('success')
    # Add extra sleep to let tx propogate correctly
    time.sleep(1)


def is_approved(token: AddressLike) -> bool:
    """
    Check to see if the exchange and token is approved.
    """
    # gg
    max_approval_check_hex = f"0x{15 * '0'}{49 * 'f'}"
    max_approval_check_int = int(max_approval_check_hex, 16)
    # gg

    validate_address(token)

    contract_addr = UNISWAP_ROUTER02_ADDRESS
    # amount = (
    #     get_erc20_contract(token).functions
    #     .allowance(WALLET_ADDRESS, contract_addr)
    #     .call()
    # )
    amount = (
        load_contract('erc20.json', token).functions
        .allowance(WALLET_ADDRESS, contract_addr)
        .call()
    )

    if amount >= max_approval_check_int:
        return True
    else:
        return False


# ------ расчет кол-ва токенов на отправку ------------------------------------
def get_eth_token_output_price(
    quantity_in_wei: int,
    token_address: AddressLike,
) -> Wei:
    """
    Public price for ETH to token trades with an exact output.
    """
    contract = load_contract(
        'uniswap_router02.json',
        UNISWAP_ROUTER02_ADDRESS
    )
    price = contract.functions.getAmountsIn(
        quantity_in_wei,
        [
            Web3.toChecksumAddress(get_weth_address()),
            Web3.toChecksumAddress(token_address),
        ]
    ).call()[0]

    logging.info('ETH token output price is: {}'.format(price))

    return price


def get_token_eth_output_price(
    quantity_in_wei: Wei,
    token_address: AddressLike,
) -> int:
    """
    Public price for token to ETH trades with an exact output.
    """
    # Если хотим получить на выходе 1 эфир то нужно закинуть не менее output
    # рубиков.

    # abi = get_abi_by_filename("uniswap_router02.json")
    # contract = w3.eth.contract(address=UNISWAP_ROUTER02_ADDRESS, abi=abi)

    contract = load_contract(
        'uniswap_router02.json',
        UNISWAP_ROUTER02_ADDRESS
    )
    price = contract.functions.getAmountsIn(
        quantity_in_wei,
        [
            Web3.toChecksumAddress(token_address),
            Web3.toChecksumAddress(get_weth_address()),
        ]
    ).call()[0]

    logging.info('Token ETH output price is: {}'.format(price))

    return price


# ------ обмен высчитанных токенов --------------------------------------------
def get_tx_params(value: Wei = Wei(0), gas: Wei = Wei(250000)) -> TxParams:
    """
    Get generic transaction parameters.
    """

    logging.info('get_tx_params function was called.')

    return {
        "from": addr_to_str(WALLET_ADDRESS),
        "value": value,
        "gas": gas,
        "nonce": w3.eth.getTransactionCount(WALLET_ADDRESS),
    }


def eth_to_token_swap_output(
    output_token: AddressLike,
    qty: int,
    recipient: Optional[AddressLike]
) -> HexBytes:
    """
    Convert ETH to tokens given an output amount.
    """
    if recipient is None:
        recipient = WALLET_ADDRESS

    eth_qty = get_eth_token_output_price(
        quantity_in_wei=qty,
        token_address=output_token
    )
    contract = load_contract(
        'uniswap_router02.json',
        UNISWAP_ROUTER02_ADDRESS
    )
    swap_func = contract.functions.swapETHForExactTokens

    sended_transaction = build_and_send_tx(
        swap_func(
            qty,
            [get_weth_address(), RUBIC_ADDRESS],
            recipient,
            deadline(),
        ),
        get_tx_params(eth_qty),
    )

    # ---
    logging.info(sended_transaction)
    result = w3.eth.waitForTransactionReceipt(
        sended_transaction,
        timeout=600
    )
    logging.info(result)
    # ---

    return 1


def token_to_eth_swap_output(
    input_token: AddressLike, qty: Wei
) -> HexBytes:
    """
    Convert tokens to ETH given an output amount.
    """
    # !---
    cost = get_token_eth_output_price(
        token_address=input_token,
        quantity_in_wei=qty
    )
    # ---
    max_tokens = int((1 + MAX_SLIPPAGE) * cost)
    contract = load_contract(
        'uniswap_router02.json',
        UNISWAP_ROUTER02_ADDRESS,
    )
    swap_func = contract.functions.swapTokensForExactETH

    sended_transaction = build_and_send_tx(
        swap_func(
            qty,
            max_tokens,
            [input_token, get_weth_address()],
            WALLET_ADDRESS,
            deadline(),
        ),
    )

    # ---
    logging.info(sended_transaction)
    result = w3.eth.waitForTransactionReceipt(
        sended_transaction,
        timeout=600
    )
    logging.info(result)
    # ---

    return 1


def build_and_send_tx(
    function: ContractFunction,
    tx_params: Optional[TxParams] = None
) -> HexBytes:
    """
    Build and send a transaction.
    """
    if not tx_params:
        tx_params = get_tx_params()

    transaction = function.buildTransaction(tx_params)
    signed_txn = w3.eth.account.sign_transaction(
        transaction, private_key=PRIVATE_KEY
    )

    logging.info(signed_txn.rawTransaction)

    # !--- Commented for test.
    # return w3.eth.sendRawTransaction(signed_txn.rawTransaction)
    return w3.eth.send_raw_transaction(signed_txn.rawTransaction)
    # ---


def get_weth_address() -> ChecksumAddress:
    """
    Returns UniswapsRouter02 contract address.
    """
    # Contract calls should always return checksummed addresses
    router_contract = load_contract(
        'uniswap_router02.json',
        UNISWAP_ROUTER02_ADDRESS,
    )

    return router_contract.functions.WETH().call()


def _get_rbc_eth_ratio(token_address) -> float:
    """
    Parse exchange rate rbc to eth from UniSwap.
    Return exchange rate: float.
    """
    transport = RequestsHTTPTransport(url=UNISWAP_API_URL)
    client = Client(transport=transport, fetch_schema_from_transport=True)
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
        """ % token_address.lower()
    )

    while 1:
        # Execute the query on the transport
        result = client.execute(query)

        if result:
            logging.info('UNISWAP GQL response: {}'.format(
                float(result.get("token").get("derivedETH")))
            )

            break

    return float(result.get("token").get("derivedETH"))
