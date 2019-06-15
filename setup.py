import os
from setuptools import find_packages, setup

with open(os.path.join(os.path.dirname(__file__), 'README.md')) as readme:
	README = readme.read()
	
os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

setup (
	name='django-smart-filter',
	version='0.2',
	packages=find_packages(),
	include_package_data=True,
	license='MIT License',
	description='Django middleware layer for https://getipintel.net/',
	long_description=README,
	author='Jeff Gonzalez',
	author_email='contact@gnzlabs.io',
	classifiers = [
		'Environment :: Web Environment',
		'Framework :: Django',
		'Framework :: Django :: 2.2',
		'Intended Audience :: Developers',
		'License :: OSI Approved :: MIT License',
		'Operating System :: OS Independent',
		'Programming Language :: Python',
		'Programming Language :: Python :: 3',
		'Topic :: Internet :: WWW/HTTP',
	]
)