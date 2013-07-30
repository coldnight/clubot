#!/usr/bin/env python
#-*- coding:utf-8 -*-
"""
# 设置
"""
import sys
reload(sys)
sys.setdefaultencoding('utf-8')

USER = 'qxbot@vim-cn.com'
PASSWORD = ''

DEBUG = True
IMPORT = False # 如果数据库中有而角色中无则添加好友
TRACE = False

PIDPATH = r'clubot.pid'
LOGPATH = r'clubot.log'

DB_HOST = 'localhost'
DB_PORT = 3306
DB_NAME = 'clubot'
DB_USER = 'root'
DB_PASSWD = ''

STATUS = u"Pythoner Club Linux/Vim/Python 技术交流"
MODES  = dict(talk = u'聊天模式', quiet = u'安静模式(不接收消息)')
ADMINS = ['coldnight.linux@gmail.com']


# 下面是有道辞典需要的api, 可以到下面网站申请一个key和keyfrom
# http://fanyi.youdao.com/openapi
YOUDAO_KEY = 1234567890

YOUDAO_KEYFROM = "clubot"
