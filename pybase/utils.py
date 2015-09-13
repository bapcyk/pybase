# -*- coding: cp1251 -*-

"""
CONTRIBS: Thanks to Mercurial development command!
"""

import itertools
import collections
from threading import Lock
import socket
import datetime
import time
import math
import subprocess
import tempfile
import types
import sys
import os


def panic(msg, exc=None, rc=1):
    print u"ERROR: %s"%msg
    if exc:
        print "Details >>>"
        print unicode(exc) or exc.__class__.__name__
    sys.exit(rc)

def islices(seq, num):
    """Cuts sequence seq on slices with length num.
    Each slice is iterator on its elements. Yielding
    will be to the end of sequence. To finish early,
    use close() of Generator:
    >>> for sl in islices((1,2,3,4,5,6,7,8,9,0), 4):
    ...     for x in sl: print x
    ...     print '--'
    1
    2
    3
    4
    --
    5
    6
    7
    8
    --
    9
    0
    --
    """

    if num <= 0:
        raise ValueError("num must be > 0")

    # подбираем empty - критерий окончания итерирования
    try:
        # если seq имеет длину, пытаемся ограничить генерацию слайсов ею
        length = len(seq)
        empty = lambda abeg: abeg >= length
    except:
        empty = lambda _:False

    seq = iter(seq) # иначе для list/tuple будет выдавать 0,1,2; 0,1,2; 0,1,2.. вместо 0,1,2; 3,4,5..
    beg = 0
    while not empty(beg):
        yield itertools.islice(seq, 0, num)
        beg += num

def atof(s):
    """Convert string s to float; s can be with `,` instead of `.`:
    >>> atof("12.3")
    12.3
    >>> atof("12,3")
    12.3
    """
    return float(s.replace(',', '.'))

def dictdefaults(original_dict={}, **defaults):
    """Returns copy of original_dict but if some keys from
    defauls are missed in it (only in this case!), then
    they will be set to its defaults values:
    >>> dictdefaults({1:100, 2:200, 'z':0}, x=56, z=100)
    {1: 100, 2: 200, 'z': 0, 'x': 56}
    """
    ret = {}
    ret.update(original_dict)
    for k,v in defaults.iteritems():
        ret.setdefault(k, v)
    return ret

def dothier(seq, sep='.'):
    """Generate path from dot-strings in order for creation
    tree: first - parents then children:
    >>> for x in dothier(["x.y.z", "a"]): print x, x.leaf
    a True
    x False
    x.y False
    x.y.z True

    Every returned string (unicode) has flag - leaf
    """
    # returns this, as unicode but with flag leaf
    _Node = type("dothier_node", (unicode,), {"leaf":False})

    seq = sorted(seq)
    mem = set()
    for p in seq:
        spl = p.split(sep)
        for ip in xrange(1, len(spl) + 1):
            pp = _Node(sep.join(spl[:ip]))
            if len(spl) == 1 or ip == len(spl):
                pp.leaf = True
            if not pp in mem:
                yield pp
                mem.add(pp)

def dottree(seq, sep='.', fullpath=False):
    """Returns dict of dicts like tree from sequence of dot separated strings.
    For example,
    >>> dottree(["x.y.z", "x.y", "a", "a.b.c", "a.b"])
    {'a': {'b': {'c': {}}}, 'x': {'y': {'z': {}}}}

    and

    >>> dottree(["x.y.z", "x.y", "a", "a.b.c", "a.b"], fullpath=True)
    {'a': {'a.b': {'a.b.c': {}}}, 'x': {'x.y': {'x.y.z': {}}}}
    """
    def ins(map, path):
        d = map
        parents = []
        for p in path:
            if fullpath:
                key = sep.join(parents + [p])
            else:
                key = p
            d = d.setdefault(key, {})
            parents.append(p)
    ret = {}
    seq = sorted(seq)
    for p in seq:
        pp = p.split(sep)
        if not pp:
            continue
        ins(ret, pp)
    return ret

def strindent(s, tabstep=None):
    """Returns IndStr (indented string) with attrs 'sp' (spaces),
    'ts' (tabstop), tabstop is the number of spaces (' '|'\t')*tabstep
    or tabstep (if it's None). spaces is the number of spaces (not steps).
    If there are even spaces, raises IndentationError. If ' ' and '\t'
    are mixed, raises too. Empty strings are ignored. Use unicode strings!
    >>> s=strindent('    qwe')
    >>> s.sp
    4
    >>> s.ts
    4
    >>> s=strindent('    qwe', 2)
    >>> s.sp
    4
    >>> s.ts
    2
    >>> str(s)
    'qwe'
    >>> strindent('   qwe', 2)
    Traceback (most recent call last):
        ...
    IndentationError: not odd indentation steps
    """
    IndStr = type("IndStr", (type(s),), {"ts":0, "sp":0})
    parts = None
    tabs = spaces = False
    for i,ch in enumerate(s):
        if ch not in (u' ', u'\t'):
            parts = [s[:i], s[i:]]
            break
        elif ch==u' ':
            spaces = True
        elif ch==u'\t':
            tabs = True
    if not parts:
        # no spaces in string begining
        return IndStr(s)
    else:
        # else there are spaces at start of string
        if tabs and spaces:
            # mixed ' ', '\t' - error!
            raise IndentationError("mixed ' ', '\\t' in indent")
        else:
            # no mixed ' ' and '\t'
            if tabstep is None:
                s = IndStr(parts[1])
                s.sp = len(parts[0])
                s.ts = s.sp
                return s
            else:
                if len(parts[0]) % (tabstep or 1):
                    raise IndentationError("not odd indentation steps")
                else:
                    s = IndStr(parts[1])
                    s.sp = len(parts[0])
                    s.ts = s.sp/(tabstep or 1)
                    return s

def indentlines(lines):
    """Iterate over lines, yields pairs (level, string).
    >>> for l,s in indentlines((\
    'File',\
    'Info')):
    ...     print l,s
    0 File
    0 Info

    >>> for l,s in indentlines((\
    'File',\
    'Open',\
    '    Open',\
    'Info')):
    ...     print l,s
    0 File
    0 Open
    1 Open
    0 Info

    >>> for l,s in indentlines((\
    '    File',\
    '        Open',\
    '    --',\
    '    Info')):
    ...     print l,s
    0 File
    1 Open
    0 --
    0 Info

    >>> for l,s in indentlines((\
    '    File',\
    '     Open',\
    '    --',\
    '    Info')):
    ...     print l,s
    0 File
    1 Open
    0 --
    0 Info

    >>> for l,s in indentlines((\
    '    File',\
    '      Open',\
    '       --',\
    '    Info')):
    ...     print l,s
    Traceback (most recent call last):
        ...
    IndentationError: line 3: not odd indentation steps

    >>> for l,s in indentlines((\
    '    File',\
    '      Open',\
    '          --',\
    '    Info')):
    ...     print l,s
    Traceback (most recent call last):
        ...
    IndentationError: line 3: unexpected indentation
    """
    tabstep = None
    start = None
    prevind = 0
    i = 0
    for ln in lines:
        if not ln.strip():
            # skip empty lines
            continue
        try:
            indstr = strindent(ln, tabstep)
            if i == 0:
                start = indstr.sp
                ind = 0
            else:
                sp = indstr.sp - start
                if tabstep is None and sp:
                    # tabstep is first non-zero spaces count
                    tabstep = sp
                ind = sp/(tabstep or 1)
                if ind - prevind > 1:
                    raise IndentationError("unexpected indentation")
            yield (ind, unicode(indstr))
            prevind = ind
            i += 1
        except IndentationError as x:
            raise IndentationError("line %d: %s"%(i+1,str(x)))

def safe(func, default=None, exceptions=None):
    """Makes from func safe function which instead of
    exception raising will return default value.
    Avoided exceptions are list of Exception-based classes.
    Default avoid ALL exceptions:
    >>> safe(int, -1)("a") == -1
    True
    >>> safe(int, -1)("8") == 8
    True
    >>> safe(int, exceptions=(KeyError,))("a")
    Traceback (most recent call last):
        ...
    ValueError: invalid literal for int() with base 10: 'a'
    >>> sint = safe(int, exceptions=(ValueError, KeyError))
    >>> sint('a', 16)
    10
    >>> sint.__doc__
    'Safe version of int. Avoided exceptions: (ValueError, KeyError)'
    """
    X = exceptions or (Exception,)
    def w(*a, **kw):
        try:
            return func(*a, **kw)
        except X:
            return default
    prevented = ", ".join(x.__name__ for x in X)
    w.__doc__ = "Safe version of %s. Avoided exceptions: (%s)"%(func.__name__, prevented)
    return w
safe_int = safe(int, default=None)

def find(items, item=None, func=None):
    """Find item by self or by predicate function. If no such
    element, raises ValueError. If no item and no
    func, nothing to do:
    >>> find([1,2,3,4,5], 3)
    3
    >>> find([1,2,3,4,5], func=lambda el:el==4)
    4
    >>> find([1,2,3,4,5])
    >>> find([1,2,3,4,5], 10)
    Traceback (most recent call last):
        ...
    ValueError: no such element
    """
    if func:
        for it in items:
            if func(it):
                return it
        raise ValueError("no such element")
    elif item:
        for it in items:
            if it==item:
                return it
        raise ValueError("no such element")

class namedlist(list):
    """Like named tuple:
    >>> nl = namedlist([1, 2, 3])
    >>> nl.names = ("first", "second")
    >>> nl["first"]
    1
    >>> nl["second"]
    2
    >>> nl[0]
    1
    >>> nl[1]
    2
    >>> nl[2]
    3
    >>> nl["third"]
    Traceback (most recent call last):
        ...
    IndexError: namedlist index out of range
    >>> nl.first
    1
    >>> nl.x
    Traceback (most recent call last):
        ...
    AttributeError: 'namedlist' object has no attribute 'x'
    """
    def __init__(self, items=None):
        super(namedlist, self).__init__(items or [])
        self.names = []

    def __getattr__(self, atr):
        try:
            i = self.names.index(atr)
            return super(namedlist, self).__getitem__(i)
        except:
            raise AttributeError(u"'namedlist' object has no attribute '%s'"%atr)

    def __getitem__(self, i):
        try:
            if not isinstance(i, int):
                i = self.names.index(i)
            return super(namedlist, self).__getitem__(i)
        except:
            raise IndexError("namedlist index out of range")

# TODO never tested
def modpath(modfile):
    """Absolute path of calling module.
    modfile is the module __file__"""
    return os.path.dirname(modfile) or os.getcwd()

if "win" in sys.platform:
    DEFAULT_OS_EDITOR = "c:\\windows\\notepad.exe"
else:
    DEFAULT_OS_EDITOR = "/usr/bin/vi"

def find_editor():
    return os.environ.get("EDITOR", DEFAULT_OS_EDITOR)

def system(cmd, environ={}, cwd=None):
    """
    Enhanced shell command execution.
    run with environment maybe modified, maybe in different dir.
    """
    sh_encoding = sys.getfilesystemencoding()
    def py2shell(val):
        'convert python object into string that is useful to shell'
        if val is None or val is False:
            return '0'
        if val is True:
            return '1'
        return str(val)

    #if sys.platform == "win32":
    if cmd: cmd = cmd.encode(sh_encoding)
    if cwd: cwd = cwd.encode(sh_encoding)

    origcmd = cmd
    if os.name == 'nt':
        cmd = '"%s"' % cmd
    env = dict(os.environ)
    closefds = os.name == "posix"
    env.update((k, py2shell(v)) for k, v in environ.iteritems())
    rc = subprocess.call(cmd, shell=True, close_fds=closefds,
                         env=env, cwd=cwd)
    if sys.platform == 'OpenVMS' and rc & 1:
        rc = 0
    if rc:
        raise OSError("Error to execute %s"%cmd)
    return rc

def os_edit_text(text, editor=None):
    """Edit text by OS default text editor (may be set as EDITOR environment variable)
    or by editor (full path to program).  Returns None if nothing changed else new text.
    """
    (fd, name) = tempfile.mkstemp(prefix="pybase", suffix=".txt",
                                  text=True)
    try:
        f = os.fdopen(fd, "w")
        f.write(text)
        f.close()

        editor_prg = editor if editor else find_editor()
        system("%s %s"%(editor_prg, name))

        f = open(name)
        t = f.read()
        f.close()
    finally:
        os.unlink(name)

    return None if t==text else t

# TODO need improving, testing!
def quote_win32(c):
    """Quoting of string for Win32 command line (very basicely!):
    """
    c = c.strip("'")
    c = c.replace('\\', '\\\\')
    c = c.replace('"', '\\"')
    c = u'"%s"'%c
    return c

def minmax(v, min_, max_):
    """Return v when it in min_, max_ range, when it
    out of range, returns min_ (if less) and max_ (if above):
    >>> minmax(10, 0, 20)
    10
    >>> minmax(-1, 0, 20)
    0
    >>> minmax(100, 0, 20)
    20
    >>> minmax(20, 0, 20)
    20
    """
    if v < min_:
        return min_
    elif v > max_:
        return max_
    else:
        return v

## TODO never tested!
#def thrsafe(func):
#    """decorate func to be thread-safe"""
#    lock = Lock() # does shared for ALL funcs?????????
#    def f(*a, **kw):
#        with lock:
#            return func(*a, **kw)
#    return f
#
## TODO never tested!
#class MetaThrSafeCont(type):
#    """Metaclass for creation thread-safe classes"""
#    def __new__(meta, name, bases, dict):
#        for mn,mb in dict.iteritems():
#            if mn.startswith("__"):
#                continue
#            elif isinstance(mb, collections.Callable):
#                dict[mn] = thrsafe(mb)
#        return type.__new__(meta, name, bases, dict)
#
## TODO never tested!
#SharedList = MetaThrSafeCont("SharedList", (list,), {})
#SharedDict = MetaThrSafeCont("SharedDict", (dict,), {})

# TODO never tested!
#class Listeners:
#    """Thread-safe calling of function list.
#    Every function has name (or default name) and is append
#    under this name like to dictionary. When function is called
#    it's impossible to be deleted (at the same time).
#    Main idea of this class is to get thread-safe way to
#    call funcs. from collection of functions: one or all of them.
#    Something like Listeners pool"""
#    def __init__(self):
#        self.__funcs = SharedDict()
#
#    def reg(self, func, name=""):
#        """Append named func"""
#        if not name:
#            name = id(func)
#        if name in self.__funcs:
#            raise KeyError("Replacing is not supported")
#        self.__funcs[name] = {"func":func, "lock":Lock()}
#        return name
#
#    def call(self, name, *a, **kw):
#        """Call one function with name and args a, kw;
#        since is called, deletion is not possible (by lock)"""
#        p = self.__funcs[name]
#        with p["lock"]:
#            ret = p["func"](*a, **kw)
#        return ret
#
#    def call_all(self, *a, **kw):
#        """Call all funcs with the same arguments.
#        Results are yielding"""
#        for n in self.__funcs:
#            ret = self.call(n, *a, **kw)
#            yield ret
#
#    def unreg(self, name):
#        """Remove func with name; since func is called,
#        remove will be blocked"""
#        p = self.__funcs[name]
#        with p["lock"]:
#            del self.__funcs[name]

TZ = os.environ.get("PYBASE_TZ", "UTC")

try:
    import pytz

    def tzinfo(tzname=None):
        """Returns tzinfo from timezone name"""
        if not tzname:
            tzname = TZ
        return pytz.timezone(tzname)

except:
    def tzinfo(tzname=None):
        if not tzname:
            tzname = TZ
        class TZinfo(datetime.tzinfo):
            """TZinfo"""
            def utcoffset(self, dt):
                return datetime.timedelta(seconds=time.timezone)
            def dst(self, dt):
                return datetime.timedelta(0)
            def tzname(self, dt):
                return tzname
        return TZinfo()

def now(tz=None):
    """Return current datetime with timezone info.
    tz is tzinfo object|None|timezone name like 'Asia/Omsk'
    """
    if isinstance(tz, (types.NoneType, unicode, str)):
        tz = tzinfo(tz)
    return datetime.datetime.now(tz)

MAX_RECV = 8192
def recvall(sock, timeout=None):
    """Receive from socket sock. Suck all (MAX_RECV for one recv() call)
    from socket
    """
    if timeout is not None:
        sock.settimeout(timeout)
    chunks = []
    try:
        while True:
            buf = sock.recv(MAX_RECV)
            if not buf:
                break
            chunks.append(buf)
    except socket.timeout:
        pass
    return "".join(chunks)

# another variant of recvall - results are the same
#import select
#def recvall(sock, timeout=0):
#    chunks = []
#    try:
#        while 1:
#            r,w,x = select.select([sock], [], [], timeout)
#            if not r:
#                break
#            buf = sock.recv(MAX_RECV)
#            if not buf:
#                break
#            chunks.append(buf)
#    except:
#        pass
#    return "".join(chunks)

#def rint(f):
#    """Round number:
#    >>> rint(1.2)
#    1
#    >>> rint(1.5)
#    1
#    >>> rint(1.9)
#    2
#    >>> rint(0)
#    0
#    >>> rint(0.1)
#    0
#    """
#    f, c = math.modf(f)
#    if f > 0.5:
#        return int(c+1)
#    else:
#        return int(c)

if __name__ == "__main__":
    import doctest
    doctest.testmod()
    #s = IndentedString("   asd", 3)
    #print s.sp, s.ts, s
    #for l,t in indentlines("""
        #File
            #Open
            #Close
        #Info""".splitlines()):
        #print l, t
