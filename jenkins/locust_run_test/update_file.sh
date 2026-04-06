#!/bin/bash

export LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8

mv gatling.zip ../test_runner/

cd ../test_runner
unzip -o gatling.zip
rsync -a gatling/ ./
rm -rf gatling
chmod +x kubectl run_test*