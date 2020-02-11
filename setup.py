"""
Setup of the ihcsdk module
"""
from setuptools import setup

setup(
    name='ihcsdk',
    version='2.6.0',
    description='IHC Python SDK',
    long_description=("SDK for connection to the LK IHC Controller. "
                      "Made for interfacing to home assistant"),
    author='Jens Nielsen',
    url='https://github.com/dingusdk/PythonIhcSdk',
    packages=['ihcsdk'],
    license='GPL-3.0',
)
