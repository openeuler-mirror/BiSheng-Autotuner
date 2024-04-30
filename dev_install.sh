#!/bin/bash -e

# Script to install autotuner
# Copyright (C) 2017-2020, Huawei Technologies Co., Ltd. All rights reserved.

SCRIPT_DIR=$(dirname $(realpath -s $0))
PYTHONPATH=$SCRIPT_DIR:$SCRIPT_DIR/../opentuner:$PYTHONPATH
export PYTHONPATH

usage() {
cat <<EOF
Usage: $0 [option]

Install autotuner command in development mode

Options:
  -h          Display this help message.
  -t          Test autotuner after installation.
  --test-only Test autotuner without installing it.
  --test-installation Test the autotuner installation script.
EOF
}

run_tests() {
    python3 -m unittest discover -s $SCRIPT_DIR/autotuner/test/ --buffer
}

run_install() {
    python3 -m pip install "$SCRIPT_DIR" --user
}

if [[ "$1" = "-h" ]];
then
    usage
    exit
elif [[ "$1" = "-t" ]];
then
    run_install
    run_tests
elif [[ "$1" = "--test-only" ]];
then
    run_tests
    exit
elif [[ "$1" = "--test-installation" ]];
then
    $SCRIPT_DIR/../huawei/autotuner-install-test.sh
    exit
else
    run_install
fi
