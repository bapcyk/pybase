# Virtual root, for sandbox - portable file system pie
# May be used when app need portable FS pie:
#
# VRoot:
#   usr/
#     share/
#   lib
#   ...etc...
#
# And app have to access files under relative paths in VRoot (sandbox)

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

# Virtual file system root
# VRoot(mount_point) create virtual (sandbox) root with methods:
#   hpath(virtual_path) -> path on host
#   vpath(host_path, keep_host=False) -> virtual path, if not possible
#       and keep_host, returns original host_path (None otherwise)
# And function:
#   path2uri(path, base=None) -> URI, like a/b/c to be inserted to 'file:///<HERE>'

# Author: P. Yosifov, 2010

from os import path

class VRoot:
    """Use always unicode in path!
    """
    _mp = None

    def __init__(self, mp):
        "mp is the mount-point: abs. path on host"
        self.mount(mp)

    def hpath(self, vp):
        """Returns host path from virtual path:
        >>> vr = VRoot(u'/a/b')
        >>> vr.hpath(u'c///') == VRoot._fixed_abspath(u'/a/b/c')
        True
        >>> vr.hpath(u'/c///') == VRoot._fixed_abspath(u'/a/b/c')
        True
        >>> vr.hpath(u"../../../c/") == VRoot._fixed_abspath(u'/a/b/c')
        True
        >>> vr.hpath(u"/../c/") == VRoot._fixed_abspath(u'/a/b/c')
        True
        """
        vp = vp.replace(u"\\", u"/").split(u'/')
        vp = u'/'.join(x for x in vp if x and x!=u"..")
        return VRoot._fixed_abspath(path.join(self._mp, vp))

    def vpath(self, hp, keep_host=False):
        """Returns virtual path, relative to _mp. If keep_host, then
        returns original hp when hp is not in _mp, otherwise returns None:
        >>> vr = VRoot(u'/a/b/')
        >>> vr.vpath(u'/a/b/') == path.sep
        True
        >>> vr.vpath(u'/a/b/', True) == path.sep
        True
        >>> vr.vpath(u"/x///")
        >>> vr.vpath(u"/x/", True) == path.sep + u'x'
        True
        >>> vr = VRoot(u'/')
        >>> vr.vpath(u'/a/b/') == path.normpath(u"a/b")
        True
        """
        ap = VRoot._fixed_abspath(hp)
        ap = VRoot._fixed_relpath(ap, self._mp)
        if u".." in ap:
            if keep_host:
                return path.normpath(hp)
            else:
                return None
        elif ap == u".":
            return path.sep
        else:
            return ap

    @staticmethod
    def _pathroot(p):
        """Returns absolute path of root of path p:
        >>> VRoot._pathroot("/a/") == VRoot._fixed_abspath("/")
        True
        >>> VRoot._pathroot(r"d:\\x\\y\\\\")
        'd:\\\\'
        """
        p_drive = path.splitdrive(p)[0]
        if p_drive:
            # if there is the drive, absroot will be '<drive><sep>'
            absroot = p_drive + path.sep
        else:
            # else will be default system root
            absroot = VRoot._fixed_abspath(u"/")
        return absroot

    @staticmethod
    def _fixed_abspath(p):
        """Issue: not normalized case"""
        return path.normcase(path.abspath(p))

    @staticmethod
    def _fixed_relpath(p, base):
        """Issue: when base is root, p is prefixed by '..<root>':
        >>> VRoot._fixed_relpath('/a/b/c/', '/') == r'a\\b\\c'
        True
        >>> VRoot._fixed_relpath(r'd:\\x\\y', r'd:\\\\') == path.normpath("x/y")
        True
        """
        base_drive = path.splitdrive(base)[0]
        if base_drive:
            # if there is the drive, absroot will be '<drive><sep>'
            absroot = base_drive + path.sep
        else:
            # else will be default system root
            absroot = VRoot._fixed_abspath(u"/")
        if VRoot._fixed_abspath(base) == absroot:
            # if base is root
            return path.normpath(p).lstrip(u".." + absroot)
        else:
            return path.relpath(p, base)

    def mount(self, mp):
        self._mp = VRoot._fixed_abspath(mp)

def path2uri(p, base=None):
    """Path to uri, but without 'file:///'! See:
    >>> path2uri('/a/b/c///')
    u'a/b/c'
    >>> path2uri(r'd:\\x\\y')
    u'x/y'
    >>> path2uri(u'/x/y/z', '/x')
    u'y/z'
    """
    return VRoot(base or VRoot._pathroot(p)).vpath(p).replace('\\', '/')

if __name__ == "__main__":
    import doctest
    doctest.testmod()
    #print VRoot._pathroot(r'd:\\\\x\y')
