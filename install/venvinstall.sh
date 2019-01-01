#!/bin/bash
pyvenv-3.4 myvenv
source myvenv/bin/activate
pip install pip --upgrade
pip install -r requirements.txt
