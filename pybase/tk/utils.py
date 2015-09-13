# -*- coding: cp1251 -*-

import os
import re
import math
#import sys
from Tkinter import *
import tkMessageBox
import tkFont
from async import TkAsync
import Tix
from pybase import utils

# Common funcs {{{

def tkpanic(msg, exc=None, rc=1):
    text = u"ERROR: %s"%msg
    if exc:
        text += u"\nDetails: "
        text += (unicode(exc) or exc.__class__.__name__)
    tkMessageBox.showerror("Failure", text)
    sys.exit(rc)

_noimg = "R0lGODlhHgAeAMIGAAAAAP8AAFVVVYCAgL+/v8DAwP///////yH+EUNyZWF0ZWQgd2l0aCBHSU1QACH5BAEKAAcALAAAAAAeAB4AAAONWLrc/kvISau1RAnIeS5bJzJfOI7leaaqyLae5gx0bdvOuwxG7/+GAiAna/CAQCERNEMmhw2d4ujsKaNFBjUQ6HGtUFJ29+N+wUsTudz1XcVMI/scDC+khW37/L6Pp1Vudgp4VFV9hH95gWhYcVqMdWkzI4MFeACZmpubkzAxj5+eoqOkcGqmiaGplwUJADs="

def open_photo_image(file):
    """Try to load PhotoImage, if not exists, returns _noimg"""
    try:
        return PhotoImage(file=file)
    except:
        return PhotoImage(data=_noimg)

def set_stretchable_grid(widget, ncols, nrows):
    """Grid expansable to size of container widget"""
    top = widget.winfo_toplevel()
    for c in xrange(ncols):
        top.columnconfigure(c, weight=1)
        widget.columnconfigure(c, weight=1)
    for r in xrange(nrows):
        top.rowconfigure(r, weight=1)
        widget.rowconfigure(r, weight=1)

def maximize_toplevel(widget):
    """Maximize window"""
    toplevel = widget.winfo_toplevel()
    root = toplevel._root()
    try:
        # On MS Windows one can set the "zoomed" state.
        toplevel.wm_state('zoomed')
    except:
        w = root.winfo_screenwidth()
        h = root.winfo_screenheight() - 60
        geom_string = "%dx%d+0+0" % (w,h)
        toplevel.wm_geometry(geom_string)

# RE for geometry string parsing
_geosre = re.compile(r"[x+]")
def get_geometry(widget):
    """Widget geometry as list of ints (w, h, x, y)"""
    # string like "450x320+100+0", first 2 numbers are size
    return [int(x) for x in _geosre.split(widget.winfo_geometry())]

def set_relsize(w, relw, relwidth=1., relheight=1.):
    """Set relative size of widget w (relative to relw widget)
    relw may be widget or 'screen'. Automatic center on container
    """
    if relw=="screen":
        contw = w.winfo_screenwidth()
        conth = w.winfo_screenheight()
    else:
        contw = relw.winfo_reqwidth()
        conth = relw.winfo_reqheight()

    width = int(contw * relwidth)
    height = int(conth * relheight)
    x = (contw - width)/2
    y = (conth - height)/2
    w.geometry("%dx%d+%d+%d"%(width, height, x, y))

def center_toplevel(w):
    """Center toplevel on screen"""
    scrw = w.winfo_screenwidth()
    scrh = w.winfo_screenheight()
    ww = w.winfo_reqwidth()
    wh = w.winfo_reqheight()
    x = (scrw - ww)/2
    y = (scrh - wh)/2
    w.geometry("%dx%d+%d+%d"%(ww, wh, x,y))

def create_canvas_cross(canvas, x, y, length=5, **kw):
    t1 = canvas.create_line(x, y-length, x, y+length+1, **kw)
    t2 = canvas.create_line(x-length, y, x+length+1, y, **kw)
    return (t1,t2)

def anchor_coords(x0, y0, x1, y1, anchor=CENTER):
    """Returns coords (x,y) of anchor (N|NW|CENTER...) bounded
    by box with x0,y0 and x1,y1
    """
    cx = x0 + (x1 - x0)/2 # horizontal center
    cy = y0 + (y1 - y0)/2 # vertical center
    coords = {
            NW: (x0, y0),
            N: (cx, y0),
            NE: (x1, y0),
            W: (x0, cy),
            CENTER: (cx, cy),
            E: (x1, cy),
            SW: (x0, y1),
            S: (cx, y1),
            SE: (x1, y1),
    }
    return coords.get(anchor, coords[CENTER])

try:
    import Image, ImageDraw
    def transparent_image(width, height, dark="#666666",
            light="#999999", outline1="yellow", outline2="black", square=10):
        """Create image for transparent background, like in Gimp, with size
        width,height, color of dark square and light square, outline segments
        colors outline1 and outline2. Each square has side square pixels
        """
        im = Image.new("RGB", (width, height), "yellow")
        dr = ImageDraw.Draw(im)
        square = min(square, width, height)
        xcount = int(math.ceil(width/square))
        ycount = int(math.ceil(height/square))
        wpie = width%square
        hpie = height%square
        colors = (dark, light)
        for i in xrange(xcount+1):
            if i == xcount:
                w = wpie
            else:
                w = square
            for j in xrange(ycount+1):
                if j == ycount:
                    h = hpie
                else:
                    h = square
                if not w or not h:
                    # when wpine or hpie is 0
                    continue
                x = i*square
                y = j*square
                ci = ((i%2) + (j%2))%2 # index of bg color
                # drawing square
                dr.rectangle((x,y,x+w,y+h), fill=colors[ci])

        # drawing border
        bdsegment = max(2, square/2)
        xcount = int(math.ceil(width/bdsegment))
        ycount = int(math.ceil(height/bdsegment))
        wpie = width%bdsegment
        hpie = height%bdsegment
        colors = (outline1, outline2)
        for i in xrange(xcount+1):
            if i == xcount:
                l = wpie
            else:
                l = bdsegment
            if not l:
                continue
            x = i*bdsegment
            ci = i%2
            dr.line((x,0,x+l,0), fill=colors[ci])
            dr.line((x,height-1,x+l,height-1), fill=colors[ci])
        for i in xrange(ycount+1):
            if i == ycount:
                l = hpie
            else:
                l = bdsegment
            if not l:
                continue
            y = i*bdsegment
            ci = i%2
            dr.line((0,y,0,y+l), fill=colors[ci])
            dr.line((width-1,y,width-1,y+l), fill=colors[ci])
        return im
except:
    def transparent_image(*ignored_a, **ignored_kw):
        return None

# }}}

# Toolbar {{{

class Toolbar(Frame):
    def __init__(self, master, *a, **kw):
        Frame.__init__(self, master, *a, **kw)
        self.config(relief=RAISED, bd=1)
        self.vars = {}

    def var(self, varname):
        return self.vars[varname].get()

    def add_button(self, text="Submit", image=None, command=None, pack={}, *a, **kw):
        """Add button with image or text, command, packing arguments (pack(...))
        and *a, **kw for Button constructor
        """
        if image:
            # FIXME: почему-то приходится два раза устанавливать image (чтобы ссылку сохранить?)
            img = PhotoImage(file=image)
            b = Button(self, image=img, command=command, *a, **kw)
            b.image = img
        else:
            b = Button(self, text=text, command=command, *a, **kw)
        b.pack(**utils.dictdefaults(pack, side=LEFT, padx=2, pady=2))

    def add_check(self, text, var, command=None, pack={}, state=False, *a, **kw):
        """var - name (string) of Tk variable"""
        self.vars[var] = BooleanVar()
        self.vars[var].set(state)
        c = Checkbutton(self, text=text, variable=self.vars[var], command=command, *a, **kw)
        c.pack(**utils.dictdefaults(pack, side=LEFT, padx=2, pady=2))

    def add_space(self, pack={}, *a, **kw):
        """Insert spacing"""
        d = Label(self, *a, **kw)
        d.pack(**utils.dictdefaults(pack, side=LEFT, padx=6, pady=2))

    def add_widget(self, w, pack={}):
        """Insert instantiated widget"""
        w.pack(**utils.dictdefaults(pack, side=LEFT, padx=6, pady=2))

# FIXME: работает, но требует знания высоты картинки в момент вставки, а это ДО паковки,
# а до нее высота = 0
    IMGDATA = """#define sep_width 2
    #define sep_height %(height)s
    static unsigned char sep_bits[] = {
        %(bits)s
    };
    """
    def add_separator(self, height=None, pack={}, *a, **kw):
        if not height:
            height = self["height"] if self["height"]>1 else 16
        bits = ("0x01,"*height)[:-1]
        imgdata = Toolbar.IMGDATA % locals()
        b = BitmapImage(data=imgdata, foreground="#555555", background="#BFBFBF")
        l = Label(self, image=b, *a, **kw)
        l.image = b
        l.pack(**utils.dictdefaults(pack, side=LEFT, padx=3, pady=2))

    def pack(self, **kw):
        """панель размещает сама себя"""
        Frame.pack(self, **utils.dictdefaults(kw, side=TOP, expand=NO, anchor=N, fill=X))
        
# }}}

# ScrolledWidget {{{

class ScrolledWidget(Frame):
    """
    sw = ScrolledWidget(self, Text)
    sw.w.config(...)
    """
    w = None
    def __init__(self, master, wclass, *a, **kw):
        Frame.__init__(self, master)
        self.config(relief=RAISED, bd=1)
        self.w = wclass(self)
        self.vscroller = Scrollbar(self, orient=VERTICAL, command=self.w.yview)
        self.hscroller = Scrollbar(self, orient=HORIZONTAL, command=self.w.xview)
        self.w["yscrollcommand"] = self.vscroller.set
        self.w["xscrollcommand"] = self.hscroller.set
        self.w.grid(row=1, column=0, sticky="swen")
        # so w will get focus when click on it
        self.w.bind("<Button-1>", lambda e: e.widget.focus())
        self.hscroller.grid(row=2, column=0, sticky="swen")
        self.vscroller.grid(row=1, column=1, sticky="swen")
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

    def __getattr__(self, attr):
        # all unknown attrs will be assume in w
        if hasattr(self.w, attr):
            return getattr(self.w, attr)
        else:
            raise AttributeError

# }}}

# FontSpec {{{

# TODO: есть ощущения что не вполне работоспособен. В частности шрифт может называться
# двумя словами (и более) - нужно это как-то обрабатывать (напр., _ либо \)
class FontSpec:
    """Расширенные атрибуты шрифта по строке спецификации
    типа 'Arial 10 bold #red'
    """

    tkf = None # Tk Font
    spec = "" # исходная строковая спецификация
    tkspec = "" # то же но пригодная для Tk (без доп. опций)
    family = None
    size = 0
    color = "black"
    weight = "normal" # толщина (bold)
    slant = "roman" # наклонная (когда italic)
    underline = 0 # подчеркнута
    overstrike = 0 # перечеркнута
    linespace = 0 # вся высота строки шрифта
    descent = 0 # высота подстрочного "хвоста"
    ascent = 0 # высота надстрочных "ушей"

    def __init__(self, spec=None):
        """spec: семейство только с заглавной буквы, цвет с # (#red, ##FF00FF),
        размер - int, прочее - стили"""
        try:
            if not spec:
                return

            spec = spec.split()

            family = [s for s in spec if s.istitle()]
            if family:
                self.family = family[0]
                spec.remove(self.family)

            color = [s for s in spec if s.startswith('#')]
            if color:
                self.color = color[0]
                spec.remove(self.color)
                self.color = self.color[1:]

            size = [s for s in spec if s.isdigit()]
            if size:
                self.size = size[0]
                spec.remove(self.size)
                self.size = int(self.size)

            if "bold" in spec:
                self.weight = "bold"

            if "italic" in spec:
                self.slant = "italic"

            if "underline" in spec:
                self.underline = 1

            if "overstrike" in spec:
                self.overstrike = 1

            # создаем tkFont для замеров метрик
            self.tkf = tkFont.Font(family=self.family, size=self.size, weight=self.weight,
                    slant=self.slant, underline=self.underline, overstrike=self.overstrike)

            self.ascent = self.tkf.metrics("ascent")

            self.descent = self.tkf.metrics("descent")

            self.linespace = self.tkf.metrics("linespace")

            # tkspec - строковая спецификация в стандарте Tk
            self.tkspec = []
            if self.family:
                self.tkspec.append(self.family)
            if self.size:
                self.tkspec.append(str(self.size))
            if self.weight == "bold":
                self.tkspec.append("bold")
            if self.slant == "italic":
                self.tkspec.append("italic")
            if self.underline:
                self.tkspec.append("underline")
            if self.overstrike:
                self.tkspec.append("overstrike")
            self.tkspec = " ".join(self.tkspec)

        except:
            raise ValueError("invalid font specification")

    def __str__(self):
        return self.tkspec
# }}}

# Tk wrapers - custom Tk {{{

class _EngineWrap:
    """wrapper around Tk|Tix.Tk"""
    def __init(self, engine, styles, appicon, aperiod, title, onerror, *a, **kw):
        """aperiod - period of async. command executions"""
        engine.title(title)
        self.engine = engine
        try:
            if styles:
                self.engine.option_readfile(styles)
        except: pass
        try:
            if appicon:
                self.engine.iconbitmap(default=appicon)
        except: pass
        onerror = onerror or self.__report_callback_exception
        #self.engine.tk.createcommand("tkerror", self.tkerror)
        #self.engine.tk.createcommand("bgerror", self.tkerror)
        self.engine.report_callback_exception = onerror
        self.tkasync = TkAsync(self, aperiod)

    @staticmethod
    def wrap(engine_class, styles=None, appicon=None, aperiod=20, title="No title", onerror=None, *a, **kw):
        """create engine instance with (*a, **kw) then bind it with self;
        returns own instance"""
        engine = engine_class(*a, **kw)
        we = _EngineWrap()
        we.__init(engine, styles, appicon, aperiod, title, onerror, *a, **kw)
        return we

    def __getattr__(self, atr):
        return getattr(self.engine, atr)

    def destroy(self):
        self.tkasync.clear()
        self.engine.destroy()

    def __report_callback_exception(self, exc, val, tb):
        """Report about errors, must be set as self.engine.report_callback_exception"""
        try:
            type_ = exc.__name__
            text = u"%s: %s"%(type_, getattr(val, "message", None) or unicode(val) or "Unknown error")
            tkMessageBox.showerror("Error", text)
        except Exception, x:
            print "Error in error handler: %s"%str(x)

    # почему-то не вызывается
    #def tkerror(self, *a):
        #print a
        #msg = a[0]
        #self._showerror(msg)

def TkWrap(*a, **kw):
    return _EngineWrap.wrap(Tk, *a, **kw)

def TixWrap(*a, **kw):
    return _EngineWrap.wrap(Tix.Tk, *a, **kw)

# }}}
