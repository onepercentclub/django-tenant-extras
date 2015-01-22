import os
from setuptools import setup

with open(os.path.join(os.path.dirname(__file__), 'README.rst')) as readme:
    README = readme.read()

os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

setup(
	name="django-tenant-extras",
	version=tenant_extras.__version__,
	packages=['tenant_extras'],
	include_package_data=True,
	license='None',
	description='A small package for extra utils for tenant schemas',
	long_description=README,
	url="http://onepercentclub.com",
	author="1%Club Developers"
	author_email="devteam@onepercentclub.com", 
	install_requires=[
		'Django >= 1.6.8',
		'django-tenant-schemas >= 1.5.0',
	],
	classifiers=[
	    'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: None', 
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content'
	]

)

