from typing import Type
import warnings

from django.db import models
from django.utils.module_loading import import_string


def default_receiver(
        sender: Type[models.Model],
        instance: models.Model,
        **kwargs
) -> None:
    """
    Converts resource dotted path to callable object and call it
    with current context.

    :param sender:
    :param instance:
    :param kwargs:
    :return:
    """
    from .models import Resource

    queryset = Resource.objects.related_object(instance)
    for resource in queryset:
        try:
            cb = import_string(resource.callback)
            if callable(cb):
                cb(queryset=queryset, **{
                    'sender': sender,
                    'instance': instance,
                    **kwargs
                })
            else:
                warnings.warn(
                    f'Resource {resource} has an invalid callback value: {resource.callback}',
                    ImportWarning
                )
        except (ImportError, TypeError, AttributeError):
            pass
        resource.save()
