import os
from setuptools import setup
import tenant_extras

with open(os.path.join(os.path.dirname(__file__), 'README.md')) as readme:
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
    author="1%Club Developers",
    author_email="devteam@onepercentclub.com",
    install_requires=[
        'Django >= 1.6.8,<1.7',
        'django-tenant-schemas >= 1.5.0',
    ],
    tests_require={
        'django-nose==1.3',
        'django-setuptest==0.1.4',
        'mock==1.0.1'
    },
    test_suite = "tenant_extras.runtests.runtests",
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

