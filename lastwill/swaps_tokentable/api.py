from rest_framework.response import Response
from rest_framework.decorators import api_view

from lastwill.swaps_tokentable.models import Tokens
from lastwill.contracts.models import *
from lastwill.settings import DEFAULT_IMAGE_LINK



def add_eth_for_test(result):
    t = Tokens.objects.get(token_short_name='ETH')
    result.append({
        'address': t.address,
        'token_name': t.token_name,
        'token_short_name': t.token_short_name,
        'decimals': t.decimals,
        'image_link': t.image_link
    })
    return result


def get_test_tokens(token_name=None, token_short_name=None, address=None):
    token_list = ContractDetailsToken.objects.all().exclude(contract__state__in=('CREATED', 'POSTPONED'))
    if token_short_name:
        token_list = token_list.filter(
            token_short_name__startswith=token_short_name.upper())

    if token_name:
        token_list = token_list.filter(token_name__istartswith=token_name)

    if address:
        token_list = token_list.filter(eth_contract_token__address=address.lower())

    result = []
    for t in token_list:
        result.append({
            'address': t.eth_contract_token.address,
            'token_name': t.token_name,
            'token_short_name': t.token_short_name,
            'decimals': t.decimals,
            'image_link': DEFAULT_IMAGE_LINK
        })
    result = add_eth_for_test(result)
    return result


@api_view()
def get_all_tokens(request):
    host = request.META['HTTP_HOST']
    token_short_name = request.query_params.get('token_short_name', None)
    token_name = request.query_params.get('token_name', None)
    address = request.query_params.get('address', None)

    if 'dev' in host.lower():
        result = get_test_tokens(token_name, token_short_name, address)
        return Response(result)

    token_list = Tokens.objects.all()
    if token_short_name:
        token_list = token_list.filter(token_short_name__startswith=token_short_name.upper())

    if token_name:
        token_list = token_list.filter(token_name__istartswith=token_name)

    if address:
        token_list = token_list.filter(address=address.lower())

    result = []
    for t in token_list:
        result.append({
            'address': t.address,
            'token_name': t.token_name,
            'token_short_name': t.token_short_name,
            'decimals': t.decimals,
            'image_link': t.image_link
        })
    return Response(result)


@api_view()
def get_standarts_tokens(request):

    tokens_all = Tokens.objects.all()
    token_list = tokens_all.filter(token_short_name__in=[
        'BNB', 'MKR', 'CRO', 'BAT', 'USDC', 'OMG', 'TUSD', 'LINK', 'ZIL', 'HOT'
    ])

    result = []
    for t in token_list:
        result.append({
            'address': t.address,
            'token_name': t.token_name,
            'token_short_name': t.token_short_name,
            'decimals': t.decimals,
            'image_link': t.image_link
        })
    return Response(result)
