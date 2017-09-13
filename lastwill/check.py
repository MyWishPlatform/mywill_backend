import re
from django.core.validators import validate_email
from rest_framework.serializers import ValidationError

def die(message):
    raise ValidationError(code=400, detail=message)


def is_address(string):
    re.match('^0x[a-fA-F\d]{40}$', string) or die('{} is not a valid ethereum address'.format(string))


def is_email(string):
    # django.core.validators.validate_email does not eat emails without a dot 
    # like user@localserver user@[IPv6:2001:db8::1] but angular does
    # EmailValidator has whitelist for domains, but not regex so whitelist=['.*'] does not work
    # so there custom simplified check
    re.match('.*@.*', string) or die('{} is not a valid email'.format(string))


def is_percent(number):
    try:
        assert 1 <= int(number) <= 100
    except (ValueError, AssertionError):
        die('{} is bad percent'.format(number))


def is_sum_eq_100(iterable):
    sum(iterable) == 100 or die('percentage sum is {} not 100'.format(sum(iterable)))
