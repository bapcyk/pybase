# -*- coding: cp1251 -*-

import Queue
from pybase.thread import *
#from threading import Thread, Event

class TkAsync:
    """Асинхронный обработчик команд Tk. Ему можно послать
    на исполнение функцию с ее аргументами при помощи post().
    Исполняет команды из очереди команд, после исполнения
    указывает Tk запустить обработчик через period usec.
    """
    after_id = None
    def __init__(self, master, period=20):
        """period - период. проверки сообщений в мсек"""
        self.master = master
        self.q = Queue.Queue()
        self.period = period
        self.after_id = self.master.after(self.period, self._idle)

    def post(self, func, *args, **kw):
        """Постановка команды на асинхронную обработку
        """
        try:
            self.q.put((func, args, kw), block=False)
        except Queue.Full:
            pass

    def clear(self):
        try:
            if self.after_id is not None:
                self.master.after_cancel(self.after_id)
        except:
            pass
        # XXX not sure that is safe:
        # 1. If some items in self.q are processing in the moment?
        # 2. Task, that is clearing may clear not only own, but alien msg.
        try:
            if self.q:
                self.q = Queue.Queue()
        except:
            pass

    def _idle(self):
        """Фоновая обработка асинхронных сообщений к GUI"""
        while True:
            try:
                func, args, kw = self.q.get(block=False)
                func(*args, **kw)
            except Queue.Empty:
                break
        self.master.after(self.period, self._idle) 

    def safe(self):
        """Decorator function"""
        def w(func):
            def f(*a, **kw):
                return self.post(func, *a, **kw)
            return f
        return w

def tksafe(tkasyncobj):
    """Decorator function"""
    def w(func):
        def f(*a, **kw):
            return tkasyncobj.post(func, *a, **kw)
        return f
    return w

#class TkPeriodic(ThreadManager):
#    """Simulate periodic process"""
#    def __init__(self, func, delay=1, nrespawns=None, *a, **kw):
#        """
#        #tkas - TkAsync object
#        func - tkasync-safe simulation function which takes when call a and kw as arguments,
#        delay - period in seconds, nrespawns is respawning times on exception (see ThreadManager)"""
#        ThreadManager.__init__(self, nrespawns)
#        #self.tkas = tkas
#        self.sim_func = func
#        self.sim_args = a
#        self.sim_kwargs = kw
#        self._delay = delay
#
#    #def post(self, func, *a, **kw):
#        #"""Async. calling Tk"""
#        #self.tkas.post(func, *a, **kw)
#
#    def __thrrun__(self):
#        while not self._cancel:
#            #self.post(self.sim_func, *self.sim_args, **self.sim_kwargs)
#            self.sim_func(*self.sim_args, **self.sim_kwargs)
#            self.delay(self._delay)
