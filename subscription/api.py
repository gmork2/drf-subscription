from rest_framework.viewsets import ModelViewSet

from .models import Subscription, SubscriptionLine, SubscriptionEvent, Resource
from .serializers import (
    SubscriptionSerializer, SubscriptionLineSerializer, SubscriptionEventSerializer,
    ResourceSerializer
)


class SubscriptionViewSet(ModelViewSet):
    queryset = Subscription.objects.all()
    serializer_class = SubscriptionSerializer


class SubscriptionLineViewSet(ModelViewSet):
    queryset = SubscriptionLine.objects.all()
    serializer_class = SubscriptionLineSerializer


class SubscriptionEventViewSet(ModelViewSet):
    queryset = SubscriptionEvent.objects.all()
    serializer_class = SubscriptionEventSerializer


class ResourceViewSet(ModelViewSet):
    queryset = Resource.objects.all()
    serializer_class = ResourceSerializer
