# -*- coding: cp1251 -*-

from threading import Thread, Event

class StopRespawn(Exception):
    """Occurs when no more possibility to respawn thread
    (if number is limited)"""
    def __init__(self, reason=None, message=""):
        """reason is Exception of stopping"""
        self.reason = reason
        self.message = message

class ThreadManager:
    def __init__(self, nrespawns=None):
        self._nrespawns = nrespawns # how much times may be respawn
        self._cancel = False
        self._stop_delay = Event()
        self._thr = Thread(target=self.run)
        self.nlife = None # number of "life"

    def start(self):
        # FIXME: condition does not works!!!
        #if not self._thr.is_alive():
            #self._thr.start()
        try:
            self._thr.start()
        except RuntimeError:
            # try to run more than one times
            pass

    def cancel(self):
        self._cancel = True
        self.nodelay()

    def delay(self, sec):
        """freeze threads on sec seconds"""
        self._stop_delay.clear()
        self._stop_delay.wait(sec)

    def nodelay(self):
        """unfreeze thread which was delayed"""
        self._stop_delay.set()

    def wait(self):
        """wait since thread ends"""
        self._thr.join()

    def __thrdel__(self, error):
        """Override to make custom cleaning.
        If error is False then user stop execution,
        else if error is True then exception occurs in __thrinit__ or __thrrun__
        """
        pass

    def __thrinit__(self):
        """Override to make custom initialization on spawn/respawn"""
        pass

    def __thrrun__(self):
        """Override for thread run(), use
        ...
        while not self._cancel:
            body
        ...
        All known exception must be catched, but unexpected - will caused
        thread to be respawn. So, if you need respawn, raise Exception
        """
        pass

    def run(self):
        """Real thread run(); can be overriden but with calling of base
        class run()! Raises StopRespawn when no more respawns possible,
        Exception occurs on other errors or quietly ends.
        Overrided run() can be
        ...
        try:
            ThreadManager.run():
        except StopRespawn:
            report-of-respawning-limit
        except Exception:
            other-errors-report
        # else:
            was canceled...
        ...
        """
        self.nlife = 0
        while not self._cancel:
            # respawning loop
            stop_reason = None
            try:
                self.__thrinit__()
                #print "Before __thrrun__"
                self.__thrrun__()
                #print "After __thrrun__"
            except Exception, x:
                stop_reason = x
                try:
                    #print "Before __thrdel__"
                    self.__thrdel__(True)
                    #print "After __thrdel__"
                except: pass
            else:
                try:
                    self.__thrdel__(False)
                except: pass

            if self._nrespawns is not None and self.nlife >= self._nrespawns:
                # there is respawning limit
                if self._cancel:
                    # and was already canceled, so exit
                    return
                else:
                    # was not canceled yet, so raise StopRespawn
                    raise StopRespawn(stop_reason)

            self.nlife += 1
