import enum
import threading

from django.utils import timezone

from smart_filter.models import RateLimitState
from smart_filter.configuration import Configuration


class RateLimiter(object):

    _instance = None

    class RateLimitResponse(enum.IntEnum):

        CAN_QUERY = 0
        INTERVAL_LIMIT_EXCEEDED = 1
        DAILY_LIMIT_EXCEEDED = 2

    class _RateLimiter(object):

        def __init__(self):
            self._daily_count_lock = threading.Lock()
            self._minute_count_lock = threading.Lock()
            self._max_queries_per_minute = Configuration().SF_MAX_QUERIES_PER_MINUTE
            self._max_queries_per_day = Configuration().SF_MAX_QUERIES_PER_DAY
            self._current_minute_query_count = 0
            self._current_daily_query_count = 0

        @staticmethod
        def get_timer(target_func, interval=300.0):
            timer = threading.Timer(interval, target_func)
            timer.daemon = True
            return timer

        def _set_daily_count_to(self, count, reset_time=False):
            self._daily_count_lock.acquire()
            rate_limit_state = RateLimitState.objects.filter(id=1).first()
            rate_limit_state.current_count = count
            self._current_daily_query_count = rate_limit_state.current_count
            if reset_time:
                rate_limit_state.last_reset_time = timezone.now()
            rate_limit_state.save()
            self._daily_count_lock.release()

        def _reset_daily_count_if_time_elapsed(self):
            rate_limit_state = RateLimitState.objects.filter(id=1).first()
            seconds_since_last_reset = (timezone.now() - rate_limit_state.last_reset_time).total_seconds()
            if seconds_since_last_reset >= 86400:
                self._set_daily_count_to(0, reset_time=True)
            self.get_timer(self._reset_daily_count_if_time_elapsed, 900.0).start()

        def _reset_interval_rate_limit(self):
            self._minute_count_lock.acquire()
            self._current_minute_query_count = 0
            self._minute_count_lock.release()
            self.get_timer(self._reset_interval_rate_limit, 60.0).start()

        def load_rate_limiter(self):
            if RateLimitState.objects.filter(id=1).exists():
                rate_limit_state = RateLimitState.objects.filter(id=1).get()
                self._set_daily_count_to(rate_limit_state.current_count)
            else:
                RateLimitState.objects.create(
                    current_count = 0,
                    last_reset_time = timezone.now()
                )
            self._reset_daily_count_if_time_elapsed()
            self._reset_interval_rate_limit()

        def check_rate_limit(self):
            rate_limiter_response = RateLimiter.RateLimitResponse.CAN_QUERY
            daily_queries_remaining = self._max_queries_per_day - self._current_daily_query_count
            minute_queries_remaining = self._max_queries_per_minute - self._current_minute_query_count
            if daily_queries_remaining <= 0:
                rate_limiter_response = RateLimiter.RateLimitResponse.DAILY_LIMIT_EXCEEDED
            elif minute_queries_remaining <= 0:
                rate_limiter_response = RateLimiter.RateLimitResponse.INTERVAL_LIMIT_EXCEEDED
            return rate_limiter_response

        def increment_counter(self):
            self._minute_count_lock.acquire()
            self._current_minute_query_count -= 1
            self._minute_count_lock.release()
            self._set_daily_count_to(self._current_daily_query_count + 1)

    def __new__(self, *args, **kwargs):
        if not RateLimiter._instance:
            RateLimiter._instance = RateLimiter._RateLimiter()
            RateLimiter._instance.load_rate_limiter()
        return RateLimiter._instance
        