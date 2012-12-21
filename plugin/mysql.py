#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
#   Author  :   cold
#   E-mail  :   wh_linux@126.com
#   Date    :   12/12/20 17:43:45
#   Desc    :   Clubot MySQL 接口
#
import logging
import MySQLdb as mysqldb
from datetime import datetime
from settings import DEBUG
from settings import LOGPATH
from settings import DB_NAME, DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWD
from settings import USER


logger = logging.getLogger()
if DEBUG:
    hdl = logging.StreamHandler()
    level = logging.DEBUG
else:
    hdl = logging.FileHandler(LOGPATH)
level = logging.INFO
fmt = logging.Formatter("%(asctime)s %(levelname)s [%(threadName)-10s] %(message)s")
hdl.setFormatter(fmt)
handler = hdl
logger.addHandler(handler)
logger.setLevel(logging.INFO) # change to DEBUG for higher verbosity

NOW = lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def get_email(frm):
    try:
        result = frm.bare().as_string()
    except:
        result = frm
    return result



def get_cursor():
    """
    获取数据库游标
    """
    conn  = mysqldb.Connection(host=DB_HOST, port = DB_PORT,
                               user = DB_USER, passwd = DB_PASSWD,
                               db = DB_NAME, charset = 'utf8')
    cursor = conn.cursor()
    return cursor, conn


def get_status(email, resource = None):
    if resource:
        sql = 'select status,statustext from status where email=%s and resource=%s'
        param = (email, resource)
    else:
        sql = 'select status, statustext from status where email=%s'
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
    if email == USER:return
    resource = frm.resource
    stat = get_status(email, resource)
    if stat and status==0:
        sql = 'delete from status where email=%s and resource=%s'
        param = (email, resource)
    elif stat and status==1:
        sql = 'update status set status=%s, statustext=%s where email=%s and resource=%s'
        param = (status, statustext, email, resource)
    elif not stat and  status==1:
        sql = 'insert into status(status, statustext,email, resource) VALUES(%s,%s,%s,%s)'
        param = (status, statustext, email, resource)
    else:
        return
    cursor, conn = get_cursor()
    cursor.execute(sql, param)
    conn.commit()
    cursor.close()
    conn.close()


def is_online(email):
    sql = 'select status from status where email=%s and status=1'
    cursor, conn = get_cursor()
    cursor.execute(sql,(email,))
    r = True if cursor.fetchall() else False
    return r

def empty_status():
    sql = 'delete from status;'
    cursor, conn = get_cursor()
    cursor.execute(sql)
    conn.commit()
    cursor.close()
    conn.close()

now = datetime.now()
def add_member(frm):
    cursor, conn = get_cursor()
    name = frm.local
    email = get_email(frm)
    if get_member(frm):return
    sql = 'insert into members(email, name, nick, last, lastchange, date) VALUES(%s,%s,%s,%s,%s,%s)'
    cursor.execute(sql, (email, name, name, now, now, now))
    conn.commit()
    cursor.close()
    conn.close()


def del_member(frm):
    cursor, conn = get_cursor()
    email = get_email(frm)
    sql = 'delete from members where email=%s'
    cursor.execute(sql, (email,))
    conn.commit()
    cursor.close()
    conn.close()


def edit_member(frm, nick = None, last=None):
    cursor, conn = get_cursor()
    email = get_email(frm)
    if nick == 'system': return False
    if nick:
        cursor.execute('select * from members where nick=%s',(nick,))
        if cursor.fetchall():return False
        sql = 'update members set nick=%s,lastchange=%s where email=%s'
        param = (nick, now, email)
    else:
        sql = 'update members set last=%s where email=%s'
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
        sql = 'select email from members where id=%s'
        param = (int(uid),)
    elif frm:
        email = get_email(frm)
        sql = 'select id from members where email=%s'
        param = (email, )
    elif nick:
        sql = 'select email from members where nick=%s'
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
        sql = 'select email from members where email !=%s'
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
        sql = 'select nick from members where email =%s'
        param = (email,)
    elif uid:
        sql = 'select nick from members where id=%s'
        param = (uid,)

    cursor.execute(sql, param)
    r = cursor.fetchall()
    result = r[0][0] if len(r) == 1 else email.split('@')[0]
    cursor.close()
    conn.close()
    return result


def add_history(frm, to, content):
    cursor, conn = get_cursor()
    frmemail = get_email(frm)
    sql = 'insert into history(frmemail, toemail, content, date) VALUES(%s,%s,%s,%s)'
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
        sql = basesql + 'toemail=%s or toemail=%s ORDER BY id DESC limit %s offset %s'
        param = (sef, 'all', limit, skip)
    else:
        frmemail = get_member(nick=frm)
        sql = basesql +'(toemail=%s or toemail=%s) and frmemail=%s ORDER BY id DESC limit %s offset %s'
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
    result.reverse()
    return '\n'.join(result)



def get_date(date):
    date = datetime.strptime(date, '%Y-%m-%d %H:%M:%S.%f')
    nowdate = datetime.now().date()
    dstdate = date.date()
    if nowdate == dstdate:
        return date.strftime("%H:%M:%S")
    else:
        return date.strftime("%Y-%m-%d %H:%M:%S")


def format(values):
    import string
    t = string.Template("""$date [$nick] $content""")
    values['nick'] = get_nick(values.get('frm'))
    if values['to']!='all':
        values['nick'] += u' 悄悄对你说'

    values['date'] = values['date']

    return t.substitute(values)
