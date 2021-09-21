from rest_framework import serializers
from django.contrib.auth.models import User


class UserMinifiedSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        exclude = [""]
