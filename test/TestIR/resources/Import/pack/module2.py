a = 1
from .module3 import a as b     # from relative module import names
from .pack2.module5 import *    # from relative module import names     # from module import *
from pack.pack2 import *        # from absolute package import modules  # from package import *
# print("\nIn module2")
# for name, value in globals().copy().items():
#     if(name[0] != '_'):
#         print(f"{name}: {value}")

