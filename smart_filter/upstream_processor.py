import json
import logging
import queue
import threading
import time
import urllib.request

from django.utils import timezone

from smart_filter.blacklist import Blacklist
from smart_filter.query_cache import QueryCache
from smart_filter.rate_limiter import RateLimiter
from smart_filter.configuration import Configuration


logger = logging.getLogger(__name__)


class UpstreamProcessor(object):

    _instance = None

    class _UpstreamProcessor(object):

        def __init__(self):
            self._address_queue = queue.Queue()
            self._queue_processor_thread = None
            self._upstream_url_template = self._build_upstream_url_template()
            self._blacklist_threshold = Configuration().SF_BLACKLIST_THRESHOLD

        @staticmethod
        def get_timer(target_func, interval=300.0):
            timer = threading.Timer(interval, target_func)
            timer.daemon = True
            return timer
            
        @staticmethod
        def _build_upstream_url_template():
            configuration = Configuration()
            url_flags = "&contact={0}".format(configuration.SF_CONTACT_ADDRESS)
            if configuration.SF_QUERY_FLAGS:
                url_flags += "&flags={0}".format(url_flags)
            url_flags = "?ip={0}" + url_flags + "&format=json"
            return configuration.SF_PROVIDER_ADDRESS + url_flags

        @staticmethod
        def _can_make_request():
            can_make_request = True
            rate_limiter_response = RateLimiter().check_rate_limit()
            if rate_limiter_response == RateLimiter.RateLimitResponse.DAILY_LIMIT_EXCEEDED:
                logger.warning("(SmartFilter) Daily rate limit exceeded, unable to process request.")
                can_make_request = False
            elif rate_limiter_response == RateLimiter.RateLimitResponse.INTERVAL_LIMIT_EXCEEDED:
                logger.warning("(SmartFilter) Interval rate limit exceeded, unable to process request.")
                can_make_request = False
            return can_make_request

        def _process_request(self, data):
            if data["status"] == "success":
                result = int(data["result"]) * 100
                address = data["queryIP"]
                is_authorized = False
                if result < self._blacklist_threshold:
                    is_authorized = True
                logger.debug("(SmartFilter) Address {0} analyzed with result {1}.  Authorized: {2}".format(
                    address, result, is_authorized
                ))
                QueryCache().add_query_result(address, result, is_authorized)
                if not is_authorized:
                    Blacklist().append(address, timezone.now())
                    logger.info("(SmartFilter) Address {0} failed IP check (result: {1}).  Address is blacklisted until cache expiry.".format(
                        address, result
                    ))
            else:
                logger.error("(SmartFilter) Upstream request failed with error message: {0}".format(
                    data["message"]
                ))
                logger.debug("(SmartFilter) Offending data: {0}".format(json.dumps(data)))
                if Configuration().SF_FAIL_SECURE:
                    logger.warning("(SmartFilter) Unable to process request and SF_FAIL_SECURE enabled.  Blackliting address: {0}".format(
                        data["queryIP"]
                    ))
                    self._process_request({
                        "status": "success",
                        "result": 1,
                        "address": data["queryIP"]
                    })


        def _process_address(self, address):
            if not QueryCache().check_cache_for(address):
                if self._can_make_request():
                    logger.debug("(SmartFilter) Request: {0}".format(self._upstream_url_template.format(address)))
                    request = urllib.request.Request(
                        self._upstream_url_template.format(address),
                        data=None,
                        headers={
                            'User-Agent': 'Django Smart IP Filter (www.gnzlabs.io/smart-filter)'
                        }
                    )
                    response = urllib.request.urlopen(request)
                    result = json.loads(response.read().decode(
                        response.info().get_content_charset('utf-8')
                    ))
                    RateLimiter().increment_counter
                    self._process_request(result)
                else:
                    if not Configuration().SF_FAIL_SECURE:
                        logger.warning("(SmartFilter) Unable to process request, storing address {0} for later processing.".format(
                            address
                        ))
                        self._address_queue.put(address)
                    else:
                        logger.warning("(SmartFilter) Unable to process request and SF_FAIL_SECURE enabled.  Blacklisting address: {0}".format(
                            address
                        ))
                        self._process_request({
                            "status": "success",
                            "result": 1,
                            "queryIP": address
                        })
            else:
                logger.debug("(SmartFilter) A cache entry for the address {0} has been found.  Skipping.".format(
                    address
                ))

        def _process_address_queue(self):
            while True:
                if not self._address_queue.empty():
                    next_address = self._address_queue.get()
                    self._process_address(next_address)
                time.sleep(0.25)

        def check_ip_address(self, address):
            self._address_queue.put(address)

        def start(self):
            self._queue_processor_thread = threading.Thread(target=self._process_address_queue)
            self._queue_processor_thread.setDaemon(True)
            self._queue_processor_thread.start()

    def __new__(self, *args, **kwargs):
        if not UpstreamProcessor._instance:
            UpstreamProcessor._instance = UpstreamProcessor._UpstreamProcessor()
            UpstreamProcessor._instance.start()
        return UpstreamProcessor._instance