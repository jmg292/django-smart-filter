# Django Smart Filter

Smart filter is a Django middleware application that links your Django project to the IP reputation service provided by https://getipintel.net/

IP Intelligence is a service that determines how likely an IP address is a proxy / VPN / bad IP using advanced mathematical and modern computing techniques.

**Disclaimer:** I am in no way associated with the IP Intelligence project.  However, I did reach out to the author/maintainer before publishing his module to get permission.  The rate limits and  the contact address requirement exist to ensure users of this module stay within the requirements for using the IP Intelligence service.

Quick Start
-----------

1.) Add 'smart_filter' to your INSTALLED_APPS setting like this:

	INSTALLED_APPS = [
		...
		'smart_filter',
	]
	
2.) Add the Smart Filter middleware to your MIDDLEWARE setting like this:

	MIDDLEWARE = [
		...
		'smart_filter.middleware.SmartFilterMiddleware',
	]
	
3.) Add your contact email to settings.py like this:

    SF_CONTACT_ADDRESS = "your@email.com"
    
**Note**: This is sent to https://getipintel.net/ with each query, and is a requirement for using the service.  As such, not setting this value will throw an `ImproperlyConfigured` exception.  Additionally, this value must be set to a valid, working email address you can be contacted on.  Not setting this value appropriately will get you banned from using the service.
	
4.) Run 'python manage.py migrate' to create the various models used by Smart Filter.

Congratulations, requests to your site are now being vetted using https://getpintel.net/.

Performance Overhead
---

In testing, this module only adds 500 microseconds (half a millisecond) to each request to your site.  It's able to do this because of gratuitous use of caching, as well as an asynchronous communication model with the IP Intelligence service.

When a request is processed by the middleware, the middleware first checks the whitelist.  If the address is whitelisted, it stops processing.  Otherwise, it checks the blacklist.  If the address is blacklisted, it stops processing.

If the address is neither whitelisted or blacklisted, the middleware returns immediately with behavior configured by the `SF_FAIL_SECURE` setting. Before returning, however, it adds the requester's IP address to a queue to be processed.

The request to https://check.getipintel.net/ is not made in the thread handling the request.  Rather, there is a dedicated thread that runs every 0.25 seconds to process the request for information.  The information from the query is processed using the settings described in *Additional Configuration Options*.  The procsssed results are cached for a time (default: 6 hours), and all subsequent requests from the same IP address are handled using the cached results.  Thus, the first and second HTTP requests made from a bad IP address may not be blocked (depending on your settings), but all subsequent requests will be.

Additional Configuration Options
--

The following options are not required, but can be set within your settings.py file in order to tweak your configuration as required.

#### Protection levels

The following values can be modified to change how aggressive the middleware behaves when blacklisting IP addresses.  These settings are currently at their default or recommended settings.  Please note, modifying these values may increase false positives.

**SF_QUERY_AGGRESSIVENESS:** An integer value from 0-3 (Default: 2) with 0 being the fastest and least thorough analysis and 3 being the slowest and most thorough analysis.  This value corresponds directly to the query flags described here: http://getipintel.net/free-proxy-vpn-tor-detection-api/#flags_compare

**SF_EXCLUDE_REALTIME_BLOCKLIST:** When `SF_QUERY_AGGRESSIVENESS` is not set to the default value, includes the "m" flag in the request.  This causes realtime blocklist checks to be skipped when analyzing the IP address.

**SF_BLACKLIST_AGGRESSIVENESS:** An integer value from 0-4 (Default: 1) that determines how certain the backend needs to be that a request is from a potentially dangerous source before that source is automatically blocked.  0 is the least aggressive (requiring 100% certainty), and 4 is the most aggressive (requiring 90% certainty).  The default value (99.5%) is the value recommended by the author as described here:  http://getipintel.net/free-proxy-vpn-tor-detection-api/#int_results

**SF_FAIL_SECURE:**  A boolean value that determines the behavior (fail open / fail secure, False and True respectively) of the middleware when information about an address isn't immediately available (Default: fail open).  Due to the asynchronous nature of backend communication in this middleware, the failure behavior will almost always be encountered the first time a user makes a request.  Additionally, this behavior will be used when your rate limit is met or exceeded.

Setting this option to True will cause any requester whose address is not cached or explicitly whitelisted to receive a 403 error while the information is being fetched, or to be blacklisted if the middleware is unable to request information on the address from IP Intelligence.

#### Caching

In order to minimize requests sent upstream, as well as improve performance, query results for each IP address are cached for a configurable amount of time (default: 6 hours).  This can be overridden if you'd like to cache values for more or less time.  

**Note:**  Modifying this setting is not recommended.  It is currently set to the maximum recommended lifetime of query results (as outlined here: http://getipintel.net/free-proxy-vpn-tor-detection-api/#FAQ), and decreasing this amount will increase the likelihood of reaching the rate limit for queries to the IP intelligence service.

**SF_CACHE_EXPIRY_TIME_SECONDS:** The time, in seconds, before cached results expire (default: 6 hours - 21600 seconds).

#### Compatibility with Custom Query Plans

While the service is free, it is rate limited to 15 requests per minute and 500 total requests per day.  This module enforces compliance with those requirements, and should be enough for most use cases.  Should your site require more, IP Intelligence offers custom query plans that start at a rate limit of 300 queries per minute.  Please email contact@getipinfo.net for more information on custom query plans.

This module strives to offer compatibility with custom query plans by providing settings to override the free-tier rate limits, as well as providing the ability to use a different URL if required.  These settings are as follows:

**NOTE:** Modifying these settings without purchasing a custom query plan may lead to your free-tier access being terminated.

**SF_MAX_QUERIES_PER_MINUTE:** Sets the maximum queries that can be made to https://check.getipintel.net each minute (default: 15).

**SF_MAX_QUERIES_PER_DAY:** Sets the maximum queries that can be made to https://check.getipintel.net each day (default: 500).

**SF_PROVIDER_ADDRESS:** The address to which IP information queries are sent (default: http://check.getipintel.net/check.php)

Additional Features
---

#### Whitelisting

From within the Django admin panel, you can create whitelist entries for IPv4 and IPv6 subnets.  These whitelist entries are evaluated prior to looking at the cache, the blacklist, or making a request to the upstream service.  Therefore, if you have known good addresses that you don't need to query, or if the service has blocked a legitimate user, you can create a whitelist entry to ensure these addresses will always be allowed.