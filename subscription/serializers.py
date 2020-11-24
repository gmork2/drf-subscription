from rest_framework import serializers

from .models import SubscriptionEvent


class SubscriptionEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionEvent
        fields = '__all__'
