# function defintion
# nested function (3 levels)
# class, class method
# global, nonlocal
# names
# attributes

def func(arg1, arg2=2, arg3=[]):
    a = arg1
    b = arg2
    c = arg3
    def func2(*args, **kwargs):
        global b
        def func3(self):
            nonlocal c
            c = self
            c.f = b
        return func3
            
    class C:
        global b
        nonlocal c
        a = b
        c = a.f
        def method(self):
            self.attr1 = a
            self.attr2 = b
            return func2()

    return C
b = "b"
c = func(0)()
_func3 = c.method()
_func3()



