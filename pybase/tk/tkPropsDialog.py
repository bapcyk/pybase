from pybase.tk.tkSimpleDialog import Dialog
from pybase.tk import utils as tkutils
import collections
import Tix
from Tkinter import *

# PropsDialog dialog {{{

class PropsDialog(Dialog):
    """Tk dialog for multiline text editing
    """
    def __init__(self, master, title="", headers=None, class_=None, *a, **kw):
        """headers is the pair, default is ('Name', 'Value')
        """
        class_ = class_ or "TkPropsDialog"
        if headers:
            self._h = headers
        else:
            self._h = ("Name", "Value")
        self.st = None # ScrolledText
        # modal is False to allow users to add properties with add_prop()
        Dialog.__init__(self, master, title=title, class_=class_, modal=False, *a, **kw)
        self.bind_all("<Configure>", self._onconfigure)

    def add_prop(self, name, value):
        """Add property with name and value
        """
        name = unicode(name)
        value = unicode(value)
        self.st.text.config(state=NORMAL)
        self.st.text.insert(END, u"%s\t%s\n"%(name, value))
        self.st.text.config(state=DISABLED)

    def _onconfigure(self, event):
        if self.st:
            ts = self.winfo_width()/2 # tabstop will be half of width
            self.st.text.config(tabs=(ts,))

    def body(self, master):
        master.configure(relief=RAISED, bd=1)
        master.pack_configure(fill=BOTH, expand=YES)

        # grid for headers
        self.hfr = Frame(master)
        self.hfr.pack(fill=X)
        self.h1 = Label(self.hfr, justify=LEFT, text=self._h[0], relief=RAISED)
        self.h2 = Label(self.hfr, justify=LEFT, text=self._h[1], relief=RAISED)
        self.h1.grid(column=0, row=0, sticky=N+W+E)
        self.h2.grid(column=1, row=0, sticky=N+W+E)
        tkutils.set_stretchable_grid(self.hfr, 2, 1)

        self.st = Tix.ScrolledText(master, height=5)
        tkutils.set_relsize(self, "screen", .4, .6)
        self.st.pack(padx=5, pady=5, fill=BOTH, expand=YES)
        # and after set size...
        self.update_idletasks() # to update size of widgets
        self.st.text.config(font="Arial 9", wrap=NONE, spacing3=10, state=DISABLED)
        return self.st.text

    def destroy(self):
        self.unbind_all("<Escape>")
        self.unbind_all("<Configure>")
        Dialog.destroy(self)

    def buttonbox(self):
        self.btnbox = Frame(self)
        self.option_add("*okbtn.text", "OK", 60)
        self.okbtn = Button(self.btnbox, width=10, command=self.ok, name="okbtn", default=ACTIVE)
        self.okbtn.pack(side=LEFT, padx=5, pady=5)
        self.bind("<Escape>", self.cancel)
        self.btnbox.pack(side=RIGHT)

# }}}

if __name__=="__main__":
    root = Tix.Tk()
    root.withdraw()
    pd = PropsDialog(root, title="Properties", headers=("Key", "Value"))
    pd.add_prop("Something", 123)
    pd.add_prop("The size", (100,200))
    pd.add_prop("The Something", "lalalalalalalala lalala")
    pd.show_modal()
