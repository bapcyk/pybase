from pybase.tk.tkSimpleDialog import Dialog
from pybase.tk import utils as tkutils
import collections
import Tix
from Tkinter import *

# ItemsChooser dialog {{{

class ItemsChooser(Dialog):
    """Tk dialog for select one (or more - see selectmode) item from many
    """
    result = None
    stl = None # ScrolledTList
    def __init__(self, master, items=(), title="", hint="", selectmode=Tix.SINGLE,
            initialsel=None, class_=None, *a, **kw):
        """items is list of pairs (key, value): key is returned when selected, value is
        shown in list, hint is the text under items list, selectmode is SINGLE or EXTENDED,
        initialsel is the string like 'a,b,c,d' (only keys of selected items)
        """
        class_ = class_ or "TkItemsChooser"
        self.items = collections.OrderedDict((unicode(k), unicode(v)) for k,v in items)
        self._sm = selectmode
        self._is = initialsel
        if hint:
            self._h = hint
        else:
            if selectmode in (Tix.SINGLE, Tix.BROWSE):
                self._h = "Select some item:"
            else:
                self._h = "Select one or more items:"
        Dialog.__init__(self, master, title=title, class_=class_, *a, **kw)

    def body(self, master):
        master.configure(relief=RAISED, bd=1)
        master.pack_configure(fill=BOTH, expand=YES)
        self.hint = Label(master, justify=LEFT, text=self._h)
        self.hint.pack(anchor=W, padx=5, pady=5)
        self.stl = Tix.ScrolledTList(master)
        self.stl.tlist["selectmode"] = self._sm
        for k,v in self.items.iteritems():
            self.stl.tlist.insert(END, itemtype=Tix.TEXT, text=unicode(v))
        if self.items:
            # if there are items then try to select initialsel items or first
            if self._is:
                for el in self._is.split(','):
                    index = self.items.keys().index(el.strip())
                    if index!=-1:
                        self.stl.tlist.selection_set(index)
            else:
                self.stl.tlist.selection_set(0)
        self.stl.pack(padx=5, pady=5, fill=BOTH, expand=YES)
        tkutils.set_relsize(self, "screen", .3, .4)
        return self.stl.tlist

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

    def destroy(self):
        self.unbind_all("<Return>")
        self.unbind_all("<Escape>")
        Dialog.destroy(self)

    def apply(self):
        try:
            if self.items:
                self.result = self.stl.tlist.info_selection()
                self.result = tuple(self.items.keys()[int(i)] for i in self.result)
        except:
            pass

# }}}

# RangeChooser dialog {{{

class RangeChooser(Dialog):
    """Tk dialog for select one value from range
    """
    result = None
    sb = None # Spinbox
    items = None
    def __init__(self, master, max=None, items=None, min=0, step=1, format=None, title="", hint="",
            initialval=None, class_=None, *a, **kw):
        class_ = class_ or "TkRangeChooser"
        if items is not None:
            # using list of pairs to spinning
            initialval = [v for k,v in items if k==initialval]
            if initialval:
                initialval = initialval[0]
            self.items = collections.OrderedDict((unicode(v), unicode(k)) for k,v in items)
            self.v = StringVar()
            self.sb = dict(textvariable=self.v, values=self.items.keys())
        else:
            # else use numeric values to spinning
            if type(max) is float:
                self.v = DoubleVar()
            else:
                self.v = IntVar()
            self.sb = dict(textvariable=self.v, from_=min, to=max, increment=step, format=format)

        self._iv = initialval

        if hint:
            self._h = hint
        else:
            self._h = "Enter value from range:"
        Dialog.__init__(self, master, title=title, class_=class_, *a, **kw)

    def body(self, master):
        master.configure(relief=RAISED, bd=1)
        master.pack_configure(fill=BOTH, expand=YES)
        self.hint = Label(master, justify=LEFT, text=self._h)
        self.hint.pack(anchor=W, padx=5, pady=5)
        self.sb = Spinbox(master, **self.sb)
        # set only AFTER creation of widget
        if self._iv:
            self.v.set(self._iv)
        self.sb.pack(anchor=W, padx=5, pady=5, fill=X)
        tkutils.set_relsize(self, "screen", .2, .2)
        return self.sb

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

    def destroy(self):
        self.unbind_all("<Return>")
        self.unbind_all("<Escape>")
        self.v = None
        Dialog.destroy(self)

    def apply(self):
        res = self.v.get()
        if res is not None:
            if self.items:
                self.result = self.items.get(res, None)
            else:
                self.result = res

# }}}

def askone(*a, **kw):
    """ask only for one item"""
    c = ItemsChooser(*a, selectmode=Tix.SINGLE, **kw)
    return c.result

def askmany(*a, **kw):
    """ask for several selected items"""
    c = ItemsChooser(*a, selectmode=Tix.EXTENDED, **kw)
    return c.result

def askrange(*a, **kw):
    """ask for value from range"""
    c = RangeChooser(*a, **kw)
    return c.result


if __name__=="__main__":
    root = Tix.Tk()
    root.withdraw()
    print "entered", askrange(root, max=100, step=5, title="Title", initialval=10)
    print "entered", askrange(root, max=100., min=10., format="%.2f", step=.1, title="Title", initialval=10)
    print "entered", askrange(root, items=((1,"aaa"), (2,"bbb"), (3,"ccc")), title="Title", initialval=2)

    print "selection", askmany(root, title="Title", hint="Select something please:",
            items=((10, "aaa"), (20, "bbb"), (30, "ccc"), (40, "ddd"), (50, "eee"),
            (60, "fff"), ("yo!", "ggg")),
            initialsel="10, 50, yo!")
