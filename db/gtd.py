#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
#   Author  :   wh
#   E-mail  :   wh_linux@126.com
#   Date    :   13/02/25 14:54:35
#   Desc    :   clubot 时间管理数据库操作
#
#XXX 暂不支持重复
""" GTD Task 实现
    `author`     --- 创建者
    `assigned`   --- 指派给
    `task`       --- 任务内容
    `expirse`    --- 过期时间
    `postpone_num` --- 推迟次数
    `status`     --- 状态
    `pubdate`    --- 发布日期
    `donedate`   --- 完成日志
    `priority`   --- 优先级(无(4) -> 一般(3) -> 重要(2) -> 紧急(1))
    `repeat`     --- 重复格式按照crontab   (* * * * *)
                                            | | | | |---------- 星期
                                            | | | |------------ 月
                                            | | |-------------- 日
                                            | |---------------- 小时
                                            |------------------ 分钟
    `location`   --- 地点
    `note`       --- 备注
    `listtype`   --- 所属列表
    `id`       --- 唯一表示符
"""
import time
import functools
from datetime import datetime
from collections import namedtuple

from .db import MySQLContext as MC
from plugin.util import get_email

ListType = namedtuple("ListType", "INBOX JOB STUDY")
ListType = ListType("inbox", "job", "study")

Status = namedtuple("Status", "START DONE POSTPONE RUBBISH EXPIRED")
Status = Status("S", "D", "P", "R", "E")

def todo_cmp(self, other):
    result = cmp(other.get("priority"), self.get("priority"))
    if result == 0:
        sex = self.get("expirse")
        oex = other.get("expirse")
        if sex and oex:
            return cmp(oex, sex)
        elif sex:
            return -1
        elif oex:
            return 1
        else:
            return 0
    return result

class GTD(object):
    def __init__(self):
        self._mc = functools.partial(MC, "todo")

    def todo(self, task, frm):
        """ 收集未做的事项 """
        author = get_email(frm)
        with self._mc() as op:
            op.insert_dict({"task":task, "author":author})

    def show(self, frm):
        with self._mc() as op:
            where = self._handle_author(frm)
            where += " and `status` != '{0}'".format(Status.DONE)
            lst = op.select(where = where)

        lst = sorted(lst, cmp = todo_cmp)
        return self._format_tasks(lst)

    def up(self, tid, frm):
        task, where = self._get_task_by_id(tid, frm)
        with self._mc() as op:
            priority = task.get("priority", 0)
            if priority < 3:
                task["priority"] = priority + 1
                op.update(set_dict = task, where = where)
                return u"提升优先级成功"
            else:
                return u"优先级已经最高"

    def down(self, tid, frm):
        task, where = self._get_task_by_id(tid, frm)
        with self._mc() as op:
            priority = task.get("priority", 0)
            if priority > 0:
                task["priority"] = priority -1
                op.update(set_dict = task, where = where)
                return u"降低优先级成功"
            else:
                return u"优先级已经最低"

    def expirse(self, tid, _time, frm):
        """ 设置过期时间 """
        task, where = self._get_task_by_id(tid, frm)
        _expirse = self._get_expirse(_time, task.get("pubdate"))
        task["expirse"] = _expirse
        with self._mc() as op:
            op.update(task, where = where)

    def done(self, tid, frm):
        task, where = self._get_task_by_id(tid, frm)
        task["status"] = Status.DONE
        task["donedate"] = datetime.now()

        with self._mc() as op:
            op.update(task, where)

    def _get_task_by_id(self, tid, frm):
        with self._mc() as op:
            where = self._handle_author(frm, tid)
            task = op.select_one(where = where)
            return task, where


    def _get_expirse(self, _time, pubdate):
        """ 根据time获取过期时间 """
        _expirse = None
        if _time:
            try:
                return datetime.strptime(_time, "%Y-%m-%d %H:%M")
            except:
                pass
            unit = _time[-1].lower()
            num = int(_time[0:-1])
            _pubtime = time.mktime(pubdate.timetuple())
            if unit == 'm':
                dst = num * 60
            elif unit == 'h':
                dst = num * 60 * 60
            elif unit == 'd':
                dst = num * 60 *60 * 24
            else:
                dst = 86400
            _expirse = datetime.fromtimestamp(_pubtime + dst)
            return _expirse

    def _handle_author(self, frm, _id = None):
        author = get_email(frm)
        with self._mc() as op:
            sql = "`author`='{0}'".format(op.escape(author))
            if _id:
                sql = sql + " and `id`='{0}'".format(op.escape(_id))
            return sql

    def _format_tasks(self, lst):
        task_strs = []
        for t in lst:
            task_strs.append(self._format_task_str(t))
        return u"\n".join(task_strs)

    def _format_task_str(self, task):
        expirse = self._get_date_desc(task.get("expirse"))
        info = task.get("task")
        last_info = u" [ID:{0} E:{1} T:{2} P:{3}]"\
                .format(task.get("id"), expirse, task.get("list_type"),
                        task.get("priority", 0))
        return info + last_info

    def _get_date_desc(self, dest):
        """ 获取一个日期相对于今天的描述,比如昨天,明天,今天,一月前等 """
        #TODO 今天明天的判断
        if not dest: return "无"
        now_mk = time.mktime(datetime.now().timetuple())
        dest_mk = time.mktime(dest.timetuple())
        sub = now_mk - dest_mk
        suffix = "ago" if sub > 0 else "later"
        if sub == 0:
            return "now"
        sub = abs(sub)
        get_num = lambda num1, num2: int(num1 / num2)
        if sub >= (86400 * 365):
            num = get_num(sub, 86400 * 365)
            return "{0} year(s) {1}".format(num, suffix)
        if sub >= (86400 * 30):
            num = get_num(sub, 86400 * 30)
            return "{0} month(s) {1}".format(num, suffix)
        if sub >= 86400:
            new_date = datetime.fromtimestamp(now_mk + sub)
            now = datetime.now()
            sub_day = new_date.day - now.day
            if suffix == "ago":
                d_map = {1:"昨天", 0:"今天", 2:"前天",
                         -1:"明天", -2:"后天"}
            else:
                d_map = {1:"明天", 0: "今天", 2:"后天",
                         -1: "昨天", -2 : "前天"}
            desc = d_map.get(sub_day)
            if desc:return desc
            num = get_num(sub, 86400)
            return "{0} day(s) {1}".format(num, suffix)
        if sub >= 3600:
            new_date = datetime.fromtimestamp(now_mk + sub)
            now = datetime.now()
            sub_day = new_date.day - now.day
            if suffix == "ago":
                d_map = {1:"昨天", 2:"前天", -1:"明天", -2:"后天"}
            else:
                d_map = {1:"明天", 2:"后天", -1: "昨天", -2 : "前天"}
            desc = d_map.get(sub_day)
            if desc:return desc
            num = get_num(sub, 3600)
            return "{0} hour(s) {1}".format(num, suffix)
        if sub >= 60:
            num = get_num(sub, 60)
            return "{0} minute(s) {1}".format(num, suffix)
