# includes function defintion, nested function (3 levels), global, nonlocal, name, attribute

def func(arg1, arg2=2, arg3=3):
    a = arg1
    b = arg2
    c = arg3
    def func2(arg4):
        global b
        def func3(arg5):
            nonlocal arg4
            a = arg4
            # b should be global
            c = b
            

    class C:
        global b
        nonlocal c
        b = a
        a = b.f
        c = a.f


