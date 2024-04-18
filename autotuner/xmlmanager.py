# coding=utf-8
"""
A set of tools to generate/parse the XML files for AutoTuning-enabled LLVM
Copyright (C) 2017-2020, Huawei Technologies Co., Ltd. All rights reserved.
"""
import os

import defusedxml.ElementTree as xml_reader  # for reading xml file
import xml.etree.ElementTree as xml_writer  # for writing xml file
from autotuner.models import LegacyCodeRegion
from autotuner.models import Task
from autotuner.utils import create_secure_fd
from opentuner.search.manipulator import EnumParameter
from opentuner.search.manipulator import IntegerParameter
from opentuner.search.manipulator import FloatParameter
from opentuner.search.manipulator import PermutationParameter
from opentuner.search.manipulator import SelectionParameter
from autotuner.iomanager import EmptySearchSpaceError
from autotuner.iomanager import IOManager


def _convert_defusedxml_to_etree(ele):
    """
    Convert a Element from defusedxml.ElementTree into etree.ElementTree
    for compatibility.
    """
    # get a string from xml_reader.Element
    ele_str = xml_reader.tostring(ele)
    # create a xml_writer.Element from the string
    ele = xml_writer.fromstring(ele_str)
    return ele


def _parse_param(tuning_id, xml_param):
    """
    Help function to return a enumeration list based on param type
    """
    param_type = xml_param.get("type")

    if param_type == "bool":
        return EnumParameter(tuning_id + xml_param.find("name").text, ["1",
                                                                       "0"])

    elif param_type == "enum":
        options = [value.text for value in xml_param.findall("value")]
        return EnumParameter(tuning_id + xml_param.find("name").text, options)

    elif param_type == "range":
        # Keep param_type == "range" for backwards compatability
        min_value = int(xml_param.find("min").text)
        max_value = int(xml_param.find("max").text)
        return IntegerParameter(tuning_id + xml_param.find("name").text,
                                min_value, max_value)

    elif param_type == "int":
        min_value = int(xml_param.find("Min").text)
        max_value = int(xml_param.find("Max").text)
        return IntegerParameter(tuning_id + xml_param.find("name").text,
                                min_value, max_value)

    elif param_type == "float":
        min_value = float(xml_param.find("Min").text)
        max_value = float(xml_param.find("Max").text)
        return FloatParameter(tuning_id + xml_param.find("name").text,
                                min_value, max_value)

    elif param_type == "permutation":
        options = [value.text for value in xml_param.findall("value")]
        return PermutationParameter(tuning_id + xml_param.find("name").text,
                                    options)

    elif param_type == "selection":
        options = [value.text for value in xml_param.findall("value")]
        return SelectionParameter(tuning_id + xml_param.find("name").text,
                                  options)

    else:
        raise Exception("No type specified for params in xml")


def _merge_llvm_input_trees(tree_a, tree_b):
    root_a = _convert_defusedxml_to_etree(tree_a.getroot())
    root_b = _convert_defusedxml_to_etree(tree_b.getroot())
    for ele in root_b.findall('input'):
        root_a.append(ele)
    tree_a._setroot(root_a)
    return tree_a


def _divide_llvm_input_tree(tree):
    tree_map = {}
    root = tree.getroot()
    for input_ele in root.findall("input"):
        code_region = input_ele.find("code_region")
        if code_region is not None:
            file_name = code_region.find("file_name")
            if file_name is not None:
                if file_name.text in tree_map:
                    tree_map[file_name.text].getroot().append(
                        _convert_defusedxml_to_etree(input_ele))
                else:
                    inputs = xml_writer.Element('inputs')
                    inputs.append(_convert_defusedxml_to_etree(input_ele))
                    new_tree = xml_writer.ElementTree(inputs)
                    tree_map[file_name.text] = new_tree

    return tree_map


def _generate_search_space(file_path, new_xml_root, start_tuning_id,
                           config_file, name_filter, func_name_filter,
                           file_name_filter, type_filter, pass_filter):
    tuning_id = start_tuning_id

    # search space of xml configuration file
    config_tree = xml_reader.parse(config_file)
    config_root = config_tree.getroot()
    global_param_config = {}
    for code_region in config_root.findall("code_region"):
        global_params = code_region.find("params")
        if global_params is not None:
            global_param_config[code_region.attrib["type"]] = global_params

    with open(file_path, 'r+') as input_file:
        content = input_file.read()
        # parse the input xml
        parser = xml_reader.XMLParser()
        parser.feed(b'<root>')
        parser.feed(content)
        parser.feed(b'</root>')
        opp_root = parser.close()

    code_regions_list = opp_root.findall("code_regions")
    for code_regions in code_regions_list:
        code_region_list = code_regions.findall("code_region")
        for code_region in code_region_list:
            code_region_type = code_region.attrib["type"]
            # check if code_region type exists in global config
            if code_region_type in global_param_config:
                # apply filters
                file_name = code_region.find("file_name").text
                func_name = code_region.find("func_name").text
                name = code_region.find("name").text
                code_region_type = code_region.attrib["type"]
                filtered = _apply_code_region_filter(file_name,
                                                     file_name_filter) and \
                    _apply_code_region_filter(func_name,
                                              func_name_filter) and \
                    _apply_code_region_filter(code_region_type,
                                              type_filter) and \
                    _apply_code_region_filter(name,
                                              name_filter)

                if filtered:
                    tuning_id += 1
                    task = xml_writer.SubElement(new_xml_root, "task")
                    task.append(code_region)
                    xml_writer.SubElement(task, "tuning_id").text = \
                        str(tuning_id)

                    params = xml_writer.SubElement(task, "params")
                    # add params from global config file
                    params.extend(_convert_defusedxml_to_etree(
                        global_param_config[code_region_type]))

    # return the last tuning id
    return tuning_id


def _apply_code_region_filter(string, filer_list):
    if filer_list and string != "undefined":
        return string in filer_list
    else:
        return True


class XMLManager(IOManager):
    def get_file_extension(self):
        return ".xml"

    def parse_search_space(self, search_space, use_dynamic_values=False,
                           use_baseline_config = False, filepath = None):
        """
        Parse the xml search space config file to init the tuner

        Args:
            search_space (str or ElementTree): A string representing the path
            to search space file or an ElementTree representing search space.
        Returns:
            task_map (dict of int: Task): A task map where the key is a tuning
            id and the value is a Task which specifies CodeRegion and
            Parameters.

        """
        task_map = {}

        # if search_space is a ElementTree already
        if isinstance(search_space, xml_writer.ElementTree):
            tree = search_space
        # else we parse the file and get an ElementTree
        else:
            tree = xml_reader.parse(search_space)

        root = tree.getroot()
        # to avoid duplicate CodeRegions
        code_region_set = set()

        # if the root does not have any children, empty search space is empty
        if not root.getchildren():
            raise EmptySearchSpaceError("empty search space")

        # loop through the task elements in the xml file
        for task_xml in root:

            tuning_id = task_xml.find("tuning_id").text
            param_list_xml = task_xml.find("params").findall("param")

            param_list = []
            # loop through the task elements in xml file
            for ele in param_list_xml:
                param = _parse_param(tuning_id, ele)
                if param:
                    param_list.append(param)

            if param_list:
                # retrieve code_region information from xml
                code_region_xml = task_xml.find("code_region")
                code_region = \
                    LegacyCodeRegion(code_region_xml.find("name").text,
                                     code_region_xml.find("file_name").text,
                                     code_region_xml.find("func_name").text,
                                     int(code_region_xml.find(
                                         "start_line").text),
                                     int(code_region_xml.find(
                                         "end_line").text),
                                     code_region_xml.get("type"))
                if code_region not in code_region_set:
                    code_region_set.add(code_region)
                    task_map[int(tuning_id)] = Task(int(tuning_id),
                                                    param_list, code_region)
        return task_map

    def build_llvm_input(self, configuration_data, task_map, output_file,
                         fixed_llvm_input_tree=None, config_db=None,
                         use_hash_matching=False):
        """
        Build input xml file for tuning-enabled LLVM based on task_map and
        configuration_data, and output as output_file

        Args:
            configuration_data: configuration data generated in each iteration
            of tuning.

            task_map (dict of int: Task): A task map where the key is a tuning
            id and the value is a Task which specifies CodeRegion and
            Parameters.

            output_file (str): A path to the output file.

            fixed_llvm_input_tree (ElementTree): fixed llvm configuration input
            files as constants in addition to the configuration data.
        """

        # generating the root
        inputs = xml_writer.Element('inputs')
        # loop through the task map to generate xml input for tuning-enabled
        # LLVM
        for tuning_id, task in task_map.items():

            input_ele = xml_writer.SubElement(inputs, 'input')
            params_xml = xml_writer.SubElement(input_ele, 'params')

            for param in task.param_list:
                # Since param.name is in the form of ID+Param
                # (e.g. 14UnrollCount), only remove the first occurrence.
                raw_param_name = param.name.replace(str(tuning_id), "", 1)

                if raw_param_name == "OptPass":
                    choice = configuration_data[param.name]

                    # check if the value comes from selection parameter
                    if isinstance(choice, dict):
                        pass_order = choice["order"]
                        size = choice["size"]
                        pass_list = pass_order[:size]

                    # otherwise the value comes from permutation parameter
                    else:
                        pass_list = choice

                    if pass_list:
                        param_xml = xml_writer.SubElement(params_xml, 'param')
                        param_xml.set('type', 'list')
                        name = xml_writer.SubElement(param_xml, 'name')
                        name.text = raw_param_name

                        for ele in pass_list:
                            value = xml_writer.SubElement(param_xml, 'value')
                            value.text = ele

                # FIXME
                elif raw_param_name == "MachineScheduling":
                    param_xml = xml_writer.SubElement(params_xml, 'param')
                    name = xml_writer.SubElement(param_xml, 'name')
                    value = xml_writer.SubElement(param_xml, 'value')
                    sed_param_xml = xml_writer.SubElement(params_xml, 'param')
                    sed_name = xml_writer.SubElement(sed_param_xml, 'name')
                    sed_value = xml_writer.SubElement(sed_param_xml, 'value')
                    if configuration_data[param.name] == "TopDown":
                        name.text = "ForceTopDown"
                        value.text = "1"
                        sed_name.text = "ForceBottomUp"
                        sed_value.text = "0"
                    elif configuration_data[param.name] == "BottomUp":
                        name.text = "ForceBottomUp"
                        value.text = "1"
                        sed_name.text = "ForceTopDown"
                        sed_value.text = "0"
                    else:
                        name.text = "ForceBottomUp"
                        value.text = "0"
                        sed_name.text = "ForceTopDown"
                        sed_value.text = "0"

                else:
                    param_xml = xml_writer.SubElement(params_xml, 'param')
                    name = xml_writer.SubElement(param_xml, 'name')
                    name.text = raw_param_name
                    value = xml_writer.SubElement(param_xml, 'value')
                    value.text = str(configuration_data[param.name])

            # construct the code region in the xml tree
            code_region = xml_writer.SubElement(input_ele, 'code_region')
            code_region.set('type', task.code_region.code_region_type)

            code_region_file_name = xml_writer.SubElement(code_region, 'name')
            code_region_file_name.text = task.code_region.name

            code_region_file_name = xml_writer.SubElement(code_region,
                                                         'file_name')
            code_region_file_name.text = task.code_region.file_name

            code_region_func_name = xml_writer.SubElement(code_region,
                                                         'func_name')
            code_region_func_name.text = task.code_region.func_name

            code_region_start_line = xml_writer.SubElement(code_region,
                                                          'start_line')
            code_region_start_line.text = str(task.code_region.start_line)

            code_region_end_line = xml_writer.SubElement(code_region,
                                                        'end_line')
            code_region_end_line.text = str(task.code_region.end_line)

        tree = xml_writer.ElementTree(inputs)

        if fixed_llvm_input_tree:
            tree = _merge_llvm_input_trees(tree, fixed_llvm_input_tree)

        self.output_to_file(output_file, tree)

    def generate_baseline_llvm_input(self, output_file, config_db=None):
        self.create_dummy_llvm_input(output_file)

    def parse_llvm_inputs(self, input_files):
        """
        Parse a list of llvm xml input files
        Args:
            input_files (a list of str): a list of llvm xml input files.
        Returns:
            result_xml_tree (ElementTree): an ElementTree instance.
        """
        result_xml_tree = None
        for input_file in input_files:
            xml_tree = xml_reader.parse(input_file)
            if not result_xml_tree:
                result_xml_tree = xml_tree
            else:
                _merge_llvm_input_trees(result_xml_tree, xml_tree)

        return result_xml_tree

    def divide_llvm_input(self, input_file):
        xml_tree = xml_reader.parse(input_file)
        return _divide_llvm_input_tree(xml_tree)

    def generate_search_space_file(self, files, output_file, config_file,
                                   name_filter=None, func_name_filter=None,
                                   file_name_filter=None, type_filter=None,
                                   pass_filter=None, config_db=None,
                                   use_hash_matching=False,
                                   use_prev_configs=False, inject_seed=False):
        """
        Generate search space file for auto-tuner driver based on opportunities
        files which are generated by llvm, and output as output_file

        Args:
            files (str): a list of files opportunity files.
            eg. a file contains code regions of all the loops in a program
            or a directory contains all the files of code regions.
            config_file (str): A path to the config file
            where the global search space settings are defined.
        """

        new_xml_tree = self.generate_search_space(files, config_file,
                                                  file_name_filter,
                                                  func_name_filter,
                                                  name_filter,
                                                  type_filter,
                                                  pass_filter)
        new_xml_tree.write(output_file)

    def generate_search_space(self, files, config_file, file_name_filter=None,
                              func_name_filter=None, name_filter=None,
                              type_filter=None, pass_filter=None,
                              config_db=None, use_hash_matching=False,
                              use_prev_configs=False, inject_seed=False):
        """
        Parse opportunities files generated by llvm and return a search space
        as ElementTree.

        Args:
            files (str): a list of files opportunity files.
            eg. a file contains code regions of all the loops in a program
            or a directory contains all the files of code regions.
            config_file (str): A path to the config file
            where the global search space settings are defined.
        Returns:
            new_xml_tree (ElementTree): an ElementTree instance representing a
            search space.
        """

        # new xml file for output
        new_xml_root = xml_writer.Element('tuning_request')
        # if the given path is a directory
        tuning_id = 0
        for filename in files:
            end_tuning_id = _generate_search_space(filename, new_xml_root,
                                                   tuning_id, config_file,
                                                   name_filter,
                                                   func_name_filter,
                                                   file_name_filter,
                                                   type_filter,
                                                   pass_filter)
            tuning_id = end_tuning_id
        # output xml tree into the output_file
        new_xml_tree = xml_writer.ElementTree(new_xml_root)

        return new_xml_tree

    def output_to_file(self, output_file, tree):
        """
        Output an etree.ElementTree into the file
        """
        fd = create_secure_fd(output_file)
        with os.fdopen(fd, 'wb') as output_file_handler:
            tree.write(output_file_handler)

    @staticmethod
    def seed_baseline(task_map, config_db, filepath):
        return None

    def create_dummy_llvm_input(self, output_file):
        # The old version of auto-tuning enabled LLVM doesn't require
        # any dummy llvm config file. Therefore simply do nothing and return.
        return
