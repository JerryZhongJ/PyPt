# function defintion
# nested function (3 levels)
# class, class method
# global, nonlocal
# names
# attributes

def func(arg1, arg2=2, arg3=3):
    a = arg1
    b = arg2
    c = arg3
    def func2():
        global b
        def func3():
            nonlocal c
            c = b
            # b should be global
            a = c
            
    class C:
        global b
        nonlocal c
        a = b
        c = a.f
        def method(self):
            self.attr1 = a
            self.attr2 = b

    return C



