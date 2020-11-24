from rest_framework import serializers

from .models import Subscription, SubscriptionEvent, SubscriptionLine


class SubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscription
        fields = '__all__'


class SubscriptionLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionLine
        fields = '__all__'


class SubscriptionEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionEvent
        fields = '__all__'
