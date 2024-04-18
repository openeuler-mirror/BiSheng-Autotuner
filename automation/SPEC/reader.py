# coding=utf-8
"""
Copyright (C) 2017-2020, Huawei Technologies Co., Ltd. All rights reserved.
"""
import os
import sys
from spec_csv_parser import SPECCSVParser

INTSPEED_NAMES = ["600", "602", "605", "620",
                  "623", "625", "631", "641", "648", "657"]
INTRATE_NAMES = ["500", "502", "505", "520",
                 "523", "525", "531", "541", "548", "557"]
FLOATSPEED_NAMES = ["603", "607", "619", "621",
                    "627", "628", "638", "644", "649", "654"]
FLOATRATE_NAMES = ["503", "507", "508", "510", "511",
                   "519", "521", "526", "527", "538", "544", "549", "554"]


def log(*args, extra_line=True):
    if extra_line:
        print("[SPEC AUTOMATION] ", *args, end="\n\n")
    else:
        print("[SPEC AUTOMATION] ", *args)


def find_largest_num(dir: str):
    """
    Find and return the largest SPEC csv order number in dir
    If can't find anything greater than 1, return None
    """
    end = 0
    for filename in os.listdir(dir):
        if filename[:3] == "CPU":  # Only look at files start with "CPU2017"
            number = int(filename[8:11])
            end = max(end, number)
    else:
        return end


def get_infix(benchmark: str, size: str):
    """
    Return the infix from a centain benchmark.
    :param benchmark: SPEC benchmark. Example benchmark: "600"
    :param size: the SPEC input size flag (ref, train, test)
    """
    suite = get_suite(benchmark)
    if size == "ref":
        if suite[-4:] == "rate":
            return suite + ".refrate"
        else:
            return suite + ".refspeed"
    else:
        return suite + '.' + size


def get_suite(benchmark: str):
    """
    Return the suite name from a centain benchmark.
    Example benchmark: "600"
    """
    if benchmark in INTSPEED_NAMES:
        return "intspeed"
    elif benchmark in INTRATE_NAMES:
        return "intrate"
    elif benchmark in FLOATRATE_NAMES:
        return "fprate"
    elif benchmark in FLOATSPEED_NAMES:
        return "fpspeed"
    else:
        log("Invalid benchmark name. Use a number to denote benchmark, " \
            "for ex: '602'")
        sys.exit(1)


def parse_one_csv(filename_template: str, i: int, benchmark: str) -> float:
    """
    Parse one csv file with given order number i
    """
    number = ("%03d" % i) if i < 1000 else str(i)
    filename = filename_template.format(number)

    try:
        return SPECCSVParser().get_runtime(filename, benchmark)
    except FileNotFoundError as _:
        log("File {} cannot be found".format(filename))
        return float("inf")


def parse_baseline(infix: str, benchmark: str, baseline_num: int,
                   result_dir: str):
    """
    Parse and return the runtime of baseline with given params
    """
    filename_template = result_dir + "CPU2017.{}." + infix + ".csv"
    baseline_time = parse_one_csv(filename_template, baseline_num, benchmark)

    return baseline_time


def parse_autotuner(infix: str, benchmark: str, start: int, end: int,
                    result_dir: str):
    """
    Parse and return the minimum runtime of all autotuner results.
    Return None if no runtime found.
    """
    mininum = float("inf")

    filename_template = result_dir + "CPU2017.{}." + infix + ".csv"
    log("THE FILENAMES ARE: " + filename_template.format("<xxx>"))

    log("Start parsing files")
    for i in range(start, end+1):
        mininum = min(mininum, parse_one_csv(filename_template, i, benchmark))

    if mininum == float("inf"):
        log("\nNo file found in directory")
        return None
    else:
        return mininum
