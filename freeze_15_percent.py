import os
from ethereum import abi
from threading import Timer
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lastwill.settings')
import django
django.setup()

from lastwill.payments.models import *
from lastwill.settings import FREEZE_THRESHOLD_EOSISH, FREEZE_THRESHOLD_WISH, MYWISH_ADDRESS, NETWORK_SIGN_TRANSACTION_WISH, NETWORK_SIGN_TRANSACTION_EOSISH, COLD_TOKEN_SYMBOL
from lastwill.settings import COLD_EOSISH_ADDRESS, COLD_WISH_ADDRESS,UPDATE_EOSISH_ADDRESS, UPDATE_WISH_ADDRESS, EOS_ATTEMPTS_COUNT, CLEOS_TIME_COOLDOWN, CLEOS_TIME_LIMIT
from lastwill.contracts.models import unlock_eos_account
from lastwill.contracts.submodels.common import *
from lastwill.json_templates import get_freeze_wish_abi


def freeze_wish(amount):
    abi_dict = get_freeze_wish_abi()
    tr = abi.ContractTranslator(abi_dict)
    par_int = ParInt(NETWORK_SIGN_TRANSACTION_WISH)
    nonce = int(par_int.eth_getTransactionCount(UPDATE_WISH_ADDRESS, "pending"), 16)
    signed_data = sign_transaction(
      UPDATE_WISH_ADDRESS, nonce,
      100000,
      NETWORK_SIGN_TRANSACTION_WISH,
      dest=MYWISH_ADDRESS,
      contract_data=binascii.hexlify(
        tr.encode_function_call('transfer', [COLD_WISH_ADDRESS, int(amount)])
      ).decode()
    )
    tx_hash = par_int.eth_sendRawTransaction(
      '0x' + signed_data
    )
    print('tx_hash=', tx_hash, flush=True)


def freeze_eosish(amount):
    wallet_name = NETWORKS[NETWORK_SIGN_TRANSACTION_EOSISH]['wallet']
    password = NETWORKS[NETWORK_SIGN_TRANSACTION_EOSISH]['eos_password']
    unlock_eos_account(wallet_name, password)
    eos_url = 'http://%s:%s' % (
      str(NETWORKS[NETWORK_SIGN_TRANSACTION_EOSISH]['host']),
      str(NETWORKS[NETWORK_SIGN_TRANSACTION_EOSISH]['port']))
    amount_with_decimals = (
            str(amount)[0:len(str(amount))-4]
            + '.0000'
    )
    command_list = [
        'cleos', '-u', eos_url, 'push', 'action', 'buildertoken', 'transfer',
        '[ "{address_from}", "{address_to}", "{amount} {token_name}", "m" ]'.format(
            address_from=UPDATE_EOSISH_ADDRESS,
            address_to=COLD_EOSISH_ADDRESS,
            amount=amount_with_decimals,
            token_name=COLD_TOKEN_SYMBOL
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


def check_payments():
    freeze_balance = FreezeBalance.objects.all().first()
    if freeze_balance.wish > FREEZE_THRESHOLD_WISH:
        freeze_wish(freeze_balance.wish)
        freeze_balance.wish = 0
        freeze_balance.save()
    if freeze_balance.eosish > FREEZE_THRESHOLD_EOSISH:
      freeze_eosish(freeze_balance.eosish)
      freeze_balance.eosish = 0
      freeze_balance.save()


if __name__ == '__main__':
    while 1:
        check_payments()
        time.sleep(60 * 10)
