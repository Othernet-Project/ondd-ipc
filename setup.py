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
    license='BSD',
    packages=[pkg.__name__],
    include_package_data=True,
    long_description=read('README.rst'),
    include_requires=[
        'bottle',
        'bottle-utils-html'
    ],
    classifiers=[
        'Development Status :: 1 - Pre Alpha',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.4',
    ],
)
