#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
#   Author  :   cold
#   E-mail  :   wh_linux@126.com
#   Date    :   12/12/27 09:30:58
#   Desc    :   简单线程池
#
import Queue
import threading
import functools

class ThreadPool(object):
    """ 线程池
        启动相应的线程数,提供接口添加任务,任务为函数
        因为线程池时刻都有可能用到所以不做清理
        `thread_num`  - 初始化线程数
    """
    def __init__(self, thread_num = 1):
        self._thread_num = thread_num
        self._jobs_queue = Queue.Queue()
        self._threads = []

        return

    def add_job(self, func, *args, **kwargs):
        """ 添加任务 """
        func = functools.partial(func, *args, **kwargs)
        self._jobs_queue.put(func)

        return

    def worker(self):
        """ 工作线程
            使用Queue阻塞
            因为传入的函数已经做了相应的错误处理,
            所以在此不做进一步错误处理
        """
        while True:
            func = self._jobs_queue.get()
            func()

    def start(self):
        """ 根据线程数启动工作线程 """
        target = self.worker
        for i in xrange(0, self._thread_num):
            name = 'thread_pool-' + str(i)
            t = threading.Thread(target = target, name = name)
            t.setDaemon(True)
            self._threads.append(t)
            t.start()
