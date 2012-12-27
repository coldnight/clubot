#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
#   Author  :   cold
#   E-mail  :   wh_linux@126.com
#   Date    :   12/12/27 09:30:58
#   Desc    :   线程池
#
import Queue
import threading
import functools

class ThreadPool(object):
    """ 线程池
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
        """ 工作线程 """
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
