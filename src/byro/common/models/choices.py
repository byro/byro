from collections import OrderedDict

from django.utils.functional import classproperty


class ChoicesMeta(type):
    @classmethod
    def __prepare__(self, name, bases):
        return OrderedDict()

    def __new__(cls, name, parents, dct):
        if "valid_choices" not in dct:
            dct["valid_choices"] = [
                dct[key] for key in dct if isinstance(key, str) and key.upper() == key
            ]
        return super().__new__(cls, name, parents, dct)


class Choices(metaclass=ChoicesMeta):
    """Helper class to make choices available as class variables, expose a list
    with valid choices and at the same time generate the choices tuples for the
    model class.

    Usage:
        class MyChoices(Choices):
            ONE = 'one'
            TWO = 'dwa'

        class MyModel(models.Model):
            variant = models.CharField(
                max_length=MyChoices.max_length,
                choices=MyChoices.choices,
            )
    """

    @classproperty
    def choices(cls):
        return ((val, val) for val in cls.valid_choices)

    @classproperty
    def max_length(cls):
        if hasattr(cls, "valid_choices"):
            return max(len(val) for val in cls.valid_choices)
        else:
            return max(len(val) for val, _ in cls.choices)
