import hashlib
import hmac
import json
from datetime import timedelta
from unittest import mock

from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.utils import timezone

from subscription.models import (
    Resource,
    Subscription,
    SubscriptionEvent,
    SubscriptionLine,
)
from subscription.tasks import send_webhook, execute_resource_now


def make_resource(webhook_url=None, webhook_secret=None, **kwargs):
    ct = ContentType.objects.get_for_model(User)
    now = timezone.now()
    subscription = Subscription.objects.create(
        name='test',
        active=True,
        content_type=ct,
        object_pk='1',
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
    user = User.objects.create_user('webhook-user', password='pass')
    return Resource.objects.create(
        subscription_event=event,
        content_type=ContentType.objects.get_for_model(User),
        object_pk=str(user.pk),
        webhook_url=webhook_url,
        webhook_secret=webhook_secret,
        active=True,
        **kwargs
    )


class SendWebhookTestCase(TestCase):
    def test_sends_signed_payload(self):
        resource = make_resource(
            webhook_url='https://example.com/hook',
            webhook_secret='secret',
        )
        resource.content_object_fields = {'username': 'webhook-user'}
        resource.save()

        with mock.patch(
            'subscription.tasks.urllib.request.urlopen'
        ) as mock_open:
            mock_response = mock.MagicMock()
            mock_response.status = 200
            mock_open.return_value.__enter__.return_value = mock_response

            send_webhook(resource)

        request = mock_open.call_args[0][0]
        self.assertEqual(request.full_url, 'https://example.com/hook')

        body = request.data
        expected_signature = hmac.new(
            b'secret', body, hashlib.sha256
        ).hexdigest()
        self.assertEqual(
            request.get_header('X-subscription-signature'),
            'sha256=%s' % expected_signature,
        )
        self.assertEqual(
            request.get_header('X-subscription-resource'),
            str(resource.pk),
        )
        self.assertEqual(
            json.loads(body.decode('utf-8')),
            {'username': 'webhook-user'},
        )

    def test_raises_on_http_error(self):
        resource = make_resource(webhook_url='https://example.com/hook')

        with mock.patch(
            'subscription.tasks.urllib.request.urlopen'
        ) as mock_open:
            mock_response = mock.MagicMock()
            mock_response.status = 500
            mock_open.return_value.__enter__.return_value = mock_response

            with self.assertRaises(RuntimeError):
                send_webhook(resource)

    def test_execution_records_failed_webhook(self):
        resource = make_resource(webhook_url='https://example.com/hook')

        with mock.patch(
            'subscription.tasks.urllib.request.urlopen',
            side_effect=OSError('connection refused'),
        ):
            execution = execute_resource_now(resource, timezone.now())

        self.assertEqual(execution.status, 'failed')
        self.assertIn('connection refused', execution.error_message)

    @mock.patch('subscription.tasks.urllib.request.urlopen')
    @mock.patch('subscription.signals.import_string')
    def test_runs_webhook_and_callback(self, mock_import, mock_open):
        mock_open.return_value.__enter__.return_value.status = 200
        callback = mock.Mock()
        mock_import.return_value = callback
        resource = make_resource(
            webhook_url='https://example.com/hook',
            callback='dummy.path',
        )

        execute_resource_now(resource, timezone.now())

        mock_open.assert_called_once()
        callback.assert_called_once()

    def test_no_webhook_runs_only_callback(self):
        resource = make_resource(callback=None)
        resource.callback = 'dummy.path'
        resource.save()

        with mock.patch(
            'subscription.tasks.urllib.request.urlopen'
        ) as mock_open, \
                mock.patch('subscription.signals.import_string') as mock_import:
            mock_import.return_value = mock.Mock()
            execute_resource_now(resource, timezone.now())

        mock_open.assert_not_called()

    @override_settings(SUBSCRIPTION_WEBHOOK_ALLOWED_HOSTS=['allowed.example.com'])
    def test_clean_rejects_disallowed_host(self):
        resource = make_resource(webhook_url='https://evil.example.com/hook')
        with self.assertRaises(ValidationError):
            resource.clean()

    @override_settings(SUBSCRIPTION_WEBHOOK_ALLOWED_HOSTS=['allowed.example.com'])
    def test_clean_accepts_allowed_host(self):
        resource = make_resource(webhook_url='https://allowed.example.com/hook')
        self.assertIsNone(resource.clean())


class ResourceUrlTestCase(TestCase):
    def test_get_resource_url_uses_get_absolute_url(self):
        resource = make_resource()
        self.assertIsNone(resource.get_resource_url())

        resource.content_object.get_absolute_url = lambda: '/users/1/'
        self.assertEqual(resource.get_resource_url(), '/users/1/')

    def test_get_resource_url_absolute_with_request(self):
        resource = make_resource()
        resource.content_object.get_absolute_url = lambda: '/users/1/'

        request = mock.MagicMock()
        request.build_absolute_uri.return_value = (
            'https://example.com/users/1/'
        )

        self.assertEqual(
            resource.get_resource_url(request),
            'https://example.com/users/1/',
        )
