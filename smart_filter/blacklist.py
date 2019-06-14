import threading

from django.utils import timezone

from smart_filter.models import IPCheckResult
from smart_filter.configuration import Configuration


class Blacklist(object):

    _instance = None

    class _Blacklist(object):

        def __init__(self):
            # Dict containing address and time entered
            self._blacklisted_addresses = {}
            self._blacklist_lock = threading.Lock()
            self._max_blacklist_retention = Configuration().SF_CACHE_EXPIRY_TIME_SECONDS

        @staticmethod
        def get_timer(target_func, interval=300.0):
            timer = threading.Timer(interval, target_func)
            timer.daemon = True
            return timer

        def _process_removals(self, removal_list):
            self._blacklist_lock.acquire()
            for entry in removal_list:
                if entry in self._blacklisted_addresses:
                    del self._blacklisted_addresses[entry]
            self._blacklist_lock.release()

        def _prune_blacklist(self):
            removal_list = []
            current_time = timezone.now()            
            self._blacklist_lock.acquire()
            blacklist = dict(self._blacklisted_addresses)
            self._blacklist_lock.release()
            for entry in blacklist:
                entry_timestamp = blacklist[entry]
                seconds_since_entry = (current_time - entry_timestamp).totalseconds()
                if seconds_since_entry >= self._max_blacklist_retention:
                    removal_list.append(entry)
            if len(removal_list):
                t = threading.Thread(target=self._process_removals, args=(removal_list,))
                t.setDaemon(True)
                t.start()
            self.get_timer(self._prune_blacklist).start()

        def load_blacklist_entries(self, blacklist_entries):
            for entry in blacklist_entries:
                self.append(entry[0], entry[1])
            self._prune_blacklist()

        def append(self, address, entry_time):
            self._blacklist_lock.acquire()
            self._blacklisted_addresses[address] = entry_time
            self._blacklist_lock.release()

        def is_blacklisted(self, address):
            self._blacklist_lock.acquire()
            blacklist = dict(self._blacklisted_addresses)
            self._blacklist_lock.release()
            return address in blacklist

    def __new__(self, *args, **kwargs):
        if not Blacklist._instance:
            Blacklist._instance = Blacklist._Blacklist()
        return Blacklist._instance