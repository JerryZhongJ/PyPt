# nested function: local, global, nonlocal
# class attribute, method call
def getF(obj):
    return obj.f
def getG(obj):
    return obj.g
class C:
    def __init__(self, f, g):
        self.f = f
        self.g = g

    def method(self, func):
        return func(self)

def func():
    nl = 0          # nl should be 0, ins
    def func2(arg, getter):
        nonlocal nl
        global g
        nl = arg
        g = arg.method(getter)  # g should be "g"
    return func2

ins = C("f", "g")            # instance
func()(ins, getG)

    
