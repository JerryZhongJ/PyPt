def func1():
    pass

def func2():
    pass
def func3():
    pass

class C:
    def __init__(self):
        self.l = [func1, func2, func3]

    def __iter__(self):
        self.n = 0
        return self

    def __next__(self):
        if self.n < len(self.l):
            f = self.l[self.n]
            self.n += 1
            return f
        else:
            raise StopIteration


for f in C():
    f()
