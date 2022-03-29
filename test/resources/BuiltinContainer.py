# build List, Tuple, Dict
# slice
# List, Tuple assign
# List, Tuple return

def foo(x, y, z):
    sum = x + y + z
    return x / sum, y / sum, z / sum

t = []
t[0:2] = [d, e, f] = a, b, c = foo(1, 2, 3)

