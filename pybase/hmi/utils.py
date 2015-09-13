def tksafe(meth):
    """Make method Tk-asynchronous, bcz Tk is not thread-safe - this
    wrapper made method thread-safe to be used in Tk in async. manier.
    To be usable, object (symbol) should have tkroot.tkasync (see
    pybase.tk.utils engines)
    """
    def wmeth(self, *a, **kw):
        # uses pybase.tk.async
        self.tkroot.tkasync.post(meth, self, *a, **kw)
    return wmeth
