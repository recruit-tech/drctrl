#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

setup(
    name='drctrl',
    version='0.0.4',
    description="Automatically configuration tool for DataRobot.",
    author='e-mon',
    author_email='emon18@icloud.com',
    url='https://github.com/recruit-tech/drctrl',
    packages=find_packages(),
    entry_points={'console_scripts': ['drctrl = drctrl.cli:main']},
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
