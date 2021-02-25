import time
import json
import os
from typing import Union, Optional
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


ETH_ADDRESS = '0x0000000000000000000000000000000000000000'
UNISWAP_RBC_ETH_CONTRACT_ADDRESS = "0x10db37f4d9b3bc32AE8303B46E6166F7e9652d28"
OLD_MAINNET_CONTRACT_ADDRESS = '0xAAaCFf66942df4f1e1cB32C21Af875AC971A8117'
NEW_KOVAN_ADDRESS = "0xB09fe422dE371a86D7148d6ED9DBD499287cc95c"
RUBIC_ADDRESS = "0xA4EED63db85311E22dF4473f87CcfC3DaDCFA3E3"
UNISWAP_ROUTER02_ADDRESS = '0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D'

INFURA_URL = 'https://mainnet.infura.io/v3/519bcee159504883ad8af59830dec2bb'
ETHERSCAN_API = "https://api.etherscan.io/api"
UNISWAP_API = "https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v2"

# TEST_PRIVATE_KEY = 'e2331db69cda61275c8d5addbfd288c8ba76d1243e6cdb26fba541d740583fb9'
ETHERSCAN_API_KEY = "D8QKZPVM9BMRWS7BY41RU9EKU2VMWT8PM5"
MAX_SLIPPAGE = 0.1
BLOCKCHAIN_DECIMALS = 10 ** 18
MIN_BALANCE_PARAM = 1

# TEST_WALLET_ADDRESS = '0x226362f9cB9bAfF72f3D63513954838cD86282e1'
TEST_WALLET_ADDRESS = ''
# WALLET_ADDRESS = '0xfCf49f25a2D1E49631d05614E2eCB45296F26258'
WALLET_ADDRESS = TEST_WALLET_ADDRESS
TEST_PRIVATE_KEY = ''
PRIVATE_KEY = TEST_PRIVATE_KEY

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
    build_dir = os.path.join(os.getcwd(), 'lastwill/swaps_common/orderbook/contracts_abi/')

    with open(os.path.join(build_dir, filename), 'r') as contract:
        return json.load(contract)


def get_erc20_contract(token_addr: AddressLike) -> Contract:
    # TODO: rewrite rubic contract use to erc20 contract
    return load_contract(abi_name="erc20.json", address=token_addr)


def load_contract(abi_name: str, address: AddressLike) -> Contract:
    # TODO: refactor using this func
    return w3.eth.contract(address=address, abi=get_abi_by_filename(abi_name))


def validate_address(a: AddressLike) -> None:
    assert addr_to_str(a)


def get_eth_balance(wallet_address) -> Wei:
    """Get the balance of ETH in a wallet."""
    return w3.eth.getBalance(wallet_address)


def get_rbc_balance(wallet_address) -> Wei:
    """
        Return user rbc balance on wallet on rbc.
    """
    # TODO: rewrite func to get token status
    #  input: wallet address, token address
    rubic_abi = get_abi_by_filename("rubic_token.json")
    contract = w3.eth.contract(address=RUBIC_ADDRESS, abi=rubic_abi)

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


# ------ Approval Utils ------------------------------------------------------------
def approve(
    token: AddressLike,
    max_approval: Optional[int] = None,
    contract_address=UNISWAP_ROUTER02_ADDRESS
) -> None:
    # gg
    max_approval_hex = f"0x{64 * 'f'}"
    max_approval_int = int(max_approval_hex, 16)
    max_approval = max_approval_int if not max_approval else max_approval
    # gg

    """Give an exchange/router max approval of a token."""
    # TODO: now it works only for rubic
    #  change rubic_abi to erc20_abi
    rubic_abi = get_abi_by_filename("rubic_token.json")
    contract = w3.eth.contract(address=token, abi=rubic_abi)
    function = contract.functions.approve(
        contract_address, max_approval
    )

    tx = build_and_send_tx(function)
    print("yep")
    w3.eth.waitForTransactionReceipt(tx, timeout=6000)
    print("success")
    # Add extra sleep to let tx propogate correctly
    time.sleep(1)


def is_approved(token: AddressLike) -> bool:
    """Check to see if the exchange and token is approved."""
    # gg
    max_approval_check_hex = f"0x{15 * '0'}{49 * 'f'}"
    max_approval_check_int = int(max_approval_check_hex, 16)
    # gg

    validate_address(token)
    contract_addr = UNISWAP_ROUTER02_ADDRESS
    amount = (
        get_erc20_contract(token).functions
        .allowance(WALLET_ADDRESS, contract_addr)
        .call()
    )
    if amount >= max_approval_check_int:
        return True
    else:
        return False


#----------расчет кол-ва токенов на отправку-------------
def get_eth_token_output_price(
        quantity_in_wei: int,
        token_address: AddressLike,
) -> Wei:

    """Public price for ETH to token trades with an exact output."""
    abi = get_abi_by_filename("uniswap_router02.json")
    contract = w3.eth.contract(address=UNISWAP_ROUTER02_ADDRESS, abi=abi)
    # function_get_price = contract.get_function_by_name("getAmountsIn")
    print("token_address: ", token_address, "quantity_in_wei: ", quantity_in_wei)
    price = contract.functions.getAmountsIn(
        quantity_in_wei, [get_weth_address(), token_address]
    ).call()[0]
    return price


def get_token_eth_output_price(
        token_address: AddressLike,
        quantity_in_wei: Wei
) -> int:
    """
        Public price for token to ETH trades with an exact output.
    """
    # Если зотим получить на выходе 1 эфир то нужно закинуть не менее output рубиков

    abi = get_abi_by_filename("uniswap_router02.json")
    contract = w3.eth.contract(address=UNISWAP_ROUTER02_ADDRESS, abi=abi)

    price = contract.functions.getAmountsIn(
        quantity_in_wei, [token_address, get_weth_address()]
    ).call()[0]

    return price


#----------обмен высчитанных токенов------------------
def get_tx_params(value: Wei = Wei(0), gas: Wei = Wei(250000)) -> TxParams:
    """Get generic transaction parameters."""
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
    eth_qty = get_eth_token_output_price(quantity_in_wei=qty, token_address=output_token)

    # get swap function from contract
    router_abi = get_abi_by_filename("uniswap_router02.json")
    router_contract = w3.eth.contract(address=UNISWAP_ROUTER02_ADDRESS, abi=router_abi)
    swap_func = router_contract.functions.swapETHForExactTokens

    return build_and_send_tx(
        swap_func(
            qty,
            [get_weth_address(), RUBIC_ADDRESS],
            recipient,
            deadline(),
        ),
        get_tx_params(eth_qty),
    )


def token_to_eth_swap_output(
    input_token: AddressLike, qty: Wei
) -> HexBytes:
    """
        Convert tokens to ETH given an output amount.
    """
    cost = get_token_eth_output_price(input_token, qty)
    max_tokens = int((1 + MAX_SLIPPAGE) * cost)

    router_abi = get_abi_by_filename("uniswap_router02.json")
    router_contract = w3.eth.contract(address=UNISWAP_ROUTER02_ADDRESS, abi=router_abi)

    swap_func = router_contract.functions.swapTokensForExactETH

    return build_and_send_tx(
        swap_func(
            qty,
            max_tokens,
            [input_token, get_weth_address()],
            WALLET_ADDRESS,
            deadline(),
        ),
    )


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
    print(signed_txn.rawTransaction)
    # !--- Commented for test.
    # return w3.eth.sendRawTransaction(signed_txn.rawTransaction)
    # ---


def get_weth_address() -> ChecksumAddress:
    # Contract calls should always return checksummed addresses

    router_abi = get_abi_by_filename("uniswap_router02.json")
    router_contract = w3.eth.contract(address=UNISWAP_ROUTER02_ADDRESS, abi=router_abi)

    address: ChecksumAddress = router_contract.functions.WETH().call()
    return address
