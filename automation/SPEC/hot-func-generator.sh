#!/bin/sh -e

# Script for generating hot functions
# Copyright (C) 2017-2020, Huawei Technologies Co., Ltd. All rights reserved.

TUNE=base
CONFIG=llvm.cfg
BENCHMARK_NUMBER=$1
BENCHMARK_NAME=$2
LLVM_LIB=$3
PARTERRN=${BENCHMARK_NAME}_${TUNE}

echo "Building benchmark."
runcpu --config=$CONFIG -a build --noreportable $BENCHMARK_NUMBER --define LLVM_DIR=$LLVM_LIB --copies=1 --threads=1 >/dev/null 2>&1
echo "Building done, now start running."
runcpu --config=$CONFIG -a onlyrun --size=train --noreportable $BENCHMARK_NUMBER --define LLVM_DIR=$LLVM_LIB --copies=1 --threads=1  >/dev/null 2>&1 &
sleep 30

SPECPID=$(ps x | grep $PARTERRN | awk '{print $1,$3}'  | grep R | awk '{print $1}'| sed -n '1p')

set -x
perf record  -e cycles -p "$SPECPID" -o "perf.data.${BENCHMARK_NUMBER}_${BENCHMARK_NAME}"
set +x

killcmd="kill $SPECPID >/dev/null 2>&1"
trap "$killcmd" EXIT SIGINT SIGTERM

OUTPUT=$(perf report -i perf.data.${BENCHMARK_NUMBER}_${BENCHMARK_NAME}  --hierarchy --stdio)
echo "${OUTPUT}" > hot_function_${BENCHMARK_NUMBER}_${BENCHMARK_NAME}.csv
