#==============#
# Smart Filter #
#==============#

Smart filter is a Django middleware application that links your Django project to the IP reputation service provided by https://getipintel.net/

IP Intelligence is a service that determines how likely an IP address is a proxy / VPN / bad IP using advanced mathematical and modern computing techniques.

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
	
3.) Run 'python manage.py migrate' to create the various models used by Smart Filter.

Congratulations, requests to your site are now being vetted using https://getpintel.net/.
