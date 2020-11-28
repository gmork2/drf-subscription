from django.utils.deconstruct import deconstructible
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _
from django.utils.module_loading import import_string


@deconstructible
class CallBackValidator(object):
    message = _('Invalid path: "{}"')
    code = "invalid"

    def __call__(self, value: str) -> None:
        try:
            if value:
                obj = import_string(value)
                if not callable(obj):
                    raise ValidationError(
                        _(f'{obj} object is not callable')
                    )
        except (ImportError, TypeError, AttributeError) as e:
            raise ValidationError(
                self.message.format(value)
            )
