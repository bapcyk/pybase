# -*- coding: cp1251 -*-

# XXX must be used standard tkSimpleDialog but there are some issues
# in there so I use custom tkSimpleDialog which has only 2 workarounds
# in __init__

from pybase.utils import dothier
from pybase.tk import utils as tkutils
from pybase.dotcfg import DotCfg, DotCfgError, DotCfgErrorSrc, DOT
#from tkSimpleDialog import Dialog
from pybase.tk.tkSimpleDialog import Dialog
from pybase.tk.tkChooserDialog import askone, askmany, askrange
from pybase.tk.tkTextDialog import asktext
import Tix
from tkFileDialog import Open, SaveAs, Directory
from tkColorChooser import Chooser as Color
from Tkconstants import *
from Tkinter import *
import os



_editor_img = "R0lGODlhDAAMAIABAAAAAP///yH+EUNyZWF0ZWQgd2l0aCBHSU1QACH5BAEKAAEALAAAAAAMAAwAAAIZjI9poAi83nkw0Cixpbx7vn0Z2IRldC5KAQA7"

# Predefined editors {{{

class BaseEditor:
    initial = None # initial value from entry
    master = None # master widget
    def __init__(self, *a, **kw):
        self._args = a
        self._kwargs = kw
    def onget(self, *a, **kw):
        """Open some dialog with self.initial as initial value
        and self.master as master widget, retrieve user enter and
        returns it"""
        raise NotImplementedError
    def ask(self, master, var):
        """called from DotCfg or similar dialogs,
        var is Tk variable (like IntVar)"""
        self.initial = var.get()
        self.master = master
        res = self.onget(*self._args, **self._kwargs)
        if res:
            var.set(res)

class OpenFileEditor(BaseEditor):
    def __init__(self, *a, **kw):
        BaseEditor.__init__(self, *a, **kw)
    def onget(self, *a, **kw):
        if self.initial:
            d = os.path.split(self.initial)[0]
        else:
            d = os.getcwd()
        return Open(initialdir=d, *a, **kw).show()

class SaveFileEditor(BaseEditor):
    def __init__(self, *a, **kw):
        BaseEditor.__init__(self, *a, **kw)
    def onget(self, *a, **kw):
        if self.initial:
            d = os.path.split(self.initial)[0]
        else:
            d = os.getcwd()
        return SaveAs(initialdir=d, *a, **kw).show()

class DirectoryEditor(BaseEditor):
    def __init__(self, *a, **kw):
        BaseEditor.__init__(self, *a, **kw)
    def onget(self, *a, **kw):
        return Directory(initialdir=self.initial or os.getcwd(), *a, **kw).show()

class ColorEditor(BaseEditor):
    def __init__(self, *a, **kw):
        BaseEditor.__init__(self, *a, **kw)
    def onget(self, *a, **kw):
        res = Color(initialcolor=self.initial or "black", *a, **kw).show()
        return res[1] if res else None

class ItemsChooserEditor(BaseEditor):
    def __init__(self, selectmode=Tix.SINGLE, *a, **kw):
        self._sm = selectmode
        BaseEditor.__init__(self, *a, **kw)
    def onget(self, *a, **kw):
        if self._sm in (Tix.SINGLE, Tix.BROWSE):
            res = askone(self.master, initialsel=self.initial, *a, **kw)
        else:
            res = askmany(self.master, initialsel=self.initial, *a, **kw)
        if not res:
            return ""
        else:
            return ','.join(res)

class RangeEditor(BaseEditor):
    def __init__(self, *a, **kw):
        BaseEditor.__init__(self, *a, **kw)
    def onget(self, *a, **kw):
        res = askrange(self.master, initialval=self.initial or kw.get("min", 0), *a, **kw)
        return res

class TextEditor(BaseEditor):
    def __init__(self, *a, **kw):
        BaseEditor.__init__(self, *a, **kw)
    def onget(self, *a, **kw):
        if self.initial:
            text = self.initial.replace("\\n", '\n')
        else:
            text = self.initial
        res = asktext(self.master, text=text, *a, **kw)
        if res:
            res = res.replace('\n', "\\n")
        return res

# }}}

# TkDotCfg dialog {{{

class TkDotCfg(Dialog):
    """Tk dialog for editing dot-based config files, see
    pybase.dotcfg
    """
    _par = None # edited parameter (Parameter())
    edttracename = None # save here name of trace, need for remove
    def __init__(self, master, dotcfgobj, title="", class_=None, *a, **kw):
        """dotcfgobj is DotCfg (parsed)
        """
        self.dotcfg = dotcfgobj
        class_ = class_ or "TkDotCfg"
        Dialog.__init__(self, master, title=title, class_=class_, *a, **kw)

    def apply(self):
        """Occurs after ok/save selected"""
        #self.__onchange(None)
        self.dotcfg.flush()

    def destroy(self):
        self.hint.unbind_all("<Configure>")
        if self.edttracename:
            self.edtvar.trace_vdelete('w', self.edttracename)
            self.edttracename = None
        self.edtvar = None
        self.validhintvar = None
        self.hint = None
        self.edtbtnimg = None
        Dialog.destroy(self)

    def body(self, master):
        master.configure(relief=RAISED, bd=1)
        master.pack_configure(fill=BOTH, expand=YES)
        self.shlist = Tix.ScrolledHList(master, name="hlist")
        #self.shlist.hlist["selectmode"] = SINGLE
        self.shlist.hlist["indent"] = 20
        self.shlist.hlist["browsecmd"] = self.__onbrowse
        self.rightfr = Frame(master)
        self.caption = Label(self.rightfr, name="caption")
        self.caption.pack(padx=5, pady=5, anchor=W, fill=X, expand=YES)
        self.hint = Message(self.rightfr, anchor=W, justify=LEFT)
        self.hint.bind("<Configure>", self.__onhintconfigure)
        #self.hint = Label(self.rightfr, justify=LEFT)
        self.hint.pack(padx=5, anchor=W, fill=BOTH, expand=YES)
        self.edfr = Frame(self.rightfr)
        self.edtvar = StringVar()
        self.edttracename = self.edtvar.trace('w', self.__ontrace_edtvar)
        self.edt = Entry(self.edfr, textvariable=self.edtvar)
        #self.edt.pack(padx=5, pady=5, anchor=W, fill=X, expand=YES)
        self.edt.pack(side=LEFT, fill=X, expand=YES)
        self.edtbtnimg = PhotoImage(data=_editor_img)
        self.edtbtn = Button(self.edfr, image=self.edtbtnimg)
        self.edtbtn.pack(side=LEFT, padx=5)
        self.edfr.pack(padx=5, pady=5, anchor=W, fill=X, expand=YES)
        self.validhintvar = StringVar()
        self.validhint = Label(self.rightfr, name="validhint", textvariable=self.validhintvar, justify=LEFT)
        self.validhint.pack(padx=5, side=LEFT)
        self.shlist.place(relx=.01, rely=.01, relwidth=.48, relheight=.98)
        self.rightfr.place(relx=.5, relwidth=.5)
        self.__load_list()
        #self.shlist.hlist.bind("<KeyRelease>", lambda ev: self.edtbtn.event_generate("<Button-1>"))
        tkutils.set_relsize(self, "screen", .5, .5)
        return self.shlist.hlist

    def buttonbox(self):
        self.btnbox = Frame(self)
        self.option_add("*okbtn.text", "OK", 60)
        self.option_add("*cancelbtn.text", "Cancel", 60)
        self.okbtn = Button(self.btnbox, width=10, command=self.ok, name="okbtn", default=ACTIVE)
        self.okbtn.pack(side=LEFT, padx=5, pady=5)
        self.cancelbtn = Button(self.btnbox, width=10, command=self.cancel, name="cancelbtn")
        self.cancelbtn.pack(side=LEFT, padx=5, pady=5)
        self.bind("<Return>", self.ok)
        self.bind("<Escape>", self.cancel)
        self.btnbox.pack(side=RIGHT)

    def onerror(self, exc):
        """Can be overriden to generate exception with new msg OR
        change DotCfgErrorSrc.REASONS"""
        raise exc

#    def __onexpose(self, event):
#        # FIXME: hack!!! Из-за невозможности вывести сообщение после
#        # вывода диалога, сделал вот так, с затиранием self._openerror
#        if self._openerror:
#            x = self._openerror
#            self._openerror = None
#            self.onerror(x)

    # FIXME: при показе окна не срабатывает!
    def __onhintconfigure(self, event):
        """Occurs when self.hint size has been changed. So here aspect is
        changing"""
        self.__hint_auto_aspect()

    def __hint_auto_aspect(self):
        """Autocalculate aspect ration of self.hint - it's needed for
        correct text wrapping"""
        h = self.hint.winfo_height()
        w = self.hint.winfo_width()
        self.hint["aspect"] = 100 * w/h

    def __onbrowse(self, path):
        """Вызывается на выбор параметра"""
        # FIXME: вызывается ДВА раза подряд!
        # FIXME: path в неизв. кодировке. Приходится через info_data
        key = self.shlist.hlist.info_data(path)
        self._par = self.dotcfg.get(key)
        if self._par:
            self.caption["text"] = self._par.path[-1].capitalize()
            self.hint["text"] = self._par.comment or ""
            self.edtvar.set(repr(self._par))
            editor = self._par.opts.get("editor", None)
            if not editor:
                self.edtbtn["state"] = DISABLED
            else:
                self.edtbtn["state"] = NORMAL
                self.edtbtn["command"] = lambda: editor.ask(self, self.edtvar)
            validhint = getattr(self._par.validator, "hint", "")
            if validhint:
                validhint = u"(%s)"%validhint
            self.validhintvar.set(validhint)

    def __ontrace_edtvar(self, name, index, mode):
        """tracing entry Tk variable"""
        value = self.edtvar.get()
        if value:
            # only if was NOT EMPTY input
            try:
                self._par.value = value
                self.setvar(name, repr(self._par))
            except ValueError:
                # validation error (?), so set to entry widget old value (self._par.value)
                self.edtvar.set(repr(self._par))
                x = DotCfgError(all=(DotCfgErrorSrc(src=self._par, reason=ValueError),))
                self.onerror(x)

    def __load_list(self):
        """Add all items to parameters list"""
        initial_sel = None
        leaf_style = Tix.DisplayStyle(Tix.TEXT, refwindow=self.shlist.hlist,
                font="Arial 7")
        not_leaf_style = Tix.DisplayStyle(Tix.TEXT, refwindow=self.shlist.hlist,
                font="Arial 9 bold", fg="grey40", pady=10)
        for key in dothier(self.dotcfg.names):
            text = key.split(DOT)[-1]
            if key.leaf:
                text = text.lower()
                state = NORMAL
                style = leaf_style
                if initial_sel is None:
                    initial_sel = key
            else:
                text = text.capitalize() + "..."
                state = DISABLED
                style = not_leaf_style
            self.shlist.hlist.add(key, text=text, state=state, data=key, style=style)
        if initial_sel is not None:
            self.shlist.hlist.selection_set(initial_sel)
            self.__onbrowse(initial_sel)
            self.__hint_auto_aspect()

# }}}

if __name__=="__main__":
    import StringIO
    from pybase.dotcfg import Parameter
    sio = StringIO.StringIO(
            "# comment1\n"
            "# comment2\n"
            "obj = 10\n"
            "obj.dir = \n"
            "obj.opened = \n"
            "obj.saved = \n"
            "obj.color = #FF0000\n"
            "other.color = #4567FF\n"
            "other.weight = 200\n"
            "# speed is one of 1,2,3,4,5\n"
            "speed = 2\n"
            "# Some text\n"
            "text = aaa\\nbbb\n"
            )
    items = ((1,"4800"), (2,"9600"), (3,"14400"), (4,"19200"))
    exp = (
            Parameter("obj", comments="Object name..."),
            Parameter("obj.dir", comments="Directory...", editor=DirectoryEditor()),
            Parameter("obj.opened", comments="Opened file...", editor=OpenFileEditor()),
            Parameter("obj.saved", comments="Saved file...", editor=SaveFileEditor()),
            Parameter("obj.color", comments="Color...", editor=ColorEditor()),
            Parameter("other.color", comments="Color...", editor=ColorEditor()),
            Parameter("other.weight", comments="Weight...", editor=RangeEditor(max=200., step=5.5, format="%.1f", title="the title")),
            Parameter("speed", comments="Speed...", editor=ItemsChooserEditor(selectmode=Tix.EXTENDED, items=items)),
            Parameter("text", comments="Text...", editor=TextEditor()),
            )
    dc = DotCfg(exp)
    dc.parse(sio)
    root = Tix.Tk()
    root.withdraw()
    tdc = TkDotCfg(root, dc)
