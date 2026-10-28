from rest_framework import permissions, routers
from rest_framework.viewsets import ModelViewSet

from .models import Subscription, SubscriptionLine, SubscriptionEvent, Resource
from .serializers import (
    SubscriptionSerializer, SubscriptionLineSerializer, SubscriptionEventSerializer,
    ResourceSerializer
)


class BaseSubscriptionViewSet(ModelViewSet):
    """
    Base viewset for subscription management.

    Subscription and resource management is considered an administrative
    concern, so access is restricted to staff users by default. Override
    ``permission_classes`` in a subclass to relax it.
    """
    permission_classes = [permissions.IsAdminUser]


class SubscriptionViewSet(BaseSubscriptionViewSet):
    queryset = Subscription.objects.all()
    serializer_class = SubscriptionSerializer


class SubscriptionLineViewSet(BaseSubscriptionViewSet):
    queryset = SubscriptionLine.objects.all()
    serializer_class = SubscriptionLineSerializer


class SubscriptionEventViewSet(BaseSubscriptionViewSet):
    queryset = SubscriptionEvent.objects.all()
    serializer_class = SubscriptionEventSerializer


class ResourceViewSet(BaseSubscriptionViewSet):
    queryset = Resource.objects.all()
    serializer_class = ResourceSerializer


router = routers.DefaultRouter()
router.register(r'subscriptions', SubscriptionViewSet)
router.register(r'subscription-lines', SubscriptionLineViewSet)
router.register(r'subscription-events', SubscriptionEventViewSet)
router.register(r'resources', ResourceViewSet)

urlpatterns = router.urls
