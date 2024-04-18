# coding=utf-8
"""
Copyright (C) 2017-2020, Huawei Technologies Co., Ltd. All rights reserved.
"""
import csv
import os
import stat
import shutil
import sys

from reader import log

FIELDNAMES = ["benchmark", "baseline (s)", "best after tuning (s)",
              "# of iterations", "speedup"]


ALL_BENCHMARKS = {
    "intspeed.csv": ["600.perlbench_s", "602.gcc_s", "605.mcf_s",
                     "620.omnetpp_s", "623.xalancbmk_s", "625.x264_s",
                     "631.deepsjeng_s", "641.leela_s", "648.exchange2_s",
                     "657.xz_s"],
    "intrate.csv": ["500.perlbench_r", "502.gcc_r", "505.mcf_r",
                    "520.omnetpp_r", "523.xalancbmk_r", "525.x264_r",
                    "531.deepsjeng_r", "541.leela_r", "548.exchange2_r",
                    "557.xz_r"],
    "fpspeed.csv": ["603.bwaves_s", "607.cactuBSSN_s", "619.lbm_s",
                    "621.wrf_s", "627.cam4_s", "628.pop2_s", "638.imagick_s",
                    "644.nab_s", "649.fotonik3d_s", "654.roms_s"],
    "fprate.csv": ["503.bwaves_r", "507.cactuBSSN_r", "508.namd_r",
                   "510.parest_r", "511.povray_r", "519.lbm_r", "521.wrf_r",
                   "526.blender_r", "527.cam4_r", "538.imagick_r",
                   "544.nab_r", "549.fotonik3d_r", "554.roms_r"]
}


def init_accumulate(dir: str, filename: str):
    """
    Create an accumulate csv file.

    :param dir: the directory that file should be in
    :param filename: the name of the file that will be created
    """
    benchmarks = ALL_BENCHMARKS.get(filename)
    if benchmarks is None:  # filename is not valid
        print("filename should be one of 'intspeed.csv', 'intrate.csv', \
              'fpspeed.csv', 'fprate.csv'")
        sys.exit(1)

    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
    modes = stat.S_IWUSR | stat.S_IRUSR
    with os.fdopen(os.open(dir + filename, flags, modes), 'w') as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=FIELDNAMES)
        writer.writeheader()
        for benchmark_name in benchmarks:
            writer.writerow({"benchmark": benchmark_name})


def update(suite: str, benchmark: str, baseline: float, autotuner: float,
           iterations: int):
    """
    update csv file with given data
    """

    try:
        flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
        modes = stat.S_IWUSR | stat.S_IRUSR
        with open("{}.csv".format(suite), mode="r") as in_file, os.fdopen(
                os.open("temp.csv", flags, modes), 'w') as temp_file:
            reader = csv.DictReader(in_file)
            writer = csv.DictWriter(temp_file, FIELDNAMES)

            writer.writeheader()
            for row in reader:
                if benchmark in row["benchmark"]:
                    row["baseline (s)"] = baseline
                    row["best after tuning (s)"] = autotuner
                    row["# of iterations"] = iterations
                    row["speedup"] = str(
                        round((baseline / autotuner - 1) * 100,
                        ndigits=2)) + '%'
                writer.writerow(row)

        shutil.move("temp.csv", "{}.csv".format(suite))
        log("ACCUMULATED RESULT CSV SAVED TO {}.csv".format(suite))
    except TypeError as _:
        log("RUNTIME NOT PRODUCED, " +
            "WILL NOT UPDATE AUTOMATION OUTPUT CSV FILES")
        os.remove("temp.csv")
