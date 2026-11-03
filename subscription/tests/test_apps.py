from typing import Callable

from django.contrib.auth.models import User
from django.db.models.signals import ModelSignal, post_migrate
from django.test import TestCase

import subscription
from subscription.apps import SubscriptionConfig
from subscription.models import Resource
from subscription.models.decorators import (
    DEFAULT_SIGNAL, DEFAULT_RECEIVER, signal_uid,
)


class SubscriptionConfigTestCase(TestCase):
    fixtures = ['auth.json', 'contenttypes.json', 'subscription.json']

    def setUp(self):
        super().setUp()
        self.signal: ModelSignal = DEFAULT_SIGNAL
        self.recv: Callable = DEFAULT_RECEIVER
        self.config = SubscriptionConfig('subscription', subscription)
        # Start from a clean signal registry.
        for model_class in Resource.objects.related_models():
            self.signal.disconnect(
                self.recv,
                sender=model_class,
                dispatch_uid=signal_uid(model_class),
            )

    def _post_migrate(self):
        self.config.ready()
        post_migrate.send(sender=self.config, app_config=self.config)

    def test_empty_resources_connects_nothing(self):
        Resource.objects.all().delete()

        self._post_migrate()

        self.assertFalse(
            self.signal.disconnect(
                self.recv, sender=User, dispatch_uid=signal_uid(User)
            )
        )

    def test_related_class_connected(self):
        self._post_migrate()

        resource = Resource.objects.first()
        model_class = resource.content_type.model_class()
        self.assertTrue(
            self.signal.disconnect(
                self.recv,
                sender=model_class,
                dispatch_uid=signal_uid(model_class),
            )
        )

    def test_all_related_class_connected(self):
        self._post_migrate()

        for model_class in Resource.objects.related_models():
            self.assertTrue(
                self.signal.disconnect(
                    self.recv,
                    sender=model_class,
                    dispatch_uid=signal_uid(model_class),
                )
            )

    def test_ready_is_idempotent(self):
        # Running the post_migrate flow twice must not stack duplicate
        # receivers.
        self._post_migrate()
        self._post_migrate()

        for model_class in Resource.objects.related_models():
            first = self.signal.disconnect(
                self.recv,
                sender=model_class,
                dispatch_uid=signal_uid(model_class),
            )
            second = self.signal.disconnect(
                self.recv,
                sender=model_class,
                dispatch_uid=signal_uid(model_class),
            )
            self.assertTrue(first)
            self.assertFalse(second)
