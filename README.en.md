# BiSheng-Autotuner

#### Description
BiSheng-Autotuner is a command line tool built on top of BiSheng-OpenTuner, and works with a tuning-enabled LLVM-based compiler (such as Bisheng Compiler). It manages the search space generation and parameter manipulation, and drives the entire tuning process.

BiSheng-OpenTuner is an open-source framework for building domain-specific multi-objective automatic tuners.

#### Software Dependencies

1.  Python 3.6 or newer （Python 3.10 recomended）
2.  SQLite 3.0 or newer

Install or check the installation:

Ubuntu / Debian
`apt-get install python-dev sqlite3 libsqlite3-dev`

CentOS / EulerOS
`yum install -y python3-devel sqlite-deve`


#### Installation

Clone and install [BiSheng-OpenTuner](https://gitee.com/src-openeuler/BiSheng-opentuner/tree/master) :
```
cd BiSheng-opentuner/
python3 -m pip install ./ --user
```

Install BiSheng-Autotuner :
```
cd BiSheng-Autotuner/
./dev_install.sh
```

#### Running BiSheng-Autotuner

Run the following command to see help messages on all available options:
`./bin/llvm-autotune -h`

#### Check installation

`python3 -m pip show autotuner`

#### Uninstall

`./uninstall.sh`

#### Contribution

1.  Fork the repository
2.  Create Feat_xxx branch
3.  Commit your code
4.  Create Pull Request
