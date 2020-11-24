from rest_framework import serializers

from .models import Subscription, SubscriptionEvent, SubscriptionLine, Resource


class GenericSerializer(serializers.ModelSerializer):
    @classmethod
    def from_model(cls, model_class, content_object_fields, *args, **kwargs):
        cls.Meta = type('Meta', (), {
            'model': model_class,
            'fields': content_object_fields
        })
        return cls(*args, **kwargs)


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


class ResourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Resource
        fields = '__all__'
