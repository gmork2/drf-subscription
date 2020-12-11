from typing import Type, Union
import warnings

from django.db import models
from django.utils.module_loading import import_string


def callback_receiver(sender, instance, **kwargs):
    try:
        cb = import_string(instance.callback)
        if callable(cb):
            cb(**{
                'sender': sender,
                'instance': instance,
                **kwargs
            })
        else:
            warnings.warn(
                f'Resource {instance} has an invalid callback value: {instance.callback}',
                ImportWarning
            )
    except (ImportError, TypeError, AttributeError):
        pass


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

    queryset = Resource.objects.all().related_objects(instance)
    for resource in queryset:
        if resource.is_ready:
            callback_receiver(sender, resource, queryset=queryset, **kwargs)
            resource.save()
