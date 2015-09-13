# -*- coding: cp1251 -*-
from pybase.utils import safe, atof

def _avoid_value(hole):
    """Decorator - return validator which enable any value except
    hole"""
    def f(value):
        if value==hole:
            raise ValueError
        else:
            return value
    return f

class BaseValidator:
    """Base validation. Default behaviour is to `eat` any not None value:

    >>> bv = BaseValidator()
    >>> bv(0)
    0
    >>> bv('a')
    'a'
    >>> bv(None)
    Traceback (most recent call last):
        ...
    ValueError
    """
    def __init__(self, vfunc=_avoid_value(None), hint="", opts={}, **kw):
        """vfunc is validation function which must raise Exception
        (ValueError!) on invalid data and return casted
        value to it's domain. opts is additional options for
        validator, default is value to be returned instead of
        exception raised when is set"""
        self.opts = dict(opts)
        self.hint = hint or self.__class__.__name__
        if "default" in kw:
            self.vfunc = safe(vfunc, kw["default"])
        else:
            self.vfunc = vfunc
    def __call__(self, *a, **kw):
        return self.vfunc(*a, **kw)

class SetValidator(BaseValidator):
    """Validate that value is in set.
    Note, in_ __init__ arg must have __contains__ and __str__.

    >>> sv = SetValidator()
    >>> sv.hint
    'any'
    >>> sv(9)
    9
    >>> sv = SetValidator(in_=(1,2,3))
    >>> sv.hint
    'in (1, 2, 3)'
    >>> sv(3)
    3
    >>> sv(9)
    Traceback (most recent call last):
        ...
    ValueError
    >>> sv = SetValidator("available weight", (1,2,3))
    >>> sv.hint
    'available weight'
    >>> sv(3)
    3
    >>> sv = SetValidator(in_=(1,2), default='unknown')
    >>> sv(0)
    'unknown'
    >>> sv = SetValidator(in_=xrange(0,1000))
    >>> sv(1)
    1
    >>> sv(1)
    1
    """
    def __init__(self, hint=None, in_=None, **kw):
        self.in_ = in_
        hint = hint or ("any" if in_ is None else "in %s"%str(in_))
        def vfunc(value):
            if self.in_ is None or value in self.in_:
                return value
            else:
                raise ValueError
        BaseValidator.__init__(self, vfunc, hint, **kw)

class IntValidator(BaseValidator):
    """Validate that value is integer:
    >>> iv = IntValidator()
    >>> iv("9")
    9
    >>> iv("a")
    Traceback (most recent call last):
        ...
    ValueError: invalid literal for int() with base 10: 'a'
    >>> iv("a", 16)
    10
    """
    def __init__(self, hint=None, **kw):
        BaseValidator.__init__(self, int, hint, **kw)

class FloatValidator(BaseValidator):
    """Validate that value is float:
    >>> fv = FloatValidator("weight", default='no')
    >>> fv.hint
    'weight'
    >>> fv(9)
    9.0
    >>> fv("9.12")
    9.12
    >>> fv("9,12")
    9.12
    >>> fv("a")
    'no'
    """
    def __init__(self, hint=None, **kw):
        def vfunc(value):
            if isinstance(value, str):
                return atof(value)
            else:
                return float(value)
        BaseValidator.__init__(self, vfunc, hint, **kw)

class ChainValidator(BaseValidator):
    """Validators chaining: all validators pipes value. If exception occurs
    in piping then default of this validator will be returned or exception
    occurs (if default is not set):
    >>> sv = SetValidator(in_=(1,2,3,4))
    >>> sv('1')
    Traceback (most recent call last):
        ...
    ValueError
    >>> iv = IntValidator(default=4)
    >>> av = ChainValidator(and_=(iv, sv), default='what?')
    >>> av('1')
    1
    >>> av('2')
    2
    >>> av('10')
    'what?'
    >>> av('x')
    4
    >>> av.hint
    'IntValidator & in (1, 2, 3, 4)'
    >>> av = ChainValidator(and_=(iv, sv), hint="int list", opts={"something":123})
    >>> av.hint
    'int list'
    >>> av.opts["something"]
    123
    """
    def __init__(self, and_, hint=None, **kw):
        self.and_ = and_
        def vfunc(value):
            v = value
            for validator in and_:
                v = validator(v)
            return v
        if not hint:
            h = []
            for v in and_:
                h.append(str(v.hint))
            h = " & ".join(h)
            #if h: h = "[%s]"%h
        else:
            h = hint
        BaseValidator.__init__(self, vfunc, h, **kw)

if __name__=="__main__":
    import doctest
    doctest.testmod()
