# GFig GIMP 2.6 files parsing. Parses only KNOWN_SHAPES, all
# other are ignored. Also parses styles and extra parameters.
# Suppose fixed structure of file: lines are not joined!

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

import re

# all other are ignored
KNOWN_SHAPES = (u"line", u"rectangle", u"circle", u"ellipse", u"poly",
        u"star", u"spiral", u"bezier", u"arc")

class GFigParseError(Exception):
    def __init__(self, msg, nline, line=""):
        """nline is ZERO-BASED!"""
        l = u" (%s)"%line if line else ""
        self.message = u"%d: %s%s"%(nline+1, msg, l)
    def __unicode__(self):
        return self.message

def _normline(line):
    """strip and lower-case, if is empty,
    returns None"""
    try:
        return line.strip().lower()
    except:
        return None

def _getpair(line, varname=None):
    """If line starts with varname, extract
    following part of line and returns pair
    (varname, tail). varname may be omitted,
    so first word will be varname:
    >>> _getpair('name1: 567', 'name1:')
    ('name1', '567')
    >>> _getpair('', 'abc:')
    >>> _getpair("var:     12 34")
    ('var', '12 34')
    """
    spl = line.split(varname)
    if len(spl) < 2:
        return None
    var = (spl[0] or varname).strip(':')
    val = " ".join(s.strip(": \t") for s in spl[1:])
    return (var, val)

_cre1 = re.compile(u"<\s*(\w+)\s*(.*)>")
_cre2 = re.compile(u"(\w+)\s*=\s*(\w+|'[^']+'|\"[^\"]+\")")
_cre3 = re.compile(u"<\s*/\s*(\w+)\s*>")
def _gettag(line):
    """Match tag and returns {"name":, "opened":} or None:
    >>> _gettag('aaaa')
    >>> _gettag('< line a = "1 2 3" b= xxx c =12 >')
    {'attrs': {'a': '1 2 3', 'c': '12', 'b': 'xxx'}, 'name': 'line', 'opened': True}
    >>> _gettag('</line>')
    {'attrs': {}, 'name': 'line', 'opened': False}
    >>> _gettag('<line')
    >>> _gettag('')
    """
    m = _cre1.search(line)
    if m:
        tag = {"name":"", "opened":True, "attrs":{}}
        tag["name"] = m.group(1)
        if m.lastindex > 1:
            m = _cre2.findall(m.group(2).strip())
            if m:
                tag["attrs"] = dict((k,v.strip("'\"")) for k,v in m)
        return tag
    else:
        m = _cre3.search(line)
        if m:
            return {"name":m.group(1), "opened":False, "attrs":{}}
    return None

class Shape:
    """Shape like line or circle...
    """
    def __init__(self, name, attrs=None, ignored=False):
        self.points = [] # pairs of coordinates (int)
        self.extra = [] # list of numbers
        self.attrs = attrs or {} # dict of attributes (like HTML tag)
        self.name = name
        self._ignored = ignored
        self.styles = {}
        self.opts = {} # additional options (for user)

class GFigParser:
    def __init__(self):
        pass

    # override them!
    def handle_header(self, attrs):
        "override to handle header with attrs as list of pairs"
        pass
    def handle_options(self, attrs):
        "override to handle options with attrs as list of pairs"
        pass
    def handle_shape(self, shape):
        "override to handle some shape (see Shape)"
        pass

    def feed(self, data):
        """Parser. data is the strings (decode as utf8->unicode!)
        """
        HEAD = 1
        OPTS = 2
        OBJ = 3 # general content of file (tags after <options>)
        EXTRA = 4
        STYLE = 5

        shapes = []
        pairs = []
        st = HEAD
        for nline,line in enumerate(data.splitlines()):
            line = _normline(line)
            if not line:
                continue

            if st == HEAD:
                if line == u"<options>":
                    self.handle_header(pairs)
                    st = OPTS
                    del pairs[:]
                else:
                    #pair = _getpair(line, u"gfig version") or \
                            #_getpair(line, u"name:") or \
                            #_getpair(line, u"version:") or \
                            #_getpair(line, u"objcount:")
                    pair = _getpair(line)
                    if pair:
                        pairs.append(pair)
                    else:
                        raise GFigParseError(u"unexpected line", nline, line)

            elif st == OPTS:
                if line == u"</options>":
                    self.handle_options(pairs)
                    st = OBJ
                    del pairs[:]
                else:
                    #pair = _getpair(line, u"gridspacing:") or \
                            #_getpair(line, u"gridtype:") or \
                            #_getpair(line, u"snap2grid:") or \
                            #_getpair(line, u"lockongrid:") or \
                            #_getpair(line, u"drawgrid:") or \
                            #_getpair(line, u"showcontrol:")
                    pair = _getpair(line)
                    if pair:
                        pairs.append(pair)
                    else:
                        raise GFigParseError(u"unexpected line", nline, line)

            elif st == OBJ:
                # don't change order of if's !
                if line == u"<extra>":
                    st = EXTRA
                elif line == u"<style object>":
                    st = STYLE
                else:
                    tag = _gettag(line)
                    if tag:
                        if tag["opened"]:
                            # opened tag
                            if tag["name"] not in KNOWN_SHAPES:
                                ignored = True
                            else:
                                ignored = False
                            shapes.append(Shape(tag["name"], ignored=ignored, attrs=tag["attrs"]))
                        else:
                            # closed tag
                            if len(shapes) < 1:
                                raise GFigParseError(u"unbalanced tag", nline, line)
                            if shapes[-1].name != tag["name"]:
                                raise GFigParseError(u"unexpected closed tag", nline, line)
                            sh = shapes.pop()
                            if not sh._ignored:
                                self.handle_shape(sh)
                    else:
                        # not tag but points coordinates
                        if len(shapes) < 1:
                            raise GFigParseError(u"unexpected string", nline, line)
                        if not shapes[-1]._ignored:
                            shapes[-1].points.append([int(s) for s in line.split()])

            elif st == EXTRA:
                if len(shapes) < 1:
                    raise GFigParseError(u"out of the tag", nline, line)
                if line == u"</extra>":
                    st = OBJ
                else:
                    try:
                        shapes[-1].extra.extend(int(s) for s in line.split())
                    except:
                        raise GFigParseError(u"Incorrect extra data", nline, line)

            elif st == STYLE:
                if len(shapes) < 1:
                    raise GFigParseError(u"out of the tag", nline, line)
                if line == u"</style>":
                    st = OBJ
                else:
                    pair = _getpair(line)
                    if pair:
                        shapes[-1].styles[pair[0]] = pair[1]
                    else:
                        raise GFigParseError(u"Incorrect style data", nline, line)

        if shapes:
            raise GFigParseError(u"Unbalanced tags detected", nline)
        if st == EXTRA:
            raise GFigParseError(u"No closed </extra> tag", nline)
        if st != OBJ:
            raise GFigParseError(u"No any shapes", nline)


if __name__ == "__main__":
    import sys
    import doctest
    doctest.testmod()

    print "Internal tests passed"

    if len(sys.argv) < 2:
        sys.exit(0)


    class MyGFigParser(GFigParser):
        def handle_header(self, attrs):
            print "Header:", attrs
            print
        def handle_options(self, attrs):
            print "Options:", attrs
            print
        def handle_shape(self, shape):
            print "Shape:", shape.name, "points:", shape.points, "attrs:", shape.attrs, \
                    "styles:", shape.styles, "extra:", shape.extra
            print

    p = MyGFigParser()
    f = None
    try:
        f = open(sys.argv[1], "rt")
        p.feed(f.read().decode("utf8"))
    except Exception, x:
        print unicode(x)
    finally:
        if f: f.close()
