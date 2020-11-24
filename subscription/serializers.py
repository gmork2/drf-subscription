from rest_framework import serializers

from .models import SubscriptionEvent, SubscriptionLine


class SubscriptionLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionLine
        fields = '__all__'


class SubscriptionEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionEvent
        fields = '__all__'
