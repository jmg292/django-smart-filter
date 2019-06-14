import ipaddress
import logging
import socket
import struct
import threading
import typing

from smart_filter.models import WhitelistEntry


logger = logging.getLogger(__name__)


class Whitelist(object):

    _instance = None

    class _Whitelist(object):

        def __init__(self):
            self._network_list_lock = threading.Lock()
            self._whitelisted_networks = {}

        def append(self, whitelist_entry: WhitelistEntry):
                network = ipaddress.ip_network("{0}/{1}".format(
                    whitelist_entry.ip_address, 
                    whitelist_entry.subnet
                ))
                netmask = int(network.netmask)
                address = int(network.network_address)
                self._network_list_lock.acquire()
                if not netmask in self._whitelisted_networks:
                    self._whitelisted_networks[netmask] = [address]
                else:
                    self._whitelisted_networks[netmask].append(address)
                self._network_list_lock.release()

        def load_whitelist(self):
            logger.debug("(SmartFilter) Loading whitelist from database.")
            for entry in WhitelistEntry.objects.all():
                self.append(entry)
            logger.info("(SmartFilter) Loaded {0} whitelisted networks from database.".format(
                len(self._whitelisted_networks)
            ))

        def is_whitelisted(self, address):
            is_whitelisted = False
            try:                
                ip_address = ipaddress.ip_address(address)
            except ValueError:
                logger.error("(SmartFilter) Invalid IP address supplied for whitelist check: {0}".format(
                    address
                ))
                return is_whitelisted
            is_whitelisted = not ip_address.is_global
            if not is_whitelisted:
                self._network_list_lock.acquire()
                whitelisted_networks = dict(self._whitelisted_networks)
                self._network_list_lock.release()
                address_dec = struct.unpack("!I", ip_address.packed)[0]
                for netmask in whitelisted_networks:
                    network_address = address_dec & netmask
                    for network in whitelisted_networks[netmask]:
                        is_whitelisted = network == network_address
                        if is_whitelisted:
                            break
            return is_whitelisted

    def __new__(self, *args, **kwargs):
        if not Whitelist._instance:
            Whitelist._instance = Whitelist._Whitelist()
            Whitelist._instance.load_whitelist()
        return Whitelist._instance