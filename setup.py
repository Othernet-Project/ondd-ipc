import os
from setuptools import setup

import ondd_ipc as pkg


def read(fname):
        """ Return content of specified file """
        return open(os.path.join(os.path.dirname(__file__), fname)).read()


VERSION = pkg.__version__

setup(
    name='ondd-ipc',
    version=VERSION,
    license='GPLv3',
    author='Outernet Inc',
    author_email='apps@outernet.is',
    url='https://github.com/Outernet-Project/ondd-ipc',
    packages=[pkg.__name__],
    long_description=read('README.rst'),
    classifiers=[
        'Development Status :: 1 - Pre Alpha',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.4',
    ],
)
