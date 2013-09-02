#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
#   Author  :   cold
#   E-mail  :   wh_linux@126.com
#   Date    :   13/04/25 14:14:33
#   Desc    :   逻辑
#
import time
import const
from db import MongoDB
from datetime import datetime

from utility import get_email, now

class AttrDict(dict):
    def __getattr__(self, key):
        return self[key]


class Logics(object):
    db = MongoDB()

    @classmethod
    def wrap_dict(cls, data):
        if isinstance(data, (list,tuple)):
            lst = []
            for i in data:
                lst.append(cls.wrap_dict(i))
            return lst
        elif isinstance(data, dict):
            return AttrDict(data)
        else:
            return data


    @classmethod
    def wrap_member(cls, m):
        if isinstance(m, (list, tuple)):
            lst = []
            for i in m:
                lst.append(cls.wrap_member(i))
            return lst
        elif isinstance(m, dict):
            m = AttrDict(m)
            m["infos"] = cls.wrap_dict(list(cls.db[const.INFO].find({"mid":m._id})))
            m["history"] = cls.wrap_dict(list(cls.db[const.HISTORY].find({"from_member.$id":m._id})))
            m["status"] = cls.wrap_dict(list(cls.db[const.STATUS].find({"mid":m._id})))
            return m
        else:
            return m


    @classmethod
    def get_with_nick(cls, nick):
        """ 根据昵称获取成员
        Arguments:
            `nick`  -   成员昵称
        """

        m = cls.db[const.MEMBER].find_one({"nick":nick})
        return cls.wrap_member(m)


    @classmethod
    def get_one(cls, jid):
        """ 获取一个成员
        Arguments:
            `jid`   -   成员jid
        """
        email = get_email(jid)
        return cls.wrap_member(cls.db[const.MEMBER].find_one({"email":email}))


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
        doc = {"email":get_email(jid), "nick":nick, "isonline":True,
               "join_date":now()}
        mid = cls.db[const.MEMBER].insert(doc)
        cls.db[const.STATUS].insert({"mid":mid, "statustext": show,
                                     "resource" : jid.resource,
                                     "status":const.ONLINE})

        return cls.get_one(cls, jid)



    @classmethod
    def drop(cls, jid):
        """ 删除一个成员
        Arguments:
            `jid`   -   成员jid
        """
        m = cls.get_one(jid)
        cls.db[const.MEMBER].remove({"email":get_email})
        cls.db[const.STATUS].remove({"mid":m._id})
        cls.db[const.INFO].remove({"mid":m._id})

        return

    @classmethod
    def get_members(cls, remove = None):
        """ 获取所有成员
        Arguments:
            `remove`    -   排除成员
        """
        remove_email = get_email(remove)
        if remove:
            ms = cls.db[const.MEMBER].find({"email":{"$ne":remove_email}})
            return cls.wrap_member(list(ms))
        ms = cls.db[const.MEMBER].find()
        return cls.wrap_member(list(ms))


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
            cls.db[const.MEMBER].update({"_id":m._id},
                                        {"$set":{"nick":nick, "last_change":now()},
                                         "$push":{"used_nick":nick}})
            cls.set_info(jid, const.INFO_CHANGE_NICK_TIMES,
                         int(cls.get_info(jid,
                                          const.INFO_CHANGE_NICK_TIMES ,
                                          0).value) + 1)
            return True


    @classmethod
    def get_one_status(cls, jid):
        m = cls.get_one(jid)
        if not m:
            return False, False
        return cls.db[const.STATUS].find_one({"resource":jid.resource},
                                               {"mid":m._id}), m

    @classmethod
    def set_online(cls, jid, show=None):
        """ 设置成员在线
        Arguments:
            `jid`   -   成员jid
            `show`  -   stanza.show
        """
        status,m  = cls.get_one_status(jid)
        if not m:
            return False

        if status:
            cls.db[const.STATUS].update({"_id":status.get("_id")},
                                        {"$set":{ "statustext":show}})
        else:
            cls.db[const.STATUS].insert({"status":const.ONLINE,
                                         "statustext":show,
                                         "resource":jid.resource,
                                         "mid": m._id})

        return True

    @classmethod
    def set_offline(cls, jid):
        status, m = cls.get_one_status(jid)
        if not m or not status: return False
        cls.db[const.STATUS].remove({"_id":status.get("_id")})


    @classmethod
    def _get_info(cls, jid = None, key = None, default = None, is_global = False):
        """ 获取成员选项
        Arguments:
            `jid`   -   jid
            `key`   -   选项键
            `default` -   默认值
        """
        cond = {"key":key, "is_global":is_global}
        m = None
        if jid:
            m = cls.get_one(jid)
            if not m:
                return AttrDict( dict(key = key, value = default, is_global = is_global)), False, None
            cond.update(mid=m._id)
        info = cls.db[const.INFO].find_one(cond)

        from_db = True
        if not info:
            info = dict(key = key, value = default, is_global = is_global)
            from_db = False

        return AttrDict(info), from_db, m

    @classmethod
    def get_info(cls, jid, key, default = None):
        return cls._get_info(jid, key, default)[0]


    @classmethod
    def set_info(cls, jid, key, value):
        """ 设置成员选项
        Arguments:
            `jid`   -   jid
            `key`   -   选项键
            `value` -   选项值
        """
        info, f, m = cls._get_info(jid, key)
        if f:
            cls.db[const.INFO].update({"_id":info._id},
                                      {"$set":{"value":value}})
        else:
            cls.db[const.INFO].insert({"key":key, "value":value,
                                       "is_global":False,
                                       "pubdate":now(),
                                       "mid":m._id})
        return info


    @classmethod
    def get_today_rp(cls, jid):
        """ 获取今日rp """
        rp = None
        rp_date = Logics.get_info(jid, const.INFO_RP_DATE).value

        if rp_date:
            try:
                rp_date = datetime.fromtimestamp(float(rp_date))
            except:
                rp_date = time.time() - 86400
                rp_date = datetime.fromtimestamp(float(rp_date))
            now = datetime.now()

            if now.year == rp_date.year and now.month == rp_date.month and \
            now.day == rp_date.day:
                rp = Logics.get_info(jid, const.INFO_RP).value

        return rp


    @classmethod
    def set_today_rp(cls, jid, rp):
        cls.set_info(jid, const.INFO_RP, rp)
        cls.set_info(jid, const.INFO_RP_DATE, time.time())
        cls.db[const.MEMBER].update({"email":get_email(jid)},
                                    {"$push":{"rps":{"value":rp, "date":now()}}})


    @classmethod
    def get_global_info(cls, key, default = None):
        """ 获取全局选项
        Arguments:
            `key`   -   选项键
            `default` -   默认值
        """
        return cls._get_info(key = key, default = default, is_global = True)[0]

    @classmethod
    def set_global_info(cls, key, value):
        """ 设置全局选项
        Arguments:
            `key`   -   选项键
            `value` -   选项值
        """
        info, f, _ = cls._get_info(key = key,  is_global = True)
        if f:
            cls.db[const.INFO].update({"_id":info._id},
                                      {"$set":{"value":value}})
        else:
            cls.db[const.INFO].insert({"key":key, "value":value,
                                       "pubdate":now(), "is_global":True})
        return info


    @classmethod
    def add_history(cls, jid, to_jid, content):
        m = cls.get_one(jid)
        cls.db[const.MEMBER].update({"_id":m._id}, {"$set":{"last_say":now()}})
        cls.db[const.HISTORY].insert({"from_member":cls.db.ref(const.MEMBER, m._id),
                                      "to_member":to_jid, "content":content,
                                      "pubdate":now()})


    @classmethod
    def get_history(cls, jid = None,  starttime = None):
        """ 获取历史信息
        Arguments:
            `jid`   -   发送人
            `to`    -   接收人
            `starttime` -   开始时间
        """
        condition = {"to_member":"all"}
        if jid:
            m = cls.get_one(jid)
            condition.update({"from_member.$id":m._id})

        if starttime:
            condition.update(pubdate = {"$gte":starttime})

        return cls.db.deref(list(cls.db[const.HISTORY].find(condition)\
                                 .sort("pubdate", cls.db.asc)))


    @classmethod
    def is_online(cls, jid):
        m = cls.get_one(jid)
        return bool([status.status for status in m.status if status.status])


    @classmethod
    def empty_status(cls):
        cls.db[const.STATUS].remove()
