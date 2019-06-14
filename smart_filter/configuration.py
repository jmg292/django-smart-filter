from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


class Configuration(object):

    _instance = None

    class _Configuration(object):

        def __init__(self):
            self._query_flags = [
                "m",
                "b",
                None,
                "f"
            ]

            self._blacklist_threshold = [
                100,
                99.5,
                99,
                95,
                90
            ]

            # Dict of setting names and default values
            self._configuration_items = {
                "SF_CONTACT_ADDRESS": None,
                "SF_PROVIDER_ADDRESS": "http://check.getipintel.net/check.php",
                "SF_MAX_QUERIES_PER_MINUTE": 15,
                "SF_MAX_QUERIES_PER_DAY": 500,
                "SF_QUERY_AGGRESSIVENESS": 2,
                "SF_BLACKLIST_AGGRESSIVENESS": 1,
                "SF_EXCLUDE_REALTIME_BLOCKLIST": False,
                "SF_FAIL_SECURE": False,
                "SF_CACHE_EXPIRY_TIME_SECONDS": 21600,
            }

        @staticmethod
        def _get_from_settings(setting_name, default_value):
            return getattr(settings, setting_name, default_value)

        def load_configuration(self):
            for config_item in self._configuration_items:
                config_value = self._get_from_settings(
                    config_item, 
                    self._configuration_items[config_item]
                )
                setattr(self, config_item, config_value)
            self.SF_QUERY_FLAGS = self._query_flags[self.SF_QUERY_AGGRESSIVENESS]
            if self.SF_QUERY_FLAGS and self.SF_EXCLUDE_REALTIME_BLOCKLIST:
                self.SF_QUERY_FLAGS = "n{0}".format(self.SF_QUERY_FLAGS)
            self.SF_BLACKLIST_THRESHOLD = self._blacklist_threshold[self.SF_BLACKLIST_AGGRESSIVENESS]
            if not self.SF_CONTACT_ADDRESS:
                raise ImproperlyConfigured("SF_CONTACT_ADDRESS setting MUST be set to a real, routable email address.")

    def __new__(self):
        if not Configuration._instance:
            Configuration._instance = Configuration._Configuration()
            Configuration._instance.load_configuration()
        return Configuration._instance
