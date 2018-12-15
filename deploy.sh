#!/usr/bin/env bash

set -ex

pip install --user virtualenv==16.0.0 -i http://mirrors.aliyun.com/pypi/simple --trusted-host mirrors.aliyun.com
home=`pwd`
rm -rf venv
echo "deploy path ${home}"
virtualenv ${home}/venv --python=python3.7 --no-setuptools
${home}/venv/bin/pip install Cython==0.28.3 -i http://mirrors.aliyun.com/pypi/simple --trusted-host mirrors.aliyun.com
${home}/venv/bin/pip install setuptools==39.1.0 -i http://mirrors.aliyun.com/pypi/simple --trusted-host mirrors.aliyun.com
${home}/venv/bin/pip install -U -r requirements.txt -i http://mirrors.aliyun.com/pypi/simple --trusted-host mirrors.aliyun.com
echo "deploy finish"
