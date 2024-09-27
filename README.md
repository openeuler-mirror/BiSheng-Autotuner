# BiSheng-Autotuner

#### 介绍

BiSheng-Autotuner 是一个基于 BiSheng-OpenTuner 的命令行工具，与支持调优的基于 LLVM 的编译器（如 Bisheng 编译器）配合使用。它负责生成搜索空间、操作参数并驱动整个调优过程。BiSheng-OpenTuner 是一个开源框架，用于构建特定领域的、多目标的自动调优器。

#### 环境

1.  Python 3.6 及以上 （推荐 Python 3.10）
2.  SQLite 3.0 及以上

安装下列依赖，或检查安装
Ubuntu / Debian：
`apt-get install python-dev sqlite3 libsqlite3-dev`

CentOS / EulerOS：
`yum install -y python3-devel sqlite-deve`

#### 安装教程

克隆并安装 [BiSheng-OpenTuner](https://gitee.com/src-openeuler/BiSheng-opentuner/tree/master)
```
cd BiSheng-opentuner/
python3 -m pip install ./ --user
```

安装BiSheng-Autotuner
```
cd BiSheng-Autotuner/
./dev_install.sh
```
#### 运行 BiSheng-Autotuner

运行以下命令查看所有可用选项的帮助信息：
`./bin/llvm-autotune -h`

#### 检查安装

`python3 -m pip show autotuner`

#### 卸载

`./uninstall.sh`

#### 参与贡献

1.  Fork 本仓库
2.  新建 Feat_xxx 分支
3.  提交代码
4.  新建 Pull Request
