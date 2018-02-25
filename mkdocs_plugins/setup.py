#!/usr/bin/env python
"""Setup script for abinit mkdocs plugins."""
from __future__ import absolute_import, unicode_literals, print_function, division

from setuptools import setup


setup(
    entry_points={
        'mkdocs.plugins': [
            'abidocs = plugins:AbidocsPlugin',
        ]
    }
)
