# coding=utf-8
"""
A set of tools to generate/parse the YAML files for AutoTuning-enabled LLVM
Copyright (C) 2017-2020, Huawei Technologies Co., Ltd. All rights reserved.
"""

from autotuner.dbutils import add_current_code_region
from autotuner.dbutils import clear_config_db
from autotuner.dbutils import get_current_code_regions
from autotuner.dbutils import is_duplicate_hash
from autotuner.dbutils import optimal_config_exists
from autotuner.dbutils import update_optimal_configs
from autotuner.dbutils import get_optimal_config
from autotuner.models import Task
from autotuner.models import CodeRegion
from autotuner.utils import create_secure_fd
from opentuner.search.manipulator import EnumParameter
from opentuner.search.manipulator import IntegerParameter
from opentuner.search.manipulator import FloatParameter
from opentuner.search.manipulator import PermutationParameter
from opentuner.search.manipulator import SelectionParameter

from copy import deepcopy
import json
import logging
import os
import yaml

try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader

from .remarkparser import get_remarks
from .remarkparser import AutoTuning
from autotuner.iomanager import EmptySearchSpaceError
from autotuner.iomanager import IOManager

log = logging.getLogger(__name__)


def _apply_code_region_filter(string, filer_list):
    if filer_list and string != "undefined":
        return string in filer_list
    else:
        return True


def _parse_param(tuning_id, yaml_param, ele):
    """
    Help function to return a enumeration list based on param type
    """
    param_type = yaml_param["Type"]

    if param_type == "bool":
        return EnumParameter(str(tuning_id) + ele, ["1", "0"])

    elif param_type == "enum":
        options = yaml_param['Value']
        return EnumParameter(str(tuning_id) + ele, options)

    elif param_type == "range":
        # Keep param_type == "range" for backwards compatability
        min_value = int(yaml_param["min"])
        max_value = int(yaml_param["max"])
        return IntegerParameter(str(tuning_id) + ele, min_value, max_value)

    elif param_type == "int":
        min_value = int(yaml_param["Min"])
        max_value = int(yaml_param["Max"])
        return IntegerParameter(str(tuning_id) + ele, min_value, max_value)

    elif param_type == "float":
        min_value = float(yaml_param["Min"])
        max_value = float(yaml_param["Max"])
        return FloatParameter(str(tuning_id) + ele, min_value, max_value)

    elif param_type == "permutation":
        options = yaml_param['Value']
        return PermutationParameter(str(tuning_id) + ele, options)

    elif param_type == "selection":
        options = yaml_param['Value']
        return SelectionParameter(str(tuning_id) + ele, options)

    else:
        raise Exception("No type specified for params in file")


def _update_program_param_code_regions(config_db, code_region):
    """
    This function does similar thing as _update_current_code_regions().
    This function is added to handle program-param explicitly.
    """
    add_current_code_region(config_db, code_region, seen=False)
    if (is_duplicate_hash(config_db,
        code_region['Hashcode'], code_region["CodeRegionType"],
        code_region["Pass"])):
        return False
    return True


def _update_current_code_regions(config_db, code_region, use_hash_matching,
                                 use_prev_configs, inject_seed):
    """
    Stores `code_region` into the CurrentCodeRegions table and determines if
    it should be added to the search space.
    A code_region should be added to the search space iff
        1. There is no configuration found in OptimalConfigs AND
           We have not yet encountered a code region with the same
           (hash, type, pass) triple during this tuning run.
        2. If an optimal configuration found AND
           we want to use optimal configuration for re-tuning.

    Args:
        config_db: databse to look for optimal configurations.
        code_region: code region under consideration.
        use_hash_matching: Enable code region pruning.
        use_prev_configs: Reuse the optimal configurations found (if any) and
           tune the remaining code regions.
        inject_seed: Use the optimal configurations found as starting point
           and re-tune all code regions.

    Returns True iff the given code_region should be added to the search space.
    """
    if (use_prev_configs and optimal_config_exists(config_db,
            code_region['Hashcode'], code_region["CodeRegionType"],
            code_region["Pass"])):
        add_current_code_region(config_db, code_region, seen=True)
        if inject_seed and not is_duplicate_hash(config_db,
                code_region['Hashcode'], code_region["CodeRegionType"],
                code_region["Pass"]):
            return True
        return False
    else:
        add_current_code_region(config_db, code_region, seen=False)

    if (use_hash_matching and is_duplicate_hash(config_db,
            code_region['Hashcode'], code_region["CodeRegionType"],
            code_region["Pass"])):
        return False
    return True


def _generate_search_space(file_path, yaml_list, start_tuning_id,
                      config_file, name_filter, func_name_filter,
                      file_name_filter, type_filter, pass_filter,
                      config_db, use_hash_matching, use_prev_configs,
                      inject_seed):
    tuning_id = start_tuning_id
    coderegion_found = 0

    # Stores the possible configurations for a given type (type, pass) -> param
    global_param_config = {}

    # search space of yaml configuration file
    with open(config_file) as config_file_handler:
        config_dic = yaml.load_all(config_file_handler, Loader=yaml.FullLoader)

        for code_region in config_dic:
            global_params = code_region['CodeRegion']["Args"]
            if global_params is not None:
                type_pass_tuple = (
                    code_region['CodeRegion']["CodeRegionType"],
                    code_region['CodeRegion']['Pass'])
                global_param_config[type_pass_tuple] = global_params
    # A list of all opportunites found by the compiler
    remarks_list = get_remarks(file_path)
    for remark in remarks_list:
        code_region = {}
        type_pass_tuple = (remark.CodeRegionType, remark.Pass)
        if type_pass_tuple in global_param_config:
            coderegion_found += 1
            code_region['Function'] = (remark.Function if
                                       hasattr(remark, 'Function') else "")
            code_region['Name'] = (remark.Name if
                                   hasattr(remark, 'Name') else "")
            code_region['CodeRegionType'] = remark.CodeRegionType
            code_region['Pass'] = remark.Pass
            code_region['Hashcode'] = str(remark.CodeRegionHash)
            code_region['BaselineConfig'] = (remark.BaselineConfig if
                                             hasattr(remark, 'BaselineConfig')
                                             else {})
            # DynamicConfigs is a dic: str -> list[int].
            # Where the str represents a tuning parameter associated with the
            # code region. List[int] represent the possible dynamic tuning
            # values associated with the tuning parameter.
            code_region['DynamicConfigs'] = (remark.DynamicConfigs
                                      if hasattr(remark, 'DynamicConfigs')
                                      else None)
            code_region['Invocation'] = str(remark.Invocation
                                            if hasattr(remark, 'Invocation')
                                            else "0")
            filtered = _apply_code_region_filter(code_region['Function'],
                                                 func_name_filter) and \
                _apply_code_region_filter(code_region['CodeRegionType'],
                                          type_filter) and \
                _apply_code_region_filter(code_region['Name'],
                                          name_filter) and \
                _apply_code_region_filter(code_region['Pass'], pass_filter)
            if hasattr(remark, "DebugLoc"):
                code_region['DebugLoc'] = {"File": remark.File,
                                           "Line": remark.Line,
                                           "Column": remark.Column}
                filtered = filtered and _apply_code_region_filter(
                    remark.File, file_name_filter)

            should_add = True
            if filtered:
                if code_region.get('CodeRegionType') == "program-param":
                    should_add = \
                        _update_program_param_code_regions(config_db, code_region)
                elif use_hash_matching:
                    should_add = _update_current_code_regions(
                        config_db, code_region, use_hash_matching,
                        use_prev_configs, inject_seed
                    )
                if not should_add:
                    continue

                # Add this code region to the search space
                tuning_id += 1
                param = global_param_config[type_pass_tuple]
                yaml_list.append({'TuningId': tuning_id,
                                  'CodeRegion': code_region, 'Params': param})

    # return the last tuning id and code regions found in this file.
    return tuning_id, coderegion_found


def _prepare_remarks(configuration_data, task_map, use_hash_matching):
    """
    Returns a collections of remarks for a given configuration and task_map.
    If hash_matching is not on: Returns a dict of (hash, type) -> Remark.
                                Represents configurations for all
                                equivalence classes in the search space.
    Otherwise: Returns a list of all remarks in the search space.
    """
    remark_lookup = dict()
    remark_list = []

    # loop through the task map to generate llvm input file for
    # tuning-enabled LLVM
    for tuning_id, task in task_map.items():
        remark = code_region_to_remark(task.code_region)
        remark.Args = []

        # construct the param
        for param in task.param_list:
            # Since param.name is in the form of ID+Param
            # (e.g. 14UnrollCount), only remove the first occurrence.
            raw_param_name = param.name.replace(str(tuning_id), "", 1)

            if raw_param_name == "OptPass":
                remark.Args.append({"OptPass": []})
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
                    remark.Args[0]["OptPass"] = pass_list

            elif raw_param_name == "MachineScheduling":
                if configuration_data[param.name] == "TopDown":
                    remark.Args.append({"ForceBottomUp": 0})
                    remark.Args.append({"ForceTopDown": 1})
                elif configuration_data[param.name] == "BottomUp":
                    remark.Args.append({"ForceBottomUp": 1})
                    remark.Args.append({"ForceTopDown": 0})
                else:
                    # Bidirectional
                    remark.Args.append({"ForceBottomUp": 0})
                    remark.Args.append({"ForceTopDown": 0})
            else:
                data = {}
                data[str(raw_param_name)] = configuration_data[param.name]
                remark.Args.append(data)

        # add this new created remark into the remark list
        if use_hash_matching:
            # If we are using the config db, only store the configs for
            # (hash, type, pass) equivalance classes.
            key = (remark.CodeRegionHash, remark.CodeRegionType, remark.Pass)
            remark_lookup[key] = remark
        else:
            # If we aren't using the config db,
            # store the configurations for all remarks.
            remark_list.append(remark)

    return remark_lookup if use_hash_matching else remark_list


def _construct_remarks(configuration_data, task_map, config_db,
                          use_hash_matching, fixed_llvm_input=None):
    """
    Build a list of remarks ready to be serialized for tuning-enabled LLVM
    based on the task_map and configuration_data.

    Args:
        configuration_data: configuration data generated in each iteration
        of tuning.

        task_map (dict of int: Task): A task map where the key is a tuning
        id and the value is a Task which specifies CodeRegion and
        Parameters. Contains all Code Regions in the search space.

        fixed_llvm_input (list of remarkparser.AutoTuning): existing fixed
        configuration data to be appended into the current
        configuration_data for the llvm input file being generated.

        config_db (String): path to the configuration database (configs.db)
        or None if no connection has been made.

        use_hash_matching (Bool): Flag determining if identical hashes have
        been filered out of the search space.
    """

    # a list of Autotuning remarks that will be dumped into a file
    remark_list = []
    program_param_remark = None

    # The remarks from opporutunities in the search space.
    # If use_hash_matching == True, will be
    #   a dictionary of equivalance classes (hash, type, pass).
    # Otherwise, will be a list of remarks.
    remark_lookup = _prepare_remarks(
        configuration_data, task_map, use_hash_matching
    )
    # There is at most one program-param within the remark_lookup and we want to
    # filter out the arguments that the only program-param code region has
    # If use_hash_matching is set to ture, the remark_loopup is a dict type
    # which would be updated in the same way as llvm-param.
    if not use_hash_matching:
        program_param_remark_list = list(filter(lambda r: r.CodeRegionType == "program-param", remark_lookup))
        if len(program_param_remark_list) == 1:
            # There is at most one program-param code region.
            program_param_remark = program_param_remark_list[0]
            remark_lookup.remove(program_param_remark)
        elif len(program_param_remark_list) == 0:
            # Program-param code region is not found.
            pass
        else:
            # Report error if multiple program-param code regions are found.
            log.error("More than one program-params code region found.")

    # add the existing auto-tuning remarks
    # as the constant configuration into the current llvm input
    # file being generated.
    if (fixed_llvm_input and len(fixed_llvm_input) >= 1):
        remark_list += fixed_llvm_input

    # For each code region in CurrentCodeRegions, create a remark.
    if config_db:
        for code_region_config in get_current_code_regions(config_db):
            code_region = code_region_config.code_region
            remark = code_region_to_remark(code_region)

            if code_region_config.parameters:
                # Parameters from a previous tuning run exist
                # and we will use those.
                remark.Args = code_region_config.parameters
            else:
                # No previous parameters exist.
                # Use the ones found in the current run.
                if not use_hash_matching:
                    # When use_hash_matching is false, remark_lookup is a list object.
                    # If program_param_remark is found, we want to use the same arguments
                    # for all remarks.
                    if program_param_remark and remark.CodeRegionType == "program-param":
                        remark.Args = program_param_remark.Args
                        remark_list.append(remark)
                    continue
                # Find the arguments for the corresponding
                # (hash, type, pass) triple.
                key = (int(code_region.hashcode),
                code_region.code_region_type,
                code_region.pass_name)
                remark.Args = remark_lookup[key].Args
            remark_list.append(remark)

    if not use_hash_matching:
        # Add in all remarks from the search space.
        # If the config_db is not used, all remarks will be in the list.
        # If only use_prev_configs == True,
        #   all previously unseen remarks will be in the list
        # Note all program-param related code regions have already been added.
        for remark in remark_lookup:
            remark_list.append(remark)

    return remark_list


def code_region_to_remark(code_region):
    """
    Create a remark with the fields of `code_region`
    """
    remark = AutoTuning()
    if len(code_region.name) > 0:
        remark.Name = code_region.name
    if len(code_region.func_name) > 0:
        remark.Function = code_region.func_name
    remark.CodeRegionType = code_region.code_region_type
    remark.CodeRegionHash = int(code_region.hashcode)
    remark.Invocation = int(code_region.invocation)
    if code_region.debug_loc:
        remark.DebugLoc = {}
        remark.DebugLoc['File'] = code_region.debug_loc.file_name
        remark.DebugLoc['Line'] = code_region.debug_loc.line
        remark.DebugLoc['Column'] = code_region.debug_loc.column
    remark.Pass = code_region.pass_name

    return remark


class YAMLManager(IOManager):
    def get_file_extension(self):
        return ".yaml"


    def parse_search_space(self, search_space, use_dynamic_values = False,
                           use_baseline_config = False, filepath = None):
        """
        Parse the yaml search space config file to init the tuner

        Args:
            search_space: A string representing the path to search space file
            or an dictionary representing search space.
        Returns:
            task_map (dict of int: Task): A task map where the key is a tuning
            id and the value is a Task which specifies CodeRegion and
            Parameters.

        """
        task_map = {}
        yaml_list = []
        seed_configuration = dict()
        options = dict()

        # if search_space is a list already
        if isinstance(search_space, list):
            yaml_list = search_space
        # else we parse the file and get an list
        else:
            with open(search_space) as sfile:
                # The FullLoader parameter handles the conversion from YAML
                # scalar values to Python the dictionary format
                yaml_temp = yaml.load_all(sfile, Loader=Loader)
                for info in yaml_temp:
                    yaml_list.append(info)

        # Make it to be set() to avoid duplicate CodeRegion.
        code_region_set = set()

        # if the root does not have any children, search space is empty.
        if not yaml_list:
            raise EmptySearchSpaceError("empty search space")

        # Loop through the task elements in the yaml_list to create a task map.
        for yaml_elem in yaml_list:
            tuning_id = yaml_elem['TuningId']
            param_list_yaml = yaml_elem['Params']

            # Retrieve available (multiple) baseline compiler decisions (stored
            # as dictionary).
            baseline_dic = {}
            if "BaselineConfig" in yaml_elem["CodeRegion"]:
                baseline_dic = yaml_elem["CodeRegion"]["BaselineConfig"]

            # Retrieve all possible dynamic args available.
            dynamic_dic = {}
            if 'DynamicConfigs' in yaml_elem['CodeRegion']:
                dynamic_dic = yaml_elem['CodeRegion']['DynamicConfigs']

            tune_compilation_flags = False
            if ((yaml_elem['CodeRegion']['CodeRegionType'] == 'program-param') or
                    (yaml_elem['CodeRegion']['CodeRegionType'] == 'llvm-param')):
                tune_compilation_flags = True

            param_list = []
            # loop through the task elements in yaml file
            for ele in param_list_yaml.keys():
                options = {}
                if use_dynamic_values and ele in dynamic_dic:
                    options['Type'] = param_list_yaml[ele]['Type']
                    options['Value'] = dynamic_dic[ele]
                else:
                    options = param_list_yaml[ele]
                param = _parse_param(tuning_id, options, ele)
                param_name = str(tuning_id) + str(ele)

                baseline_config = None
                # Fetch the baseline compiler decisions for Loop and CallSite
                # code region recorded dynamically durning baseline compilation.
                if ele in baseline_dic:
                    baseline_config = baseline_dic[ele]
                # Fetch baseline/default values for compiler flags statically
                # stored in 'extended_search_space.yaml' file for LLVMParam and
                # ProgramParam code regions.
                if tune_compilation_flags:
                    baseline_config = (options['Default']
                                            if 'Default' in options
                                            else param.seed_value())
                seed_configuration[param_name] = (param.seed_value()
                                                  if (baseline_config is None)
                                                  else baseline_config)
                if param:
                    param_list.append(param)

            if param_list:
                # retrieve code_region information from yaml
                code_region_yaml = yaml_elem["CodeRegion"]
                code_region = CodeRegion(code_region_yaml["Pass"],
                                         code_region_yaml["Name"],
                                         code_region_yaml["Function"],
                                         code_region_yaml["CodeRegionType"],
                                         code_region_yaml["Hashcode"],
                                         code_region_yaml["Invocation"])
                if 'DebugLoc' in code_region_yaml:
                    code_region.set_debug_loc(code_region_yaml['DebugLoc'])

                if code_region not in code_region_set:
                    code_region_set.add(code_region)
                    task_map[int(tuning_id)] = Task(int(tuning_id),
                                                    param_list, code_region)
        if use_baseline_config:
            with open(filepath, 'w') as file:
                json.dump(seed_configuration, file)

        return task_map


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

        yaml_list = self.generate_search_space(files, config_file,
                                               file_name_filter,
                                               func_name_filter, name_filter,
                                               type_filter, pass_filter,
                                               config_db, use_hash_matching,
                                               use_prev_configs, inject_seed)
        self.output_to_file(output_file, yaml_list)


    def generate_search_space(self, files, config_file, file_name_filter=None,
                              func_name_filter=None, name_filter=None,
                              type_filter=None, pass_filter=None,
                              config_db=None, use_hash_matching=False,
                              use_prev_configs=False, inject_seed=False):
        """
        Parse opportunities files generated by llvm and return a search space
        as list.

        Args:
            files (str): a list of files opportunity files.
            eg. a file contains code regions of all the loops in a program
            or a directory contains all the files of code regions.
            config_file (str): A path to the config file
            where the global search space settings are defined.
        Returns:
            a new list type object represents the search space file
        """

        # since module is other in yaml format, then replace it
        if type_filter and ("module" in type_filter):
            type_filter[type_filter.index("module")] = "other"

        # Clear the currentCodeRegion table from the database
        if config_db:
            clear_config_db(config_db)

        # new yaml file for output
        yaml_list = []
        # if the given path is a directory
        # Total coderegions found in opportunity files.
        total_coderegion_found = 0
        # ID to keep track of code regions added to create search space.
        tuning_id = 0
        for filename in files:
            end_tuning_id, coderegion_found = _generate_search_space(filename,
                                                   yaml_list, tuning_id,
                                                   config_file, name_filter,
                                                   func_name_filter,
                                                   file_name_filter,
                                                   type_filter, pass_filter,
                                                   config_db, use_hash_matching,
                                                   use_prev_configs,
                                                   inject_seed)
            tuning_id = end_tuning_id
            total_coderegion_found += coderegion_found

        if total_coderegion_found == 0:
            log.error("No code region found in the opportunity files.")
        else:
            log.debug("Total code regions found: %d", total_coderegion_found)
            log.debug("Code regions added: %d", tuning_id)

        return yaml_list


    @staticmethod
    def update_config_db(configuration_data, task_map,
                         fixed_llvm_input=None, config_db=None,
                         use_hash_matching=True):
        remark_list = _construct_remarks(configuration_data, task_map,
                                config_db, use_hash_matching, fixed_llvm_input)
        update_optimal_configs(config_db, remark_list)


    def build_llvm_input(self, configuration_data, task_map, output_file,
                         fixed_llvm_input=None, config_db=None,
                         use_hash_matching=False):
        """
        Build an input yaml file for tuning-enabled LLVM based on task_map and
        configuration_data, and output as output_file
        """
        remark_list = _construct_remarks(
            configuration_data, task_map,
            config_db, use_hash_matching, fixed_llvm_input)
        self.output_to_file(output_file, remark_list)

    def generate_baseline_llvm_input(self, output_file, config_db=None):
        remark_list = []
        for code_region_config in get_current_code_regions(config_db,
                                                           ignore_seen=True):
            if code_region_config.parameters is None:
                # Skip the code region if no previous setting was found.
                continue
            code_region = code_region_config.code_region
            remark = code_region_to_remark(code_region)
            remark.Args = code_region_config.parameters
            remark_list.append(remark)

        if len(remark_list) == 0:
            self.create_dummy_llvm_input(output_file)
        else:
            self.output_to_file(output_file, remark_list)


    @staticmethod
    def seed_baseline(task_map, config_db, filepath):
        """
        Generate a configuration consisting of past opportunities stored in
        config_db (if it exists). For each opportunity in the task_map,
        initialize the configuration with the parameters found in config_db,
        or randomly otherwise.
        """
        seed_configuration = dict()
        for task_id, tuning_task in task_map.items():
            # task_map: int --> (ID, param_list, Coderegion)
            task_hash = tuning_task.code_region.hashcode
            task_pass = tuning_task.code_region.pass_name
            task_type = tuning_task.code_region.code_region_type
            stored_params = get_optimal_config(config_db, task_hash,
                                               task_type, task_pass)
            if stored_params:
                param_map = {k: v for x in stored_params for k, v in x.items()}
            else:
                param_map = None

            for param in tuning_task.param_list:
                if param_map is None:
                    # If there is no associated configuration, initialize
                    # it to some random value (Opentuner implementation).
                    seed_configuration[param.name] = param.seed_value()
                else:
                    raw_name = param.name.replace(str(task_id), "", 1)
                    if raw_name == "MachineScheduling":
                        seed_configuration[param.name] = param_map
                    elif raw_name == "OptPass":
                        # Creating parameter according to SelectionParameter.
                        parameter = deepcopy(param_map)
                        parameter['order'] = parameter.pop(raw_name)
                        parameter['size'] = len(parameter['order'])
                        seed_configuration[param.name] = parameter
                    elif raw_name in param_map:
                        seed_configuration[param.name] = param_map[raw_name]
                    else:
                        # In case the user changes the search space,
                        # there may be unseen paramters that are not stored.
                        seed_configuration[param.name] = param.seed_value()

        with open(filepath, 'w') as file:
            json.dump(seed_configuration, file)
        return filepath


    def parse_llvm_inputs(self, input_files):
        """
        Parse a list of llvm yaml input files
        Args:
            input_files (a list of str): a list of llvm yaml input files.
        Returns:
            result list: a list that represent the merged yaml input file
        """
        result_list = []
        for input_file in input_files:
            remarks = get_remarks(input_file)
            result_list += remarks
        return result_list

    def output_to_file(self, output_file, remark_list):
        fd = create_secure_fd(output_file)
        with os.fdopen(fd, 'w') as output_file_handler:
            yaml.dump_all(
                remark_list,
                output_file_handler,
                width=1200,
                default_flow_style=True
            )


    def divide_llvm_input(self, input_file):
        remark_map = {}
        remarks = get_remarks(input_file)
        for remark in remarks:
            if hasattr(remark, "DebugLoc"):
                if remark.DebugLoc["File"] in remark_map.keys():
                    remark_map[remark.DebugLoc["File"]].append(remark)
                else:
                    remark_map[remark.DebugLoc["File"]] = [remark]
            else:
                if ("no_name" in remark_map.keys()):
                    remark_map["no_name"].append(remark)
                else:
                    remark_map["no_name"] = [remark]
        return remark_map


    def create_dummy_llvm_input(self, output_file):
        dummy_remark = AutoTuning()
        dummy_remark.Name = "dummy"
        dummy_remark.Function = "dummy_function"
        dummy_remark.Pass = "dummy_pass"
        dummy_remark.CodeRegionType = "other"
        dummy_remark.CodeRegionHash = 0

        remark_list = [dummy_remark]
        self.output_to_file(output_file, remark_list)
