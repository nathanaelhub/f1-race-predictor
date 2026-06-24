#!/usr/bin/env bash
set -e
python --version
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
