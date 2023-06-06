import pyotp
from ethereum.utils import ecrecover_to_pub, sha3
from eth_utils.hexadecimal import encode_hex, decode_hex, add_0x_prefix
from eth_account.messages import defunct_hash_message
from web3.auto import w3
from eth_account.messages import encode_defunct
from rest_framework.exceptions import ValidationError
from random import choice
from string import ascii_letters
from rest_framework.decorators import api_view
from rest_framework.response import Response


def valid_totp(user, totp):
    if pyotp.TOTP(user.profile.totp_key).now() != totp:
        return False
    # prevent replay attack
    if user.profile.last_used_totp is not None and user.profile.last_used_totp == totp:
        return False
    user.profile.last_used_totp = totp
    user.profile.save(update_fields=['last_used_totp'])
    return True


def valid_metamask_message(address, message, signature):
    #address = attrs['address']
    #message = attrs['msg']
    #signature = attrs['signed_msg']

    r = int(signature[0:66], 16)
    s = int(add_0x_prefix(signature[66:130]), 16)
    v = int(add_0x_prefix(signature[130:132]), 16)
    if v not in (27,28):
        v += 27

    message_hash = encode_defunct(text=message)
    signer_address = w3.eth.account.recover_message(message_hash, signature=signature)

    if signer_address.lower() != address.lower():
        raise ValidationError({'result': 'Incorrect signature'}, code=400)

    return True


@api_view(http_method_names=['GET'])
def generate_metamask_message(request):

    generated_message = ''.join(choice(ascii_letters) for ch in range(30))
    request.session['metamask_message'] = generated_message

    return Response(generated_message)
