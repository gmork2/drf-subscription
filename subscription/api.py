from rest_framework.viewsets import ModelViewSet

from .models import SubscriptionEvent
from .serializers import SubscriptionEventSerializer


class SubscriptionEventViewSet(ModelViewSet):
    queryset = SubscriptionEvent.objects.all()
    serializer_class = SubscriptionEventSerializer
