# Multi-thread console input() via class MTInput

import sys
import msvcrt
import string
from threading import Lock

# FIXME Needs Win32 module msvcrt! Under Linux is possible to use
# tty (but not on FAT FS system like in Linpac controllers!)
PROMPT = ">>>"
def normstr(s):
    """Interpret backspaces in string s,
    returns normal string
    """
    rs = reversed(s)
    res = []
    skip = 0
    for ch in rs:
        if ord(ch) == 8:
            skip += 1
            continue
        elif skip:
            skip -= 1
            continue
        else:
            res.append(ch)
    return u"".join(reversed(res))

class MTInput:
    """Multi-thread input line. Can be used like:

    import time
    import thread

    inputer = MTInput()
    def f():
    while 1:
        print '\ntest.......'
        inputer.update()
        time.sleep(2)
    thread.start_new_thread(f, ())
    while 1:
        inp = inputer.input()
        print 'ENTERED:', inp
        if inp == ".":
            break
        else:
            # ... process ...
    """
    def __init__(self, stdout=None, prompt=PROMPT):
        self._stdout = stdout or sys.stdout
        self._enc = getattr(self._stdout, "encoding", "ascii")
        self._prompt = prompt
        self._buf = []
        self._lock = Lock()

    def update(self):
        with self._lock:
            buf = u"".join(self._buf)
            try:
                s = u"%s %s" % (self._prompt, buf)
                encs = s.encode(self._enc)
                self._stdout.write(encs)
                self._stdout.flush()
            except:
                pass

    def input(self, prompt=PROMPT):
        with self._lock:
            self._buf = []
            self._prompt = prompt
        self._stdout.write(self._prompt + " ")
        self._stdout.flush()
        while True:
            ch = msvcrt.getwche()
            if ch in "\r\n":
                with self._lock:
                    buf = u"".join(self._buf)
                    self._buf = []
                buf = normstr(buf)
                return buf
            else:
                with self._lock:
                    self._buf.append(ch)
