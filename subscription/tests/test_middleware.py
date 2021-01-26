from typing import Callable

from django.db.models.signals import ModelSignal
from django.test import TestCase
from django.contrib.auth.models import User

from subscription.middleware import SubscriberMiddleware
from subscription.models import Resource


class SubscriberMiddlewareTestCase(TestCase):
    fixtures = ['auth.json', 'contenttypes.json', 'subscription.json']

    def setUp(self):
        super().setUp()
        self.signal: ModelSignal = Resource.signal
        self.recv: Callable = Resource.receiver
        self.user = User.objects.create(username='test')

    def test_empty_resources(self):
        resources = Resource.objects.all()
        resources.delete()

        _ = SubscriberMiddleware(lambda x: x)
        response = self.signal.disconnect(self.recv, sender=self.user.__class__)
        self.assertFalse(response)

    def test_related_class_connected(self):
        _ = SubscriberMiddleware(lambda x: x)

        resource = Resource.objects.first()
        model_class = resource.content_type.model_class()
        response = self.signal.disconnect(self.recv, sender=model_class)

        self.assertTrue(response)

    def test_not_related_class(self):
        resource = Resource.objects.first()
        model_class = resource.content_type.model_class()
        resources = Resource.objects.filter(content_type=resource.content_type)
        resources.delete()

        _ = SubscriberMiddleware(lambda x: x)
        response = self.signal.disconnect(self.recv, sender=model_class)
        self.assertFalse(response)

    def test_all_related_class_connected(self):
        _ = SubscriberMiddleware(lambda x: x)

        for model_class in Resource.objects.related_models():
            response = self.signal.disconnect(self.recv, sender=model_class)
            self.assertTrue(response)
        else:
            response = self.signal.disconnect(self.recv, sender=model_class)
            self.assertFalse(response)
