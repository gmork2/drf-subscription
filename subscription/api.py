from django.conf import settings
from django.utils.module_loading import import_string
from rest_framework import permissions, routers, status
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from .models import Subscription, SubscriptionLine, SubscriptionEvent, Resource
from .serializers import (
    SubscriptionSerializer, SubscriptionLineSerializer, SubscriptionEventSerializer,
    ResourceSerializer, ResourceExecutionSerializer
)
from .tasks import run_resource

DEFAULT_PERMISSION_CLASSES = ['rest_framework.permissions.IsAdminUser']


class SubscriptionPagination(PageNumberPagination):
    page_size = 100
    page_size_query_param = 'page_size'
    max_page_size = 1000


def get_permission_classes():
    """
    Permission classes for the subscription viewsets. Configurable with
    the ``SUBSCRIPTION_PERMISSION_CLASSES`` setting (a list of dotted
    paths); defaults to admin-only.
    """
    paths = getattr(
        settings, 'SUBSCRIPTION_PERMISSION_CLASSES', DEFAULT_PERMISSION_CLASSES
    )
    return [import_string(path) for path in paths]


class BaseSubscriptionViewSet(ModelViewSet):
    """
    Base viewset for subscription management.

    Subscription and resource management is considered an administrative
    concern, so access is restricted to staff users by default. Override
    ``permission_classes`` in a subclass or set
    ``SUBSCRIPTION_PERMISSION_CLASSES`` to relax it.
    """
    permission_classes = get_permission_classes()
    pagination_class = SubscriptionPagination

    def _bool_param(self, name):
        value = self.request.query_params.get(name)
        if value is None:
            return None
        return value.lower() in ('1', 'true', 'yes', 'on')


class SubscriptionViewSet(BaseSubscriptionViewSet):
    queryset = Subscription.objects.all()
    serializer_class = SubscriptionSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        active = self._bool_param('active')
        if active is not None:
            queryset = queryset.filter(active=active)
        name = self.request.query_params.get('name')
        if name:
            queryset = queryset.filter(name__icontains=name)
        return queryset


class SubscriptionLineViewSet(BaseSubscriptionViewSet):
    queryset = SubscriptionLine.objects.all()
    serializer_class = SubscriptionLineSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        subscription = self.request.query_params.get('subscription')
        if subscription:
            queryset = queryset.filter(subscription_id=subscription)
        started = self._bool_param('started')
        finished = self._bool_param('finished')
        if started:
            queryset = queryset.started()
        if finished:
            queryset = queryset.finished()
        return queryset


class SubscriptionEventViewSet(BaseSubscriptionViewSet):
    queryset = SubscriptionEvent.objects.all()
    serializer_class = SubscriptionEventSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        line = self.request.query_params.get('line')
        if line:
            queryset = queryset.filter(subscription_line_id=line)
        frequency = self.request.query_params.get('frequency')
        if frequency:
            queryset = queryset.filter(frequency=frequency)
        return queryset


class ResourceViewSet(BaseSubscriptionViewSet):
    queryset = Resource.objects.all()
    serializer_class = ResourceSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        active = self._bool_param('active')
        if active is not None:
            queryset = queryset.filter(active=active)
        subscription = self.request.query_params.get('subscription')
        if subscription:
            queryset = queryset.filter(
                subscription_event__subscription_line__subscription_id=subscription
            )
        return queryset

    @action(detail=True, methods=['post'])
    def run(self, request, pk=None):
        """
        Execute the resource right now (queued when Celery is
        available) and return the execution record when it ran
        synchronously.
        """
        resource = self.get_object()
        if not resource.is_ready:
            return Response(
                {'detail': 'The resource is not ready.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        mode, execution = run_resource(resource)
        if mode == 'queued':
            return Response(
                {'status': 'queued'},
                status=status.HTTP_202_ACCEPTED,
            )
        return Response(ResourceExecutionSerializer(execution).data)

    @action(detail=True, methods=['post'])
    def pause(self, request, pk=None):
        """
        Deactivate the resource.
        """
        resource = self.get_object()
        resource.active = False
        resource.save(update_fields=['active'])
        return Response(self.get_serializer(resource).data)

    @action(detail=True, methods=['post'])
    def resume(self, request, pk=None):
        """
        Activate the resource.
        """
        resource = self.get_object()
        resource.active = True
        resource.save(update_fields=['active'])
        return Response(self.get_serializer(resource).data)

    @action(detail=True, methods=['get'])
    def history(self, request, pk=None):
        """
        List the execution records of the resource.
        """
        resource = self.get_object()
        executions = resource.executions.all()
        page = self.paginate_queryset(executions)
        if page is not None:
            serializer = ResourceExecutionSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = ResourceExecutionSerializer(executions, many=True)
        return Response(serializer.data)


router = routers.DefaultRouter()
router.register(r'subscriptions', SubscriptionViewSet)
router.register(r'subscription-lines', SubscriptionLineViewSet)
router.register(r'subscription-events', SubscriptionEventViewSet)
router.register(r'resources', ResourceViewSet)

urlpatterns = router.urls
