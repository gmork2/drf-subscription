from django.test import TestCase
from django.contrib.auth.models import User

from rest_framework.serializers import ALL_FIELDS

from subscription.serializers import GenericSerializer


class GenericSerializerTestCase(TestCase):
    def test_set_serializer_class(self):
        serializer = GenericSerializer.from_model(User, ALL_FIELDS)
        self.assertEqual(User, serializer.Meta.model)

    def test_set_serializer_fields(self):
        fields = ['username', 'is_active']
        serializer = GenericSerializer.from_model(User, fields)
        self.assertListEqual(fields, list(serializer.data.keys()))

    def test_set_serializer_with_all_fields(self):
        fields = [f.name for f in User._meta.get_fields()]
        serializer = GenericSerializer.from_model(User, ALL_FIELDS)
        for k in serializer.data.keys():
            self.assertIn(k, fields)

    def test_create_serializer(self):
        data = {
            'username': 'test',
            'is_active': True
        }
        user = User.objects.create(**data)
        serializer = GenericSerializer.from_model(User, tuple(data.keys()), user)
        self.assertEqual(data, serializer.data)
