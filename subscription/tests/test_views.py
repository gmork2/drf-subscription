from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from rest_framework.test import APIClient

from subscription.models import Subscription


class SubscriptionViewSetTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_superuser(
            'admin', 'admin@example.com', 'pass',
        )
        self.client.force_authenticate(self.admin)

    def _data(self, **overrides):
        ct = ContentType.objects.get_for_model(User)
        data = {
            'name': 'test',
            'active': True,
            'content_type': ct.pk,
            'object_pk': str(self.admin.pk),
        }
        data.update(overrides)
        return data

    def test_list_subscriptions(self):
        response = self.client.get('/api/subscriptions/')
        self.assertEqual(response.status_code, 200)

    def test_create_subscription(self):
        response = self.client.post(
            '/api/subscriptions/', self._data(), format='json',
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Subscription.objects.count(), 1)

    def test_retrieve_update_delete_subscription(self):
        ct = ContentType.objects.get_for_model(User)
        subscription = Subscription.objects.create(
            name='test',
            active=True,
            content_type=ct,
            object_pk=str(self.admin.pk),
        )
        detail = f'/api/subscriptions/{subscription.pk}/'

        response = self.client.get(detail)
        self.assertEqual(response.status_code, 200)

        response = self.client.patch(detail, {'name': 'updated'}, format='json')
        self.assertEqual(response.status_code, 200)
        subscription.refresh_from_db()
        self.assertEqual(subscription.name, 'updated')

        response = self.client.delete(detail)
        self.assertEqual(response.status_code, 204)
        self.assertEqual(Subscription.objects.count(), 0)

    def test_non_staff_user_is_forbidden(self):
        self.client.force_authenticate(
            User.objects.create_user('bob', 'bob@example.com', 'pass'),
        )
        response = self.client.get('/api/subscriptions/')
        self.assertEqual(response.status_code, 403)
