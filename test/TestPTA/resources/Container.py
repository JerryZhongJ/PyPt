# list: subscript
# tuple: return tuple, tuple unpack, starred
# dict

def reverse(x, y, z):
    return z, y ,x

t = x, y, z = reverse(1, 2, 3)
l = [e for e in t]

t2 = (0, *l, 4)
e0 = t2[0]
e1 = t2[1]
e4 = t2[-1]

for elt in t2:
    pass
