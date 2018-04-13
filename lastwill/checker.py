from ethereum import abi
import binascii
import datetime
from django.utils import timezone
from django.core.mail import send_mail
from lastwill.contracts.models import Contract, blocking
from lastwill.parint import *
from lastwill.settings import SIGNER, DEFAULT_FROM_EMAIL
import email_messages


def check_one(contract):
    # print('checking', contract.name)
    # tr = abi.ContractTranslator(contract.get_details().eth_contract.abi)
    # par_int = ParInt()
    # address = contract.network.deployaddress_set.all()[0].address
    # nonce = int(par_int.parity_nextNonce(address), 16)
    # print('nonce', nonce)
    # response = json.loads(requests.post('http://{}/sign/'.format(SIGNER), json={
    #         'source' : contract.owner_address,
    #         'data': binascii.hexlify(tr.encode_function_call('check', [])).decode(),
    #         'nonce': nonce,
    #         'dest': contract.address,
    #         'value': int(0.005 * 10 ** 18),
    #         'gaslimit': 300000,
    # }).content.decode())
    # print('response', response)
    # signed_data = response['result']
    # print('signed_data', signed_data)
    # par_int.eth_sendRawTransaction('0x'+signed_data)
    # print('check ok!')
    contract.get_details().check_contract()


def check_all():
    print('check_all method')
    for contract in Contract.objects.filter(contract_type__in=(0,1,4)):
       if contract.next_check:
           if contract.next_check <= timezone.now():
            check_one(contract)
       send_reminders(contract)
       carry_out_lastwillcontract(contract)


def send_reminders(contract):
    if contract.contract_type == 0:
        details = contract.get_details()
        if contract.state == 'ACTIVE' and contract.user.email:
            if details.next_check:
                now = timezone.now()
                delta = details.next_check - now
                if delta.days <= 1:
                    send_mail(
                        email_messages.remind_subject,
                        email_messages.remind_message.format(days=1),
                        DEFAULT_FROM_EMAIL,
                        [contract.user.email]
                    )
                elif delta.days == 5:
                    send_mail(
                        email_messages.remind_subject,
                        email_messages.remind_message.format(days=5),
                        DEFAULT_FROM_EMAIL,
                        [contract.user.email]
                    )
                elif delta.days == 10:
                    send_mail(
                        email_messages.remind_subject,
                        email_messages.remind_message.format(days=10),
                        DEFAULT_FROM_EMAIL,
                        [contract.user.email]
                    )


def carry_out_lastwillcontract(contract):
    if contract.contract_type == 0:
        details = contract.get_details()
        if contract.state == 'ACTIVE' and contract.user.email:
            if details.next_check:
                now = timezone.now()
                delta = details.next_check - now
                if delta.days < -1:
                    contract.state = 'ENDED'
                    contract.save()
                    send_mail(
                        email_messages.carry_out_subject,
                        email_messages.carry_out_message,
                        DEFAULT_FROM_EMAIL,
                        [contract.user.email]
                    )
