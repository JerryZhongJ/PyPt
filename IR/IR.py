
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

class CodeBlock:
    name: str
    moduleName: str                             # a unique description of the module to which this code block belongs
    # TODO: implement this
    qualified_name: str
    type: str                                   # module, class, function
    IRs: List[IR]
    enclosing: 'CodeBlock'                          # reference to enclosing scope, this is used in name resolution. 
                                                    # Only function code block is remained

    localVariables: Dict[str, Variable]                         # a map from name to variable
    globalNames: Set[str]                            # a list of names declared global
    # nonlocalNames = []                          # a list of names declared nonlocal
    scopeLevel: int                             # used when type = "function", showing how deep a function is defined, startging with 0
                                                # here, class code block and module code block is ignored in "depth"

    globalVariable: Variable                    # $global, all code blocks in a module share a single $global variable 
    thisClassVariable: Variable                 # refer to $thisClass

    # posargs and kwargs both store all the arguments
    # using two data structure is for convenience 
    posargs: List[Variable]
    kwargs: Dict[str, Variable]
    

    def __init__(self, moduleName:str, type: str, name: str, enclosing: 'CodeBlock'):
        self.moduleName = moduleName
        self.name = name
        self.type = type
        self.IRs = []
        self.localVariables = {}
        self.globalNames = set()

        if(type == "module"):
            self.qualified_name = moduleName
            self.globalVariable = Variable("$global", self)
        else:
            self.qualified_name = f"{enclosing.qualified_name}.{name}"
            self.globalVariable = enclosing.globalVariable
            
        if(type == "class"):
            self.thisClassVariable = Variable("$thisClass", self)

        if(type == "function"):
            self.posargs = []
            self.kwargs = {}

        if(enclosing != None and enclosing.type != "function"):
            self.enclosing = enclosing.enclosing
            if(self.enclosing != None):
                self.scopeLevel = enclosing.scopeLevel + 1
            else:
                self.scopeLevel = 0
        else:
            self.enclosing = enclosing
    
    def __str__(self):
        des = f"{self.qualified_name} ({len(self.IRs)} lines):\n"
        codeBlocks = []
        for ir in self.IRs:
            des += f"{ir}\n"
            if(isinstance(ir, New)):
                codeBlocks.append(ir.codeBlock)
        
        for codeBlock in codeBlocks:
            des += f"\n{codeBlock}"
        return des
