# coding=utf-8
"""
Autotuner Models
Copyright (C) 2017-2020, Huawei Technologies Co., Ltd. All rights reserved.
"""


class LegacyCodeRegion(object):
    """
    A representation of Legacy Code Region
    This is used to support compilers with legacy auto-tuning APIs for
    compatibilities.
    """

    def __init__(self, name, file_name, func_name, start_line, end_line,
                 code_region_type):
        self.name = name
        self.file_name = file_name
        self.func_name = func_name
        self.start_line = start_line
        self.end_line = end_line
        self.code_region_type = code_region_type

    def __eq__(self, other):
        return self.code_region_type == other.code_region_type \
            and self.name == other.name \
            and self.file_name == other.file_name \
            and self.func_name == other.func_name

    def __hash__(self):
        return hash(
            (self.code_region_type, self.name, self.file_name, self.func_name))


class CodeRegion(object):
    """
    A representation of Code Region
    """

    def __init__(self, pass_name, name, func_name, code_region_type,
                 hashcode="", invocation=0, debug_loc=None):
        self.pass_name = pass_name
        self.name = name
        self.func_name = func_name
        self.code_region_type = code_region_type
        self.hashcode = hashcode
        self.debug_loc = debug_loc
        self.invocation = invocation

    def __eq__(self, other):
        return self.code_region_type == other.code_region_type \
            and self.name == other.name \
            and self.debug_loc == other.debug_loc \
            and self.func_name == other.func_name \
            and self.pass_name == other.pass_name \
            and self.hashcode == other.hashcode   \
            and self.invocation == other.invocation

    def set_debug_loc(self, debug_loc):
        if isinstance(debug_loc, dict):
            if 'File' in debug_loc.keys() and \
                    'Line' in debug_loc.keys() and \
                    'Column' in debug_loc.keys():
                self.debug_loc = DebugLoc(
                    debug_loc['File'], debug_loc['Line'],
                    debug_loc['Column'])
        elif isinstance(debug_loc, DebugLoc):
            self.debug_loc = debug_loc

    def __hash__(self):
        return hash(
            (self.code_region_type, self.name, self.debug_loc, self.func_name,
             self.pass_name))

    def __str__(self):
        return "Name: " + self.name + "\n" + \
               "Function Name: " + self.func_name + "\n" + \
               "Type: " + self.code_region_type + "\n" + \
               "DebugLoc: " + str(self.debug_loc) + "\n" + \
               "Pass: " + self.pass_name + "\n" + \
               "Hash: " + str(self.hashcode) + "\n" + \
               "Invocation: " + str(self.invocation)


class CodeRegionConfiguration(object):
    """
    A wrapper for a CodeRegion and its parameter(s)
    """

    def __init__(self, code_region, parameters):
        self.code_region = code_region
        self.parameters = parameters

    def __repr__(self):
        return str(self.code_region) + "\n\t" + str(self.parameters)


class Task(object):
    """
    A representation of a tuning task
    """

    def __init__(self, tuning_id, param_list, code_region):
        self.tuning_id = tuning_id
        self.param_list = param_list
        self.code_region = code_region

    def __repr__(self):
        return str(self.tuning_id) + str(self.param_list) + str(
            self.code_region)


class DebugLoc(object):
    """
    A representation of DebugLoc information
    """

    def __init__(self, file_name, line, column):
        self.file_name = file_name
        self.line = line
        self.column = column

    def __str__(self):
        return "File: " + self.file_name + ", " \
               + "Line: " + str(self.line) + ", " \
               + "Column: " + str(self.column)

    def __repr__(self):
        return "File: " + self.file_name + ", " \
               + "Line: " + str(self.line) + ", " \
               + "Column: " + str(self.column)

    def __hash__(self):
        return hash((self.file_name, self.line, self.column))

    def __eq__(self, other):
        return self.file_name == other.file_name \
            and self.line == other.line \
            and self.column == other.column
