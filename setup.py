#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

with open('requirements.txt', 'r') as fp:
    install_requires = fp.read().splitlines()

setup(
    name='drctrl',
    version='0.1.0',
    description="Automatically configuration tool for DataRobot.",
    author='e-mon',
    author_email='emon18@icloud.com',
    url='https://github.com/recruit-tech/drctrl',
    packages=find_packages(),
    package_data={
        'drctrl' : ['lib/schema/base_schema.yml', 'lib/schema/project_id_is_supplied.yml'],
    },
    entry_points={'console_scripts': ['drctrl = drctrl.cli:main']},
    install_requires=install_requires,
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
