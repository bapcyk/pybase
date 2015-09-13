# GFig GIMP 2.6 files rendering in Tkinter (on canvas). Supports:
#   - lines
#   - circles
#   - ellipses
#   - rectangles
#   - polygons
#   - arcs
#   - old style spirals (via lines)
#   .. and it's outline-, fill- colors, line width; also polygon has
# style ruby (recreate canvas object when changed - interesting effect
# with smooth=1, ruby=True).
# Not supported: Bezier, spiral, stars.
# All unknown objects are ignored.

# Transforming of objects is supported: move, scale, rotate. It's possible
# to transform only one object or any selected objects of gfig-file. First,
# shape class methods are used, for second, GFigRender methods are used.
# GFigRender transformation methods has arg shapes - shapes to be transformed.
# Also, you can select GFigRender shapes by find_shapes() method and process
# it (transform, configure, for ex.). Finding use classname of shape ("CanvasArc",
# "CanvasEllipse", etc) or any option (Tk cget, gfig option) in **kw form, or
# name of shape. Usually shapes don't have names (gfig-extension feature), but
# user can name each shape in order from left-to-right and top-to-bottom (canvas
# location) with method name_shapes().
# find_shapes() returns list, ifind_shapes() - iterator.

# Each shape can have label - text short string. Technically, label is created on
# first labelconfigure(), each other only changes label options. Label is placed
# by options: side (N|NW|CENTER...) and standard Tk anchor option; so side specified
# corner (about shape bbox) or center of bbox

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

# Some of this code was taken from the Whirl plug-in
# which was copyrighted by Federico Mena Quintero (as below).

# Contribs: thanks for creators of Gimp GFig:
#   - Andy Thomas
#   - Spencer Kimball
#   - Peter Mattis
# Author: P. Yosifov, 2010

import itertools
from pybase.gfig import *
from pybase.tk import utils as tkutils
from pybase.utils import namedlist, minmax, dictdefaults
from Tkinter import *
import math
import sys
import os
import re

iround = lambda x, *a: int(round(x, *a))

# TODO not one tag but list of tags in self.tag = __create__ - for complex figures
# but may be it's bad idea?

# XXX Instead of return dict in __create__ is possible to create LazyCanvas and
# translate some methods calling (lazy) to dict

# BaseCanvasShape {{{

class BaseCanvasShape:
    """Tk Canvas shape representation (importing).

    Each shape has styles: use configure()/cget()
    as usual in Tkinter. Styles like 'gfig_*' are
    from gfig-file
    """
    def __init__(self, shape, grptag, canvas):
        self.s = shape # shape from pybase.gfig
        self.grptag = grptag
        self.tag = None
        self.labeltag = None # tag of label
        self.c = canvas
        # styles from gfig file, available via configure() with 'gfig_' prefix
        self.gfig_styles = self.__gfig_styles__(shape)
        # when user set custom styles saved here between recreation/transforming
        self.user_styles = {} # kept for full recreation (now really is only reconfig, not recreate)
        # a special (not Tk) styles of label
        self.label_styles = {"side": N, "padx":0, "pady":0}

    _cre_width = re.compile(u"\((\d+)\)")
    def __gfig_styles__(self, shape):
        """Import of gfig-styles, returns dict
        """
        # defaults styles
        w = 1
        fg = ""
        bg = ""

        try:
            m = BaseCanvasShape._cre_width.search(shape.styles.get(u"brushname", ""))
            if m:
                w = int(m.group(1))
        except: pass
        try:
            rgba = shape.styles.get(u"foreground", "")
            painttype = shape.styles.get(u"painttype", "")
            if painttype=="1" and rgba:
                # if painttype is "1" then fg has reason
                rgba = [int(255*float(c)) for c in rgba.split()]
                fg = "#%02X%02X%02X"%tuple(rgba[:-1])
        except: pass
        try:
            rgba = shape.styles.get(u"background", "")
            filltype = shape.styles.get(u"filltype", "")
            if filltype=="1" and rgba:
                # if filltype is "1" then bg has reason
                rgba = [int(255*float(c)) for c in rgba.split()]
                bg = "#%02X%02X%02X"%tuple(rgba[:-1])
        except: pass
        return {"gfig_width":w, "gfig_fg":fg, "gfig_bg":bg}

    def __styles__(self):
        """Returns styles for creation (from gfig-styles). Successor can
        overload this, if needed other styles for creation (they are
        kw arg in Tk Canvas create_<shape>())
        """
        return {"outline":self.cget("gfig_fg"), "fill":self.cget("gfig_bg"),
                "width":self.cget("gfig_width")}

    def __create__(self):
        """Calculate all needed argument for canvas object
        creation (coords and so on) and returns {'func':,
        'a':, 'kw':} for calling Tk, where func is the func
        object (bound), a - are positional args (points for
        Tk Canvas), kw - are keyword args
        """
        return None

    def create(self):
        """General method of creation canvas object"""
        creation = self.__create__()
        styles = self.__styles__()
        styles.update(creation.get("kw", {}))
        if creation:
            self.tag = creation["func"](*creation["a"], **styles)
            self.c.addtag_withtag(self.grptag, self.tag)

    # NOTE If I will need to reimplement it via delete()/create() new
    # I'll have to keep user_styles (and gfig_styles?) - this is the
    # reason why I keep styles in user_styles
    def recreate(self, *coords, **options):
        """Like create
        """
        if self.tag is not None:
            self.c.coords(self.tag, *coords)
            # FIXME In some mail list there is the info that itemconfigure()
            # acomplish to Tk memory leak???
            self.c.itemconfigure(self.tag, **options)
        if self.labeltag is not None:
            labx, laby = self._align_label()
            self.c.coords(self.labeltag, labx, laby)

    # XXX I'm not sure
#    def __del__(self):
#        try:
#            self.delete()
#        except:
#            pass

    def delete(self):
        """Delete canvas object from canvas"""
        if self.labeltag is not None:
            self.c.delete(self.labeltag)
            self.labeltag = None # no items - no tag
        if self.tag is not None:
            self.c.delete(self.tag)
            self.tag = None # no items - no tag

    # Label methods {{{

    # 1st call in labelconfig returns x,y of label
    # In transform methods label will be recreated with saved label styles.
    def _align_label(self, side=None, padx=None, pady=None):
        """Returns x,y of label (for canvas coords()/create(). side is like
        in labelconfigure() - N, NW, CENTER... Use args or current label_style,
        which is always available (after __init__() with defaults values)
        """
        side = self.label_styles["side"] if side is None else side
        padx = self.label_styles["padx"] if padx is None else padx
        pady = self.label_styles["pady"] if pady is None else pady
        bx0, by0, bx1, by1 = self.c.bbox(self.tag)
        bx0 += padx
        by0 += pady
        return tkutils.anchor_coords(bx0, by0, bx1, by1, side)

    def labelconfigure(self, **kw):
        """Configure (and create if not created) label; kw is
        the dict of standard Tk Canvas text item options; side is
        one of NW|N|NE|W|CENTER|E|SW|S|SE. side is the way to align
        label on one of shape bbox corner (or center), use also
        anchor. There are additional kw-arguments - padx, pady,
        to shift text x,y more strictly
        """
        if kw:
            # set options
            side = kw.pop("side", None)
            padx = kw.pop("padx", None)
            pady = kw.pop("pady", None)

            # if kw is not empty after popping side,padx,pady, then changed should
            # be True, bcz needed not controllable via side,padx,pady comparisions
            # changes
            changed = bool(kw)
            if side is not None:
                if self.label_styles["side"] != side:
                    self.label_styles["side"] = side
                    changed = True
            if padx is not None:
                if self.label_styles["padx"] != padx:
                    self.label_styles["padx"] = padx
                    changed = True
            if pady is not None:
                if self.label_styles["pady"] != pady:
                    self.label_styles["pady"] = pady
                    changed = True
            if not changed:
                # avoid setting of attrs that already has the same values
                return

            x, y = self._align_label(side, padx, pady) # and saved label styles
            if self.labeltag is None:
                self.labeltag = self.c.create_text(x, y, **kw)
            else:
                self.c.coords(self.labeltag, x, y)
                self.c.itemconfigure(self.labeltag, **kw)
        else:
            # get options
            if self.labeltag:
                ret = self.c.itemconfigure(self.labeltag)
                ret.update(self.label_styles)
                return ret
            else:
                raise ValueError(u"label was not created")
    labelconfig = labelconfigure

    def labelcget(self, optname):
        if optname in self.label_styles:
            return self.label_styles[optname]
        elif self.labeltag:
            return self.c.itemcget(self.labeltag, optname)
        else:
            raise ValueError(u"label was not created")

    # }}}

    # Transformation methods {{{

    def move(self, xoff, yoff):
        """Move by X-offset and Y-offset"""
        self.s.points = [(p[0]+xoff, p[1]+yoff) for p in self.s.points]
        creation = self.__create__()
        if creation:
            self.recreate(*creation["a"], **creation.get("kw", {}))

    def flip(self, axe, axe_point=0):
        """Flip regarding axe 'x'|'y', axe_point - is coordinate
        of axe (need only one)
        """
        if axe in ("x", "X"):
            self.s.points = [(p[0], -p[1] + 2*axe_point) for p in self.s.points]
        elif axe in ("y", "Y"):
            self.s.points = [(-p[0] + 2*axe_point, p[1]) for p in self.s.points]
        else:
            raise ValueError(u"axe must be 'x' or 'y'")
        creation = self.__create__()
        if creation:
            self.recreate(*creation["a"], **creation.get("kw", {}))

    def xscale(self, factor, axe_point=0, widthscale=False):
        """Scale by factor by 0x, it's coords are specified by axe_point. Instead of
        coordinate, axe_point can be LEFT|RIGHT. If widthscale,
        then width of out-line will be scaled (minimal is 1 pixel)
        """
        bx0,by0,bx1,by1 = self.c.bbox(self.tag)
        if axe_point==LEFT:
            axe_point = bx0
        elif axe_point==RIGHT:
            axe_point = bx1
            
        self.s.points = [(axe_point + (p[0]-axe_point)*factor, p[1]) for p in self.s.points]
        creation = self.__create__()
        if creation:
            if widthscale:
                w = float(self.c.itemcget(self.tag, "width"))
                w = max(1, w * factor)
                creation.setdefault("kw", {})
                creation["kw"]["width"] = w
            self.recreate(*creation["a"], **creation.get("kw", {}))

    def yscale(self, factor, axe_point=0, widthscale=False):
        """Scale by factor by 0y, it's coords are specified by axe_point. Instead of
        coordinate, axe_point can be TOP|BOTTOM. If widthscale,
        then width of out-line will be scaled (minimal is 1 pixel)
        """
        bx0,by0,bx1,by1 = self.c.bbox(self.tag)
        if axe_point==TOP:
            axe_point = by0
        elif axe_point==BOTTOM:
            axe_point = by1
            
        self.s.points = [(p[0], axe_point + (p[1]-axe_point)*factor) for p in self.s.points]
        creation = self.__create__()
        if creation:
            if widthscale:
                w = float(self.c.itemcget(self.tag, "width"))
                w = max(1, w * factor)
                creation.setdefault("kw", {})
                creation["kw"]["width"] = w
            self.recreate(*creation["a"], **creation.get("kw", {}))

    # XXX can not rotate rectangles, ovals (?), circles
    def rotate(self, x, y, angle):
        """Rotate shape about x,y on specified angle
        """
        rangle = math.radians(angle)
        def rotpair(p):
            """rotate x,y (p is pair of x,y). From effbot.org:
            'Tkinter Tricks:Using Complex Numbers to Rotate Canvas Items'"""
            px = p[0] - x
            py = p[1] - y
            rx = px*math.cos(rangle) + py*math.sin(rangle)
            ry = -px*math.sin(rangle) + py*math.cos(rangle)
            return (rx+x, ry+y)

        self.s.points = [rotpair(p) for p in self.s.points]
        creation = self.__create__()
        if creation:
            self.recreate(*creation["a"], **creation.get("kw", {}))

    def place(self, x=None, y=None, relx=None, rely=None,
            width=None, height=None, relwidth=None, relheight=None, anchor=CENTER, widthscale=False):
        """Like place in Tk but on canvas
        """
        canw = float(self.c.winfo_width())
        canh = float(self.c.winfo_height())
        if relx is not None:
            x = canw * relx
        if rely is not None:
            y = canh * rely
        if relwidth is not None:
            width = canw * relwidth
        if relheight is not None:
            height = canh * relheight

        bx0, by0, bx1, by1 = self.c.bbox(self.tag)

        # first, change size

        if width:
            oldw = abs(bx1-bx0) or 1.
            self.xscale(factor=width/oldw, axe_point=LEFT, widthscale=widthscale)
        if height:
            oldh = abs(by1-by0) or 1.
            self.yscale(factor=height/oldh, axe_point=TOP, widthscale=widthscale)

        # second, move

        # Anchor coords: anchor is point inside this bound-box. Moving needs
        # shifting by the anchor coords (inside bbox) after usual movement.
        ax,ay = tkutils.anchor_coords(0, 0, bx1-bx0, by1-by0, anchor)

        if x is not None and x != bx0:
            xoff = x - bx0 - ax
        else:
            xoff = 0

        if y is not None and y != by0:
            yoff = y - by0 - ay
        else:
            yoff = 0

        #print "[%s] bx0: %d ax: %d xoff: %d canw: %d" % (self.tag, bx0, ax, xoff, canw)
        if xoff or yoff:
            self.move(xoff, yoff)

    # }}}

    def configure(self, **kw):
        """Configure item styles if kw, else return styles
        as dict. If was not created any canvas object,
        returns only gfig_styles"""
        if self.tag is not None:
            # already exists canvas item
            if not kw:
                # obtain options, not set
                ret = self.c.itemconfigure(self.tag)
                ret.update(self.gfig_styles)
                return ret
            else:
                changed = False
                # set new values for options
                for k,v in kw.iteritems():
                    if k.startswith("gfig_"):
                        self.gfig_styles[k] = v
                    else:
                        if self.user_styles.get(k) != v:
                            self.user_styles[k] = v
                            changed = True
                if not changed:
                    # avoid setting of attrs that already has the same values
                    return
                self.c.itemconfigure(self.tag, **self.user_styles)
        else:
            # canvas item not exists, so returns gfig_styles
            return self.gfig_styles
    config = configure

    def cget(self, optname):
        """Returns value of style"""
        if optname in self.gfig_styles:
            return self.gfig_styles[optname]
        else:
            return self.c.itemcget(self.tag, optname)

# }}}

#--------------------------------------------#
# Every conrete canvas shape class must have #
# name like CanvasSomething, where Something #
# is the name of gfig element (shape.name)   #
#                                            #
# Seems to be impossible to create Bezier,   #
# and spiral (may be via arcs?), starts are  #
# omitted                                    #
#--------------------------------------------#

# Canvas concrete shapes {{{

class CanvasIgnoredShape(BaseCanvasShape):
    pass

class CanvasLine(BaseCanvasShape):
    def __create__(self):
        p = list(itertools.chain(*self.s.points))
        return dict(func=self.c.create_line, a=p)

    def __styles__(self):
        return dict(fill=self.cget("gfig_fg"), width=self.cget("gfig_width"))

class CanvasCircle(BaseCanvasShape):
    def __create__(self):
        # points are coords of center and
        # some point on ANY position of the circle
        cx,cy = self.s.points[0]
        x,y = self.s.points[1]
        R = (cx-x)**2 + (cy-y)**2
        R = math.sqrt(R)
        p = (cx-R, cy-R, cx+R, cy+R)
        return dict(func=self.c.create_oval, a=p)

class CanvasEllipse(BaseCanvasShape):
    def __create__(self):
        # points are coords of center and some corner point
        cx,cy = self.s.points[0]
        x,y = self.s.points[1]
        dx = abs(cx-x)
        dy = abs(cy-y)
        p = (cx-dx, cy-dy, cx+dx, cy+dy)
        return dict(func=self.c.create_oval, a=p)

class CanvasRectangle(BaseCanvasShape):
    def __create__(self):
        # points are ANY opposite corner
        p0 = (min(self.s.points[0][0], self.s.points[1][0]),
                min(self.s.points[0][1], self.s.points[1][1]))
        p1 = (max(self.s.points[0][0], self.s.points[1][0]),
                max(self.s.points[0][1], self.s.points[1][1]))
        p = (p0[0], p0[1], p1[0], p1[1])
        return dict(func=self.c.create_rectangle, a=p)

class CanvasPoly(BaseCanvasShape):
    def __init__(self, shape, grptag, canvas, ruby=False):
        """ruby style shows polygon as ruby
        """
        self.ruby = ruby
        self.__points = self.__ruby_points if ruby else self.__solid_points
        BaseCanvasShape.__init__(self, shape, grptag, canvas)

    def configure(self, ruby=None, **kw):
        # Need overrdiding bcz of ruby style
        if not kw and ruby is None:
            # get
            ret = BaseCanvasShape.configure(self)
            ret["ruby"] = self.ruby
            return ret
        else:
            # set ruby or kw
            if ruby is not None:
                self.delete()
                self.__points = self.__ruby_points if ruby else self.__solid_points
                self.create()
                self.ruby = ruby
            if kw:
                BaseCanvasShape.configure(self, **kw)

    def __create__(self):
        p = self.__points()
        return dict(func=self.c.create_polygon, a=p)

    def __solid_points(self):
        """points for solid style (non-ruby)"""
        # there are 2 points: center (c*) and other point on
        # vertex (r*)
        nsegs = int(self.s.extra[0])
        cx,cy = self.s.points[0]
        rx,ry = self.s.points[1]
        # center must be (0,0) for normal polar coords. But
        # it's not, so there is coords shifting on (cx, cy)
        norm_rx = rx - cx # rx in normal coords (without shifting)
        norm_ry = ry - cy # ry in normal coords (without shifting)
        dang = 2*math.pi/nsegs # delta of angle (step)
        R = math.sqrt(norm_rx**2 + norm_ry**2) # radious
        rang = math.atan2(norm_ry, norm_rx) # angle of polar coords of r
        res = [rx, ry]
        for i in xrange(1, nsegs):
            ang = i*dang + rang
            x = iround(R * math.cos(ang) + cx)
            y = iround(R * math.sin(ang) + cy)
            res.extend((x, y))
        return res

    # This method is contrib. from gfig.c
    def __ruby_points(self):
        """points for ruby-style"""
        # there are 2 points: center (c*) and other point on
        # vertex (r*)
        nsegs = int(self.s.extra[0])
        cx,cy = self.s.points[0]
        rx,ry = self.s.points[1]
        shift_x = rx - cx
        shift_y = ry - cy
        R = math.sqrt(shift_x**2 + shift_y**2)
        ang_grid = 2*math.pi/nsegs
        offset_angle = math.atan2(shift_y, shift_x)

        do_line = False
        res = []
        for loop in xrange(nsegs):
            ang_loop = loop*ang_grid + offset_angle

            lx = R * math.cos(ang_loop)
            ly = R * math.sin(ang_loop)

            calc_x = iround(lx + cx)
            calc_y = iround(ly + cy)

            if do_line:
                if calc_x==start_x and calc_y==start_y:
                    continue
                res.extend((calc_x, calc_y, start_x, start_y))
            else:
                do_line = True
                first_x = calc_x
                first_y = calc_y
            start_x = calc_x
            start_y = calc_y
        res.extend((first_x, first_y, start_x, start_y))
        return res

class CanvasArc(BaseCanvasShape):
    def __create__(self):
        # points are coords of 3 points on arc:
        # 2 on edges and one in center of the arc

        # Equation of circle is: (x-cx)**2 + (y-cy)**2 = R**2, where
        # cx,cy is the center, x,y - any point
        # We have 3 points, so we can write 3 equations for them. So
        # this is the system of 3 equations. Lets express cx from
        # difference between 1st, 2nd equations, then use cx in
        # difference between 1st, 3rd for cy calculation. After
        # calculation of cx,cy it's trivial to find R (see circle equation).

        x1, y1 = (float(x) for x in self.s.points[0])
        x2, y2 = (float(x) for x in self.s.points[1])
        x3, y3 = (float(x) for x in self.s.points[2])

        cx = (-x1**2 + x2**2 - y1**2 + y2**2 + (x1**2 - x3**2 + y1**2 - y3**2)*(y1 - y2)/(y1 - y3))/ \
                (-2*(x1 - x2 - (x1 - x3)*(y1 - y2)/(y1 - y3)))

        cy = (x1**2 - x3**2 - 2*cx*(x1 - x3) + y1**2 - y3**2)/(2*(y1 - y3))

        R = math.sqrt((x1 - cx)**2 + (y1 - cy)**2)

        p0 = (cx-R, cy-R)
        p1 = (cx+R, cy+R)

        # contrib. from gfig.c
        norm_x1 = x1 - cx
        norm_y1 = -y1 + cy
        norm_x2 = x2 - cx
        norm_y2 = -y2 + cy
        norm_x3 = x3 - cx
        norm_y3 = -y3 + cy
        ang1 = math.atan2(norm_y1, norm_x1)
        ang2 = math.atan2(norm_y2, norm_x2)
        ang3 = math.atan2(norm_y3, norm_x3)

        if ang1 < 0:
            ang1 += 2*math.pi
        if ang2 < 0:
            ang2 += 2*math.pi
        if ang3 < 0:
            ang3 += 2*math.pi
        ang1 = math.degrees(ang1)
        ang2 = math.degrees(ang2)
        ang3 = math.degrees(ang3)

        maxang = ang1
        if ang3 > maxang:
            maxang = ang3
        minang = ang1
        if ang3 < minang:
            minang = ang3
        if ang2 > minang and ang2 < maxang:
            arcang = maxang - minang
        else:
            arcang = maxang - minang - 360

        ang1 = iround(ang1)
        arcang = iround(arcang)
        cx = iround(cx)
        cy = iround(cy)
        p0 = [iround(x) for x in p0]
        p1 = [iround(x) for x in p1]
        return dict(func=self.c.create_arc, a=(p0[0], p0[1], p1[0], p1[1]), kw={"start":minang, "extent":arcang})

        # for debuging: edges nodes in blue and center in red
        #tkutils.create_canvas_cross(self.c, cx, cy, width=2, fill="red")
        #tkutils.create_canvas_cross(self.c, *self.s.points[0], width=2, fill="blue")
        #tkutils.create_canvas_cross(self.c, *self.s.points[1], width=2, fill="blue")
        #tkutils.create_canvas_cross(self.c, *self.s.points[2], width=2, fill="blue")

# }}}


# GFigRender {{{

class GFigRender(GFigParser):
    """Render GFig file on canvas
    """
    def __init__(self, canvas, encoding="utf8"):
        self.name = "" # name and grptag
        self.c = canvas
        self.encoding = encoding
        self.canvas_shapes = namedlist() # in Z-order: last is top
        self._placed_shapes = {} # {shape:kw for shape.place()}

    def resize(self, event=None):
        """On canvas resizing, is called by owner of GFigRender"""
        for sh,kw in self._placed_shapes.iteritems():
            #print "place with", kw
            sh.place(**kw)

    def name_shapes(self, *names):
        """Name shapes, so each shape will have own name, and will be
        accessible like list (via index), like dictionary (via name)
        or like object (via attribute). Shapes are enumerate for naming
        in order from left-to-right, then from top-to-bottom.
        If no names, '0', '1'..  will be used.
        This method is usable bcz gfig Gimp extension doesnot set name of
        shape.
        """
        sorted_shapes = sorted(self.canvas_shapes, key=lambda sh:self.c.bbox(sh.tag)[:2])
        # names will be names and tail of "shNNN" for shapes without names
        d = len(self.canvas_shapes) - len(names)
        if d > 0:
            # if not enought names, then construct default names (shNNN)
            names = list(names)
            for i in xrange(len(names), len(names)+d+1):
                names.append("sh%d"%i)
        unsorted_names = [None]*len(self.canvas_shapes)
        for name,sh in itertools.izip(names, sorted_shapes):
            unsorted_names[self.canvas_shapes.index(sh)] = name
        self.canvas_shapes.names = unsorted_names

    def shape(self, *names):
        """Returns list of shapes, selected by name or only one shape
        """
        if len(names)==1:
            return self.canvas_shapes[names[0]]
        elif len(names)>1:
            return [self.canvas_shapes[n] for n in names]
        else:
            raise ValueError(u"'shape' expects one or more shape names")

    def configure(self, shapes=None, **kw):
        """Only set (bcz shapes of selected class are several) styles
        of Canvas* classes but only in THIS GFigRender instance.
        """
        if kw:
            if shapes is None:
                shapes = self.canvas_shapes
            for sh in shapes:
                sh.configure(**kw)
    config = configure

    # XXX I'm not sure
#    def __del__(self):
#        try:
#            self.delete()
#        except:
#            pass

    def delete(self):
        """Delete all corresponding items on canvas"""
        for sh in self.canvas_shapes:
            try:
                sh.delete()
            except:
                pass
        self._placed_shapes = {}
        self.canvas_shapes = namedlist()
        #self.c.delete(self.name) # group - not need

    def render(self, src):
        """src is the file object. Caller have to close after rendering. Also
        src may be string - file name"""
        if type(src) in (str, unicode):
            with open(src, "rt") as f:
                f.seek(0, os.SEEK_SET)
                self.feed(f.read().decode(self.encoding))
        else:
            src.seek(0, os.SEEK_SET)
            self.feed(src.read().decode(self.encoding))

    # Transformation methods {{{

    # NOTE transforms selected shapes or all

    def move(self, xoff, yoff, shapes=None):
        """Move to X-offset and Y-offset all items of this GFig
        """
        if shapes is None:
            shapes = self.canvas_shapes
        for sh in shapes:
            sh.move(xoff, yoff)

    def flip(self, axe, axe_point, shapes=None):
        """Flip regarding axe 'x'|'y', axe_point - is coordinate
        of axe (need only one)
        """
        if shapes is None:
            shapes = self.canvas_shapes
        for sh in shapes:
            sh.flip(axe, axe_point)

    def rotate(self, x, y, angle, shapes=None):
        """Rotate about x,y with angle all items of this GFig
        """
        if shapes is None:
            shapes = self.canvas_shapes
        for sh in shapes:
            sh.rotate(x, y, angle)

    def xscale(self, factor, axe_point=0, widthscale=False, shapes=None):
        """Scale by factor by 0x, it's coords are specified by axe_point. If widthscale,
        then width of out-line will be scaled (minimal is 1 pixel)
        """
        if shapes is None:
            shapes = self.canvas_shapes
        for sh in shapes:
            sh.xscale(factor, axe_point, widthscale)

    def yscale(self, factor, axe_point=0, widthscale=False, shapes=None):
        """Scale by factor by 0y, it's coords are specified by axe_point. If widthscale,
        then width of out-line will be scaled (minimal is 1 pixel)
        """
        if shapes is None:
            shapes = self.canvas_shapes
        for sh in shapes:
            sh.yscale(factor, axe_point, widthscale)

    # NOTE doesnot place on original place after forget, bcz no storage
    # of original shape points after it's transformation
    def place_forget(self, shapes):
        """Forget about thees shapes to be dynamicaly placed.
        But doesnot place on original place after forget!
        """
        for sh in shapes:
            try:
                del self._placed_shapes[sh]
            except KeyError:
                continue

    def place(self, x=None, y=None, width=None, height=None, anchor=CENTER,
            widthscale=False, delayed=True, shapes=None):
        """Place shape on canvas - like move, but is possible to
        set dynamic values (as float 0..1 or in percent '45%') which
        will be used always - when canvas changes size too. If delayed,
        then will be placed only on <Configure> Tk event, not immidiatly.
        """
        if shapes is None:
            shapes = self.canvas_shapes

        def _det(v):
            """Determine kind of value - relative|absolute...,
            value is the string like '12'|'23%'
            """
            try:
                if v is None:
                    return ('a', None)
                elif isinstance(v, float):
                    return ('r', minmax(v, 0., 1.))
                elif isinstance(v, str):
                    if v.endswith('%'):
                        v = float(v[:-1])/100.
                    else:
                        raise Exception
                    return ('r', minmax(v, 0., 1.))
                elif isinstance(v, int):
                    return ('a', v)
                else:
                    raise Exception
            except:
                raise ValueError("'place' arguments are numeric, float, string percents only")

        x = _det(x)
        y = _det(y)
        width = _det(width)
        height = _det(height)

        kw = {"anchor":anchor, "widthscale":widthscale}
        kw["relx" if x[0]=='r' else "x"] = x[1]
        kw["rely" if y[0]=='r' else "y"] = y[1]
        kw["relwidth" if width[0]=='r' else "width"] = width[1]
        kw["relheight" if height[0]=='r' else "height"] = height[1]

        if "relx" in kw or "rely" in kw or "relwidth" in kw or "relheight" in kw:
            # needs dynamic placing of shapes if one or more are relative
            for sh in shapes:
                self._placed_shapes[sh] = kw

        if not delayed:
            for sh in shapes:
                sh.place(**kw)

    # }}}

    def ifind_shapes(self, classname="any", name="any", **kw):
        """Generator: find all shapes by conditions: kw are itemcget() options,
        classname is the name of canvas shape class, name is the name of shape
        (if has)
        """
        if name != "any":
            try:
                named_shape = self.canvas_shapes[name]
            except:
                return

        for sh in self.canvas_shapes:
            if (classname=="any" or (sh.__class__.__name__==classname)) and \
                    (name=="any" or sh is named_shape) and \
                    all(sh.cget(k)==v for k,v in kw.iteritems()):
                        yield sh

    def find_shapes(self, **kw):
        """Similar to find_shapes() but returns list
        """
        return list(self.ifind_shapes(**kw))

    def ifind_shapes_at(self, x, y):
        """Find shapes in Z-order which contains x,y point: last is on the top.
        x,y are coordinates of canvas, not gfig file!
        """
        for sh in self.canvas_shapes:
            bx0,by0,bx1,by1 = self.c.bbox(sh.tag)
            if bx0 <= x <= bx1 and by0 <= y <= by1:
                yield sh

    def find_shapes_at(self, x, y):
        """Similar to ifind_shapes_at() but returns list
        """
        return list(self.ifind_shapes_at(x, y))

# TODO
#    def arrange(self, shapes, pattern="first"):
#        """Arrange all shapes (position) on pattern, which is
#        index in shapes"""

    # Parsing methods {{{

    def handle_header(self, attrs):
        """On file header"""
        d = dict(attrs)
        self.name = d.get(u"name", "unnamed").replace(u"\\040", u"_")

    def handle_shape(self, shape):
        """On any shape in the file"""
        classname = "Canvas%s"%shape.name.capitalize()
        class_ = globals().get(classname, CanvasIgnoredShape)
        # In the gfig file names often are equal, so use unique suffix
        grptag = u"%s_%d"%(self.name, id(self))
        sh = class_(shape, grptag=grptag, canvas=self.c)
        sh.create()
        self.canvas_shapes.append(sh)
    # }}}

# }}}

if __name__ == "__main__":
    import sys
    import doctest
    doctest.testmod()
    print "Internal tests passed"

    if len(sys.argv) < 2:
        sys.exit(0)

    root = Tk()
    c = Canvas(root, bd=0)
    c.pack(fill=BOTH, expand=YES)
    tkutils.maximize_toplevel(c)
    f = None
    try:
        f = open(sys.argv[1], "rt")
        r = GFigRender(c)
        r.render(f)
        #r.move(400, 0) # done
        r.name_shapes("first", "second") # done
        #r.canvas_shapes["sh3"].labelconfigure(text="1234567890", side=CENTER, anchor=CENTER, fill="yellow")
        #r.canvas_shapes[1].labelconfigure(text="iuwioueqoiw", side=N, anchor=S)
        #r.flip('x', 200) # done
        #r.flip('y', 466) # done
        #r.xscale(.5, 466, True) # done
        #r.yscale(.5, 200, True) # done
        #r.rotate(466, 200, 180) # done
        #r.yscale(.5, BOTTOM, True, shapes=r.find_shapes(name="sh3")) # done
        #r.xscale(.5, RIGHT, True, shapes=r.find_shapes(name="sh3")) # done
        #r.place(x=0, width="100%", anchor=NW, shapes=r.find_shapes(name="first")) # done, but less testing
        #r.configure(r.find_shapes(name="first"), fill="white")
        tkutils.create_canvas_cross(c, 466, 200, width=2)
        # Examples hot to change attrs of selected shapes:
        #print list(r.find_shapes(width="3.0")) # done - example of searching
        #r.configure(r.find_shapes(classname="CanvasRectangle"), fill="black") # done

        sh = r.find_shapes()[3]
        r.config((sh,), fill="black")
        c.mainloop()
    except Exception, x:
        raise
        print unicode(x)
    finally:
        if f: f.close()
