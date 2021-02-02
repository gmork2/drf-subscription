from django.apps import apps


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
            model_class.signal,
            model_class.receiver
        )

    def __call__(self, request):
        response = self.get_response(request)
        return response
