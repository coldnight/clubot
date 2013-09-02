#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
#   Author  :   cold
#   E-mail  :   wh_linux@126.com
#   Date    :   13/09/02 10:35:31
#   Desc    :   荣誉系统
#
"""
{
    getdate                 // 获取日期
    hornordate              // 荣誉日期
    type                    // 荣誉类型
    item                    // 项目
    desc                    // 荣誉描述
    value                   // 获取荣誉的值
    mid                     // 用户id
}
"""
from logics import Logics
from utility import now


class Honor(object):
    """ 荣誉系统 """
    RP_LOWEST   = (0x01, "rp", "今日最低")
    RP_HIGHEST  = (0x02, "rp", "今日最高")

    RP0         = (0x03, "rp", "冰点")
    RP100       = (0x04, "rp", "峰值")


    def rp_honor(self, nick, rp, callback):
        rp = int(rp)
        typ = False
        if rp == 0:
            typ, item, desc = self.RP0
        elif rp == 100:
            typ, item, desc = self.RP100

        if typ:
            Logics.add_honor(nick, rp, typ, item, desc)
            msg = ">>> {0} {1}达到{2}, 获得成就, 载入历史"\
                    .format(nick, item, desc)
            callback(msg)
