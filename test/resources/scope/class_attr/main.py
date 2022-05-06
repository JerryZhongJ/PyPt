
def func():
    def g():
        pass
    class C:
        f = g
        g = gg
        ff = g

    return C

def gg():
    pass

C = func()
C.f()
C.ff()