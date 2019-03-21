from rest_framework.response import Response
from rest_framework.decorators import api_view
from lastwill.swaps_tokentable.models import Tokens


@api_view()
def get_all_tokens(request):
    token_shortname = request.query_params.get('token_short_name', None)
    token_name = request.query_params.get('token_name', None)

    tokens_all = Tokens.objects.all()
    token_list = tokens_all.filter(token_short_name__startswith=token_shortname)

    if token_name:
        token_list = token_list.filter(token_name=token_name)

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
