
from typing import Dict, List, Set



class Variable:
    name: str                           # variable name
    belongsTo: 'CodeBlock'                # CodeBlock to which it belongs
    # TODO: implement this
    qualified_name: str

    def __str__(self):
        return self.qualified_name

    def __init__(self, name: str, belongsTo: 'CodeBlock'):
        self.name = name
        self.belongsTo = belongsTo
        self.qualified_name = f"{name}@{belongsTo.qualified_name}"

class IR:
    belongsTo: 'CodeBlock'                 # CodeBlock to which this IR belongs
    startLine:int
    startCol: int
    endLine: int
    endCol: int

    def __init__(self, belongsTo: 'CodeBlock'):
        self.belongsTo = belongsTo
        belongsTo.IRs.append(self)


class Assign(IR):
    target: Variable
    source: Variable

    def __init__(self, target: Variable, source: Variable, belongsTo: 'CodeBlock'):
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

    def __init__(self, target: Variable, field: str, source: Variable, belongsTo: 'CodeBlock'):
        super().__init__(belongsTo)
        self.target = target
        self.source = source
        self.field = field

    def __str__(self):
        return  f"{self.target} .{self.field} = {self.source}"

# target = source.fieldName
class Load(IR):
    target: Variable
    source: Variable
    field: str

    def __init__(self, target: Variable, source: Variable, field: str, belongsTo: 'CodeBlock'):
        super().__init__(belongsTo)
        self.target = target
        self.source = source
        self.field = field

    def __str__(self):
        return f"{self.target} = {self.source} .{self.field}"

# target = New ...
class New(IR):
    target: Variable
    objType:str                             # module, function, class, method, instance, builtin

    def __init__(self, target: Variable, objType: str, belongsTo: 'CodeBlock'):
        super().__init__(belongsTo)
        self.target = target
        self.objType = objType

class NewFunction(New):
    codeBlock: 'CodeBlock'

    def __init__(self, target:Variable, codeBlock: 'CodeBlock', belongsTo: 'CodeBlock'):
        super().__init__(target, 'function', belongsTo)
        self.codeBlock = codeBlock

    def __str__(self):
        return f"{self.target} = new function"

class NewClass(New):
    codeBlock: 'CodeBlock'
    base: List[Variable]                # variables that points to a class object

    def __init__(self, target:Variable, codeBlock: 'CodeBlock', belongsTo: 'CodeBlock'):
        super().__init__(target, 'class', belongsTo)
        self.codeBlock = codeBlock

    def __str__(self):
        return f"{self.target} = new class"

class NewInstance(New):
    codeBlock: 'CodeBlock'
    classType: Variable                 # a variable points to a class object

    def __init__(self, target:Variable, codeBlock: 'CodeBlock', belongsTo: 'CodeBlock'):
        super().__init__(target, 'instance', belongsTo)
        self.codeBlock = codeBlock

class Call(IR):
    resVariable: Variable
    callee: Variable
    args: List[Variable]
    keywords: Dict[str, Variable]

    def __init__(self, callee: Variable, args: List[Variable], keywords: Dict[str, Variable], belongsTo: 'CodeBlock'):
        super().__init__(belongsTo)
        self.callee = callee
        self.args = args
        self.keywords = keywords

