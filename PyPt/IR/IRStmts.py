
from typing import Any, Dict, List, Tuple, Union
import typing

if typing.TYPE_CHECKING:
    from .CodeBlock import CodeBlock
    from .FunctionCodeBlock import FunctionCodeBlock
    from .ClassCodeBlock import ClassCodeBlock
    from .ModuleCodeBlock import ModuleCodeBlock


class Variable:
    id: str                                # include belongsTo's id
    belongsTo: 'CodeBlock'                # 'CodeBlock' to which it belongs
    readable_name: str
    isTmp: bool

    def __str__(self):
        return self.readable_name

    def __repr__(self):
        return f"Variable: {self.id}"

    def __init__(self, name: str, belongsTo: 'CodeBlock', temp=False):
        # self.name = name
        self.belongsTo = belongsTo
        self.readable_name = f"{name}@{belongsTo.readable_name}"
        self.id = f"{name}@{belongsTo.id}"
        self.isTmp = temp
        
    def __eq__(self, other):
        return isinstance(other, Variable) and self.id == self.id

    def __hash__(self):
        return hash((self.id, self.belongsTo))

# Every stmt has a id
# If that stmt is NewFunction, NewClass, then stmt's id is used in codeblock's id.
class IRStmt:
    belongsTo: 'CodeBlock'                 # 'CodeBlock' to which this IR belongs
    srcPos: Tuple[int]
    id: int
    def __init__(self, belongsTo: 'CodeBlock', id: int):
        self.belongsTo = belongsTo
        belongsTo.addIR(self)
        self.id = id

    def __repr__(self):
        return f"IRStmt: {str(self)}"

    def __hash__(self):
        return hash((self.belongsTo, str(self)))
    
class Assign(IRStmt):
    target: Variable
    source: Variable

    def __init__(self, target: Variable, source: Variable, belongsTo: 'CodeBlock', id: int):
        super().__init__(belongsTo, id)
        self.target = target
        self.source = source

    def __str__(self):
        return f"{self.target} = {self.source}"


# target.attr = source
class SetAttr(IRStmt):
    target: Variable
    source: Variable
    attr: str

    def __init__(self, target: Variable, attr: str, source: Variable, belongsTo: 'CodeBlock', id: int):
        super().__init__(belongsTo, id)
        self.target = target
        self.source = source
        self.attr = attr
        # $global.attr = v
        if(target == belongsTo.module.globalVariable):
            target.belongsTo.module.globalNames.add(attr)

    def __str__(self):
        return  f"{self.target}.{self.attr} = {self.source}"

# target = source.attr
class GetAttr(IRStmt):
    target: Variable
    source: Variable
    attr: str

    def __init__(self, target: Variable, source: Variable, attr: str, belongsTo: 'CodeBlock', id: int):
        super().__init__(belongsTo, id)
        self.target = target
        self.source = source
        self.attr = attr

    def __str__(self):
        return f"{self.target} = {self.source}.{self.attr}"

# target = New ...
class New(IRStmt):
    target: Variable
    objType:str                             # module, function, class, method, instance, builtin
    
    def __init__(self, target: Variable, objType: str, belongsTo: 'CodeBlock', id: int):
        super().__init__(belongsTo, id)
        
        self.target = target
        self.objType = objType

        
class NewModule(New):
    module: Union['ModuleCodeBlock', str]                  

    def __init__(self, target:Variable, module: 'CodeBlock', belongsTo: 'CodeBlock', id: int):
        super().__init__(target, 'module', belongsTo, id)
        self.module = module

    def __str__(self):
        return f"{self.target} = NewModule {self.module if isinstance(self.module, str) else self.module.readable_name}"
        

class NewFunction(New):
    codeBlock: 'FunctionCodeBlock'

    def __init__(self, target:Variable, codeBlock: 'CodeBlock', belongsTo: 'CodeBlock', id: int):
        super().__init__(target, 'function', belongsTo, id)
        self.codeBlock = codeBlock

    def __str__(self):
        return f"{self.target} = NewFunction"

class NewClass(New):
    codeBlock: 'ClassCodeBlock'
    bases: List[Variable]                # variables that points to a class object

    def __init__(self, target:Variable, bases:List[Variable], codeBlock: 'CodeBlock', belongsTo: 'CodeBlock', id: int):
        super().__init__(target, 'class', belongsTo, id)
        self.codeBlock = codeBlock
        self.bases = bases
    
    def __str__(self):
        bases = [str(b) for b in self.bases]
        return f"{self.target} = NewClass ({', '.join(bases)})"
        


class NewBuiltin(New):
    type: str
    value: Any                          # optional, for example the value of str, int, double can be use
    def __init__(self, target:Variable, type: str, value: Any, belongsTo: 'CodeBlock', id: int):
        super().__init__(target, 'builtin', belongsTo, id)
        self.type = type
        self.value = value

    def __str__(self):
        return f"{self.target} = New {self.type}"

class NewStaticMethod(New):
    func: Variable
    def __init__(self, target: Variable, func: Variable, belongsTo: 'CodeBlock', id: int):
        super().__init__(target, 'staticmethod', belongsTo, id)
        self.func = func
    def __str__(self):
         return f"{self.target} = New Static Method({self.func})"

# class NewClassMethod(New):
#     func: Variable
#     def __init__(self, target: Variable, func: Variable, belongsTo: 'CodeBlock', id: int):
#         super().__init__(target, 'classmethod', belongsTo)
#         self.func = func
#     def __str__(self):
#          return f"{self.target} = New Class Method({self.func})"


class NewSuper(New):
    type: Variable
    bound: Variable
    def __init__(self, target: Variable, type: Union[Variable, None], bound: Union[Variable, None],belongsTo: 'CodeBlock', id: int):
        super().__init__(target, 'classmethod', belongsTo, id)
        self.type = type
        self.bound = bound
    def __str__(self):
         return f"{self.target} = New Super({self.type if self.type else ''}{f', {self.bound}' if self.bound else ''})"

# Important: calling a class object equarls to creating an instance! 
# adding a function/module code block should add all class code block inside!
class Call(IRStmt):
    target: Variable               
    callee: Variable
    posargs: List[Variable]
    kwargs: Dict[str, Variable]

    def __init__(self, target: Variable, callee: Variable, args: List[Variable], keywords: Dict[str, Variable], belongsTo: 'CodeBlock', id: int):
        super().__init__(belongsTo, id)
        self.target = target
        self.callee = callee
        self.posargs = [None] * len(args)
        self.posargs = args
        self.kwargs = keywords
    
    def __str__(self):
        args = [str(arg) for arg in self.posargs]
        kws = [f"{kw}={arg}" for kw, arg in self.kwargs.items()]
        args += kws
        return f"{self.target} = Call {self.callee} ({', '.join(args)})"
        

class DelAttr(IRStmt):
    var: Variable
    attr: str
    
    def __init__(self, v: Variable, attr: str, belongsTo: 'CodeBlock', id: int):
        super().__init__(belongsTo, id)
        self.var = v
        self.attr = attr

    def __str__(self):
        return f"Del {self.var}.{self.attr}"
        

# TODO: GET_ITEM(from, index), SET_ITEM(to, index), to support list, tuple, set, dict
# TODO: GET_ITER(v)

