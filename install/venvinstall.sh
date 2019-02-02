#!/bin/bash
python3 -m venv myvenv
source myvenv/bin/activate
pip install pip --upgrade
pip install -r requirements.txt
