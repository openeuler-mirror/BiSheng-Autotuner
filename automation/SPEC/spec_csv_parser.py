# coding=utf-8
"""
Copyright (C) 2017-2020, Huawei Technologies Co., Ltd. All rights reserved.
"""
import csv
import sys


class SPECCSVParser:
    """
    A CSV parser wrapper for SPEC
    """

    def print_all_csv(self, csv_file: str):
        """
        Print all lines in a csv_file
        """
        with open(csv_file, 'r') as file:
            reader = csv.reader(file)
            for i, row in enumerate(reader):
                print("[{0}] {1}".format(i, row))

    def get_runtime(self, csv_file: str, benchmark: str):
        """
        Return the SPEC runtime in given csv_file
        """
        print("[SPEC AUTOMATION]: NOW PARSE FILE: {}".format(csv_file))
        with open(csv_file, 'r') as file:
            reader = csv.reader(file)
            # loop over the Full Results Table. Ending in line 17
            try:
                i = 0
                while True:
                    i += 1
                    line = next(reader)
                    if len(line) > 0 and benchmark in line[0]:
                        return float(line[2])
            except ValueError as _:
                print(
                    "[SPEC AUTOMATION]: Error: cannot parse line {} " \
                    "with data {}".format(i, line))
                return float("inf")
            except StopIteration as _:
                print("[SPEC AUTOMATION]: Error: cannot find result " \
                "of {} in {}".format(
                    benchmark, csv_file))
                return float("inf")


if __name__ == "__main__":
    filename = sys.argv[1]
    parser = SPECCSVParser()
    print(parser.print_all_csv(filename))
