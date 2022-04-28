# nested function: local, global, nonlocal
# class attribute, method call

class C:
    def __init__(self, v):
        self.f = v

    def method(self):
        return self.f

def func():
    nl = 0          # 0, ins, 2
    def func2(arg):
        nonlocal nl
        global g
        nl = arg
        g = arg.method()
    return func2

g = C(2)            # instance, 2
func()(g)

    
