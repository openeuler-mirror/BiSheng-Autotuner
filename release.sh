#!/bin/bash

# Script to package autotuner for release purposes
# Copyright (C) 2017-2020, Huawei Technologies Co., Ltd. All rights reserved.

python3 -m pip install "wheel==0.34.2" --user
python3 -m pip install "pyc_wheel==1.2.2" --user

SCRIPT_PATH=$(dirname $(realpath -s $0))
DESTDIR=$1

rm -rf $SCRIPT_PATH/dist; mkdir $SCRIPT_PATH/dist
python3  setup.py  bdist_wheel  -d $SCRIPT_PATH/dist/wheel || exit 1;

python3 -m pyc_wheel  $SCRIPT_PATH/dist/wheel/autotuner-*.whl  || exit 1;

mkdir $SCRIPT_PATH/dist/config
cp  $SCRIPT_PATH/config/coremark_sample.ini $SCRIPT_PATH/dist/config || exit 1;
cp  $SCRIPT_PATH/config/dhrystone_sample.ini $SCRIPT_PATH/dist/config || exit 1;

mkdir $SCRIPT_PATH/dist/plugin
cp  $SCRIPT_PATH/plugin/coremark_tuner.py $SCRIPT_PATH/dist/plugin || exit 1;
cp  $SCRIPT_PATH/plugin/dhrystone_tuner.py $SCRIPT_PATH/dist/plugin || exit 1;

if [ -n "$DESTDIR" ]; then
  if mkdir -p "$DESTDIR"; then
    echo "Copying installables to $DESTDIR/autotuner"
    cp -avT $SCRIPT_PATH/dist "$DESTDIR/autotuner"
  else
    echo "Could not create installation directory: $DESTDIR"
    exit 1
  fi
else
  echo "Creating tar achive for distribution"
  tar -czvf $SCRIPT_PATH/dist.tar.gz $SCRIPT_PATH/dist/
  echo "The distribution achive has been created to  $SCRIPT_PATH/dist/ and $SCRIPT_PATH/dist.tar.gz"
fi
