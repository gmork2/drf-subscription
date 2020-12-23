from django.test import TestCase
from django.contrib.auth.models import User

from subscription.middleware import SubscriberMiddleware
from subscription.models import Resource


class SubscriberMiddlewareTestCase(TestCase):
    fixtures = ['0001_tests.json']

    def setUp(self):
        super().setUp()
        self.recv = Resource.receiver
        self.user = User.objects.create(username='test')
        self.middleware = SubscriberMiddleware(lambda x: x)
        self.signal = Resource.signal

    def test_related_class_connected(self):
        for model_class in Resource.objects.related_models():
            self.assertTrue(self.signal.disconnect(self.recv, sender=model_class))
        self.assertFalse(self.signal.disconnect(self.recv, sender=model_class))

