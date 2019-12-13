from lastwill.contracts.models import ContractDetailsTokenProtector
from rest_framework import serializers

class TokenSaverSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContractDetailsTokenProtector
        fields = '__all__'
