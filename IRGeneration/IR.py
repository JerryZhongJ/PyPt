
from typing import Any, Dict, List
from CodeBlock import CodeBlock
class Variable:
    name: str                           # variable name
    belongsTo: CodeBlock                # CodeBlock to which it belongs
    # TODO: implement this
    qualified_name: str
    isTmp: bool
    def __str__(self):
        return self.qualified_name

    def __init__(self, name: str, belongsTo: CodeBlock, temp=False):
        self.name = name
        self.belongsTo = belongsTo
        self.qualified_name = f"<{belongsTo.qualified_name}>{name}"
        self.isTmp = temp

class IR:
    belongsTo: CodeBlock                 # CodeBlock to which this IR belongs
    startLine:int
    startCol: int
    endLine: int
    endCol: int

    def __init__(self, belongsTo: CodeBlock):
        self.belongsTo = belongsTo
        belongsTo.IRs.append(self)


class Assign(IR):
    target: Variable
    source: Variable

    def __init__(self, target: Variable, source: Variable, belongsTo: CodeBlock):
        super().__init__(belongsTo)
        self.target = target
        self.source = source

    def __str__(self):
        return f"{self.target} = {self.source}"


# target.fieldName = source
class Store(IR):
    target: Variable
    source: Variable
    field: str

    def __init__(self, target: Variable, field: str, source: Variable, belongsTo: CodeBlock):
        super().__init__(belongsTo)
        self.target = target
        self.source = source
        self.field = field

    def __str__(self):
        return  f"{self.target}.{self.field} = {self.source}"

# target = source.fieldName
class Load(IR):
    target: Variable
    source: Variable
    field: str

    def __init__(self, target: Variable, source: Variable, field: str, belongsTo: CodeBlock):
        super().__init__(belongsTo)
        self.target = target
        self.source = source
        self.field = field

    def __str__(self):
        return f"{self.target} = {self.source}.{self.field}"

# target = New ...
class New(IR):
    target: Variable
    objType:str                             # module, function, class, method, instance, builtin

    def __init__(self, target: Variable, objType: str, belongsTo: CodeBlock):
        super().__init__(belongsTo)
        self.target = target
        self.objType = objType

class NewFunction(New):
    codeBlock: CodeBlock

    def __init__(self, target:Variable, codeBlock: CodeBlock, belongsTo: CodeBlock):
        super().__init__(target, 'function', belongsTo)
        self.codeBlock = codeBlock

    def __str__(self):
        return f"{self.target} = NewFunction"

class NewClass(New):
    codeBlock: CodeBlock
    base: List[Variable]                # variables that points to a class object

    def __init__(self, target:Variable, base:List[Variable], codeBlock: CodeBlock, belongsTo: CodeBlock):
        super().__init__(target, 'class', belongsTo)
        self.codeBlock = codeBlock
        self.base = base

    def __str__(self):
        des = f"{self.target} = NewClass("
        for p in self.base:
            des += f"{p}, "
        des = des[:-2] + ")"
        return des

class NewInstance(New):
    classType: Variable                 # a variable points to a class object

    def __init__(self, target:Variable, classType: Variable, belongsTo: CodeBlock):
        super().__init__(target, 'instance', belongsTo)
        self.classType = classType

    def __str__(self):
        return f"{self.target} = New {self.classType}"

class NewBuiltin(New):
    type: str
    value: Any                          # optional, for example the value of str, int, double can be use
    def __init__(self, target:Variable, type: str, belongsTo: CodeBlock, value: Any=None):
        super().__init__(target, 'builtin', belongsTo)
        self.type = type
        self.value = value

    def __str__(self):
        return f"{self.target} = New {self.type}" + " ({self.value})" if self.value else ""

class Call(IR):
    res: Variable               
    callee: Variable
    args: List[Variable]
    keywords: Dict[str, Variable]

    def __init__(self, res: Variable, callee: Variable, args: List[Variable], keywords: Dict[str, Variable], belongsTo: CodeBlock):
        super().__init__(belongsTo)
        self.res = res
        self.callee = callee
        self.args = args
        self.keywords = keywords

    def __str__(self):
        des += f"{self.res} = Call {self.callee}("
        for arg in self.args:
            des += f"{arg}, "

        for kw, arg in self.keywords:
            des += f"{kw}={arg}, "

        des = des[:-2] + ")"
        return des


