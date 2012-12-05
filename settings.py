#!/usr/bin/env python
#-*- coding:utf-8 -*-
"""
# 设置
"""

import sys
reload(sys)
sys.setdefaultencoding('utf-8')

ADMINS = ['coldnight.linux@gmail.com']

USER = ''

PASSWORD = ""

DEBUG = False

IMPORT = True     # 如果数据库中有而角色中无则添加好友

__version__ = '0.1.5 alpha-threading'

PIDPATH = r'logs/clubot.pid'

LOGPATH = r'logs/clubot.log'

DB_NAME="group.db"

status = u"Pythoner Club Linux/Vim/Python 技术交流"

# DEBUG:10
# INFO : 20
# WARNING :30
# ERROR : 40
# CRITICAL: 50
LOGLEVEL = 10
