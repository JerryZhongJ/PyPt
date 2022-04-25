# many kinds of arguments / parameters pair 
# method


def func1(arg1, /, arg2, arg3=0, *args, arg4=0, arg5, **kwargs):
    # print(posonlyarg)
    # print(arg12)
    # print(arg3)
    # print(arg4)
    # print(arg5)
    # for arg in args:
    #     print(arg)
    # for kw, arg in kwargs.items():
    #     print(f"{kw}:{arg}")
    # print("")
    pass

def func2(arg1, /, arg2, arg3=0, *args, arg4=0, arg5, **kwargs):
    pass

def func3(arg1, /, arg2, arg3=0, *args, arg4=0, arg5, **kwargs):
    pass

def func4(arg1, /, arg2, arg3=0, *args, arg4=0, arg5, **kwargs):
    pass

func1(1, 2, arg5=5)
func2(1, 2, 3, arg5=5)
func3(1, 2, arg5=5, arg4=4, arg3=3)
func4(1, 2, 3, 6, 7, arg5=5, arg4=4, arg8=8, arg9=9)