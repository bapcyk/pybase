from pybase.tk.tkSimpleDialog import Dialog
from pybase.tk import utils as tkutils
import collections
import Tix
from Tkinter import *

# TextDialog dialog {{{

class TextDialog(Dialog):
    """Tk dialog for multiline text editing
    """
    result = None
    st = None # ScrolledText
    def __init__(self, master, text="", title="", hint="", class_=None, *a, **kw):
        class_ = class_ or "TkTextDialog"
        self._t = text
        if hint:
            self._h = hint
        else:
            self._h = "Edit text lines:"
        Dialog.__init__(self, master, title=title, class_=class_, *a, **kw)

    def body(self, master):
        master.configure(relief=RAISED, bd=1)
        master.pack_configure(fill=BOTH, expand=YES)
        self.hint = Label(master, justify=LEFT, text=self._h)
        self.hint.pack(anchor=W, padx=5, pady=5)
        self.st = Tix.ScrolledText(master, height=5)
        self.st.text["font"] = "Arial 9"
        self.st.text.insert(INSERT, self._t)
        self.st.pack(padx=5, pady=5, fill=BOTH, expand=YES)
        tkutils.set_relsize(self, "screen", .4, .4)
        return self.st.text

    def buttonbox(self):
        self.btnbox = Frame(self)
        self.option_add("*okbtn.text", "OK", 60)
        self.option_add("*cancelbtn.text", "Cancel", 60)
        self.okbtn = Button(self.btnbox, width=10, command=self.ok, name="okbtn", default=ACTIVE)
        self.okbtn.pack(side=LEFT, padx=5, pady=5)
        self.cancelbtn = Button(self.btnbox, width=10, command=self.cancel, name="cancelbtn")
        self.cancelbtn.pack(side=LEFT, padx=5, pady=5)
        self.bind("<Escape>", self.cancel)
        self.btnbox.pack(side=RIGHT)

    def destroy(self):
        self.unbind_all("<Escape>")
        Dialog.destroy(self)

    def apply(self):
        self.result = self.st.text.get("1.0", END)

# }}}

def asktext(*a, **kw):
    """ask only for one item"""
    c = TextDialog(*a, **kw)
    return c.result

if __name__=="__main__":
    text = """aaaaaa
    bbb ccc ddd eee
fff     ggg"""
    root = Tix.Tk()
    root.withdraw()
    print "entered", asktext(root, text=text, title="Title", hint="Enter something please:")
