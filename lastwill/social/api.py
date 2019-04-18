from rest_framework.response import Response
from ethereum.utils import ecrecover_to_pub, sha3
from eth_utils.hexadecimal import encode_hex, decode_hex, add_0x_prefix
from eth_account.messages import defunct_hash_message


def generate_message():
    return Response({"msg": "Hello from MyWish!"})


def check_signed_message(msg):
    address = msg['address']
    message = msg['msg']
    signature = msg['signed_msg']

    r = int(signature[0:66], 16)
    s = int(add_0x_prefix(signature[66:130]), 16)
    v = int(add_0x_prefix(signature[130:132]), 16)
    if v not in (27,28):
        v += 27

    message_hash = defunct_hash_message(text=message)
    pubkey = ecrecover_to_pub(decode_hex(message_hash.hex()), v, r, s)
    signer_address = encode_hex(sha3(pubkey)[-20:])

    if signer_address != address.lower():
        return False

    return True
