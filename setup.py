"""
Setup of the ihcsdk module
"""
from setuptools import setup

setup(
    name='ihcsdk',
    version='2.7.0',
    description='IHC Python SDK',
    long_description=("SDK for connection to the LK IHC Controller. "
                      "Made for interfacing to home assistant"),
    author='Jens Nielsen',
    url='https://github.com/dingusdk/PythonIhcSdk',
    packages=['ihcsdk'],
    install_requires=[
        'requests',
        'cryptography',
    ],
    license='GPL-3.0',
    include_package_data=True,
)
