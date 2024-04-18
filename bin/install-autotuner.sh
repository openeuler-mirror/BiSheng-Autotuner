#!/bin/bash
#
# *****************************************************************************
# Copyright: (c) Huawei Technologies Co., Ltd. 2022. All rights reserved.
# Huawei BiSheng Autotuner installation script.
# *****************************************************************************

# Install BiSheng Autotuner and its dependencies using pip3. Requires Python 3.10.

curr_dir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null && pwd )"

python3=$(type -p python3)
if [ -z "$python3" -o ! -x "$python3" ]; then
  echo "$0: error: no usable Python 3"
  exit 1
fi

if ! $python3 -m pip --version > /dev/null 2>&1; then
  echo "$0: error: no usable pip"
  exit 1
fi

minorversion=$($python3 -c 'import platform; print(platform.python_version_tuple()[1])')
if [ "$minorversion" != "10" ]; then
  echo "$0: warning: Python 3.10 is recommended"
fi

pipversion=$($python3 -m pip --version 2>&1 | cut -f1 -d. | tr -dc 0-9)
if [ -z "$pipversion" ]; then
  echo "$0: error: no usable pip"
  exit 1
elif [ $pipversion -lt 21 ]; then
  echo "$0: warning: pip version is too old; automatically upgrading pip with the command '$python3 -m pip install pip --user --upgrade'"
  $python3 -m pip install pip --user --upgrade
fi

# Locate the .whl files to install. Fetch the newest version (last in
# alphabetical order) in case there are multiple matching files.
opentunerglob=( $curr_dir/../lib/autotuner/huawei_opentuner-*-py3-none-any.whl )
autotunerglob=( $curr_dir/../lib/autotuner/autotuner-*-py3-none-any.whl )
$python3 -m pip install --user --force-reinstall "${opentunerglob[-1]}" "${autotunerglob[-1]}"
