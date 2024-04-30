#!/usr/bin/env python

"""
Part of the LLVM Project, under the Apache License v2.0 with LLVM Exceptions.
See https://llvm.org/LICENSE.txt for license information.
SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
"""

from __future__ import print_function

import yaml
# Try to use the C parser.
try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader

from multiprocessing import Lock
import subprocess
try:
    # The previously builtin function `intern()` was moved
    # to the `sys` module in Python 3.
    from sys import intern
except:
    pass


try:
    dict.iteritems
except AttributeError:
    # Python 3
    def itervalues(d):
        return iter(d.values())

    def iteritems(d):
        return iter(d.items())
else:
    # Python 2
    def itervalues(d):
        return d.itervalues()

    def iteritems(d):
        return d.iteritems()


class Remark(yaml.YAMLObject):
    # Work-around for http://pyyaml.org/ticket/154.
    yaml_loader = Loader

    default_demangler = 'c++filt -n'
    demangler_proc = None

    @classmethod
    def set_demangler(cls, demangler):
        cls.demangler_proc = subprocess.Popen(
            demangler.split(), stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        cls.demangler_lock = Lock()

    @classmethod
    def demangle(cls, name):
        with cls.demangler_lock:
            cls.demangler_proc.stdin.write((name + '\n').encode('utf-8'))
            cls.demangler_proc.stdin.flush()
            return cls.demangler_proc.stdout.readline().rstrip().decode('utf-8')

    # Intern all strings since we have lot of duplication across filenames,
    # remark text.
    #
    # Change Args from a list of dicts to a tuple of tuples.  This saves
    # memory in two ways.  One, a small tuple is significantly smaller than a
    # small dict.  Two, using tuple instead of list allows Args to be directly
    # used as part of the key (in Python only immutable types are hashable).
    def _reduce_memory(self):
        self.Pass = intern(self.Pass)
        try:
            # Can't intern unicode strings.
            self.Name = intern(self.Name)
            self.Function = intern(self.Function)
        except:
            pass

        def _reduce_memory_dict(old_dict):
            new_dict = dict()
            for (k, v) in iteritems(old_dict):
                if type(k) is str:
                    k = intern(k)

                if type(v) is str:
                    v = intern(v)
                elif type(v) is dict:
                    # This handles [{'Caller': ..., 'DebugLoc': { 'File': ... }}]
                    v = _reduce_memory_dict(v)
                new_dict[k] = v
            return tuple(new_dict.items())

        self.Args = tuple([_reduce_memory_dict(arg_dict)
                           for arg_dict in self.Args])

    # The inverse operation of the dictonary-related memory optimization in
    # _reduce_memory_dict.  E.g.
    #     (('DebugLoc', (('File', ...) ... ))) -> [{'DebugLoc': {'File': ...} ....}]
    def recover_yaml_structure(self):
        def tuple_to_dict(t):
            d = dict()
            for (k, v) in t:
                if type(v) is tuple:
                    v = tuple_to_dict(v)
                d[k] = v
            return d

        self.Args = [tuple_to_dict(arg_tuple) for arg_tuple in self.Args]

    def canonicalize(self):
        if not hasattr(self, 'Hotness'):
            self.Hotness = 0
        if not hasattr(self, 'Args'):
            self.Args = []
        self._reduce_memory()

    @property
    def File(self):
        return self.DebugLoc['File']

    @property
    def Line(self):
        return int(self.DebugLoc['Line'])

    @property
    def Column(self):
        return self.DebugLoc['Column']

    @property
    def DebugLocString(self):
        return "{}:{}:{}".format(self.File, self.Line, self.Column)

    @property
    def DemangledFunctionName(self):
        return self.demangle(self.Function)

    # Return a cached dictionary for the arguments.  The key for each entry is
    # the argument key (e.g. 'Callee' for inlining remarks.  The value is a
    # list containing the value (e.g. for 'Callee' the function) and
    # optionally a DebugLoc.
    def get_arg_dict(self):
        if hasattr(self, 'ArgDict'):
            return self.ArgDict
        self.ArgDict = {}
        for arg in self.Args:
            if len(arg) == 2:
                if arg[0][0] == 'DebugLoc':
                    dbgidx = 0
                else:
                    assert(arg[1][0] == 'DebugLoc')
                    dbgidx = 1

                key = arg[1 - dbgidx][0]
                entry = (arg[1 - dbgidx][1], arg[dbgidx][1])
            else:
                arg = arg[0]
                key = arg[0]
                entry = (arg[1], )

            self.ArgDict[key] = entry
        return self.ArgDict

    @property
    def key(self):
        return (self.__class__, self.Name, self.Function)

    def __hash__(self):
        return hash(self.key)

    def __eq__(self, other):
        return self.key == other.key

    def __repr__(self):
        return str(self.key)
