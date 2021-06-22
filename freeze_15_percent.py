import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lastwill.settings')
import django
django.setup()

import base58
from ethereum import abi
from threading import Timer
from subprocess import Popen, PIPE
from tronapi import Tron

from lastwill.payments.models import *
from lastwill.settings import FREEZE_THRESHOLD_EOSISH, FREEZE_THRESHOLD_WISH, FREEZE_THRESHOLD_BWISH, MYWISH_ADDRESS, \
    NETWORK_SIGN_TRANSACTION_WISH, NETWORK_SIGN_TRANSACTION_EOSISH, NETWORK_SIGN_TRANSACTION_BWISH, COLD_TOKEN_SYMBOL_EOS, COLD_TOKEN_SYMBOL_BNB
from lastwill.settings import COLD_EOSISH_ADDRESS, COLD_WISH_ADDRESS,UPDATE_EOSISH_ADDRESS, UPDATE_WISH_ADDRESS, EOS_ATTEMPTS_COUNT, CLEOS_TIME_COOLDOWN, CLEOS_TIME_LIMIT, EOS_COLD_ABI
from lastwill.settings import COLD_TRON_ADDRESS, UPDATE_TRON_ADDRESS, TRON_COLD_PASSWORD, TRON_ADDRESS, FREEZE_THRESHOLD_TRONISH
from lastwill.settings import BINANCE_PAYMENT_PASSWORD, COLD_BNB_ADDRESS
from lastwill.contracts.models import unlock_eos_account
from lastwill.contracts.submodels.common import *
from lastwill.contracts.submodels.tron import instantiate_tronapi
from lastwill.json_templates import get_freeze_wish_abi
from lastwill.consts import NET_DECIMALS

from django.core.mail import send_mail, EmailMessage
from lastwill.settings import DEFAULT_FROM_EMAIL, SUPPORT_EMAIL
from email_messages import freeze_15_failed_subject, freeze_15_failed_message
from ethereum.abi import encode_abi
from binance_chain.messages import TransferMsg
from binance_chain.wallet import Wallet
from binance_chain.http import HttpApiClient
from binance_chain.environment import BinanceEnvironment


def convert_address_to_hex(address):
    # short_addresss = address[1:]
    decode_address = base58.b58decode(address)[1:21]
    hex_address = binascii.hexlify(decode_address)
    hex_address = '41' + hex_address.decode("utf-8")
    return hex_address


def freeze_wish(amount):
    abi_dict = get_freeze_wish_abi()
    tr = abi.ContractTranslator(abi_dict)
    eth_int = EthereumProvider().get_provider(network=NETWORK_SIGN_TRANSACTION_WISH)
    nonce = int(eth_int.eth_getTransactionCount(UPDATE_WISH_ADDRESS, "pending"), 16)
    signed_data = sign_transaction(
        UPDATE_WISH_ADDRESS, nonce,
        100000,
        NETWORK_SIGN_TRANSACTION_WISH,
        dest=MYWISH_ADDRESS,
        contract_data=binascii.hexlify(
            tr.encode_function_call('transfer', [COLD_WISH_ADDRESS, int(amount)])
        ).decode()

    )
    tx_hash = eth_int.eth_sendRawTransaction(
      '0x' + signed_data
    )
    print('tx_hash=', tx_hash, flush=True)


def freeze_eosish(amount):
    wallet_name = NETWORKS[NETWORK_SIGN_TRANSACTION_EOSISH]['wallet']
    password = NETWORKS[NETWORK_SIGN_TRANSACTION_EOSISH]['eos_password']
    unlock_eos_account(wallet_name, password)
    eos_url = 'https://%s' % (
      str(NETWORKS[NETWORK_SIGN_TRANSACTION_EOSISH]['host']))
    amount_with_decimals = (
            str(amount)[0:len(str(amount))-4]
            + '.0000'
    )
    command_list = [
        'cleos', '-u', eos_url, 'push', 'action', EOS_COLD_ABI, 'transfer',
        '[ "{address_from}", "{address_to}", "{amount} {token_name}", "m" ]'.format(
            address_from=UPDATE_EOSISH_ADDRESS,
            address_to=COLD_EOSISH_ADDRESS,
            amount=amount_with_decimals,
            token_name=COLD_TOKEN_SYMBOL_EOS
        ),
        '-p', UPDATE_EOSISH_ADDRESS
    ]
    print('commend list=', command_list, flush=True)
    for attempt in range(EOS_ATTEMPTS_COUNT):
      print('attempt', attempt, flush=True)
      proc = Popen(command_list, stdin=PIPE, stdout=PIPE, stderr=PIPE)
      timer = Timer(CLEOS_TIME_LIMIT, proc.kill)
      try:
        timer.start()
        stdout, stderr = proc.communicate()
      finally:
        timer.cancel()
      result = stdout.decode()
      if result:
        break
      time.sleep(CLEOS_TIME_COOLDOWN)
    else:
      print('stderr', stderr, flush=True)
      raise Exception(
        'cannot make tx with %i attempts' % EOS_ATTEMPTS_COUNT)
    print('result', result, flush=True)


def freeze_tronish():
    print('freeze tronish', flush=True)
    tron = instantiate_tronapi(pk=TRON_COLD_PASSWORD, net='TRON_MAINNET')

    params = [
        {'type': 'address', 'value': tron.address.to_hex(COLD_TRON_ADDRESS)},
        {'type': 'int256', 'value': 450 * NET_DECIMALS['TRONISH']}
    ]

    tx_builder = tron.transaction_builder.trigger_smart_contract(
            contract_address=tron.address.to_hex(TRON_ADDRESS),
            function_selector='transfer(address,uint256)',
            fee_limit=1000000000,
            call_value=0,
            parameters=params,
    )

    print('building tx: ', tx_builder, flush=True)
    tx = None
    if tx_builder['result']['result'] is True:
        tx = tx_builder['transaction']
    else:
        raise Exception('tx building error in tronish freeze')

    signed_tx = tron.trx.sign(tx)
    print('signed tx: ', signed_tx, flush=True)
    result = tron.trx.broadcast(signed_tx)
    print('result: ', result, flush=True)
    if result['result'] is True:
        print('freeze tronish ok', flush=True)
        print('tx: ', result['transaction'], flush=True)
        return
    else:
        print('freeze failed', flush=True)
        print('res: ', result, flush=True)
        raise Exception('error in broadcasting')


def freeze_bnb_wish(amount):
    freeze_env = BinanceEnvironment.get_production_env()
    if NETWORK_SIGN_TRANSACTION_BWISH == 'testnet':
        freeze_env = BinanceEnvironment.get_testnet_env()

    client = HttpApiClient(env=freeze_env)
    bep_wallet = Wallet(BINANCE_PAYMENT_PASSWORD, env=freeze_env)  # from settings
    value = float(amount / 10 ** 18)
    freeze_msg = TransferMsg(
            wallet=bep_wallet,
            symbol=COLD_TOKEN_SYMBOL_BNB,
            amount=value,
            to_address=COLD_BNB_ADDRESS,
            memo='freeze bnb wish'
    )
    res = client.broadcast_msg(freeze_msg, sync=True)
    print('result', res, flush=True)
    if not res[0]['ok']:
        raise Exception('cannot make bnb wish freeze tx')


def check_payments():
    global attempt
    freeze_balance = FreezeBalance.objects.all().first()
    # if freeze_balance.wish > FREEZE_THRESHOLD_WISH:
    #     try:
    #         #freeze_wish(freeze_balance.wish)
    #         freeze_bnb_wish(freeze_balance.wish)
    #         freeze_balance.wish = 0
    #         freeze_balance.save()
    #     except Exception as e:
    #         attempt += 1
    #         print(e)
    #         print('Freezing WISH failed')
    #         send_mail_attempt("WISH", freeze_balance.wish, e)
    if freeze_balance.eosish > FREEZE_THRESHOLD_EOSISH:
        try:
            freeze_eosish(freeze_balance.eosish)
            freeze_balance.eosish = 0
            freeze_balance.save()
        except Exception as e:
            attempt += 1
            print(e)
            print('Freezing EOSISH failed')
            send_mail_attempt("EOSISH", freeze_balance.eosish, e)
    if freeze_balance.tronish >= FREEZE_THRESHOLD_TRONISH:  # 450000000
        print('tronish > 0', flush=True)
        try:
            print('try send tronish', flush=True)
            freeze_tronish()
            freeze_balance.tronish = freeze_balance.tronish - FREEZE_THRESHOLD_TRONISH
            freeze_balance.save()
        except Exception as e:
            attempt += 1
            print(e, flush=True)
            print('Freezing TRONISH failed')
            send_mail_attempt("TRONISH", freeze_balance.tronish, e)
    if freeze_balance.bwish > FREEZE_THRESHOLD_BWISH:
        try:
            print('try send bnb wish',flush=True)
            freeze_bnb_wish(freeze_balance.bwish)
            freeze_balance.bwish = 0
            freeze_balance.save()
        except Exception as e:
            attempt += 1
            print(e, flush=True)
            print("Freezing BNB WISH failed")
            send_mail_attempt("BWISH", freeze_balance.bwish, e)


def send_failed_freezing(token, balance, trace):
    check_address = 'ETH addresses'

    if token == 'EOSISH':
        check_address = 'EOS accounts'
    if token == 'TRONISH':
        check_address = 'TRON addresses'
    if token == 'BWISH':
        check_address = 'BNB WISH payment address'

    mail = EmailMessage(
        subject=freeze_15_failed_subject,
        body=freeze_15_failed_message.format(
            token_type=token,
            address_type=check_address,
            tx_balance=balance,
            traceback=trace
        ),
        from_email=DEFAULT_FROM_EMAIL,
        to=SUPPORT_EMAIL
    )
    mail.send()


def send_mail_attempt(token, balance, trace):
    global attempt
    if attempt >= 100:
        send_failed_freezing(token, balance, trace)
        attempt = 0


if __name__ == '__main__':
    attempt = 0
    while 1:
        print('-' * 50)
        check_payments()
        time.sleep(60 * 10)
