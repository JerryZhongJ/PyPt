def func(arg):
    def inner():
        nonlocal arg
        arg = arg.f
    inner()
    return arg

class C:
    def f():
        pass

func(C)()