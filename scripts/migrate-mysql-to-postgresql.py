#!/usr/bin/env python3
from contextlib import contextmanager, closing

import MySQLdb
import psycopg2

mysql_conn = MySQLdb.connect(unix_socket="/var/run/mysqld/mysqld.sock", database="pajbot_test", charset="utf8mb4")
psql_conn = psycopg2.connect("dbname=pajbot options='-c search_path=pajbot1_test'")


# https://pymysql.readthedocs.io/en/latest/modules/connections.html#pymysql.connections.Connection
# http://initd.org/psycopg/docs/module.html#psycopg2.connect
# https://www.postgresql.org/docs/current/libpq-connect.html#LIBPQ-CONNSTRING
with mysql_conn.cursor() as mysql, psql_conn.cursor() as psql:
    psql.execute("")

mysql_conn.rollback()
mysql_conn.close()
print("closed mysql conn")

psql_conn.commit()
psql_conn.close()
print("closed psql conn")
