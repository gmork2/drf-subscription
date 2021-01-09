from django.core.exceptions import ValidationError
from django.test import TestCase

from subscription.models import Resource


class ResourceTestCase(TestCase):
    fixtures = ['0001_tests.json']
