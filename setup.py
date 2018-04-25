#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages
from pip.req import parse_requirements

install_reqs = parse_requirements('requirements.txt', session='hack')
reqs = [str(ir.req) for ir in install_reqs]

setup(
    name='drctrl',
    version='0.0.7',
    description="Automatically configuration tool for DataRobot.",
    author='e-mon',
    author_email='emon18@icloud.com',
    url='https://github.com/recruit-tech/drctrl',
    packages=find_packages(),
    package_data={
        'drctrl' : ['lib/schema/base_schema.yml', 'lib/schema/project_id_is_supplied.yml'],
    },
    entry_points={'console_scripts': ['drctrl = drctrl.cli:main']},
    install_requires=reqs,
    classifiers=[
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Environment :: Web Environment",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Operating System :: MacOS :: MacOS X",
        "Topic :: Software Development :: Libraries :: Python Modules"
    ])
