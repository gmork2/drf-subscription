from django.apps import apps
from subscription.models.decorators import DEFAULT_RECEIVER, DEFAULT_SIGNAL


class SubscriberMiddleware:
    def __init__(self, get_response):
        """
        Connect resources via post save signal to default
        receiver.

        :param get_response:
        """
        self.get_response = get_response
        model_class = apps.get_model('subscription', 'Resource')

        model_class.objects.connect(
            DEFAULT_SIGNAL,
            DEFAULT_RECEIVER
        )

    def __call__(self, request):
        response = self.get_response(request)
        return response
