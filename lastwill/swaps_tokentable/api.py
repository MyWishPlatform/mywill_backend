from rest_framework.response import Response
from rest_framework.decorators import api_view
from lastwill.swaps_tokentable.models import Tokens


@api_view()
def get_all_tokens(request):
    result = []
    tokens_all = Tokens.objects.all()

    token_list = tokens_all.filter(token_short_name=request.query_params['token_short_name'])
    if request.query_params['token_name']:
        token_list = token_list.filter(token_name=request.query_params['token_name'])

    for t in token_list:
        result.append({
            'address': t.address,
            'id': t.token_name,
            'token_name': t.token_name,
            'token_short_name': t.token_short_name,
            'decimals': t.decimals,
            'image_link': t.image_link
        })
    return Response(result)
