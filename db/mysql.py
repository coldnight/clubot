#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
#   Author  :   cold
#   E-mail  :   wh_linux@126.com
#   Date    :   12/12/20 17:43:45
#   Desc    :   Clubot MySQL 接口
#   History :
#               12/12/20
#                    + 继承sqlite接口
#               12/12/24
#                     + 添加info接口
#                     - 移除logger,放到util里
#                     + 添加info表记录信息和配置
#
#
import string
import MySQLdb as mysqldb
from datetime import datetime
from settings import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWD, USER
from settings import ADMINS, MODES
from .util import  get_email, now



def get_cursor():
    """
    获取数据库游标
    """
    conn  = mysqldb.Connection(host=DB_HOST, port = DB_PORT,
                               user = DB_USER, passwd = DB_PASSWD,
                               db = DB_NAME, charset = 'utf8')
    cursor = conn.cursor()
    return cursor, conn

def execute_sql(sql, params, commit=False):
    cursor, conn = get_cursor()
    cursor.execute(sql, params)
    if commit:
        conn.commit()
    r = cursor.fetchall()
    cursor.close()
    conn.close()
    return r

def get_status(email, resource = None):
    if resource:
        sql = 'select status,statustext from status where email=%s and \
                resource=%s'
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
        add_info('last_online', now, frm)
    elif stat and status==1:
        sql = 'update status set status=%s, statustext=%s where email=%s \
                and resource=%s'
        param = (status, statustext, email, resource)
    elif not stat and  status==1:
        sql = 'insert into status(status, statustext,email, resource) \
                VALUES(%s,%s,%s,%s)'
        param = (status, statustext, email, resource)
    else:
        return
    cursor, conn = get_cursor()
    cursor.execute(sql, param)
    conn.commit()
    cursor.close()
    conn.close()


def is_online(email):
    email = get_email(email)
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

def add_member(frm):
    cursor, conn = get_cursor()
    name = frm.local
    email = get_email(frm)
    if get_member(frm):return
    sql = 'insert into members(email, name, nick, last, lastchange, date) \
            VALUES(%s,%s,%s,%s,%s,%s)'
    cursor.execute(sql, (email, name, name, now, now, now))
    conn.commit()
    cursor.close()
    conn.close()
    add_info('join_time', now, frm)


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
        add_info('last_change_nick', now, frm)
        times = get_info('change_nick_times', frm)
        times = int(times) if times else 0
        add_info('change_nick_times', times + 1, frm)
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
    sql = 'insert into history(frmemail, toemail, content, date) VALUES(%s,\
            %s,%s,%s)'
    param = (frmemail, to, content, now)
    cursor.execute(sql, param)
    conn.commit()
    cursor.close()
    conn.close()
    add_info('last_say', now, frm)


def get_history(sef, frm = None, index = 1,  size = 10):
    cursor, conn = get_cursor()
    limit = int(size)
    skip = (int(index) -1) * 10
    sef = get_email(sef)
    basesql = 'select id, frmemail, toemail, content, date from history where '

    if not frm or frm.strip() == 'all':
        sql = basesql + 'toemail=%s or toemail=%s ORDER BY id DESC limit \
                %s offset %s'
        param = (sef, 'all', limit, skip)
    else:
        frmemail = get_member(nick=frm)
        sql = basesql +'(toemail=%s or toemail=%s) and frmemail=%s ORDER BY \
                id DESC limit %s offset %s'
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

def add_info(key, value, email):
    """ 添加信息 """
    email = get_email(email)
    if get_info(key, email):
        sql = 'update info set `value`=%s where `key`=%s and `email` = %s'
        params = (value, key, email)
    else:
        sql = 'insert into info(`email`, `key`, `value`) VALUES(%s, %s, %s);'
        params = (email, key, value )
    execute_sql(sql, params, True)

def get_info(key, email):
    """ 获取信息,uid=0为全局信息 """
    cursor, conn = get_cursor()
    email = get_email(email)
    sql = 'select `value` from info where `key`=%s and `email`=%s'
    params = (key, email)
    r = execute_sql(sql, params)
    result = r[0][0] if len(r) == 1 else None
    return result

def add_global_info(key, value):
    if get_global_info(key):
        sql = "update info set `value`=%s where `key`=%s and `email`='global'"
        params = (value, key)
    else:
        sql = "insert info(`key`, `value`) VALUES(%s, %s);"
        params = (key, value)
    execute_sql(sql, params, True)

def get_global_info(key):
    sql = "select `value` from info where `key`=%s and `email`=%s"
    params = (key, 'global')
    r = execute_sql(sql, params)
    return r[0][0] if len(r) == 1 else None

def get_user_info(frm):
    """ 获取用户信息 """
    nick = get_nick(frm)
    isonline = '在线' if is_online(frm) else '离线'
    status = get_status(frm)
    status = status[1] if len(status) == 2 else None
    status = status if status else isonline
    join_time = get_info('join_time', frm)
    join_time = join_time if join_time else '创造之始'
    last_say = get_info('last_say', frm)
    last_say = last_say if last_say else '从未发言'
    last_change_nick = get_info('last_change_nick', frm)
    last_change_nick = last_change_nick if last_change_nick else '从未修改'
    change_nick_times = get_info('change_nick_times', frm)
    change_nick_times = change_nick_times if change_nick_times else 0
    last_online_time = get_info('last_online', frm)
    last_online_time = last_online_time if last_online_time else join_time
    level = "管理员" if get_email(frm) in ADMINS else "成员"
    mode = get_info('mode', frm)
    mode = mode if mode else 'talk'
    mode = MODES[mode]
    result = dict(nick = nick, isonline = isonline, level = level,
                  status = status, join_time = join_time, mode = mode,
                  last_say = last_say, last_change_nick = last_change_nick,
                  last_online_time = last_online_time,
                  change_nick_times = change_nick_times)
    return result

def get_date(date):
    date = datetime.strptime(date, '%Y-%m-%d %H:%M:%S.%f')
    nowdate = datetime.now().date()
    dstdate = date.date()
    if nowdate == dstdate:
        return date.strftime("%H:%M:%S")
    else:
        return date.strftime("%Y-%m-%d %H:%M:%S")


def format(values):
    t = string.Template("""$date [$nick] $content""")
    values['nick'] = get_nick(values.get('frm'))
    if values['to']!='all':
        values['nick'] += u' 悄悄对你说'

    values['date'] = values['date']

    return t.substitute(values)

user_info_template = string.Template("""昵称: $nick         状态: $status
权限: $level        当前模式: $mode
更改昵称次数: $change_nick_times
上次更改昵称时间: $last_change_nick
加入时间: $join_time
最后发言: $last_say
最后在线时间: $last_online_time""")
