from unittest import mock

from django.contrib.auth.models import User
from django.test import TestCase

from subscription.models import Resource
from subscription.signals import callback_receiver, default_receiver


class CallBackReceiverTestCase(TestCase):
    @mock.patch('subscription.signals.import_string')
    def test_calls_callable(self, mock_import):
        callback = mock.Mock()
        mock_import.return_value = callback
        instance = mock.Mock()
        instance.callback = 'dummy.path'

        callback_receiver(sender=User, instance=instance, extra='value')

        callback.assert_called_once_with(sender=User, instance=instance, extra='value')

    @mock.patch('subscription.signals.import_string')
    def test_ignores_import_error(self, mock_import):
        mock_import.side_effect = ImportError
        instance = mock.Mock()
        instance.callback = 'bad.path'

        # Should not raise.
        callback_receiver(sender=User, instance=instance)

    @mock.patch('subscription.signals.import_string')
    def test_warns_when_not_callable(self, mock_import):
        mock_import.return_value = 'not-callable'
        instance = mock.Mock()
        instance.callback = 'dummy.path'

        with self.assertWarns(ImportWarning):
            callback_receiver(sender=User, instance=instance)


class DefaultReceiverTestCase(TestCase):
    fixtures = ['auth.json', 'contenttypes.json', 'subscription.json']

    @mock.patch('subscription.signals.callback_receiver')
    def test_triggers_callback_for_ready_resource(self, mock_callback):
        user = User.objects.get(pk=1)
        default_receiver(sender=User, instance=user)
        mock_callback.assert_called()

    @mock.patch('subscription.signals.callback_receiver')
    def test_skips_inactive_resource(self, mock_callback):
        Resource.objects.filter(pk=1).update(active=False)
        user = User.objects.get(pk=1)
        default_receiver(sender=User, instance=user)
        mock_callback.assert_not_called()
