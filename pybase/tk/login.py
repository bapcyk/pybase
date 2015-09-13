# -*- coding: cp1251 -*-

# XXX must be used standard tkSimpleDialog but there are some issues
# in there so I use custom tkSimpleDialog which has only 2 workarounds
# in __init__
#from tkSimpleDialog import Dialog
import tkMessageBox
from pybase.tk.tkSimpleDialog import Dialog
import pybase.tk.utils as tkutils
import pybase.pwd as mypwd
from pybase import rsa
from Tkconstants import *
from Tkinter import *

class TkLogin(Dialog):
    """Tk dialog for login
    """
    result = None
    def __init__(self, master, authfunc=None, title="", class_=None, *a, **kw):
        """dotcfgobj is DotCfg (opened)
        """
        self.authfunc = authfunc or (lambda u,p: None)
        class_ = class_ or "TkPwdLogin"
        Dialog.__init__(self, master, title=title, class_=class_, *a, **kw)

    def validate(self):
        self.result = self.authfunc(self.logv.get(), self.passv.get())
        if not self.result:
            tkMessageBox.showwarning(
                    u"Error",
                    u"Illegal login name, password",
                    parent=self)
            return False
        else:
            return True

    def apply(self):
        #"""Occurs after ok selected"""
        if not self.result:
            self.u = None
            self.p = None
        else:
            self.u = self.logv.get()
            self.p = self.passv.get()

    def body(self, master):
        master.pack_configure(fill=BOTH, expand=YES)
        self.option_add("*authprompt.text", "Welcome to system", 60)
        self.option_add("*authlogin.text", "Login", 60)
        self.option_add("*authpasswd.text", "Password", 60)

        l = Label(master, name="authprompt")
        l.grid(row=0, column=0, columnspan=2)

        l = Label(master, name="authlogin")
        l.grid(row=1, column=0, sticky=NE, ipadx=10, pady=10)

        self.logv = StringVar()
        self.loginedt = Entry(master, textvariable=self.logv)
        self.loginedt.grid(row=1, column=1, sticky=NW, pady=10)

        l = Label(master, name="authpasswd")
        l.grid(row=2, column=0, sticky=NE, ipadx=10, pady=10)

        self.passv = StringVar()
        self.passwdedt = Entry(master, textvariable=self.passv, show='*')
        self.passwdedt.grid(row=2, column=1, sticky=NW, pady=10)

        tkutils.set_stretchable_grid(master, 2, 3)

        tkutils.set_relsize(self, "screen", .3, .2)
        return self.loginedt

def asklogin(master, authfunc, *a, **kw):
    """Returns TkLogin, use it's attributes: result (result of
    authfunc), u - username, p - password"""
    l = TkLogin(master, authfunc=authfunc, *a, **kw)
    return l

def askpwdlogin(master, filename, privkey=None, env=None, *a, **kw):
    """Ask for password then call pybase.pwd.login() to
    authenticate again and run user 'shell'
    """
    res = _askpwdprelogin(master, filename, privkey, *a, **kw)
    if res:
        env = res["env"]
        env.update(env or {})
        mypwd.login(res["answer"].u, res["answer"].p, res["users"], env=env)

def _askpwdprelogin(master, filename, privkey=None, *a, **kw):
    """Ask for password then authenticate via pybase.pwd and
    returns {"answer":, "users":, "env":} where answer - is the TkLogin
    with it's fields (result, u, p), users - is the dictionary
    of User() (see pybase.pwd), env - environment with signed
    authentication (if privkey is not empty) and HOME, USER, SHELL...
    """
    with open(filename, "rt") as f:
        users = mypwd.parse_pwd_file(f)
        authfunc = lambda u,p: mypwd.auth(u, p, users)
        w = asklogin(master, authfunc, *a, **kw)
        if w.result:
            env = mypwd.inituser_env(w.result)
            if privkey:
                _signenvauth(w.u, privkey, env)
            return dict(answer=w, users=users, env=env)
    return None

__ENV_SIGN = "Logged user is:"
def _signenvauth(username, privkey, env):
    """Sign authentication fact in environment"""
    ch = rsa.sign(__ENV_SIGN + username, privkey)
    env.setdefault(mypwd.ENV_PREFIX + "USER", username)
    env[mypwd.ENV_PREFIX + "AUTH_S"] = ch

def _verify_envauth(pubkey, env):
    """Verify signature of authentication fact"""
    username = env.get(mypwd.ENV_PREFIX + "USER", None)
    ch = env.get(mypwd.ENV_PREFIX + "AUTH_S", None)
    if not username or not ch:
        return False
    p = rsa.verify(ch, pubkey)
    return p == __ENV_SIGN + username

if __name__=="__main__":
    import Tix
    root = Tix.Tk()
    root.withdraw()
    f = lambda u,p: p=="111"
    print "entered", asklogin(root, f).result

#root = Tk()
#askpwdlogin(root, "../../../../../../etc/passwd", title=u"Залогинься!")
