from django.http import HttpResponseForbidden
from django.utils.deprecation import MiddlewareMixin

from smart_filter.smart_filter import SmartFilter


class SmartFilterMiddleware(MiddlewareMixin):

    def process_request(self, request):
        if not SmartFilter.request_can_pass(request):
            session_keys = list(request.session.keys())
            for key in session_keys:
                del request.session[key]
            return HttpResponseForbidden(''.join([
                "Results from probabilistic analysis and machine learning have determined that ",
                "requests from your IP address may be malicious.  As such, your IP address has ",
                "been temporarily blacklisted.\n\n",
                "If you are using a VPN or other anonymization service, please disable the service ",
                "and retry your request."
            ]))