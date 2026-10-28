from django.test import TestCase
from rest_framework import permissions
from rest_framework.test import APIClient

from subscription.api import (
    ResourceViewSet,
    SubscriptionEventViewSet,
    SubscriptionLineViewSet,
    SubscriptionViewSet,
    router,
)


class ApiRouterTestCase(TestCase):
    def test_router_registers_all_viewsets(self):
        prefixes = {entry[0] for entry in router.registry}
        self.assertEqual(
            prefixes,
            {
                'subscriptions',
                'subscription-lines',
                'subscription-events',
                'resources',
            },
        )

    def test_viewsets_require_admin(self):
        viewsets = (
            SubscriptionViewSet,
            SubscriptionLineViewSet,
            SubscriptionEventViewSet,
            ResourceViewSet,
        )
        for viewset in viewsets:
            self.assertIn(permissions.IsAdminUser, viewset.permission_classes)


class SubscriptionApiTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_unauthenticated_request_is_forbidden(self):
        response = self.client.get('/api/subscriptions/')
        self.assertEqual(response.status_code, 403)
