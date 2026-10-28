from datetime import timedelta
from unittest import mock

from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.utils import timezone

from subscription.models import (
    Resource,
    Subscription,
    SubscriptionEvent,
    SubscriptionLine,
)


class SubscriptionIntegrationTestCase(TestCase):
    def _build_chain(self, user, subscription_active=True):
        ct = ContentType.objects.get_for_model(User)
        now = timezone.now()
        subscription = Subscription.objects.create(
            name='plan',
            active=subscription_active,
            content_type=ct,
            object_pk=str(user.pk),
        )
        line = SubscriptionLine.objects.create(
            subscription=subscription,
            start=now - timedelta(days=1),
            end=now + timedelta(days=1),
        )
        event = SubscriptionEvent.objects.create(
            subscription_line=line,
            start=now - timedelta(days=1),
            end=now + timedelta(days=1),
        )
        return Resource.objects.create(
            subscription_event=event,
            content_type=ct,
            object_pk=str(user.pk),
            callback='dummy.path',
            active=True,
        )

    @mock.patch('subscription.signals.import_string')
    def test_callback_fires_when_related_object_saved(self, mock_import):
        callback = mock.Mock()
        mock_import.return_value = callback
        user = User.objects.create_user('jane', password='pass')
        self._build_chain(user)

        user.first_name = 'Jane'
        user.save()

        callback.assert_called()

    @mock.patch('subscription.signals.import_string')
    def test_callback_does_not_fire_when_inactive(self, mock_import):
        callback = mock.Mock()
        mock_import.return_value = callback
        user = User.objects.create_user('inactive', password='pass')
        self._build_chain(user, subscription_active=False)

        user.first_name = 'Jane'
        user.save()

        callback.assert_not_called()
