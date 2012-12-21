#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
#   Author  :   wh
#   E-mail  :   wh_linux@126.com
#   Date    :   12/12/21 10:07:33
#   Desc    :   从sqlite导出数据到mysql
#
import sys
sys.path.append('../')
from db import get_cursor as sqlite_cursor
from mysql import get_cursor as mysql_cursor

def from_unicode(text):
    if isinstance(text, (tuple, list)):
        result = [from_unicode(t) for t in text]
        return tuple(result)
    elif isinstance(text, unicode):
        return str(text)
    elif isinstance(text, (str, int, float, long)):
        return text
    elif text is None:
        return ''

def import_sqlite(table):
    sqlite, sqlite_conn = sqlite_cursor()
    mysql, mysql_conn = mysql_cursor()
    sqlite.execute('select * from ' + table)
    members = sqlite.fetchall()
    print members

    for member in members:
        sql = 'insert into {0} VALUES{1}'.format(table, from_unicode(member))
        print sql
        mysql.execute(sql)
        mysql_conn.commit()


if __name__ == '__main__':
    import_sqlite('history')
    import_sqlite('members')
