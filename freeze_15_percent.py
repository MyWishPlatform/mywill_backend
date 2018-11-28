import time
import os
import binascii
from ethereum import abi
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lastwill.settings')
import django
django.setup()

from django.utils import timezone
from lastwill.payments.models import *
from lastwill.settings import FREEZE_THRESHOLD_EOSISH, FREEZE_THRESHOLD_WISH, MYWISH_ADDRESS, NETWORK_SIGN_TRANSACTION_WISH, NETWORK_SIGN_TRANSACTION_EOSISH
from lastwill.settings import COLD_EOSISH_ADDRESS, COLD_WISH_ADDRESS,UPDATE_EOSISH_ADDRESS, UPDATE_WISH_ADDRESS
from lastwill.contracts.models import Contract, implement_cleos_command, unlock_eos_account
from lastwill.contracts.submodels.common import *


def freeze_wish():
    abi_dict = [
  {
    "constant": True,
    "inputs": [],
    "name": "name",
    "outputs": [
      {
        "name": "",
        "type": "string"
      }
    ],
    "payable": False,
    "stateMutability": "view",
    "type": "function"
  },
  {
    "constant": False,
    "inputs": [
      {
        "name": "_spender",
        "type": "address"
      },
      {
        "name": "_value",
        "type": "uint256"
      }
    ],
    "name": "approve",
    "outputs": [
      {
        "name": "",
        "type": "bool"
      }
    ],
    "payable": False,
    "stateMutability": "nonpayable",
    "type": "function"
  },
  {
    "constant": True,
    "inputs": [],
    "name": "totalSupply",
    "outputs": [
      {
        "name": "",
        "type": "uint256"
      }
    ],
    "payable": False,
    "stateMutability": "view",
    "type": "function"
  },
  {
    "constant": False,
    "inputs": [
      {
        "name": "_from",
        "type": "address"
      },
      {
        "name": "_to",
        "type": "address"
      },
      {
        "name": "_value",
        "type": "uint256"
      }
    ],
    "name": "transferFrom",
    "outputs": [
      {
        "name": "",
        "type": "bool"
      }
    ],
    "payable": False,
    "stateMutability": "nonpayable",
    "type": "function"
  },
  {
    "constant": True,
    "inputs": [],
    "name": "decimals",
    "outputs": [
      {
        "name": "",
        "type": "uint8"
      }
    ],
    "payable": False,
    "stateMutability": "view",
    "type": "function"
  },
  {
    "constant": True,
    "inputs": [
      {
        "name": "_owner",
        "type": "address"
      }
    ],
    "name": "balanceOf",
    "outputs": [
      {
        "name": "balance",
        "type": "uint256"
      }
    ],
    "payable": False,
    "stateMutability": "view",
    "type": "function"
  },
  {
    "constant": True,
    "inputs": [],
    "name": "symbol",
    "outputs": [
      {
        "name": "",
        "type": "string"
      }
    ],
    "payable": False,
    "stateMutability": "view",
    "type": "function"
  },
  {
    "constant": False,
    "inputs": [
      {
        "name": "_to",
        "type": "address"
      },
      {
        "name": "_value",
        "type": "uint256"
      }
    ],
    "name": "transfer",
    "outputs": [
      {
        "name": "",
        "type": "bool"
      }
    ],
    "payable": False,
    "stateMutability": "nonpayable",
    "type": "function"
  },
  {
    "constant": True,
    "inputs": [
      {
        "name": "_owner",
        "type": "address"
      },
      {
        "name": "_spender",
        "type": "address"
      }
    ],
    "name": "allowance",
    "outputs": [
      {
        "name": "",
        "type": "uint256"
      }
    ],
    "payable": False,
    "stateMutability": "view",
    "type": "function"
  },
  {
    "payable": True,
    "stateMutability": "payable",
    "type": "fallback"
  },
  {
    "anonymous": False,
    "inputs": [
      {
        "indexed": True,
        "name": "owner",
        "type": "address"
      },
      {
        "indexed": True,
        "name": "spender",
        "type": "address"
      },
      {
        "indexed": False,
        "name": "value",
        "type": "uint256"
      }
    ],
    "name": "Approval",
    "type": "event"
  },
  {
    "anonymous": False,
    "inputs": [
      {
        "indexed": True,
        "name": "from",
        "type": "address"
      },
      {
        "indexed": True,
        "name": "to",
        "type": "address"
      },
      {
        "indexed": False,
        "name": "value",
        "type": "uint256"
      }
    ],
    "name": "Transfer",
    "type": "event"
  }
]
    tr = abi.ContractTranslator(abi_dict)
    par_int = ParInt(NETWORK_SIGN_TRANSACTION_WISH)
    nonce = int(par_int.eth_getTransactionCount(UPDATE_WISH_ADDRESS, "pending"), 16)
    signed_data = sign_transaction(
      UPDATE_WISH_ADDRESS, nonce,
      100000,
      NETWORK_SIGN_TRANSACTION_WISH,
      dest=MYWISH_ADDRESS,
      contract_data=binascii.hexlify(
        tr.encode_function_call('transfer', [COLD_WISH_ADDRESS, FREEZE_THRESHOLD_WISH])
      ).decode()
    )
    tx_hash = par_int.eth_sendRawTransaction(
      '0x' + signed_data
    )
    print('tx_hash=', tx_hash, flush=True)


def freeze_eosish():
    wallet_name = NETWORKS[NETWORK_SIGN_TRANSACTION_EOSISH]['wallet']
    password = NETWORKS[NETWORK_SIGN_TRANSACTION_EOSISH]['eos_password']
    our_public_key = NETWORKS[NETWORK_SIGN_TRANSACTION_EOSISH]['pub']
    # print(wallet_name, password, flush=True)
    unlock_eos_account(wallet_name, password)
    threshold_with_decimals = (
            str(FREEZE_THRESHOLD_EOSISH)[0:len(str(FREEZE_THRESHOLD_EOSISH))-4]
            + '.'
            + str(FREEZE_THRESHOLD_EOSISH)[len(str(FREEZE_THRESHOLD_EOSISH))-4:len(str(FREEZE_THRESHOLD_EOSISH))]
    )
    command_list = [
        'cleos', 'push', 'action', 'eosio.token', 'transfer',
        '[ "{address_from}", "{address_to}", "{amount} TEOSISH" ]'.format(
            address_from=UPDATE_EOSISH_ADDRESS,
            address_to=COLD_EOSISH_ADDRESS,
            amount=threshold_with_decimals
        ),
        '-p', our_public_key
    ]
    result = implement_cleos_command(command_list)
    print('result', result, flush=True)


def check_payments():
    freeze_balance = FreezeBalance.objects.all().first()
    if freeze_balance.eosish > FREEZE_THRESHOLD_EOSISH:
        freeze_eosish()
        freeze_balance.eosish = freeze_balance.eosish - FREEZE_THRESHOLD_EOSISH
        freeze_balance.save()
    if freeze_balance.wish > FREEZE_THRESHOLD_WISH:
        freeze_wish()
        freeze_balance.wish = freeze_balance.wish - FREEZE_THRESHOLD_WISH
        freeze_balance.save()


if __name__ == '__main__':
    while 1:
        check_payments()
        time.sleep(60 * 5)