# coding=utf-8
"""
Utility functions
Copyright (C) 2017-2020, Huawei Technologies Co., Ltd. All rights reserved.
"""
import os
import csv
import logging
import stat

log = logging.getLogger(__name__)


def parse_hot_function(file_path, num):
    """
    Parse the given file to get top num hot functions.
    """
    hot_functions = []
    if len(file_path) > 0:
        with open(file_path[0], "r")as file_object:
            lines = file_object.readlines()
        line_number = 0
        index = 0
        while line_number < len(lines):
            if lines[line_number].split()[0] != '#':
                line_number = line_number + 2
                while index < num and line_number < len(
                        lines) and len(lines[line_number].split()) >= 3:
                    hot_functions.append(lines[line_number].split()[-1])
                    index = index + 1
                    line_number = line_number + 1
                return hot_functions

            else:
                line_number = line_number + 1
        return hot_functions
    else:
        return hot_functions


def create_secure_fd(file_path):
    """
    Returns a file descriptor for file_path, with the
    appropriate permission bits for security reasons.
    """
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
    modes = stat.S_IWUSR | stat.S_IRUSR
    file_fd = os.open(file_path, flags, modes)
    return file_fd


def check_file_permissions(file_path):
    """
    Raise an IOError if file_path is writable by group or others
    for security reasons.
    File permission check is skipped for Windows OS because Python os module
    does not support cross-OS file permissions.
    """
    if os.name == "nt":
        log.info("File permissions are not verified for Windows OS.")
        return

    stat_info = os.stat(file_path)
    if bool(stat_info.st_mode & (stat.S_IWGRP | stat.S_IWOTH)):
        raise IOError("file is writable by other users "
                      "(potential security risk): {}".format(file_path))


def parse_feedback_file(filename):
    if not os.path.isfile(filename):
        raise IOError("Feedback file {} not found".format(filename))
    # Check file permissions
    check_file_permissions(filename)
    feedback_values = []
    try:
        with open(filename, newline='') as file:
            # csv.reader is responsible for reporting format issues by
            # raising exceptions.
            reader = csv.reader(file)
            for row in reader:
                for ele in row:
                    if ele:
                        feedback_values.append(float(ele))
    except Exception as error:
        raise IOError("Invalid format in feedback file "
                      ":{}: {}".format(filename, str(error)))
    return feedback_values
