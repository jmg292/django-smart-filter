import datetime
import threading

from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist

from smart_filter.models import IPCheckResult
from smart_filter.blacklist import Blacklist
from smart_filter.configuration import Configuration


class QueryCache(object):

    _instance = None

    class _QueryCache(object):

        def __init__(self):
            self._cache_threshold = Configuration().SF_CACHE_EXPIRY_TIME_SECONDS

        @staticmethod
        def get_timer(target_func, interval=300.0):
            timer = threading.Timer(interval, target_func)
            timer.daemon = True
            return timer

        @staticmethod
        def check_cache_for(address):
            return IPCheckResult.objects.filter(ip_address=address).exists()

        def _prune_query_cache(self):
            time_threshold = timezone.now() - datetime.timedelta(seconds=self._cache_threshold)
            expired_entries = IPCheckResult.objects.filter(entry_time__lt=time_threshold)
            for entry in expired_entries:
                entry.delete()
            self.get_timer(self._prune_query_cache)

        def load_cache(self):
            blacklist_entries = []
            self._prune_query_cache()
            for entry in IPCheckResult.objects.all():
                if not entry.is_authorized:
                    blacklist_entries.append((entry.ip_address, entry.entry_time))
            Blacklist().load_blacklist_entries(blacklist_entries)
            
        def add_query_result(self, address, result, approved):
            try:
                ip_check_result = IPCheckResult.objects.get(ip_address=address)
                ip_check_result.query_result = result
                ip_check_result.is_authorized = approved
                ip_check_result.entry_time = timezone.now()
                ip_check_result.save()
            except ObjectDoesNotExist:
                ip_check_result = IPCheckResult.objects.create(
                    ip_address=address,
                    query_result=result,
                    is_authorized=approved
                )

    def __new__(self, *args, **kwargs):
        if not QueryCache._instance:
            QueryCache._instance = QueryCache._QueryCache()
            QueryCache._instance.load_cache()
        return QueryCache._instance