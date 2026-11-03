from datetime import timedelta
from unittest import mock

from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.utils import timezone
from rest_framework import permissions
from rest_framework.test import APIClient

from subscription.api import (
    ResourceViewSet,
    SubscriptionEventViewSet,
    SubscriptionLineViewSet,
    SubscriptionViewSet,
    router,
)
from subscription.models import Resource, Subscription, SubscriptionEvent, SubscriptionLine


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


class ResourceApiActionsTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_superuser(
            'admin', 'admin@example.com', 'pass',
        )
        self.client.force_authenticate(self.admin)
        self.user = User.objects.create_user('payload', password='pass')
        self.resource = self._make_resource()

    def _make_resource(self, active=True):
        ct = ContentType.objects.get_for_model(User)
        now = timezone.now()
        subscription = Subscription.objects.create(
            name='plan',
            active=True,
            content_type=ct,
            object_pk=str(self.user.pk),
        )
        line = SubscriptionLine.objects.create(
            subscription=subscription,
            start=now - timedelta(days=1),
            end=now + timedelta(days=1),
        )
        event = SubscriptionEvent.objects.create(
            subscription_line=line,
            start=now - timedelta(days=1),
            end=None,
        )
        return Resource.objects.create(
            subscription_event=event,
            content_type=ct,
            object_pk=str(self.user.pk),
            callback='subscription.tests.utils.dummy',
            active=active,
        )

    def test_run_action_queued(self):
        with mock.patch(
            'subscription.tasks.execute_resource.apply_async'
        ):
            response = self.client.post(
                f'/api/resources/{self.resource.pk}/run/'
            )
        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.data, {'status': 'queued'})

    def test_run_action_synchronous_fallback(self):
        with mock.patch(
            'subscription.tasks.execute_resource.apply_async',
            side_effect=Exception('broker down'),
        ):
            response = self.client.post(
                f'/api/resources/{self.resource.pk}/run/'
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['status'], 'succeeded')

    def test_run_action_rejects_not_ready_resource(self):
        self.resource.active = False
        self.resource.save(update_fields=['active'])
        response = self.client.post(f'/api/resources/{self.resource.pk}/run/')
        self.assertEqual(response.status_code, 400)

    def test_pause_action(self):
        response = self.client.post(
            f'/api/resources/{self.resource.pk}/pause/'
        )
        self.assertEqual(response.status_code, 200)
        self.resource.refresh_from_db()
        self.assertFalse(self.resource.active)

    def test_resume_action(self):
        self.resource.active = False
        self.resource.save(update_fields=['active'])
        response = self.client.post(
            f'/api/resources/{self.resource.pk}/resume/'
        )
        self.assertEqual(response.status_code, 200)
        self.resource.refresh_from_db()
        self.assertTrue(self.resource.active)

    def test_history_action(self):
        self.resource.executions.create(
            status='succeeded', scheduled_for=timezone.now(),
        )
        response = self.client.get(
            f'/api/resources/{self.resource.pk}/history/'
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['status'], 'succeeded')

    def test_list_filter_by_active(self):
        self._make_resource(active=False)
        response = self.client.get('/api/resources/?active=true')
        self.assertEqual(response.status_code, 200)
        results = response.data['results']
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['id'], self.resource.pk)
