# includes function defintion, nested function (3 levels), global, nonlocal, name, attribute

def func(arg1, arg2=2, arg3=3):
    global a
    a = arg1
    b = arg2
    c = arg3
    def func2(arg4):
        global b
        b = arg4
        def func3():
            nonlocal arg4
            arg4 = c.f
            d.f = b.f

# TODO: add a class

class C:
    b = a
    a = b.f
    c = a.f

a.f.f = b.f
