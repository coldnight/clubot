#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
#   Author  :   cold
#   E-mail  :   wh_linux@126.com
#   Date    :   13/04/25 14:14:33
#   Desc    :   逻辑
#
import time
from datetime import datetime
from sqlalchemy import and_
from sqlalchemy.orm.exc import NoResultFound

from utility import get_email, now
from models import Member, Info, History, Status, session

class Logics(object):
    @classmethod
    def get_with_nick(cls, nick):
        """ 根据昵称获取成员
        Arguments:
            `nick`  -   成员昵称
        """
        try:
            m = session.query(Member).filter(Member.nick == nick).one()
        except NoResultFound:
            m = None

        return m


    @classmethod
    def get_one(cls, jid):
        """ 获取一个成员
        Arguments:
            `jid`   -   成员jid
        """
        email = get_email(jid)
        try:
            m = session.query(Member).filter(Member.email == email).one()
        except NoResultFound:
            m = None
        return m

    @classmethod
    def add(cls, jid, nick = None, show = None):
        """ 添加一个成员
        Arguments:
            `jid`   -   成员jid
            `nick`  -   昵称
            `show`  -   stanze.show
        """
        if cls.get_one(jid):
            return
        m = Member(jid, nick)
        m.status = [Status(show, jid.resource)]
        try:
            session.add(m)
            session.commit()
        except:
            session.rollback()

        return m

    @classmethod
    def drop(cls, jid):
        """ 删除一个成员
        Arguments:
            `jid`   -   成员jid
        """
        m = cls.get_one(jid)
        if m:
            session.delete(m)

        return

    @staticmethod
    def get_members(remove = None):
        """ 获取所有成员
        Arguments:
            `remove`    -   排除成员
        """
        remove_email = get_email(remove)
        if remove:
            return session.query(Member).filter(Member.email != remove_email).all()
        return session.query(Member).all()

    @classmethod
    def modify_nick(cls, jid, nick):
        """ 修改成员昵称
        Arguments:
            `jid`   -   jid
            `nick`  -   新昵称
        Return:
            False   // 昵称已存在
            True    // 更改昵称成功
        """
        m = cls.get_one(jid)
        if not m: return False
        if m:
            exists = cls.get_with_nick(nick)
            if exists:
                return False
            m.nick = nick
            m.last_change = now()
            cls.set_info(jid, "change_nick_times",
                         int(cls.get_info(jid, "change_nick_times", 0)) + 1)
            session.commit()
            return True

    @classmethod
    def set_online(cls, jid, show=None):
        """ 设置成员在线
        Arguments:
            `jid`   -   成员jid
            `show`  -   stanza.show
        """
        m = cls.get_one(jid)
        if not m:
            return False
        try:
            status = session.query(Status)\
                    .filter(and_(Status.resource == jid.resource,
                                 Status.member == m)).one()
            status.show = show
        except NoResultFound:
            status = Status(show, jid.resource)
            if m.status:
                m.status.append(status)
            else:
                m.status = [status]
        finally:
            session.commit()

        return True

    @classmethod
    def set_offline(cls, jid):
        m = cls.get_one(jid)
        if not m: return False
        try:
            status = session.query(Status)\
                    .filter(and_(Status.resource == jid.resource,
                                 Status.member == m)).one()
            m.status.pop(m.status.index(status))
            session.delete(status)
            session.commit()
        except NoResultFound:
            pass


    @classmethod
    def get_info(cls, jid, key, default = None):
        """ 获取成员选项
        Arguments:
            `jid`   -   jid
            `key`   -   选项键
            `default` -   默认值
        """
        m = cls.get_one(jid)
        try:
            info = session.query(Info).filter(and_(Info.key == key,
                                                   Info.member == m,
                                                   Info.is_global == 0)).one()
        except NoResultFound:
            info = Info(key, default)

        return info


    @classmethod
    def set_info(cls, jid, key, value):
        """ 设置成员选项
        Arguments:
            `jid`   -   jid
            `key`   -   选项键
            `value` -   选项值
        """
        m = cls.get_one(jid)
        try:
            info = session.query(Info).filter(and_(Info.key == key,
                                                   Info.member == m,
                                                   Info.is_global == 0)).one()
            info.value = value
        except NoResultFound:
            info = Info(key, value)
            if m.infos:
                m.infos.append(info)
            else:
                m.infos = [info]
        finally:
            session.commit()

        return info


    @classmethod
    def get_today_rp(cls, jid):
        """ 获取今日rp """
        rp = None
        rp_date = Logics.get_info(jid, "rp_date").value

        if rp_date:
            try:
                rp_date = datetime.fromtimestamp(float(rp_date))
            except:
                rp_date = time.time() - 86400
                rp_date = datetime.fromtimestamp(float(rp_date))
            now = datetime.now()

            if now.year == rp_date.year and now.month == rp_date.month and \
            now.day == rp_date.day:
                rp = Logics.get_info(jid, "rp").value

        return rp




    @staticmethod
    def get_global_info(key, default = None):
        """ 获取全局选项
        Arguments:
            `key`   -   选项键
            `default` -   默认值
        """
        try:
            info = session.query(Info).filter(and_(Info.key == key,
                                                   Info.is_global == 1)).one()
        except NoResultFound:
            info = Logics.set_global_info(key, default)

        if info.value is None:
            info.value = default
            session.commit()

        return info

    @staticmethod
    def set_global_info(key, value):
        """ 设置全局选项
        Arguments:
            `key`   -   选项键
            `value` -   选项值
        """
        try:
            info = session.query(Info).filter(and_(Info.key == key,
                                                   Info.is_global == 1)).one()
            info.value = value
        except NoResultFound:
            info = Info(key, value, True)
            session.add(info)
        finally:
            session.commit()

        return info

    @classmethod
    def add_history(cls, jid, to_jid, content):
        m = cls.get_one(jid)
        m.last_say = now()
        if m.history:
            m.history.append(History(to_jid, content))
        else:
            m.history = [History(to_jid, content)]

        session.commit()

    @classmethod
    def get_history(cls, jid = None,  starttime = None):
        """ 获取历史信息
        Arguments:
            `jid`   -   发送人
            `to`    -   接收人
            `starttime` -   开始时间
        """
        if jid:
            m = cls.get_one(jid)


        if jid and not starttime:
            fil = and_(History.member == m, History.to_member == "all")

        if not jid and not starttime:
            fil = History.to_member == "all"

        if not jid and starttime:
            fil = and_(History.pubdate > starttime, History.to_member == "all")


        return session.query(History).filter(fil).order_by(History.pubdate).all()

    @classmethod
    def is_online(cls, jid):
        m = cls.get_one(jid)
        return bool([status.status for status in m.status if status.status])

    @staticmethod
    def empty_status():
        all_status = session.query(Status).all()
        for status in all_status:
            session.delete(status)

        session.commit()
