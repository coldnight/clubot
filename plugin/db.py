#!/usr/bin/env python
#-*- coding:utf-8 -*-
#
#
# Author : cold night
# email  : wh_linux@126.com
# 2012-09-27 13:00
#   + 增加一张表,为status表
#   + 增加对状态操作的函数
# 2012-10-8  09:57
#   + 增加日志

import os
import logging
import sqlite3
from datetime import datetime
from settings import DEBUG
from settings import LOGPATH
from settings import DB_NAME


logger = logging.getLogger()
if DEBUG:
    hdl = logging.StreamHandler()
else:
    hdl = logging.FileHandler(LOGPATH)
fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
hdl.setFormatter(fmt)
logger.addHandler(hdl)
logger.setLevel(logging.INFO) # change to DEBUG for higher verbosity





NOW = lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S")
get_email = lambda frm:frm.bare().as_string()

def _init_table():
    """
    初始化数据库
    """
    DB_PATH= os.path.join(os.path.split(__file__)[0], DB_NAME)
    if not os.path.exists(DB_PATH):
        conn = sqlite3.connect(DB_PATH)
        conn.isolation_level = None
        cursor = conn.cursor()
        """
        创建成员数据库 members
        key       type         default
        id     INTEGER PRIMARY KEY AUTO_INCREMENT  null
        email  VARCHAR          null
        name   VARCHAR          null
        nick   VARCHAR          null
        last   timestamp         // 最后发言
        lastchange timestamp     // 最后修改
        isonline   INT           // 是否在线(0否, 1 是)
        date timestamp           // 加入时间
        """
        cursor.execute("""
                       create table members(
                       id INTEGER PRIMARY KEY AUTOINCREMENT,
                       email VARCHAR,
                       name  VARCHAR,
                       nick VARCHAR,
                       last TIMESTAMP,
                       lastchange TIMESTAMP,
                       isonline INTEGER DEFAULT 1,
                       date TIMESTAMP
                       )
                      """)

        """
        创建聊天记录表 history
        key              type              default
        id         INTEGER PRIMARY KEY AUTO_INCREMNT null
        frmemail        VARCHAR       null
        content    TEXT          null
        toemail     VARCHAR       null             // all代表所有,其余对应相应的email
        date       TIMESTAMP     (datetime('now', 'localtime'))
        """
        conn.commit()
        cursor.execute("""
            create table history(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                frmemail VARCHAR,
                toemail VARCHAR DEFAULT "all",
                content TEXT,
                date TIMESTAMP
                )""")
        conn.commit()

        """
        状态表 status
        `key`               `type`              `default`
        email      VARCHAR                       null
        resource   VARCHAR                      null
        status     INTEGER                       1 // 1在线,0不在线
        statustext VARCHAR                      null
        """
        cursor.execute("""
                       create table status(
                       email VARCHAR,
                       resource VARCHAR,
                       status INTEGER DEFAULT 1,
                       statustext VARCHAR)
                       """
                      )
        conn.commit()
    else:
        conn = sqlite3.connect(DB_PATH)
        conn.isolation_level = None
        cursor = conn.cursor()

    return cursor, conn

def get_cursor():
    """
    获取数据库游标
    """
    return _init_table()


def get_status(email, resource = None):
    if resource:
        sql = 'select status,statustext from status where email=? and resource=?'
        param = (email, resource)
    else:
        sql = 'select status, statustext from status where email=?'
        param = (email,)

    cursor, conn = get_cursor()
    cursor.execute(sql, param)
    r = cursor.fetchall()
    cursor.close()
    conn.close()
    return r


def change_status(frm, status, statustext):
    """改变用户状态"""
    email = get_email(frm)
    resource = frm.resource
    stat = get_status(email, resource)
    if stat:
        sql = 'update status set status=?,statustext=? where email=? and resource=?'
    else:
        sql = 'insert into status(status, statustext,email, resource) VALUES(?,?,?,?)'
    param = (status, statustext, email, resource)
    cursor, conn = get_cursor()
    cursor.execute(sql, param)
    conn.commit()
    cursor.close()
    conn.close()


def is_online(email):
    sql = 'select status from status where email=? and status=1'
    cursor, conn = get_cursor()
    cursor.execute(sql,(email,))
    r = True if cursor.fetchall() else False
    return r

now = datetime.now()
def add_member(frm):
    cursor, conn = get_cursor()
    name = frm.local
    email = get_email(frm)
    if get_member(frm):return
    sql = 'insert into members(email, name, nick, last, lastchange, date) VALUES(?,?,?,?,?,?)'
    cursor.execute(sql, (email, name, name, now, now, now))
    conn.commit()
    cursor.close()
    conn.close()


def del_member(frm):
    cursor, conn = get_cursor()
    email = get_email(frm)
    sql = 'delete from members where email=?'
    cursor.execute(sql, (email,))
    conn.commit()
    cursor.close()
    conn.close()


def edit_member(frm, nick = None, last=None):
    cursor, conn = get_cursor()
    email = get_email(frm)
    if nick:
        cursor.execute('select * from members where nick=?',(nick,))
        if cursor.fetchall():return False
        sql = 'update members set nick=?,lastchange=? where email=?'
        param = (nick, now, email)
    else:
        sql = 'update members set last=? where email=?'
        param = (now, email)

    cursor.execute(sql, param)
    conn.commit()
    cursor.close()
    conn.close()
    return True


def get_member(frm = None, uid = None, nick = None):
    """
    提供email返回id
    提供uid返回email
    提供nick返回email
    """
    cursor, conn = get_cursor()
    if uid:
        sql = 'select email from members where id=?'
        param = (int(uid),)
    elif frm:
        email = get_email(frm)
        sql = 'select id from members where email=?'
        param = (email, )
    elif nick:
        sql = 'select email from members where nick=?'
        param = (nick, )

    cursor.execute(sql, param)
    r = cursor.fetchall()
    result = r[0][0] if len(r) == 1 else None
    cursor.close()
    conn.close()

    return result


def get_members(frm= None):
    """
    获取所有成员
    """
    cursor, conn = get_cursor()
    if frm:
        email = get_email(frm)
        sql = 'select email from members where email !=?'
        param = (email, )
        cursor.execute(sql, param)
        r = cursor.fetchall()
        result = [x[0] for x in r]
    else:
        sql = 'select nick, email from members'
        cursor.execute(sql)
        r = cursor.fetchall()
        result = [dict(nick=v[0], email = v[1]) for v in r]
    cursor.close()
    conn.close()
    return result


def get_nick(frm= None, uid = None):
    cursor, conn = get_cursor()
    if frm:
        email = get_email(frm)
        sql = 'select nick from members where email =?'
        param = (email,)
    elif uid:
        sql = 'select nick from members where id=?'
        param = (uid,)

    cursor.execute(sql, param)
    r = cursor.fetchall()
    result = r[0][0] if len(r) == 1 else email.split('@')[1]
    cursor.close()
    conn.close()
    return result


def add_history(frm, to, content):
    cursor, conn = get_cursor()
    frmemail = get_email(frm)
    sql = 'insert into history(frmemail, toemail, content, date) VALUES(?,?,?,?)'
    param = (frmemail, to, content, now)
    cursor.execute(sql, param)
    conn.commit()
    cursor.close()
    conn.close()


def get_history(sef, frm = None, index = 1,  size = 10):
    cursor, conn = get_cursor()
    limit = int(size)
    skip = (int(index) -1) * 10
    sef = get_email(sef)
    basesql = 'select id, frmemail, toemail, content, date from history where '

    if not frm or frm.strip() == 'all':
        sql = basesql + 'toemail=? or toemail=? ORDER BY id DESC limit ? offset ?'
        param = (sef, 'all', limit, skip)
    else:
        frmemail = get_member(nick=frm)
        sql = basesql +'(toemail=? or toemail=?) and frmemail=? ORDER BY id DESC limit ? offset ?'
        param = ('all',sef, frmemail, limit, skip)
    cursor.execute(sql, param)
    tmp = cursor.fetchall()
    cursor.close()
    conn.close()
    result = []
    for r in tmp:
        t = {}
        t['id'], t['frm'], t['to'], t['content'], t['date'] = r
        fr = format(t)
        result.append(fr)
    return '\n'.join(result)


def format(values):
    import string
    t = string.Template("""
    id      : $id
    from    : $frm
    to      : $to
    content : $content
    date    : $date
"""
        )
    return t.substitute(values)
