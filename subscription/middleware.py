from django.apps import apps

from .signals import default_receiver


class SubscriberMiddleware:
    def __init__(self, get_response):
        """
        Connect resources via post save signal to default
        receiver.

        :param get_response:
        """
        self.get_response = get_response
        resource_class = apps.get_model('subscription', 'Resource')

        resource_class.objects.connect_all(
            resource_class.signal,
            default_receiver
        )

    def __call__(self, request):
        response = self.get_response(request)
        return response
