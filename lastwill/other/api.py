from rest_framework.viewsets import ModelViewSet
from .models import Sentence
from .serializers import SentenceSerializer
from lastwill.permissions import IsStaff, CreateOnly

class SentenceViewSet(ModelViewSet):
    permission_classes = (IsStaff | CreateOnly,)
    queryset = Sentence.objects.all()
    serializer_class = SentenceSerializer
