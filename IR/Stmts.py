
from typing import Any, Dict, List, Tuple, Union
import typing

if typing.TYPE_CHECKING:
    from .CodeBlock import CodeBlock, ClassCodeBlock, FunctionCodeBlock, ModuleCodeBlock


class Variable:
    name: str                           # variable name
    belongsTo: 'CodeBlock'                # 'CodeBlock' to which it belongs
    # TODO: implement this
    qualified_name: str
    isTmp: bool

    def __str__(self):
        return self.qualified_name

    def __repr__(self):
        return f"Variable: {self.qualified_name}"

    def __init__(self, name: str, belongsTo: 'CodeBlock', temp=False):
        self.name = name
        self.belongsTo = belongsTo
        self.qualified_name = f"<{belongsTo.qualified_name}>{name}"
        self.isTmp = temp
        

    def __hash__(self):
        return hash((self.belongsTo, self.name))

class IRStmt:
    belongsTo: 'CodeBlock'                 # 'CodeBlock' to which this IR belongs
    srcPos: Tuple[int]

    def __init__(self, belongsTo: 'CodeBlock'):
        self.belongsTo = belongsTo
        belongsTo.stmts.append(self)

    def __repr__(self):
        return f"IRStmt: {str(self)}"

    def __hash__(self):
        return hash(str(self))
    


class Assign(IRStmt):
    target: Variable
    source: Variable

    def __init__(self, target: Variable, source: Variable, belongsTo: 'CodeBlock'):
        super().__init__(belongsTo)
        self.target = target
        self.source = source

    def __str__(self):
        return f"{self.target} = {self.source}"


# target.attr = source
class SetAttr(IRStmt):
    target: Variable
    source: Variable
    attr: str

    def __init__(self, target: Variable, attr: str, source: Variable, belongsTo: 'CodeBlock'):
        super().__init__(belongsTo)
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

    def __init__(self, target: Variable, source: Variable, attr: str, belongsTo: 'CodeBlock'):
        super().__init__(belongsTo)
        self.target = target
        self.source = source
        self.attr = attr

    def __str__(self):
        return f"{self.target} = {self.source}.{self.attr}"

# target = New ...
class New(IRStmt):
    target: Variable
    objType:str                             # module, function, class, method, instance, builtin

    def __init__(self, target: Variable, objType: str, belongsTo: 'CodeBlock'):
        super().__init__(belongsTo)
        self.target = target
        self.objType = objType

        
class NewModule(New):
    codeBlock: 'ModuleCodeBlock'                  

    def __init__(self, target:Variable, codeBlock: 'CodeBlock', belongsTo: 'CodeBlock'):
        super().__init__(target, 'module', belongsTo)
        self.codeBlock = codeBlock

    def __str__(self):
        return f"{self.target} = NewModule {self.codeBlock.name if self.codeBlock else ''}"

class NewFunction(New):
    codeBlock: 'FunctionCodeBlock'

    def __init__(self, target:Variable, codeBlock: 'CodeBlock', belongsTo: 'CodeBlock'):
        super().__init__(target, 'function', belongsTo)
        self.codeBlock = codeBlock

    def __str__(self):
        return f"{self.target} = NewFunction"

class NewClass(New):
    codeBlock: 'ClassCodeBlock'
    bases: List[Variable]                # variables that points to a class object

    def __init__(self, target:Variable, bases:List[Variable], codeBlock: 'CodeBlock', belongsTo: 'CodeBlock'):
        super().__init__(target, 'class', belongsTo)
        self.codeBlock = codeBlock
        self.bases = bases
    
    def __str__(self):
        bases = [str(b) for b in self.bases]
        return f"{self.target} = NewClass ({', '.join(bases)})"
        


class NewBuiltin(New):
    type: str
    value: Any                          # optional, for example the value of str, int, double can be use
    def __init__(self, target:Variable, type: str, belongsTo: 'CodeBlock', value: Any=None):
        super().__init__(target, 'builtin', belongsTo)
        self.type = type
        self.value = value

    def __str__(self):
        return f"{self.target} = New {self.type}" + (f" ({self.value})" if self.value is not None else "")

class NewStaticMethod(New):
    func: Variable
    def __init__(self, target: Variable, func: Variable, belongsTo: 'CodeBlock'):
        super().__init__(target, 'staticmethod', belongsTo)
        self.func = func
    def __str__(self):
         return f"{self.target} = New Static Method({self.func})"

class NewClassMethod(New):
    func: Variable
    def __init__(self, target: Variable, func: Variable, belongsTo: 'CodeBlock'):
        super().__init__(target, 'classmethod', belongsTo)
        self.func = func
    def __str__(self):
         return f"{self.target} = New Class Method({self.func})"


class NewSuper(New):
    type: Variable
    bound: Variable
    def __init__(self, target: Variable, type: Union[Variable, None], bound: Union[Variable, None],belongsTo: 'CodeBlock'):
        super().__init__(target, 'classmethod', belongsTo)
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

    def __init__(self, target: Variable, callee: Variable, args: List[Variable], keywords: Dict[str, Variable], belongsTo: 'CodeBlock'):
        super().__init__(belongsTo)
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
    
    def __init__(self, v: Variable, attr: str, belongsTo: 'CodeBlock'):
        super().__init__(belongsTo)
        self.var = v
        self.attr = attr

    def __str__(self):
        return f"Del {self.var}.{self.attr}"
        

# TODO: GET_ITEM(from, index), SET_ITEM(to, index), to support list, tuple, set, dict
# TODO: GET_ITER(v)

