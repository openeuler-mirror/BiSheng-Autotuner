#!/usr/bin/env python3
# coding=utf-8
"""
Copyright (C) 2017-2022, Huawei Technologies Co., Ltd. All rights reserved.
"""
import os
import subprocess

from importlib.util import cache_from_source
from setuptools import setup
from setuptools import find_packages
from setuptools.command.build_py import build_py


class BuildPyCommand(build_py):
    """ Extend build_py and ask it to generate .pyc files. """

    def run(self):
        self.compile = True
        build_py.run(self)
        # Replace original .py files with the corresponding .pyc files.
        # This should be the same as calling compileall.compiledir in
        # legacy mode.
        files = build_py.get_outputs(self)
        for pyfile in files:
            if pyfile[-3:] == '.py':
                cfile = cache_from_source(pyfile)
                print("Moving {!s} to {!s}".format(cfile, pyfile + "c"))
                os.rename(cfile, pyfile + "c")
                print("Deleting {!s}".format(pyfile))
                os.remove(pyfile)


def is_git_directory(path='.'):
    """
    Check if the path is under git version control.
    """
    return subprocess.call(['git', '-C', path, 'status'], \
            stderr=subprocess.STDOUT, stdout=open(os.devnull, 'w')) == 0


def create_keyword_metadata():
    """
    This function creates the keyword metada for autotuner package.
    If .git exist, keyword is created in the format of ['hash', 'date'],
    otherwise an empty string would be used instead.
    """
    if is_git_directory():
        git_hash = subprocess.check_output(["git", "describe", "--always"]).strip().decode()
        commit_date = subprocess.check_output(["git", "show", "-s", \
                                           "--date=short", "--format=%cd"]).strip().decode()
    else:
        git_hash = ""
        commit_date = ""
    return [git_hash, commit_date]

setup(
    name = 'autotuner',
    include_package_data = True,
    version = '2.2.0',
    description = 'BiSheng Autotuner',
    long_description = open('README.rst').read(),
    keywords = create_keyword_metadata(),
    url = 'https://www.hikunpeng.com/document/detail/en/kunpengdevps/compiler/fg-autotuner/kunpengbisheng_20_0002.html',
    author = 'Huawei Technologies Co. Ltd.',
    packages = find_packages(),
    install_requires = [
        'huawei-opentuner',
        'configparser>=3.5.0',
        'defusedxml',
        'dill',
        'pyyaml>=5.4.1',
        'requests>=2.18.4',
        'importlib-metadata; python_version < "3.8.0"',
    ],
    cmdclass = {
        'build_py' : BuildPyCommand,
    },
)
