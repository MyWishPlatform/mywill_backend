import os
import base58
from ethereum import abi
from threading import Timer
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lastwill.settings')
import django
django.setup()

from lastwill.payments.models import *
from lastwill.settings import FREEZE_THRESHOLD_EOSISH, FREEZE_THRESHOLD_WISH, MYWISH_ADDRESS, NETWORK_SIGN_TRANSACTION_WISH, NETWORK_SIGN_TRANSACTION_EOSISH, COLD_TOKEN_SYMBOL
from lastwill.settings import COLD_EOSISH_ADDRESS, COLD_WISH_ADDRESS,UPDATE_EOSISH_ADDRESS, UPDATE_WISH_ADDRESS, EOS_ATTEMPTS_COUNT, CLEOS_TIME_COOLDOWN, CLEOS_TIME_LIMIT
from lastwill.settings import COLD_TRON_ADDRESS, UPDATE_TRON_ADDRESS, TRON_COLD_PASSWORD, TRON_ADDRESS
from lastwill.contracts.models import unlock_eos_account
from lastwill.contracts.submodels.common import *
from lastwill.json_templates import get_freeze_wish_abi

from django.core.mail import send_mail, EmailMessage
from lastwill.settings import DEFAULT_FROM_EMAIL, SUPPORT_EMAIL
from email_messages import freeze_15_failed_subject, freeze_15_failed_message
from ethereum.abi import encode_abi

def convert_address_to_hex(address):
    # short_addresss = address[1:]
    decode_address = base58.b58decode(address)[1:21]
    hex_address = binascii.hexlify(decode_address)
    hex_address = '41' + hex_address.decode("utf-8")
    return hex_address


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
    eos_url = 'https://%s' % (
      str(NETWORKS[NETWORK_SIGN_TRANSACTION_EOSISH]['host']))
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


def freeze_tronish(amount):
    print('freeze tronish', flush=True)
    freeze_encoded_parameter = binascii.hexlify(
        encode_abi(['address', 'uint256'], ['0x'+convert_address_to_hex(COLD_TRON_ADDRESS)[2:], amount])
    )
    print('freeze_encoded_parameter', freeze_encoded_parameter, flush=True)
    deploy_params = {
        'contract_address': convert_address_to_hex(TRON_ADDRESS),
        'function_selector': 'transfer(address,uint)',
        'parameter': freeze_encoded_parameter,
        'fee_limit': 1000000000,
        'call_value': 0,
        'owner_address': convert_address_to_hex(UPDATE_TRON_ADDRESS)
    }
    deploy_params = json.dumps(deploy_params)
    print('params', deploy_params, flush=True)
    tron_url = 'http://%s:%s' % (
    str(NETWORKS['TRON_MAINNET']['host']),
    str(NETWORKS['TRON_MAINNET']['port']))
    result = requests.post(tron_url + '/wallet/triggersmartcontract',
                            data=deploy_params)
    print('transaction created', flush=True)
    trx_info1 = json.loads(result.content.decode())
    trx_info1 = {'transaction': trx_info1}
    print('trx info', trx_info1, flush=True)
    trx_info1['privateKey'] = TRON_COLD_PASSWORD
    trx = json.dumps(trx_info1)
    print('before', trx, flush=True)
    result = requests.post(tron_url + '/wallet/gettransactionsign', data=trx)
    print('transaction sign', flush=True)
    trx_info2 = json.loads(result.content.decode())
    trx = json.dumps(trx_info2)
    print('after', trx, flush=True)
    # print(trx)
    for i in range(5):
        print('attempt=', i, flush=True)
        result = requests.post(tron_url + '/wallet/broadcasttransaction',
                               data=trx)
        print(result.content)
        answer = json.loads(result.content.decode())
        print('answer=', answer, flush=True)
        if answer['result']:
                return
        time.sleep(5)
    else:
        raise Exception('cannot make tx with 5 attempts')


def check_payments():
    global attempt
    freeze_balance = FreezeBalance.objects.all().first()
    if freeze_balance.wish > FREEZE_THRESHOLD_WISH:
        try:
            freeze_wish(freeze_balance.wish)
            freeze_balance.wish = 0
            freeze_balance.save()
        except Exception as e:
            attempt += 1
            print(e)
            print('Freezing WISH failed')
            send_mail_attempt("WISH", freeze_balance.wish, e)
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
    if freeze_balance.tronish > 0:
        print('tronish > 0', flush=True)
        try:
            freeze_tronish(freeze_balance.tronish)
            freeze_balance.tronish = 0
            freeze_balance.save()
        except Exception as e:
            attempt += 1
            print(e)
            print('Freezing TRONISH failed')
            send_mail_attempt("WISH", freeze_balance.tronish, e)


def send_failed_freezing(token, balance, trace):
    check_address = "ETH addresses" if token == "WISH" else "EOS accounts"
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
        check_payments()
        time.sleep(60 * 10)
