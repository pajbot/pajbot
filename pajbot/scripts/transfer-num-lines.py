#!/usr/bin/env python3

import configparser
import os
import sys

import pymysql

from kvidata import KVIData
from models.user import User
from models.user import UserManager

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__ + "/../")))
os.chdir(os.path.dirname(os.path.realpath(__file__ + "/../")))


config = configparser.ConfigParser()

config.read("config.ini")

sqlconn = pymysql.connect(
    unix_socket=config["sql"]["unix_socket"],
    user=config["sql"]["user"],
    passwd=config["sql"]["passwd"],
    db=config["sql"]["db"],
    charset="utf8",
)
kvi = KVIData(sqlconn)

users = UserManager(sqlconn)

os.chdir(os.path.dirname(os.path.realpath(__file__)))

for nl in kvi.fetch_all("nl"):
    user = users[nl["key"]]
    user.num_lines = nl["value"]
    user.needs_sync = True

users.sync()
