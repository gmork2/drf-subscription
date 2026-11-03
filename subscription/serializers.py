from rest_framework import serializers

from .models import Subscription, SubscriptionEvent, SubscriptionLine, Resource, ResourceExecution


class GenericSerializer(serializers.ModelSerializer):
    @classmethod
    def from_model(cls, model_class, content_object_fields, *args, **kwargs):
        """
        Build a serializer class dynamically for the given model and
        fields, without mutating any shared state (each call returns a
        fresh class).

        :param model_class:
        :param content_object_fields:
        :param args:
        :param kwargs:
        :return:
        """
        meta_cls = type('Meta', (), {
            'model': model_class,
            'fields': content_object_fields,
        })
        serializer_cls = type(
            '%sSerializer' % model_class.__name__,
            (serializers.ModelSerializer,),
            {'Meta': meta_cls},
        )
        return serializer_cls(*args, **kwargs)


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


class ResourceExecutionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResourceExecution
        fields = [
            'id', 'resource', 'status', 'scheduled_for', 'started_at',
            'finished_at', 'attempts', 'error_message', 'created_at',
        ]
        read_only_fields = fields
