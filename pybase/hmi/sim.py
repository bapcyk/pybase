# Simulation modes
from pybase.thread import ThreadManager #, StopRespawn

class SimulPkt:
    """Packet for simulation mode
    """
    def __init__(self, *a, **kw):
        self.a = a
        self.kw = kw

class Simulator(ThreadManager):
    def __init__(self, symbols, period=1.0):
        """symbols is the sequence of symbols for testing,
        period is the period of data generation cycles
        """
        self._symbols = symbols
        self._period = period
        ThreadManager.__init__(self)

    def __thrrun__(self):
        while not self._cancel:
            for s in self._symbols:
                spkt = s.simulpkt()
                if spkt:
                    s.ondata(*spkt.a, **spkt.kw)
            self.delay(self._period) # XXX here or in for?
