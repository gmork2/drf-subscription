from functools import wraps

from typing import Callable
from django.db.models.signals import post_save, ModelSignal

from ..signals import default_receiver

DEFAULT_SIGNAL = post_save
DEFAULT_RECEIVER = default_receiver


class ConnectSignalDecorator(object):
    def __init__(
            self,
            signal: ModelSignal = DEFAULT_SIGNAL,
            receiver: Callable = DEFAULT_RECEIVER
    ):
        self.signal = signal
        self.receiver = receiver

    def __call__(self, func):

        @wraps(func)
        def wrapper(*args, **kwargs):
            model_class = args[0].content_type.model_class()
            state = getattr(args[0], '_state')

            if state.adding:
                self.signal.connect(self.receiver, sender=model_class)
            func(*args)

        return wrapper


connect_signal = ConnectSignalDecorator
