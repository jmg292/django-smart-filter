import logging

from django.http import HttpRequest

from smart_filter.whitelist import Whitelist
from smart_filter.blacklist import Blacklist
from smart_filter.configuration import Configuration
from smart_filter.upstream_processor import UpstreamProcessor


logger = logging.getLogger(__name__)


class SmartFilter(object):

    @staticmethod
    def resolve_ip_address(request: HttpRequest):
        address = request.META.get('X-Real-IP')
        if not address:
            address = request.META.get('X-Forwarded-For')
            if address:
                address = address.split(',')[0]
            else:
                address = request.META.get("REMOTE_ADDR")
        return address

    @staticmethod
    def request_can_pass(request: HttpRequest):
        authorized = False
        address = SmartFilter.resolve_ip_address(request)
        if not Whitelist().is_whitelisted(address):
            if not Blacklist().is_blacklisted(address):
                logger.debug("(SmartFilter) No list entry found for address: {0}.  Submitting to upstream processor.".format(
                    address
                ))
                UpstreamProcessor().check_ip_address(address)
                if Configuration().SF_FAIL_SECURE:
                    logger.debug("(SmartFilter) No list entry found and fail secure enabled.  Blocking request from {0}".format(
                        address
                    ))
                else:
                    authorized = True
            else:
                logger.debug("(SmartFilter) Address is blacklisted: {0}".format(address))
        else:
            logger.debug("(SmartFilter) Address is whitelisted: {0}".format(address))
            authorized = True
        return authorized