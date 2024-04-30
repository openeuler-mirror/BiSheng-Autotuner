# BiSheng Autotuner

BiSheng Autotuner is built on top of OpenTuner, an open-source framework for
building domain-specific multi-objective automatic tuners. It works with
tuning-enabled LLVM to provide autotuning support in multiple optimization
passes, and at different levels. It manages search space generation and
parameter manipulation, and provides a command-line tool that helps integrate
the tuning process into a user's software construction flow.

## Getting Started with Autotuner Development

Clone and install our customized version of
[OpenTuner](https://gitee.com/bisheng-compiler-team/opentuner):

    cd opentuner/
    python3 -m pip install ./ --user

Install BiSheng Autotuner:

    cd autotuner/
    ./dev_install.sh

Check the installation:

    python3 -m pip show autotuner

To run unit tests:

    ./dev_install.sh -t

To uninstall:

    ./uninstall.sh

