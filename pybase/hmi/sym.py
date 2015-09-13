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
from pybase import utils
from pybase.hmi import sim
from pybase.vroot import *
from pybase.tk.gfig import *
from pybase.dotcfg import DotCfg, DOT
from PIL import Image, ImageTk, ImageStat
from os import path

cre_vlayername = re.compile("[^\d]*(\d+)[^\d]*")

# errors messages
NOSYMBOLERR = u"Symbol '%s' not found"


# SymModule - symbol catalog and logic {{{

class SymModule:
    DESCR = "descr" # ASCII only!
    PYMODULE = "sym.py" # only '.py' is used. ASCII only!
    IMG = "image" # name of image file. ASCII only!

    # templates of text files (uses variable substitution in %-style)
    DESCRTEMPLATE = u"""\
# Format of the module
format = symbol,1

# Version of the symbol
version = 0.0

# Date of the creation
date = %(timestamp)s

# Author of the symbol
author = %(user)s

# Keywords: k.word =
"""
    PYMODULETEMPLATE = u"""\
# -*- coding: utf8 -*-
from pybase.hmi.sym import BaseSymbol
from pybase.hmi.utils import tksafe

# For thread-safe GUI calls use @tksafe method decorator

class Symbol(BaseSymbol):
    pass
"""

    DIR = "usr/share/sym" # after init will be absolute path
    _ready = False # register already as finder, loader

    @classmethod
    def mount(class_, root):
        """init finder,loader, only once;
        root is catalogue of portable root"""
        # XXX class_ - in successors own _ready (?)
        if class_._ready:
            return
        else:
            p = VRoot(root).hpath(SymModule.DIR)
            SymModule.DIR = VRoot(p)
            class_._ready = True

    @staticmethod
    def import_pymodule(symbol):
        """Import PYMODULE for SCADA-symbol with name symbol,
        returns module
        """
        if not SymModule._ready:
            raise ValueError(u"not mounted")

        p = SymModule.DIR.hpath(symbol)
        p = path.join(p, SymModule.PYMODULE)
        p = p.encode(sys.getfilesystemencoding())
        # In load_source(name, path): name is name of module (without extension),
        # path is full path to the file of module
        return imp.load_source(path.splitext(SymModule.PYMODULE)[0], p)

    @staticmethod
    def create(name):
        """Creates all files and folders for new symbol
        """
        if not SymModule._ready:
            raise ValueError("not mounted")

        symdir = SymModule.DIR.hpath(name)

        if path.exists(symdir):
            raise Exception("Already exists")

        # create this symbol directory
        os.makedirs(symdir)

        with codecs.open(path.join(symdir, SymModule.DESCR), "w", "utf8") as f:
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            user = os.getenv("USER", os.getenv("USERNAME", "Unknown"))
            f.write(SymModule.DESCRTEMPLATE % locals())

        with codecs.open(path.join(symdir, SymModule.PYMODULE), "w", "utf8") as f:
            f.write(SymModule.PYMODULETEMPLATE)

    @staticmethod
    def clone(name1, name2):
        """Clone symbol with name1 to name2. Doesn't chech that name1 is
        consistent symbol directory
        """
        if not SymModule._ready:
            raise ValueError("not mounted")

        symdir1 = SymModule.DIR.hpath(name1)
        symdir2 = SymModule.DIR.hpath(name2)

        if not path.exists(symdir1):
            raise Exception("Source symbol does not exist")
        if path.exists(symdir2):
            raise Exception("Destination symbol already exists")

        # copy unmodified files
        shutil.copytree(symdir1, symdir2)
        # modify descr-file
        descr2 = path.join(symdir2, SymModule.DESCR)
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
    def issymdir(p):
        """test if p (absolute, normalized) is directory of symbol
        """
        if not SymModule._ready:
            raise ValueError("not mounted")

        descrpath = path.join(p, SymModule.DESCR)
        pymodpath = path.join(p, SymModule.PYMODULE)

        if path.exists(descrpath) and path.exists(pymodpath):
            return True
        else:
            return False

    @staticmethod
    def files(name):
        """Returns {vlayers:[0st,1st...], gif:path, tiff:path, descr:path,
        py:path, dsl:path, oth:[0st,1st...], dir:path}
        If some not exists, value will be None. If symbol directory not exists,
        returns None
        """
        if not SymModule._ready:
            raise ValueError("not mounted")

        symdir = SymModule.DIR.hpath(name)
        if not path.exists(symdir):
            return None

        ret = {k:None for k in ("vlayers", "gif", "tiff", "descr", "py", "dsl", "dir")}
        ret["dir"] = symdir
        ret["vlayers"] = []
        ret["oth"] = []
        for fname in os.listdir(symdir):
            if fname == SymModule.DESCR:
                ret["descr"] = path.join(symdir, fname)
            elif fname == SymModule.PYMODULE:
                ret["py"] = path.join(symdir, fname)
            else:
                ext = path.splitext(fname)[1].lower()
                if ext in (".gif", ".tiff"):
                    ret[ext[1:]] = path.join(symdir, fname)
                else:
                    # seems to be vector layer (GFig file)
                    m = cre_vlayername.match(fname)
                    if m:
                        laynum = int(m.group(1))
                        ret["vlayers"].append((laynum,path.join(symdir, fname)))
                    else:
                        ret["oth"].append(path.join(symdir, fname))
        # sorting now vlayers
        svl = sorted(ret["vlayers"], key=lambda e:e[0])
        ret["vlayers"] = collections.OrderedDict(svl).values()
        return ret

# }}}


# Hacked version of loading frames {{{
#def _load_image_frame(filename, framenum):
#    """Load frame from GIF89/TIFF/FLI file, returns
#    as Image"""
#    # FIXME very dirty hack: iter until get None instead of frame. Frame
#    # is loaded by _load_image_frame() - here is the hack! Instead of using
#    # one Image and seeking in, I use different Images, opened for each
#    # frame, bcz in the first case I get strange picture (combined all layers?)
#    im = Image.open(filename)
#    try:
#        for i in xrange(framenum):
#            im.seek(1)
#        return im
#    except:
#        return None
#
#def _load_image_frames(filename):
#    i = 0
#    while True:
#        f = _load_image_frame(filename, i)
#        if f:
#            yield f
#            i += 1
#        else:
#            # no more frames!
#            break
# }}}

def _is_empty_image(image):
    """Test that image is empty
    """
    stat = ImageStat.Stat(image)
    return all(s==0.0 for s in stat.var)

def _load_image_frames(filename):
    """Iterator over frames of image, each item is Image. Keep
    somewhere yielded refs! If image is empty (all frames are
    transparent), then yield only frame with attrs '_noimage',
    'size'
    """
    im = Image.open(filename)
    size = im.size
    plt = copy.copy(im.palette) # was deepcopy but seems to works
    try:
        noimage = True
        i = 0
        while True:
            if not _is_empty_image(im):
                imc = im.convert("P")
                imc.putpalette(plt)
                yield imc
                noimage = False
            i += 1
            im.seek(i)
    except (ValueError, EOFError, IndexError):
        # actually is ValueError, but should be EOFError (like in PIL documentation)
        pass
    if noimage:
        # if no any not empty frames, then yield dummy frame
        class EmptyFrame: pass
        f = EmptyFrame()
        f._noimage = True
        f.size = size
        yield f

# Layers classes {{{

class Layer:
    def __init__(self, sym, num):
        """sym - BaseSymbol object, num - number of layer.
        Numbers of raster and vector layers are independend and not crossed!
        """
        self.sym = sym
        self.num = num
        self.visible = False

#    def __del__(self):
#        try:
#            self.delete()
#        except:
#            pass

    def delete(self):
        """Delete layer from canvas (unrender). Override but call base at last!
        """
        self.visible = False

    def render(self):
        """Render itself. Override but call base at last!
        """
        self.visible = True

    def tags(self):
        """Returns list of canvas tags of all layer objects
        """
        raise NotImplementedError

#    def call(self, cmd, *a, **kw):
#        """Call some method of wrapped object (GFigRender or Image)
#        """
#        raise NotImplementedError

class Rlayer(Layer):
    """Raster layer
    """
    def __init__(self, sym, num, image, photoimage):
        """image is Image object, photoimage is the ImageTk.PhotoImage
        """
        Layer.__init__(self, sym, num)
        self.im = image
        self.ph = photoimage
        self.tag = None

    def delete(self, really=True):
        """If really is not True, image resources will
        not be deleted"""
        if self.visible:
            self.sym.c.delete(self.tag)
            self.tag = None
            if really:
                self.ph = None
                self.im = None
            Layer.delete(self)

    def render(self):
        self.delete()
        self.tag = self.sym.c.create_image(self.sym.x, self.sym.y, image=self.ph)
        Layer.render(self)

    def tags(self):
        return [self.tag,]

    def __str__(self):
        """Returns rNUM"""
        return "r%d"%self.num

class Vlayer(Layer):
    """Vector layer
    """
    def __init__(self, sym, num, gfr, filename):
        """gfr is GFigRender object, filename is the full path to gfig-file
        """
        Layer.__init__(self, sym, num)
        self.gfr = gfr
        self.filename = filename

    def delete(self, really=True):
        if self.visible:
            self.gfr.delete()
            if really:
                self.gfr = None
            Layer.delete(self)

    def render(self):
        self.delete()
        self.gfr.render(self.filename)
        # All gfig coords are on Gfig (Gimp) canvas, without any offsets.
        # So, to place to new location, move it on x, y and centering
        # them (width/2, height/2) -- not sure but works ;))
        self.gfr.move(self.sym.x - self.sym.width/2, self.sym.y - self.sym.height/2)
        Layer.render(self)

    def tags(self):
        return [sh.grptag for sh in self.gfr.canvas_shapes]

    def __str__(self):
        """Returns vNUM"""
        return "v%d"%self.num

# }}}

# BaseSymbol {{{

# XXX all layers has number. GFig (vector layers) - too and it is NOT the same as
# XXX digits in regardind file name but order is the same

class BaseSymbol(SymModule):
    """Base class of symbol.
    If you need any tk-async method use @tksafe from pybase.hmi.utils
    """
    _GFIG_ENCODING = "utf8"
    format = u"symbol,1"

    def __init__(self, name, canvas, x, y):
        self.fs = self.files(name)
        if not self.fs:
            raise Exception(u"Inconsistent symbol (or mismatched location)")
        self.name = name
        self.c = canvas
        self._vlayers = []
        self._rlayers = []
        self._vilayers = [] # all visible only layers
        self.x = x
        self.y = y
        self.width = self.height = 0
        self._pmenu = None # popup menu
        self.k = {} # keywords, for ex. "sid" (Signal IDeintifier)

        # Try to load keywords from descr. Keywords are options in
        # 'descr' file like:
        #   k.something = some_value
        try:
            dc = DotCfg()
            with codecs.open(self.fs["descr"], "r", encoding="utf8") as f:
                dc.parse(f)
                for p in dc.paths:
                    if len(p) == 2 and p[0] == u"k":
                        self.k[p[1]] = dc.get(DOT.join(p)).value
        except:
            pass

        # create Vlayers
        for i,p in enumerate(self.fs["vlayers"]):
            g = GFigRender(self.c, BaseSymbol._GFIG_ENCODING)
            self._vlayers.append(Vlayer(self, i, g, p))

        # create Rlayer
        imfilename = self.fs["gif"] or self.fs["tiff"]
        if not imfilename:
            raise ValueError(u"No symbol image found")
        for i,f in enumerate(_load_image_frames(imfilename)):
            if not getattr(f, "_noimage", False):
                ph = ImageTk.PhotoImage(f)
                self._rlayers.append(Rlayer(self, i, f, ph))

        # size of symbol will be size of last frame (all are equals)
        self.width = f.size[0]
        self.height = f.size[1]

#    def __del__(self):
#        try:
#            self.delete()
#        except:
#            pass

    def delete(self):
        """Delete all
        """
        for l in self._vlayers+self._rlayers:
            try:
                l.delete()
            except:
                pass
        self._vlayers = []
        self._rlayers = []
        self._vilayers = []
        # destroy popup menu
        self.delete_popup_menu()

    def props(self):
        """Dictionary of properties
        """
        nshapes = 0
        for vl in self._vlayers:
            nshapes += len(vl.gfr.canvas_shapes)
        ret = {
                "dir": self.fs["dir"],
                "name": self.name,
                "vlayers": len(self._vlayers),
                "rlayers": len(self._rlayers),
                "vilayers": "%d ('%s')"%(len(self._vilayers), self.rendered),
                "shapes": nshapes,
                "size": (self.width, self.height),
                "pos": (self.x, self.y),
                "k": str(self.k),
        }
        return ret

    def ifind_layers(self, *layers):
        """Returns iterator of layers, selected by selectors.
        Selector is 'r<int>'|'v<int>'|'r*'|'v*'|'all' to
        selector some vector-, raster- layer or all of them.
        Caller must check Exceptions, bcz they may occurs in
        call (if selectors are incorrect) - IndexError,
        KeyError are possible!
        """
        # Algorithm: recognize selector and append iterator on such items
        # and remove this selector from layers. Each 'if' section tests
        # own selector. Selector is "r*"|"v*"|"all"|"rN"|"vN"

        layers = [l.lower() for l in layers]
        selected = [] # list of iterators of all rendered layers

        if "all" in layers:
            # iterator of 'all' selector. no any layers to select
            selected.append(itertools.chain(self._rlayers, self._vlayers))
            layers = []

        if "r*" in layers:
            # iterator of 'r*' selector
            selected.append(self._rlayers)
            layers = [l for l in layers if not l.startswith('r')]

        if "v*" in layers:
            # iterator of 'v*' selector
            selected.append(self._vlayers)
            layers = [l for l in layers if not l.startswith('v')]

        # last selector testing, so doesn't modify layers list
        if layers:
            # render only specified layers in format 'r<NUM>'|'v<NUM>'
            ld = {"v":self._vlayers, "r":self._rlayers}
            selected.append(ld[l[0]][int(l[1:])] for l in layers) # KeyError, IndexError

        return itertools.chain(*selected)

    def find_layers(self, *layers):
        """Like ifind_layers() but returns list
        """
        return list(self.ifind_layers(*layers))

    def ifind_at(self, x, y):
        """Find all objects at canvas coords x,y in Z-order. Yields
        {'type':'r'|'v', 'num':layer number, 'shape':if is vector shape}
        """
        for l in self._vilayers:
            if isinstance(l, Rlayer):
                bb = self.c.bbox(l.tag)
                if bb:
                    bx0,by0,bx1,by1 = bb
                    if bx0 <= x <= bx1 and by0 <= y <= by1:
                        yield dict(type='r', num=l.num, shape=None)
            else:
                for sh in l.gfr.ifind_shapes_at(x, y):
                    yield dict(type='v', num=l.num, shape=sh)

    def find_at(self, x, y, zorder="all"):
        """Similar to ifind_at but returns list. Defaultly returns all items,
        but if zorder is 'bottom', returns bottom item, when is 'top', return
        top item
        """
        res = list(self.ifind_at(x, y))
        if not res:
            return []

        if zorder == "top":
            return res[-1]
        elif zorder == "bottom":
            return res[0]
        else:
            return res

    def layer(self, *names):
        """Like find but on one name return single item, on more - list
        of layers
        """
        if len(names) == 1:
            return self.find_layers(*names)[0]
        elif len(names) > 1:
            return self.find_layers(*names)
        else:
            raise ValueError(u"'layer' expects one or more layer names")

    def delete_visible(self):
        """Delete from canvas all created items - clear canvas (clear all
        visible layers)
        """
        for l in self._vilayers:
            try:
                l.delete(really=False)
            except:
                pass
        self._vilayers = []

    @property
    def rendered(self):
        """Returns something like 'r0v1v2'
        """
        return "".join(str(l) for l in self._vilayers)

    def isrendered(self, layer):
        """Returns True or False if layer ('rN'|'vN') was rendered
        """
        for l in self._vilayers:
            if str(l) == layer:
                return True
        return False

    def render(self, layers=None):
        """Render selected layers (use find_layers()), all layers otherwise
        """
        if layers is None:
            layers = self.ifind_layers("all")

        # if rendering layers that already are rendered, nothing to do
        # XXX '-' needs sorting (and additional lists)
        # XXX '+' avoids canvas items recreation
        sorted_layers = sorted(layers)
        sorted_vilayers = sorted(self._vilayers)
        if sorted_layers == sorted_vilayers:
            # not rendering needed
            return

        self.delete_visible()
        for l in layers:
            l.render()
            self._vilayers.append(l)
            for tag in l.tags():
                self.c.addtag_withtag(self.name, tag)

    def resize(self, event=None):
        """On canvas resizing must be called"""
        for l in self.find_layers("v*"): 
            l.gfr.resize(event)

    def bbox(self):
        """Bound box (x0,y0,x1,y1) of all symbol (all are canvas coords)
        """
        bx0 = by0 = sys.maxint
        bx1 = by1 = 0
        for l in self._rlayers:
            if l.tag is None:
                # invisible layer
                continue
            x0,y0,x1,y1 = self.c.bbox(l.tag)
            bx0 = min(bx0, x0)
            by0 = min(by0, y0)
            bx1 = max(bx1, x1)
            by1 = max(by1, y1)
        for l in self._vlayers:
            for sh in l.gfr.canvas_shapes:
                if sh.tag is None:
                    # invisible shape (not sure about vector shapes)
                    continue
                x0,y0,x1,y1 = self.c.bbox(sh.tag)
                bx0 = min(bx0, x0)
                by0 = min(by0, y0)
                bx1 = max(bx1, x1)
                by1 = max(by1, y1)
        return (bx0,by0,bx1,by1)

    def symcoords(self, canx, cany):
        """Convert from canvas coords to symbol coords
        """
        # x,y now are coords. inside the symbol, again with normal
        # axes orientation (like in mathematics)
        #bb = self.bbox()
        #x0 = bb[0]
        #y1 = bb[3]
        x0 = self.x - self.width/2
        y1 = self.y + self.height/2
        x = canx - x0
        y = y1 - cany
        return (x, y)

    def cancoords(self, symx, symy):
        """Convert from symbol coords to canvas coords
        """
        #bb = self.bbox()
        #x0 = bb[0]
        #y1 = bb[3]
        x0 = self.x - self.width/2
        y1 = self.y + self.height/2
        x = x0 + symx
        y = y1 - symy
        return (x, y)

    def extend_button_event(self, srcevent, push):
        """Extend <Button> event from original Tk srcevent.
        push must be 'up'|'down'|'double'. srcevent will be modified after calling!
        """
        srcevent.targets_sym = self.find_at(srcevent.x, srcevent.y)
        srcevent.push = push
        x, y = self.symcoords(srcevent.x, srcevent.y)
        srcevent.x_sym = x
        srcevent.y_sym = y
        return srcevent

    def delete_popup_menu(self):
        """Destroy popup menu"""
        if self._pmenu:
            self._pmenu.destroy()
        self._pmenu = None

    def popup_menu(self, descr, callbacks=None):
        """descr is string block like
        File
            Open = meth1
            Close = meth2
        --
        Info = meth3

        callbacks is the dictionary with 'meth1', 'meth2' keys or object with
        with such methods (named meth1, meth2) - for example above. Default
        value will be self.

        Created menu is available as _pmenu attribute, also is possible to
        show it with base implementation of onbutton()
        """
        if not callbacks:
            callbacks = self

        def _menu_blocks():
            """Generate stack commands for menu creation:
            '{'|'}'|'--'|'cascade-menu-title'|'menu-item func-name'
            """
            prevlev = None
            for lev,line in utils.indentlines(descr.splitlines()):
                if prevlev is None:
                    yield '{'
                    prevlev = 0
                if lev > prevlev:
                    yield '{'
                elif lev < prevlev:
                    for i in xrange(prevlev-lev):
                        yield '}'
                yield line.strip()
                prevlev = lev
            if prevlev is not None:
                # if there are some items, so last stack-commands are
                # stack leaving
                for i in xrange(prevlev+1):
                    yield '}'

        try:
            # simple stack-based menu creation interpretator
            menus = []
            for mb in _menu_blocks():
                if mb == '{':
                    m = Menu(self.c, tearoff=0)
                    menus.append(m)
                elif mb == '}':
                    if len(menus) == 1:
                        # final '}' of root menu
                        break
                    # some cascade ending
                    casc = menus.pop()
                    l = menus.pop()
                    par = menus[-1]
                    par.add_cascade(label=l, menu=casc)
                elif mb == "--":
                    menus[-1].add_separator()
                elif mb:
                    mbarr = [x.strip() for x in mb.split('=')]
                    if len(mbarr) < 2:
                        # title for cascade, push to stack only title
                        menus.append(mb)
                    else:
                        # title and function name
                        t,f = mbarr
                        if isinstance(callbacks, dict):
                            func = callbacks.get(f)
                        else:
                            func = getattr(callbacks, f, None)
                        if not func:
                            raise Exception
                        wfunc = lambda: func(self) # XXX is this collectable by gc?
                        menus[-1].add_command(label=t, command=wfunc)
            if menus:
                self.delete_popup_menu()
                self._pmenu = menus[0]
            return self._pmenu
        except:
            raise ValueError("Incorrect menu definition")

    def ondata(self, *a, **kw):
        """Occurs on data receiving
        """

    def simulpkt(self):
        """Returns input packet in simulation (symbol testing) mode.
        Can be overriden
        """
        return sim.SimulPkt(value=random.randint(-100, 100), dtime=time.localtime())

    def onbutton(self, event):
        """Occurs when user press/release some mouse button on the symbol.
        event has fields: push ('up'|'down'|'double'), x_sym, y_sym, targets_sym
        and standard fields like x, y, x_root, y_root, type, state, num (number of
        pressed button!)...
        targets_sym is the list of symbol items where event occurs. This list
        is the same as BaseSymbol.find_at() returns.
        Default action is popup menu showing (if exists) on button-3
        """
        if self._pmenu and event.push=="down" and event.num==3:
            self._pmenu.post(event.x_root, event.y_root)
# }}}


# main

if __name__ == "__main__":
    from pybase.tk import utils as tkutils

    if len(sys.argv) < 3:
        print "arg: symbol-name root-dir"
        print "Also symbol should contain 2-layers GIF file and two vector gfig files"
        sys.exit(0)

    root = Tk()
    c = Canvas(root, bd=0)
    c.pack(fill=BOTH, expand=YES)
    tkutils.maximize_toplevel(c)
    try:
        arg2 = unicode(sys.argv[2], sys.getfilesystemencoding())
        arg1 = unicode(sys.argv[1], sys.getfilesystemencoding())
        SymModule.mount(arg2)
        bs = BaseSymbol(arg1, c, 500, 300)

        def dummy(*a): print 1
        m = bs.popup_menu("""
            File
                Open = dummy
                Close = dummy
                File Utils...
                    Create Item = dummy
            --
            Info about system = dummy""", globals()
                )
        m.post(100, 100)

        bs.render(bs.ifind_layers("v*", "r*")) # works
        #print list(bs.find_layers("r*", "r0", "r1", "all")) # works
        #bs.render_layers("v1", "r0", "r1", "v0") # works
        #bs.render_layers("all") # works
        tkutils.create_canvas_cross(c, 500, 300, width=2)
        c.mainloop()
    except Exception, x:
        raise
        print unicode(x)
