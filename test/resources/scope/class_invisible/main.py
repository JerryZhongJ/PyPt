
def func():
    pass
def func2():
    pass
class C:
    func = func2
    def method():
        func()
    class D:
        method = func


C.method()
C.D.method()