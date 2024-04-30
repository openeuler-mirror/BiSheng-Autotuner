# coding=utf-8
"""
Factory function for constructing the correct type of IOManager
Copyright (C) 2017-2020, Huawei Technologies Co., Ltd. All rights reserved.
"""
from autotuner import xmlmanager
from autotuner import yamlmanager


def create_io_manager(suffix_str):
    suffix_str = suffix_str.strip()
    if (suffix_str == 'xml'):
        filemanager = xmlmanager.XMLManager()
    else:
        filemanager = yamlmanager.YAMLManager()
    return filemanager
