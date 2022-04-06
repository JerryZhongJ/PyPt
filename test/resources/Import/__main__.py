# with alias

# import absolute module
# import absolute package.module

# from absolute package import modules
# from relative module import names
# from package import *
# from module import *

# import trigger more import
# code in __init__.py

import module1 as M1            # import absolute module
import pack.module2       # import absolute package.module
# print("\nIn __main__")
# for name, value in globals().copy().items():
#     if(name[0] != '_'):
#         print(f"{name}: {value}")
# print(f"M1.a: {M1.a}")
# print(f"pack.module2.b: {pack.module2.b}")
