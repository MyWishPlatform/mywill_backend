from rest_framework.decorators import api_view
from rest_framework.response import Response

from lastwill.swaps_common.mailing.models import SwapsMailing


@api_view(http_method_names=['POST'])
def save_swaps_mail(request):
    email = request.data['email'] if 'email' in request.data else None
    telegram = request.data['telegram'] if 'telegram' in request.data else None
    name = request.data['email'] if 'email' in request.data else None

    mail = SwapsMailing(email=email, telegram_name=telegram, name=name)
    mail.save()

    return Response({'id': mail.id, 'email': mail.email, 'telegram': mail.telegram_name, 'name': mail.name})
