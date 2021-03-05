import logging
from typing import Union

from django.db.models.query import QuerySet
from django.db.models import Q, F

from lastwill.consts import ETH_ADDRESS, NET_DECIMALS
from lastwill.swaps_common.orderbook.models import OrderBookSwaps
from lastwill.settings_local import (
    WALLET_ADDRESS,
    ORDER_FEE,
    PROFIT_RATIO,
    DEFAULT_ETH_VOLUME,
    DEFAULT_RBC_VOLUME,
)

from .consts import (
    RUBIC_ADDRESS,
    MAINNET_ORDERBOOK_ADDRESS,
    MAINNET_ORDERBOOK_ABI,

    DEFAULT_NETWORK_ID,
    DEFAULT_GAS_LIMIT,
)
from .etherscan import get_gas_price
from .uniswap import (
    HexBytes,

    approve,
    build_and_send_tx,
    is_approved,
    eth_to_token_swap_output,
    get_eth_balance,
    get_eth_token_output_price,
    _get_rbc_eth_ratio,
    get_token_eth_output_price,
    load_contract,
    token_to_eth_swap_output,

    AddressLike,
    Wei,
    w3,
)

ETH_DECIMALS = NET_DECIMALS.get('ETH', 10 ** 18)
RBC_DECIMALS = NET_DECIMALS.get('RBC', ETH_DECIMALS)


def _get_active_orders():
    """
    Returns public active orders.
    """
    return OrderBookSwaps.public_active_orders.all()


def _get_matching_orders(
    queryset: QuerySet,
    base_token_address,
    quote_token_address,
    network,
    contract_address,
    max_eth_value,
    max_token_value,
):
    """
    Returns orders filtered by the amount.
    """

    _set_base_amount_contributed(queryset)

    logging.info(
        'Total public and active orders: {}'.format(
            queryset.count()
        )
    )

    return queryset.filter(
        Q(
            network=network,
            contract_address=contract_address,
            base_address=base_token_address,
            base_limit__lte=max_eth_value,
            base_amount_contributed=F('base_limit') * ETH_DECIMALS,
            quote_address=quote_token_address,
            is_closed_by_limiter=False,
        ) |
        Q(
            network=network,
            contract_address=contract_address,
            base_address=quote_token_address,
            base_limit__lte=max_token_value,
            base_amount_contributed=F('base_limit') * ETH_DECIMALS,
            quote_address=base_token_address,
            is_closed_by_limiter=False,
        )
    )


def _get_profitability_order(
    base_token_address,
    quote_token_address,
    network_id,
    contract_address,
    max_eth_volume,
    max_token_volume,
):
    """

    """
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

    # TODO: переименовать под более подхдящее имя, потому что в сделках могут
    # участвовать не только эфир и рубик.


    active_eth_rbc_orders = _get_matching_orders(
        queryset=_get_active_orders(),
        base_token_address=base_token_address.lower(),
        quote_token_address=quote_token_address.lower(),
        network=network_id,
        contract_address=contract_address.lower(),
        # TODO: передать предельную сумму в эфире (до 5 включительно)
        # и обмениваемого токена эквивателнтного до 5 эфира по текущему курсу.
        max_eth_value=max_eth_volume,
        max_token_value=max_token_volume,
    )

    # active_eth_rbc_orders = OrderBookSwaps.objects.filter(unique_link='81dppt')

    matching_order_count = active_eth_rbc_orders.count()

    profitable_orders = []
    result = {
        'total': matching_order_count,
        'profitable_orders': 0,
    }

    if active_eth_rbc_orders.exists():
        logging.info(
            f'Matching orders have been found is: {matching_order_count}.'
        )
        rbc_eth_ratio = _get_rbc_eth_ratio(RUBIC_ADDRESS)
        gas_fee = get_gas_price() * int(DEFAULT_GAS_LIMIT)

        for _, order in enumerate(active_eth_rbc_orders):
            if (
                order.base_address == base_token_address.lower() and
                order.quote_address == quote_token_address.lower()
            ):
                if not _check_profitability(
                    exchange_rate=rbc_eth_ratio,
                    gas_fee=gas_fee,
                    eth_value=float(order.base_limit),
                    rbc_value=float(order.quote_limit),
                    is_rbc=True
                ):
                    # print(f'{counter}. NOUP...')
                    continue

                # print(f'{counter}. YEP!')
                result['profitable_orders'] += 1
                profitable_orders.append(order.id)

                _hide_order(order)
            elif (
                order.base_address == quote_token_address.lower() and
                order.quote_address == base_token_address.lower()
            ):
                if not _check_profitability(
                    exchange_rate=rbc_eth_ratio,
                    gas_fee=gas_fee,
                    rbc_value=float(order.base_limit),
                    eth_value=float(order.quote_limit),
                    is_rbc=False
                ):
                    # print(f'{counter}. NOUP...')
                    continue

                # print(f'{counter}. YEP!')
                result['profitable_orders'] += 1
                profitable_orders.append(order.id)

                _hide_order(order)
            else:
                continue

        logging.info(result)

        return active_eth_rbc_orders.filter(id__in=profitable_orders)

    logging.info('No active "ETH <> RBC" or "RBC <> ETH" orders yet.')

    return 0


def _hide_order(order: QuerySet):
    """
    Changes order visiblity to False.
    """
    order.is_displayed = False
    order.save()

    return 1


def _set_done_status_order(order: QuerySet):
    """
    Changes order visibility to True and state to 'done'.
    # TODO: done by order limiter
    """
    order.state = OrderBookSwaps.STATE_DONE
    order.is_closed_by_limiter = True
    order.is_displayed = True
    order.save()

    return 1


def _check_profitability_eth_to_token(
    exchange_rate: float,
    gas_fee: float,
    rbc_value: float,
    eth_value: float,
    is_rbc: bool = True
):
    if not is_rbc:
        is_rbc = -1
    else:
        is_rbc = int(is_rbc)
    # eth_value and rbc_value in RBC
    # (eth_value - rbc_value) is diff in RBC token
    profitability = is_rbc * (eth_value - rbc_value) * exchange_rate * \
    ETH_DECIMALS + (ORDER_FEE * ETH_DECIMALS) - gas_fee - (PROFIT_RATIO * \
    ETH_DECIMALS)

    if profitability > 0:
        return True
    else:
        return False


def _check_profitability(
    exchange_rate: float,
    gas_fee: float,
    rbc_value: float,
    eth_value: float,
    is_rbc: bool = True
):
    # profit_coeff - value in ETH showing the minimum profit for which a transaction can be carried out
    """
    Calculate profit for active orderbook. Returns True if order is
    profitable or False if it isn't.

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

    Finally we get:
    is_rbc * ((eth_value - rbc_value * exchange_rate) * ETH_DECIMALS) - gas_fee - (PROFIT_RATIO * ETH_DECIMALS) + ORDER_FEE > 0 - it's profit

    Input data: rbc/eth exchange rate, gasPrice,
        orderbook's value of eth and rbc, isRBC
    Output data: True if profit, False if not.
    """
    if not is_rbc:
        is_rbc = -1
    else:
        is_rbc = int(is_rbc)

    profitability = is_rbc * (eth_value - rbc_value * exchange_rate) * \
    ETH_DECIMALS + (ORDER_FEE * ETH_DECIMALS) - gas_fee - (PROFIT_RATIO * \
    ETH_DECIMALS)

    if profitability > 0:
        return True
    else:
        return False


def swap_token_on_uniswap(
    order: QuerySet,
    input_token: AddressLike,
    output_token: AddressLike,
    qty: Union[int, Wei],
    recipient: AddressLike = None,
) -> HexBytes:
    """
    Make a trade by defining the qty of the output token.
    Input is address of swapped tokens and exact amount of output token.
    """
    # TODO: now it works only for ETH->TOKEN and TOKEN->ETH swaps
    #  needed to add TOKEN->TOKEN swap ability
    if not is_approved(RUBIC_ADDRESS):
        approve(RUBIC_ADDRESS)
    # ---

    if input_token == w3.toChecksumAddress(ETH_ADDRESS):
        logging.info('if input token is native ETH')
        balance = get_eth_balance(WALLET_ADDRESS)
        logging.info('balance')
        need = get_eth_token_output_price(
            token_address=output_token,
            quantity_in_wei=qty
        )
        logging.info("balance: {}\nneed: {}".format(balance, need))

        if balance < need:
            logging.info('balance < need is TRUE')
            # TODO: add logging "not enough eth token"
            pass
        else:
            logging.info('balance < need is FALSE')

            eth_to_token_swap_output(output_token, qty, recipient)

            order.swaped_on_uniswap = True
            order.save()

            return 1

    elif output_token == w3.toChecksumAddress(ETH_ADDRESS):
        logging.info('if output token is ETH token')
        # balance = get_rbc_balance(WALLET_ADDRESS)
        # need = get_token_eth_output_price(output_token, qty)
        # if balance < need:
        #     # TODO: add logging "not enough eth token"
        #     pass
        # else:
        qty = Wei(qty)

        token_to_eth_swap_output(input_token, qty)

        order.swaped_on_uniswap = True
        order.save()

        return 1

    return 0


def _confirm_orders(
    orders: QuerySet,
    base_token_address,
    quote_token_address
):
    """
    make transaction great again!
    """
    eth_to_rbc_orders = orders.filter(base_address=base_token_address.lower())
    rbc_to_eth_orders = orders.filter(base_address=quote_token_address.lower())

    # TODO: Надо паралеллить?
    for _, order in enumerate(eth_to_rbc_orders):
        # RBC -> ETH
        if not _check_base_amount_contribute(order):
            continue

        rbc_eth_ratio = get_eth_token_output_price(
            int(order.quote_limit * ETH_DECIMALS),
            RUBIC_ADDRESS,
        )
        gas_fee = get_gas_price() * int(DEFAULT_GAS_LIMIT)

        if _check_profitability(
            rbc_eth_ratio / ETH_DECIMALS,
            gas_fee,
            eth_value=float(order.base_limit),
            # TODO: Need fix. "rbc_eth_ratio / ETH_DECIMALS" is RBC # qty in ETH value.
            # rbc_value=float(order.quote_limit),
            # ---
            rbc_value=1,
            is_rbc=True
        ):
            if not order.swaped_on_uniswap:
                swap_token_on_uniswap(
                    order=order,
                    input_token=w3.toChecksumAddress(order.base_address),
                    output_token=w3.toChecksumAddress(order.quote_address),
                    qty=int(order.quote_limit * ETH_DECIMALS),
                )

            _complete_order(order)

    for _, order in enumerate(rbc_to_eth_orders):
        # ETH -> RBC
        if not _check_base_amount_contribute(order):
            continue

        # !--- TODO: needs refactor.
        eth_rbc_ratio = get_token_eth_output_price(
            int(order.quote_limit * ETH_DECIMALS),
            RUBIC_ADDRESS,
        )  # Returns RBC token, not ETH.
        # eth_rbc_ratio = eth_rbc_ratio * get_rbc_eth_ratio_uniswap()
        # ---
        gas_fee = get_gas_price() * int(DEFAULT_GAS_LIMIT)

        if _check_profitability_eth_to_token(
            _get_rbc_eth_ratio(RUBIC_ADDRESS),
            gas_fee,
            rbc_value=float(order.base_limit),
            eth_value=eth_rbc_ratio / ETH_DECIMALS,
            is_rbc=False

        ):
            if not order.swaped_on_uniswap:
                swap_token_on_uniswap(
                    order=order,
                    input_token=w3.toChecksumAddress(order.base_address),
                    output_token=w3.toChecksumAddress(order.quote_address),
                    qty=int(order.quote_limit * ETH_DECIMALS),
                )

            _complete_order(order)


def _complete_order(order: QuerySet = None):
    """
    Sends tokens to contract address.
    """
    logging.info('_complete_order_func')
    # approve tokens (build tx, sign tx, send tx)
    # timeout
    # func call
    # build tx
    # sign tx
    # send tx

    # TEST_HASH = '0x79bd92a8d9b27eac4dc52d7b5aef67e97534868f7b9797018f9805d8ab863a44'
    # TEST_AMOUNT = float('1422.32415256')

    orderbook_contract = load_contract(
        MAINNET_ORDERBOOK_ABI,
        w3.toChecksumAddress(MAINNET_ORDERBOOK_ADDRESS),
    )
    logging.info(orderbook_contract)
    # `deposit`: ['deposit(bytes32,address,uint256)']
    transaction = orderbook_contract.functions.deposit(
        order.memo_contract,
        w3.toChecksumAddress(order.quote_address),
        # w3.toWei(float(order.quote_limit), unit='ether'),
        _get_quote_limit(order),
    )
    logging.info(
        '\nOrder memo: {}\nOrder qoute address: {}\nOrder quote limit: {}'.format(
            order.memo_contract,
            w3.toChecksumAddress(order.quote_address),
            w3.toWei(float(order.quote_limit), unit='ether'),
        )
    )
    tx_config = {
        "from": w3.toChecksumAddress(WALLET_ADDRESS),
        "gas": DEFAULT_GAS_LIMIT,
        'gasPrice': w3.eth.gasPrice,
        "nonce": w3.eth.getTransactionCount(WALLET_ADDRESS),
    }

    if order.quote_address == ETH_ADDRESS:
        tx_config.update(
            {"value": w3.toWei(float(order.quote_limit), unit='ether'),}
        )

    logging.info(tx_config)
    sended_transaction = build_and_send_tx(
        transaction,
        tx_params=tx_config
    )
    logging.info(sended_transaction)
    result = w3.eth.waitForTransactionReceipt(
        sended_transaction,
        timeout=600
    )
    # logging.info(result)

    if result:
        _set_done_status_order(order)

    return 1


def main(
    base_token_address=ETH_ADDRESS,
    quote_token_address=RUBIC_ADDRESS,
    network_id=DEFAULT_NETWORK_ID,
    contract_address=MAINNET_ORDERBOOK_ADDRESS,
    max_eth_volume=DEFAULT_ETH_VOLUME,
    max_token_volume=DEFAULT_RBC_VOLUME
):
    """
    Fill me.
    """
    # Получили все подходящие сделки.
    # Разбили на два набора: из 1 во 2, и из 2 во 1.
    # Отправили два набора сделок на выполнение (надо распаралеллить?).

    orders = _get_profitability_order(
        base_token_address=base_token_address,
        quote_token_address=quote_token_address,
        network_id=network_id,
        contract_address=contract_address,
        max_eth_volume=max_eth_volume,
        max_token_volume=max_token_volume,
    )

    if not orders:
        return 0

    logging.info(orders.only('unique_link').values())

    _confirm_orders(
        orders,
        base_token_address,
        quote_token_address
    )

    return 1


def _get_quote_limit(order:QuerySet):
    """
    Returns order's qoute limit from contract.
    """
    order_hash = order.memo_contract
    orderbook_contract = load_contract(
        MAINNET_ORDERBOOK_ABI,
        w3.toChecksumAddress(MAINNET_ORDERBOOK_ADDRESS),
    )
    order_qoute_limit =  orderbook_contract.functions.quoteLimit(
        order_hash
    ).call()

    logging.info('order_qoute_limit: {}'.format(order_qoute_limit))

    return order_qoute_limit


def _check_base_amount_contribute(order:QuerySet):
    """
    Проверяет заполненность левой стороны.

    Если левая сторона в следке заполнена:
     - в БД заполняется base_amout_contributed
     - сделка допускается для complete_order, возвращается 1
    Если не заполнена:
     - возвращается 0
    """
    order_hash = order.memo_contract
    orderbook_contract = load_contract(
        MAINNET_ORDERBOOK_ABI,
        w3.toChecksumAddress(MAINNET_ORDERBOOK_ADDRESS),
    )
    order_is_swaped = orderbook_contract.functions.isSwapped(
        order_hash
    ).call()

    logging.info('order_is_swaped: {}'.format(order_is_swaped))

    if not order_is_swaped:
        order_is_base_filled = orderbook_contract.functions.isBaseFilled(
            order_hash
        ).call()

        logging.info('order_is_base_filled: {}'.format(order_is_base_filled))

        if order_is_base_filled:
            return 1

        # order_is_base_raised = orderbook_contract.functions.baseRaised(
        #     order_hash
        # ).call()

        # order.base_amount_contributed = order_is_base_raised
        # order.save()

    return 0


def _set_base_amount_contributed(orders:QuerySet):
    """
    Sets base amount contributed in orders.
    """

    logging.info(
        'Total non-base-amount-contributed orders: {}'.format(orders.count())
    )

    try:
        orderbook_contract = load_contract(
            MAINNET_ORDERBOOK_ABI,
            w3.toChecksumAddress(MAINNET_ORDERBOOK_ADDRESS),
        )

        for counter, order in enumerate(orders):
            order_hash = order.memo_contract
            order_is_base_raised = orderbook_contract.functions.baseRaised(
                order_hash
            ).call()

            order.base_amount_contributed = order_is_base_raised
            order.save()

            logging.info(
                '{}. Order updated: {}'.format(counter, order.id)
            )
    except Exception as exception_error:
        logging.error('Exception: {}'.format(exception_error))

        return 0

    return 1


# def check_tx_success(self, tx):
#     try:
#         receipt = self.web3interface.eth.getTransactionReceipt(tx)
#         if receipt['status'] == 1:
#             return True
#         else:
#             return False
#     except TransactionNotFound:
#         return False

# def check_tx_on_retry(self, tx):
#     retries = 0
#     tx_found = False

#     print('Checking transaction until found in network', flush=True)
#     while retries <= 15:
#         tx_found = self.check_tx_success(tx)
#         if tx_found:
#             print('Ok, found transaction and it was completed', flush=True)
#             return True
#         else:
#             time.sleep(10)

#     if not tx_found:
#         print('Transaction receipt not found in 150 seconds. Supposedly it failed, please check hash on Etherscan',
#                 flush=True
#                 )
#         print('Stopping init for now', flush=True)
#         return False
