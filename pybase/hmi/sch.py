import collections
import itertools
import random
import codecs
import shutil
import copy
import time
import imp
import sys
import os
import re
from Tkconstants import *
from datetime import datetime
from pybase.tk import utils as tkutils
from pybase import utils
from pybase.hmi.sym import SymModule
from pybase.hmi import sim
from pybase.vroot import *
from pybase.dotcfg import DotCfg, Parameter
from PIL import Image, ImageTk
from os import path


# errors messages
NOSCHEMEERR = u"Scheme '%s' not found"


# SchModule - scheme catalog and logic {{{

class SchModule:
    DESCR = "descr" # ASCII only!
    PYMODULE = "sch.py" # only '.py' is used. ASCII only!
    IMG = "image" # name of image file. ASCII only!

    # templates of text files (uses variable substitution in %-style)
    DESCRTEMPLATE = u"""\
# Format of the module
format = scheme,1

# Version of the scheme
version = 0.0

# Date of the creation
date = %(timestamp)s

# Author of the scheme
author = %(user)s

# Keywords: k.word =
"""
    PYMODULETEMPLATE = u"""\
# -*- coding: utf8 -*-
from pybase.hmi.sch import BaseScheme
from pybase.hmi.utils import tksafe

# For thread-safe GUI calls use @tksafe method decorator

class Scheme(BaseScheme):
    pass
"""

    DIR = "usr/share/sch" # after init will be absolute path
    _ready = False # register already as finder, loader

    @classmethod
    def mount(class_, root):
        """init finder,loader, only once;
        root is catalogue of portable root"""
        # XXX class_ - in successors own _ready (?)
        if class_._ready:
            return
        else:
            p = VRoot(root).hpath(SchModule.DIR)
            SchModule.DIR = VRoot(p)
            class_._ready = True

    @staticmethod
    def import_pymodule(scheme):
        """Import PYMODULE for SCADA-scheme with name scheme,
        returns module
        """
        if not SchModule._ready:
            raise ValueError(u"not mounted")

        p = SchModule.DIR.hpath(scheme)
        p = path.join(p, SchModule.PYMODULE)
        p = p.encode(sys.getfilesystemencoding())
        # In load_source(name, path): name is name of module (without extension),
        # path is full path to the file of module
        return imp.load_source(path.splitext(SchModule.PYMODULE)[0], p)

    @staticmethod
    def create(name):
        """Creates all files and folders for new scheme
        """
        if not SchModule._ready:
            raise ValueError("not mounted")

        schdir = SchModule.DIR.hpath(name)

        if path.exists(schdir):
            raise Exception("Already exists")

        # create this scheme directory
        os.makedirs(schdir)

        with codecs.open(path.join(schdir, SchModule.DESCR), "w", "utf8") as f:
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            user = os.getenv("USER", os.getenv("USERNAME", "Unknown"))
            f.write(SchModule.DESCRTEMPLATE % locals())

        with codecs.open(path.join(schdir, SchModule.PYMODULE), "w", "utf8") as f:
            f.write(SchModule.PYMODULETEMPLATE)

    @staticmethod
    def clone(name1, name2):
        """Clone scheme with name1 to name2. Doesn't check that name1 is
        consistent scheme directory
        """
        if not SchModule._ready:
            raise ValueError("not mounted")

        schdir1 = SchModule.DIR.hpath(name1)
        schdir2 = SchModule.DIR.hpath(name2)

        if not path.exists(schdir1):
            raise Exception("Source scheme does not exist")
        if path.exists(schdir2):
            raise Exception("Destination scheme already exists")

        # copy unmodified files
        shutil.copytree(schdir1, schdir2)
        # modify descr-file
        descr2 = path.join(schdir2, SchModule.DESCR)
        dc = DotCfg()
        with codecs.open(descr2, "r", encoding="utf8") as f:
            dc.parse(f)
            par = dc.get(u"date")
            if par:
                par.value = time.strftime("%Y-%m-%d %H:%M:%S")
            par = dc.get(u"author")
            if par:
                par.value = os.getenv("USER", os.getenv("USERNAME", "Unknown"))
        dc.flush()

    @staticmethod
    def isschdir(p):
        """test if p (absolute, normalized) is directory of scheme
        """
        if not SchModule._ready:
            raise ValueError("not mounted")

        descrpath = path.join(p, SchModule.DESCR)
        pymodpath = path.join(p, SchModule.PYMODULE)

        if path.exists(descrpath) and path.exists(pymodpath):
            return True
        else:
            return False

    @staticmethod
    def files(name):
        """Returns {gif:path, tiff:path, descr:path,
        py:path, dsl:path, oth:[0st,1st...], dir:path}
        If some not exists, value will be None. If symbol directory not exists,
        returns None
        """
        if not SchModule._ready:
            raise ValueError("not mounted")

        schdir = SchModule.DIR.hpath(name)
        if not path.exists(schdir):
            return None

        ret = {k:None for k in ("gif", "png", "descr", "py", "dsl", "dir")}
        ret["dir"] = schdir
        ret["oth"] = []
        for fname in os.listdir(schdir):
            if fname == SchModule.DESCR:
                ret["descr"] = path.join(schdir, fname)
            elif fname == SchModule.PYMODULE:
                ret["py"] = path.join(schdir, fname)
            else:
                ext = path.splitext(fname)[1].lower()
                if ext in (".gif", ".png"):
                    ret[ext[1:]] = path.join(schdir, fname)
                else:
                    # seems to be something else
                    ret["oth"].append(path.join(schdir, fname))
        return ret

# }}}

class _Symbol:
    # XXX Render in __init__ immediately
    def __init__(self, scheme, name, x, y, *layers, **kw):
        """Create symbol of scheme. layers are
        layer selectors 'rN'|'vN'|'r*'|'v*'|'all'.
        SymModule should be mounted!
        """
        if not layers:
            layers = ("all",) # *args
        self.symmodule = SymModule.import_pymodule(name)
        self.symmodule.Symbol.tkroot = scheme.app.tkroot
        self.sym = self.symmodule.Symbol(name, scheme.c, x, y)
        self.sym.k.update({k:unicode(v) for k,v in kw.iteritems()})
        try:
            self.sym.render(self.sym.find_layers(*layers))
        except IndexError:
            raise IndexError(u"Incorrect layer number")

#    def __del__(self):
#        self.delete()

    def delete(self):
        try:
            self.sym.delete()
            self.sym = None
            self.symmodule = None
        except:
            pass


# BaseScheme {{{

class BaseScheme(SchModule):
    """Base class of scheme.
    If you need any tk-async method use @tksafe from pybase.hmi.utils
    """
    format = u"scheme,1"

    def __init__(self, name, app, canvas, key="sid", anchor=CENTER, scale=True,
            bg=None):
        """key - is the key for indexing _symbols, so each symbol
        in _symbols is available under key==symbol.k[key]. anchor is the anchor of
        the background image (CENTER|NW...), so it's possible to align image.
        scale enables scaling of background image when it's bigger then canvas
        (only when is bigger, not when is smaller!). bg is the background color.
        """
        self.fs = self.files(name)
        if not self.fs:
            raise Exception(u"Inconsistent scheme (or mismatched location)")
        self.name = name
        self.app = app
        self.c = canvas
        self._bganchor = anchor
        self._bgscale = scale
        self._bgcolor = bg
        self._oldbgcolor = canvas["bg"]
        self._im = None # background image
        self.width = self.height = 0
        self._imwidth = self._imheight = 0 # original size of bg image
        self._cw = self._ch = 0 # size of canvas when image was created
        self.tag = None # tag of background image
        self._key = key
        self._symbols = collections.defaultdict(list) # key is BaseSymbol.k[key]
        self._imfname = self.fs["gif"] or self.fs["png"]
        if not self._imfname:
            raise ValueError(u"No scheme image found")

    def __create_background(self, filename):
        """Create background of scheme
        """
        if self._bgcolor:
            self.c["bg"] = self._bgcolor
        im = Image.open(filename).convert("RGBA")
        self._imwidth, self._imheight = im.size
        self._cw = self.c.winfo_width()
        self._ch = self.c.winfo_height()
        if self._bgscale and (self._imwidth > self._cw or self._imheight > self._ch):
            # need increasing of image
            im = im.resize((min(self._imwidth, self._cw), min(self._imheight, self._ch)))
        self._im = ImageTk.PhotoImage(im)
        self._im.im = im
        x, y = tkutils.anchor_coords(0, 0, self._cw, self._ch, self._bganchor)
        self.tag = self.c.create_image(x, y, image=self._im, anchor=self._bganchor)
        self.c.tag_lower(self.tag, ALL) # or some symbol tag instead of ALL???
        # size of scheme
        self.width, self.height = im.size

    def __delete_background(self):
        """Delete all resource of background image
        """
        if self.tag is not None:
            self.c.delete(self.tag)
            self.tag = None
        if self._im:
            self._im.im = None # silly but... :)
            self._im = None
        if self._bgcolor:
            # was setted, so restore old
            self.c["bg"] = self._oldbgcolor

    def __resize_background(self, event):
        """Resize background image
        """
        # smart optimization: Tk in 1st call of __create_background()
        # give me incorrect width, height of canvas (less then needed),
        # also when user changes window (for example only height),
        # width is changed too (it's strange!). To avoid these cases,
        # I detect that image was created early and that size was
        # changed to be smaller - in this cases I will not really
        # recreate background image. Strange changing of width, when
        # user changes height only is increasing (!) of width to 4 pixels.
        # So I testing with 5
        if self._im and (event.width - self._cw < 5) and \
                (event.height - self._ch < 5):
            return
        self.__delete_background()
        self.__create_background(self._imfname)

#    def __del__(self):
#        try:
#            self.delete()
#        except:
#            pass

    def props(self):
        """Dictionary of properties
        """
        nshapes = 0 # totally GFigRender shapes on canvas
        for sym in self.itersymbols():
            for vl in sym.sym._vlayers:
                nshapes += len(vl.gfr.canvas_shapes)
        ret = {
                "dir": self.fs["dir"],
                "name": self.name,
                "symbols": len(self._symbols),
                "shapes": nshapes,
                "tags": len(self.c.find_all()),
                "size": (self.width, self.height),
                "key": self._key,
        }
        return ret

    def extend_button_event(self, srcevent, push):
        """Extend <Button> event from original Tk srcevent.
        push must be 'up'|'down'|'double'. srcevent will be modified after calling!
        """
        srcevent.targets_sch = self.find_at(srcevent.x, srcevent.y)
        srcevent.push = push
        x, y = self.schcoords(srcevent.x, srcevent.y)
        srcevent.x_sch = x
        srcevent.y_sch = y
        return srcevent

    def itersymbols(self):
        """Iterate over ALL symbols, yield _Symbol, not BaseSymbol!
        """
        for syms in self._symbols.itervalues():
            for sym in syms:
                yield sym

    def ifind_symbols(self, name="any", **kw):
        """Find symbols (BaseSymbol) by name or any keyword (BaseSymbol.k)
        """
        for sym in self.itersymbols():
            if (name=="any" or name==sym.sym.name) and \
                    sym.sym.k==kw:
                yield sym.sym

    def find_symbols(self, **kw):
        """Like the ifind_symbols() but not iterator - returns list
        """
        return list(self.ifind_symbols(**kw))

    def symbol(self, **kw):
        """Like find_symbols() but when found only one, returns
        one item, not list with one item
        """
        if not kw:
            raise ValueError(u"'symbol' needs keyword arguments")
        res = self.find_symbols(**kw)
        if len(res)==1:
            return res[0]
        else:
            return res

    def delete(self):
        """Delete all
        """
        for sym in self.itersymbols():
            try:
                sym.delete()
            except:
                pass
        self._symbols = collections.defaultdict(list)
        self.__delete_background()

    def ifind_at(self, x, y):
        """Find all symbols at canvas coords x,y. Yields BaseSymbol's, not
        _Symbols
        """
        for sym in self.itersymbols():
            bx0,by0,bx1,by1 = sym.sym.bbox()
            if bx0 <= x <= bx1 and by0 <= y <= by1:
                yield sym.sym

    def find_at(self, x, y):
        """Similar to ifind_at but returns list
        """
        return list(self.ifind_at(x, y))

    def resize(self, event=None):
        """On canvas resizing must be called"""
        #self.render()
        self.__resize_background(event)
        #self.__delete_background()
        #self.__create_background(self._imfname)
        for sym in self.itersymbols():
            sym.sym.resize(event)

    def schcoords(self, canx, cany):
        """Convert from canvas coordinates to scheme coordinates,
        which are safe for monitors with different resolutions
        """
        # Coordinates of scheme (0,0) corner as canvas coords.
        # Scheme (0,0) is the left, bottom corner (like in mathematic,
        # not like in canvas)
        x0 = (self._cw - self.width)/2
        y0 = (self._ch - self.height)/2 + self.height
        return (canx - x0, y0 - cany)

    def cancoords(self, schx, schy):
        """Convert from scheme coordinates to canvas coordinates.
        Scheme axes begin (0,0) is at left, bottom corner of the
        background image, not in left, top like is usual for canvas
        """
        # Coordinates of scheme (0,0) corner as canvas coords
        x0 = (self._cw - self.width)/2
        y0 = (self._ch - self.height)/2 + self.height
        return (schx + x0, y0 - schy)

    def render_symbol(self, name, x, y, *layers, **kw):
        """Create new symbol and keep it in self._symbols with
        layers (selectors like 'rN'...). Set symbol 'k' dict
        with **kw (override values from descr file). x,y are
        scheme coordinates.
        """
        if name not in self._symbols:
            ox,oy = x,y
            x,y = self.cancoords(x, y)
            sym = _Symbol(self, name, x, y, *layers, **kw)
            key = sym.sym.k.get(self._key, "noname")
            self._symbols[key].append(sym)
            return sym.sym
        else:
            return None

    def render(self):
        """Render. To render some symbols, overload this method and use in it
        render_symbol(), but first call base class render()!
        """
        self.delete()
        self.__create_background(self._imfname)
        # XXX must be last after successor implementation, but works without this line
        #self.c.event_generate("<Configure>")
        #self.c.update_idletasks()

    def ondata(self, *a, **kw):
        """Occurs on data receiving
        """
        key = kw.get(self._key)
        if key:
            # There is key for dispatching over symbols. syms_of_key
            # are symbols with the same key, if not - (). Call ondata
            # of each of them
            syms_of_key = self._symbols.get(key) or ()
            for sym in syms_of_key:
                # for all symbols with keyword==key
                sym.sym.ondata(*a, **kw)

# }}}


# main

if __name__ == "__main__":
    from Tkconstants import *
    import Tkinter
    from pybase.tk import utils as tkutils

    if len(sys.argv) < 3:
        print "arg: symbol-name root-dir"
        print "Also symbol should contain 2-layers GIF file and two vector gfig files"
        sys.exit(0)

    root = Tkinter.Tk()
    c = Tkinter.Canvas(root, bd=0)
    c.pack(fill=BOTH, expand=YES)
    tkutils.maximize_toplevel(c)
    try:
        arg2 = unicode(sys.argv[2], sys.getfilesystemencoding())
        arg1 = unicode(sys.argv[1], sys.getfilesystemencoding())
        SchModule.mount(arg2)
        bs = BaseScheme(arg1, c)
        bs.render()

#        def dummy(*a): print 1
#        m = bs.popup_menu("""
#            File
#                Open = dummy
#                Close = dummy
#                File Utils...
#                    Create Item = dummy
#            --
#            Info about system = dummy"""
#                )
#        m.post(100, 100)

        #bs.render(bs.ifind_layers("v*", "r*")) # works
        c.mainloop()
    except Exception, x:
        raise
        print unicode(x)
