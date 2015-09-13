# Calling Gimp via shell

import tempfile
import sys
import os
from pybase import utils

class Session(list):
    """list of jobs that ran on the same Gimp instance
    """
#    def __unicode__(self):
#        s = u"%s (%s)"%(super(Session, self).__str__(), self._opts)
#        return s

    _tmpfiles = [] # paths of temp. files - STATIC!
    def __init__(self, *a):
        super(Session, self).__init__(*a)
        self._opts = []
        self._args = []

    def __del__(self):
        # remove all temporary files
        for p in Session._tmpfiles:
            try:
                os.unlink(p)
            except:
                pass

    def copy(self):
        """Independed copy"""
        items = self[:]
        cpy = Session(items)
        cpy._opts = self._opts
        cpy._args = self._args
        return cpy

    def set_opt(self, opt, value=None):
        """option opt (-x|--x), value may be used or not. In _opts will be
        '-x'|'-x xxx'|'--x'|'--x=xxx'
        """
        if value and sys.platform=="win32":
            value = utils.quote_win32(value)
        if opt.startswith("--"):
            # long option
            f = u"%s=%s"%(opt,value) if value else opt
        else:
            f = u"%s %s"%(opt,value) if value else opt
        self._opts.append(f)

    @property
    def gimprc(self):
        raise AttributeError
    @gimprc.setter
    def gimprc(self, value):
        """Exception raising is possible
        """
        if not value: return
        (fd, name) = tempfile.mkstemp(prefix="gimprc", text=True)
        Session._tmpfiles.append(name)
        with os.fdopen(fd, "w") as f:
            f.write(value.encode("utf8"))
            f.close()
            self.set_opt("-g", unicode(name))

    def set_args(self, value):
        """Exception raising is possible
        """
        if not value: return

        if sys.platform=="win32":
            value = [utils.quote_win32(v) for v in value]
        self._args = value

    @property
    def cmdline(self):
        return u"%s %s"%(u" ".join(self._opts), u" ".join(self._args))

class Gimpsh:
    """Call gimp via shell. Called command lines are appened
    by append(). It's one call or many with several instances.
    It uses jobs (runnable via -b .. mechanism), so several
    Scheme functions can be called on one Gimp instance
    """
    def __init__(self, gimp="gimp", vars=None):
        """gimp is the full path to gimp program.
        Vars is the dict of variables for formatting, can be
        changed on the fly.
        """
        self.gimp = gimp
        # list of lists: each list is ran in one task, last task is
        # interactive, other are not.
        self._bs = []
        self.vars = vars or {}

    def append(self, jobs=None, args=None, gimprc=None):
        """Append list of jobs, returns job-sequence id.
        kw are the sessions settings, like gimprc path.
        args are list of positional arguments.
        """
        if not jobs:
            jobs = []
        if type(jobs) not in (list, tuple):
            raise ValueError("jobs should be sequence")
        ret = len(self._bs)

        # create Session with attributes (for options)
        ses = Session(jobs) # list of jobs with session settings
        ses.gimprc = gimprc
        ses.set_args(args)

        self._bs.append(ses)
        return ret

    def _shsession(self, jobs, last):
        """Execute only jobs of one sequence on one gimp instance (one
        session), last is the opt of last sequence (last item in self._bs!)
        """
        if len(jobs) != 0:
            if not last:
                jobs = jobs.copy()
                # FIXME but final console message is not close, so until console is close
                # starting of next gimp is impossible, may be workaround with another
                # system() without waiting child PID
                jobs.append(u"'(gimp-quit 0)'")
                jobs.set_opt("-i")
            j = Gimpsh._prebatch(jobs, self.vars) # returns real list (not Session) of -b OPTs
        else:
            j = ""
        #jobs.set_opt("-s") # no splash window
        cl = u"%s %s %s" % (self.gimp, j, jobs.cmdline)
        utils.system(cl)

    def execone(self, jobsid):
        """Like _shsession but executed jobs are pointed by jobsid. If jobsid
        out of range, IndexError will be raised
        """
        self._shsession(self._bs[jobsid], jobsid==len(self._bs)-1)

    def execall(self, vars={}):
        """Executes all jobs sequence
        """
        for jobsid in xrange(len(self._bs)):
            self.execone(jobsid)

    @staticmethod
    def _prebatch(batches, vars={}):
        """Prepare batch for command line: quotes on win32, adds -b
        """
        if sys.platform ==  "win32":
            bs = [u"-b "+utils.quote_win32(b%vars) for b in batches]
        else:
            bs = [u"-b "+b%vars for b in batches]
        return u" ".join(bs)
