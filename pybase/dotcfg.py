# -*- coding: cp1251 -*-
import codecs
from collections import OrderedDict

DOT = "."  # delimiter of sections (in path)
SET = "="  # symbol of setting (may be '=' or something else)
REM = "#"  # commented lines begins with this
CON = "\\" # continuous line by this (at end), NOTE NOLY ONE SYMBOL

# Errors {{{

class DotCfgError(Exception):
    def __init__(self, all):
        """all is seq of DotCfgErrorSrc
        """
        self.all = all
        msg = "\n".join(unicode(a) for a in all)
        Exception.__init__(self, msg)

class DotCfgErrorSrc:
    # string representation of exception class, may be changed
    REASONS = {
        ValueError: "invalid value",
        "default": "syntax error", # never delete "default" !
    }
    def __init__(self, reason, nline=None, src=None):
        """reason is the exception class: ValueError (invalid value of
        Parameter), else - syntax error nature; nline is the line number,
        src is the Parameter object if one is invalid and is source of error
        """
        self.nline = nline
        self.reason = reason
        self.src = src
        self._defreas = DotCfgErrorSrc.REASONS["default"]
    def __unicode__(self):
        reas = DotCfgErrorSrc.REASONS.get(self.reason, self._defreas)
        if self.nline is not None:
            return u"%d: %s"%(self.nline, reas)
        else:
            return reas

# }}}

# Parameter {{{

# type for block (multiline string), nline is first line number
_Block = type("_Block", (unicode,), {"line":0, "nlines":1})

def parse_parameter_line(line):
    """Parse parameter line, returns (name, value). Raise Exception on syntax error"""
    spl = line.split(SET)
    if len(spl) != 2:
        raise Exception()
    n,v = [s.strip() for s in spl]
    return (n,v)

# Validation is in Parameter bcz is possible to retriev parameter
# from cfg file and then change it's value via Parameter instance
class Parameter(object):
    """Parameter of config file
    All members starts with `_` are read-only!
    """
    def __init__(self, name=None, default=None, validator=None, comments=None, **kw):
        self._name = None
        self._path = [] # name splitted by DOT
        self._default = default
        self._validator = validator
        self._comment = None # comments, joined to line
        self._comments = [] # list of commented lines (with REM at begin on each)
        self._value = None
        self.name = name
        self.comments = comments
        self.opts = kw

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, v):
        self._name = v
        self._path = v.split(DOT) if v else [] # splitted name

    @property
    def path(self):
        return self._path

    @property
    def validator(self):
        return self._validator
            
    @property
    def comments(self):
        return self._comments

    @comments.setter
    def comments(self, v):
        """v is list of lines (or one string)!"""
        if v:
            if not isinstance(v, (list, tuple)):
                v = [v]
            self._comments = [l.lstrip(REM+' ') for l in v]
            self._comment = " ".join(self._comments)

    @property
    def comment(self):
        """Joined comments without REM"""
        return self._comment

    @property
    def value(self):
        return self._default if self._value is None else self._value

    @value.setter
    def value(self, v):
        """When validator exists and try to set INVALID value,
        self._value will be set to _default value and the same time
        exception will be thrown.
        """
        if self.validator:
            try:
                self._value = self.validator(v)
            except:
                # invalid value
                if self._value is None:
                    self._value = self._default
                raise
        else:
            self._value = v

    def __repr__(self):
        """External representation of value, for ex, in input fields
        of UI forms
        """
        return u"%s"%self.value

    def parse(self, line):
        """Parse not-comment line. Can raise exception:
        bcz of ValueError (there is validator and v
        is invalid) or something else (syntax error).
        After exception state is VALID (value will be
        untouched!):
        >>> par = Parameter(comments=u"some comment")
        >>> par.parse("a.b.c = 100")
        >>> par.name
        'a.b.c'
        >>> par.value
        '100'
        >>> par.path
        ['a', 'b', 'c']
        >>> par.comment
        u'some comment'
        >>> unicode(par)
        u'# some comment\\na.b.c = 100'
        >>> par = Parameter()
        >>> par.parse("a.b.c =")
        >>> par.name
        'a.b.c'
        >>> par.value
        ''
        >>> unicode(par)
        u'a.b.c = '
        >>> par.parse("a = xxx\\nyyy\\nzzz")
        >>> par.value
        'xxx\\nyyy\\nzzz'
        """
        n,v = parse_parameter_line(line)
        self.name = n # first set name (for lazy validation)!
        self.value = v

    def __unicode__(self):
        ret = ""
        if self._comments:
            ret += "\n".join(u"%s %s" % (REM,c) for c in self._comments)
        if ret: ret += "\n"
        ret += "%s %s %s" % (self.name, SET, self.value)
        return ret

    def __nonzero__(self):
        return bool(self._name)

# }}}

# DotCfg {{{

class DotCfg(object):
    """Config parser:
    >>> exp = (Parameter("a.b.c", comments="sensor 1", default=10), Parameter("a.b.d", comments="sensor 2", default=20))
    >>> dc = DotCfg(exp)
    >>> dc.template()
    u'# sensor 1\\na.b.c = 10\\n# sensor 2\\na.b.d = 20'
    """
    def __init__(self, expected=None):
        """expected is seq of Parameter"""
        self._params = OrderedDict()
        self._expected = expected or []
        self._src = None # parsed fileobj with possible .name, .encoding

    @property
    def names(self):
        """Iterator on parameters name"""
        if self._params:
            return self._params.iterkeys()
        else:
            return [par.name for par in self._expected]

    @property
    def paths(self):
        """Iterator on parameters name"""
        if self._params:
            return [par.path for par in self._params.itervalues()]
        else:
            return [par.path for par in self._expected]

    def _iterblocks(self, fileobj):
        """Iterate over text blocks (one block is one parameter
        definition), blocks can be multiline
        """
        blklines = []
        for nline, line in enumerate(fileobj):
            line = line.rstrip()
            if not line:
                continue
            # test on multiline
            multiline = line.endswith(CON)
            # cut spaces and CON-symbol at the end
            line = line.rstrip(CON)
            if multiline:
                blklines.append(line)
            elif blklines:
                blklines.append(line)
                block = _Block("\n".join(blklines))
                block.line = nline
                block.nlines = len(blklines)
                yield block
                blklines = []
            else:
                block = _Block(line)
                block.line = nline
                yield block

        if blklines:
            block = _Block("\n".join(blklines))
            block.line = nline
            block.nlines = len(blklines)
            yield block

    def parse(self, fileobj):
        """Can raise exception. Usually DotCfgError, describes errors:
        real syntax or validation errors.
        fileobj is the file-like object with .name and .encoding
        (so flush() will use it to writing if they exists) and
        iterable (on text lines!):
        >>> import StringIO
        >>> sio = StringIO.StringIO(
        ...     '# comment1\\n'
        ...     '# comment2\\n'
        ...     'x.y = aaa\\\\n'
        ...     ' bbb\\\\n'
        ...     '  ccc\\n'
        ...     '# comment3\\n'
        ...     'a = 10\\n'
        ...     'a.b.c = 20')
        >>> dc = DotCfg()
        >>> dc.parse(sio)
        >>> dc.get_value('x.y')==r'aaa\\n bbb\\n  ccc'
        True
        >>> dc.get('x.y').comments
        [u'comment1', u'comment2']
        >>> dc.get('x.y').comment
        u'comment1 comment2'
        >>> dc.get_value('a')
        u'10'
        >>> dc.get('a').comment
        u'comment3'
        >>> dc.get_value('a.b.c')
        u'20'
        >>> dc.get('a.b.c').comment
        >>> dc.get('a.b.c').comments
        []
        """

        def name2par(name):
            """find expected Parameter for name"""
            exp = [p for p in self._expected if name==p.name]
            return exp[0] if exp else Parameter(name=name)

        self._src = fileobj
        self._params.clear()
        errors = []
        comments = []
        name = None
        value = None
        par = None
        #for nline, line in enumerate(fileobj):
        for line in self._iterblocks(fileobj):
            # line is _Block object
            nline = line.line
            if line.startswith(REM):
                # is comment
                comments.append(line)
            else:
                # is not comment
                try:
                    name, value = parse_parameter_line(line)
                    par = name2par(name)
                    par.name = name
                    par.comments = comments
                    par.value = value
                except ValueError:
                    # invalid value of parameter (validator raises exception)
                    errors.append(DotCfgErrorSrc(nline=nline+1, reason=ValueError, src=par))
                    if par:
                        self._params[par.name] = par
                except Exception, x:
                    # error in parsing
                    errors.append(DotCfgErrorSrc(nline=nline+1, reason=x.__class__))
                else:
                    if par:
                        self._params[par.name] = par

                # new iteration - forget stail data
                comments = []
                name = None
                value = None
                par = None
        if par:
            self._params[par.name] = par
        if errors:
            raise DotCfgError(all=errors)

    def template(self):
        """Only expected parameters as string"""
        return "\n".join(unicode(par) for par in self._expected)

    def flush(self, filename=None, encoding=None):
        filename = filename or getattr(self._src, "name", None)
        encoding = encoding or getattr(self._src, "encoding", "utf8")
        if filename and encoding:
            with codecs.open(filename, "w", encoding=encoding) as f:
                f.write(unicode(self))

    def __unicode__(self):
        return "\n\n".join(unicode(par) for par in self._params.itervalues())

    def get(self, key, default=None):
        """get Parameter if exists, else get from _expected,
        else returns default
        """
        ret = self._params.get(key, None)
        if ret:
            return ret
        else:
            exp = [par for par in self._expected if par.name==key]
            if exp:
                return exp[0]
            else:
                return default

    def get_value(self, key, default=None):
        """Like get but returns value"""
        par = self.get(key, None)
        if par:
            return par.value
        else:
            return default

# }}}

if __name__=="__main__":
    import doctest
    doctest.testmod()

#    import StringIO
#    CON = '$'
#    sio = StringIO.StringIO(
#        '# comment1\n'
#        '# comment2\n'
#        'x.y = aaa$\n'
#        ' bbb$\n'
#        '  ccc\n'
#        '# comment3\n'
#        'a = 10\n'
#        'a.b.c = 20\n')
#    dc = DotCfg()
#    dc.parse(sio)
#    print
#    print dc.get('a').value=='10'
#    print dc.get('x.y').value=='aaa\n bbb\n  ccc'
#    print dc.get('a.b.c').value=='20'
#    print dc.get('a').comment=='comment3'
#    print dc.get('x.y').comment=='comment1 comment2'
#    print dc.get('a.b.c').comment is None
