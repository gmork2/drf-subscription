from django.apps import AppConfig


class SubscriptionConfig(AppConfig):
    name = 'subscription'

    def ready(self):
        import subscription.signals
