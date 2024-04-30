=================
BiSheng Autotuner
=================

BiSheng Autotuner is a command-line tool (``llvm-autotune``) that enables
a user to search for the optimal compiler optimization parameters for
fine-grained code regions in a given program, via an iterative compilation
process using BiSheng Compiler.

Quickstart
----------

BiSheng Autotuner requires Python 3.10. Before installing the tool, make
sure that ``python3`` in your search path is the correct version of Python.

To start, run ``bin/install-autotuner.sh`` in the BiSheng Compiler installation
directory. This will invoke ``pip`` to install Autotuner along with a number
of dependencies. If the installation completes successfully, running
``bin/llvm-autotune -h`` should display a help message instead of an error.

For more detailed instructions on how to perform automatic tuning, visit
the official web site::

    https://www.hikunpeng.com/document/detail/en/kunpengdevps/compiler/fg-autotuner/kunpengbisheng_20_0002.html

