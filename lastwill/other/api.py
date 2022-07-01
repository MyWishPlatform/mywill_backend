from django.core.mail import send_mail
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from lastwill.permissions import CreateOnly, IsStaff
from lastwill.settings import DEFAULT_FROM_EMAIL, UNBLOCKING_EMAIL

from .models import Sentence
from .serializers import SentenceSerializer


class SentenceViewSet(ModelViewSet):
    permission_classes = (IsStaff | CreateOnly,)
    queryset = Sentence.objects.all()
    serializer_class = SentenceSerializer


@api_view(http_method_names=['POST'])
def send_unblocking_info(request):
    name = request.data.get('name')
    email = request.data.get('email')
    telegram = request.data.get('socialNetwork')
    message = request.data.get('message')
    page = request.data.get('page')
    text = """
    Name: {name}
    E-mail: {email}
    Message: {message}
    Telegram: {telegram}
    Page: {page}
    """.format(name=name, email=email, telegram=telegram, message=message, page=page)
    send_mail('Request from rocknblock.io contact form', text, DEFAULT_FROM_EMAIL, [UNBLOCKING_EMAIL])
    return Response({'result': 'ok'})
