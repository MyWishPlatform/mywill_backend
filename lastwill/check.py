import re
import requests
import base58
import near_api
import json
from string import ascii_letters, digits
from rest_framework.serializers import ValidationError
from solana.publickey import PublicKey
from lastwill.contracts.submodels.near.token import init_account
from typing import Union


def die(message):
    raise ValidationError(code=400, detail=message)


def is_address(string):
    re.match('^0[xX][a-fA-F\d]{40}$', string) or die('{} is not a valid ethereum address'.format(string))


def is_xin_address(string):
    re.match('^(xdc|XDC)[a-fA-F\d]{40}$', string) or die('{} is not a valid xinfin address'.format(string))


def is_neo3_address(string):
    die_message = '{} is not a valid neo3 address'.format(string)
    data = base58.b58decode_check(string) or die(die_message)
    if len(data) != 21:
        die(die_message)
    elif data[0] != 53:
        die(die_message)


def is_solana_address(string: str) -> Union[bool, Exception]:
    try:
        PublicKey(string)
        return True
    except ValueError:
        die(f'{string} is not a valid solana address')


def is_email(string):
    # django.core.validators.validate_email does not eat emails without a dot
    # like user@localserver user@[IPv6:2001:db8::1] but angular does
    # EmailValidator has whitelist for domains, but not regex so whitelist=['.*'] does not work
    # so there custom simplified check
    re.match('.*@.*', string) or die('{} is not a valid email'.format(string))


def is_percent(number):
    try:
        number = int(number)
        if number < 1 or number > 100:
            raise ValueError
    except ValueError:
        die('{} is bad percent'.format(number))


def is_sum_eq_100(iterable):
    sum(iterable) == 100 or die('percentage sum is {} not 100'.format(sum(iterable)))


def is_eos_address(string):
    re.match('^[1-5a-z\.]{1,12}$', string) or die('{} is not a valid eos address'.format(string))


def is_eos_public(string):
    all(x in ascii_letters + digits for x in string) or die('{} is not a valid public key'.format(string))


def is_near_address(admin_address: str, testnet: bool):
    if testnet:
        near_url = 'https://rpc.testnet.near.org'
    else:
        near_url = 'https://rpc.mainnet.near.org'
    j = {
        "jsonrpc": "2.0",
        "id": "dontcare",
        "method": "query",
        "params": {
            "request_type": "view_account",
            "finality": "final",
            "account_id": admin_address
        }
    }
    res = requests.post(near_url, json=j, timeout=10)
    res.raise_for_status()
    content = json.loads(res.content)
    if "error" in content:
        return False
    return True
