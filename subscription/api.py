from rest_framework.viewsets import ModelViewSet

from .models import SubscriptionLine, SubscriptionEvent
from .serializers import SubscriptionLineSerializer, SubscriptionEventSerializer


class SubscriptionLineViewSet(ModelViewSet):
    queryset = SubscriptionLine.objects.all()
    serializer_class = SubscriptionLineSerializer


class SubscriptionEventViewSet(ModelViewSet):
    queryset = SubscriptionEvent.objects.all()
    serializer_class = SubscriptionEventSerializer
