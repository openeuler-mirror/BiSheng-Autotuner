#!/bin/bash

# Copyright (C) 2017-2023, Huawei Technologies Co., Ltd. All rights reserved.

SHELL_FOLDER=$(cd "$(dirname "$0")";pwd)
cd $SHELL_FOLDER

# User settings
LLVM_DIR="$HOME/llvm-project/install"
Clang="$LLVM_DIR/bin/clang"
ClangXX="$LLVM_DIR/bin/clang++"
LLVMAutotune="$HOME/llvm-project/autotuner/bin/llvm-autotune"
MySQLWorkspace="$HOME/Mysql_sysbench/XXX"
MySQLUser="root"
MySQLDB="loadtest"
MySQLPort="3306"
MySQLHost=$(hostnamectl | grep hostname | awk '{print $3}')
MySQLPassword="123456"

if [ ! -x "$Clang" -o ! -x "$ClangXX" -o ! -x "$LLVMAutotune" ]; then
  echo "Error: $Clang, $ClangXX or $LLVMAutotune not found or not executable"
  exit 1
fi

if [ ! -e "$MySQLWorkspace" ]; then
  echo "Error: $MySQLWorkspace does not exist"
  exit 1
fi

# Other paths
SearchSpace="$MySQLWorkspace/custom_search_space.yaml"
MySQLServer="$MySQLWorkspace/mysql-server-mysql-cluster-8.0.28"
MySQLConfig="$MySQLWorkspace/my.cnf"
MySQLLuaDir="$MySQLWorkspace/sysbench/install/share/sysbench/"
MySQLCommand="sysbench oltp_read_write.lua --tables=10 --table-size=10000 \
  --mysql-user=$MySQLUser --mysql-db=$MySQLDB --mysql-port=$MySQLPort \
  --mysql-host=$MySQLHost  --mysql-password=$MySQLPassword --threads=96 \
  --report-interval=10 --time=60"

# Generate opportunity files under ./tmp/autotuner_data_$Date/opp
if [ "$1" = "generate" ]; then
  
  Date=`date "+%d%H-%M%S"`
  export AUTOTUNE_DATADIR=$SHELL_FOLDER/tmp/autotuner_data_$Date/
  mkdir -p $AUTOTUNE_DATADIR
  echo `date "+%d-%H-%M"` "Start compiling and generating tuning opportunities:\n"
  cd $MySQLServer/build
  export CC=$Clang
  export CXX=$ClangXX
  cmake .. -DBUILD_CONFIG=mysql_release \
    -DCMAKE_INSTALL_PREFIX=$MySQLWorkspace/install \
    -DMYSQL_DATADIR=$MySQLWorkspace/data \
    -DCMAKE_C_FLAGS="-O3 -mcpu=tsv110 -fautotune-generate=LLVMParam" \
    -DCMAKE_CXX_FLAGS="-O3 -mcpu=tsv110 -fautotune-generate=LLVMParam" \
    -DWITH_BOOST=../boost_1_73_0 -DWITH_UNIT_TESTS=0
  make clean
  make -s -j $(nproc)
  make install

# Generate initial configuration for a new autotuner run under $AUTOTUNE_DATADIR
elif [ "$1" = "minimize" ]; then
  
  if [ -z "$AUTOTUNE_DATADIR" ]; then
    export AUTOTUNE_DATADIR=$2
  fi
  echo `date "+%d-%H-%M"` "Start generating initial autotuner configuration:\n"
  $LLVMAutotune minimize --search-space=$SearchSpace --name-filter \
    $MySQLServer/sql-common/net_serv.cc $MySQLServer/sql-common/client.cc \
    $MySQLServer/libmysql/libmysql.cc $MySQLServer/mysys/my_alloc.cc \
    $MySQLServer/vio/viosocket.cc $MySQLServer/sql-common/bind_params.cc \
    $MySQLServer/mysys/my_malloc.cc $MySQLServer/mysys/pack.cc

# Run the first iteration of autotuner
# Rebuild the entire MySQL since cmake flags change from the previous stage.
elif [ "$1" = "run-one" ]; then
  
  if [ -z "$AUTOTUNE_DATADIR" ]; then
    export AUTOTUNE_DATADIR=$2
  fi
  cd $MySQLServer/build
  cmake .. -DBUILD_CONFIG=mysql_release \
    -DCMAKE_INSTALL_PREFIX=$MySQLWorkspace/install \
    -DMYSQL_DATADIR=$MySQLWorkspace/data \
    -DCMAKE_C_FLAGS="-O3 -mcpu=tsv110 -fautotune" \
    -DCMAKE_CXX_FLAGS="-O3 -mcpu=tsv110 -fautotune" \
    -DWITH_BOOST=../boost_1_73_0 -DWITH_UNIT_TESTS=0
  make clean
  make -s -j $(nproc)
  make install
  if [ $? -eq 0 ]; then
    # Run sysbench
    cd $MySQLLuaDir
    tempfile=$(mktemp)
    tempfile=${tempfile##*/}
    $MySQLCommand cleanup
    $MySQLCommand prepare
    $MySQLCommand run | tee $tempfile
    transactions=$(grep 'transactions:' $tempfile | awk '{print $3}')
    score=${tps:1:-3}
    echo "Score: $score tps"
    $LLVMAutotune feedback -$score
    rm $tempfile
  else
    $LLVMAutotune feedback 9999
  fi

# Run autotuner for a custom number of iterations
# No need to rebuild the entire MySQL since cmake flags do not change 
# from the previous stage
elif [ "$1" = "autotune" ]; then
  Iteration=$2
  if [ -z "$AUTOTUNE_DATADIR" ]; then
    export AUTOTUNE_DATADIR=$3
  fi
  for i in $(seq $Iteration); do
    # Compile MySQL
    cd $MySQLServer/build/libmysql && make clean
    cd $MySQLServer/build/mysys && make clean
    cd $MySQLServer/build/vio && make clean
    cd ..
    make -s -j $(nproc)
    make install
    if [ $? -eq 0 ]; then
      # Run sysbench
      cd $MySQLLuaDir
      tempfile=$(mktemp)
      tempfile=${tempfile##*/}
      $MySQLCommand cleanup
      $MySQLCommand prepare
      $MySQLCommand run | tee $tempfile
      tps=$(grep 'transactions:' $tempfile | awk '{print $3}')
      score=${tps:1}
      echo "Iteration: $i, Score: $score tps"
      $LLVMAutotune feedback -$score
      rm $tempfile
    else
      $LLVMAutotune feedback 9999
    fi
  done
  echo `date "+%d-%H-%M"` "Finish autotune:\n"
  $LLVMAutotune finalize

else
  echo "Error: Unrecognized command"
  exit 1

fi
