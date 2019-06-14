import ipaddress

from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError


class RateLimitState(models.Model):

    current_count = models.IntegerField()
    last_reset_time = models.DateTimeField()


class IPCheckResult(models.Model):

    ip_address = models.GenericIPAddressField(db_index=True)
    query_result = models.DecimalField(max_digits=8, decimal_places=5)
    is_authorized = models.BooleanField(default=False)
    entry_time = models.DateTimeField(db_index=True)

    def save(self, *args, **kwargs):
        if not self.id:
            self.entry_time = timezone.now()
        super(IPCheckResult, self).save(*args, **kwargs)


class WhitelistEntry(models.Model):

    name = models.CharField(max_length=64)
    ip_address = models.GenericIPAddressField()
    subnet = models.IntegerField(default=32)

    def clean(self):
        if self.subnet < 1:
            raise ValidationError("Subnet mask must be greater than or equal to 1.")
        address = ipaddress.ip_address(self.ip_address)
        if type(address) is ipaddress.IPv6Address:
            if self.subnet > 128:
                raise ValidationError("Invalid IPv6 subnet mask supplied.")
        elif self.subnet > 32:
            raise ValidationError("Invalid IPv4 subnet mask supplied.")
        return super(WhitelistEntry, self).clean()

    def save(self, *args, **kwargs):
        super(WhitelistEntry, self).save(*args, **kwargs)
