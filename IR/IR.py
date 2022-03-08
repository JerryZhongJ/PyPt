from distutils.command.build_scripts import first_line_re
from typing import Dict, KeysView, List
from typing_extensions import Self


class Variable:
    name: str                           # variable name
    belongsTo: 'CodeBlock'                # CodeBlock to which it belongs

    def __str__(self):
        return self.name

    def __init__(self, name: str, belongsTo: 'CodeBlock'):
        self.name = name
        self.belongsTo = belongsTo

class IR:
    belongsTo: 'CodeBlock'                 # CodeBlock to which this IR belongs
    startLine:int
    startCol: int
    endLine: int
    endCol: int



class Assign(IR):
    target: Variable
    source: Variable

    def __init__(self, target: Variable, source: Variable):
        self.target = target
        self.source = source

    def __str__(self):
        return str(self.target) + " = " + str(self.source)


# target.fieldName = source
class Store(IR):
    target: Variable
    source: Variable
    fieldName: str

    def __init__(self, target: Variable, fieldName: str, source: Variable):
        self.target = target
        self.source = source
        self.fieldName = fieldName

    def __str__(self):
        return str(self.target) + "." + self.fieldName + " = " + str(self.source)

# target = source.fieldName
class Load(IR):
    target: Variable
    source: Variable
    fieldName: str

    def __init__(self, target: Variable, source: Variable, fieldName: str):
        self.target = target
        self.source = source
        self.fieldName = fieldName

    def __str__(self):
        return str(self.target) + " = " + str(self.source) + "." + self.fieldName

# target = New ...
class New(IR):
    target: Variable
    objType:str                             # module, function, class, method, instance, builtin

    def __init__(self, target: Variable, objType: str):
        self.target = target
        self.objType = objType

class NewFunction(New):
    codeBlock: 'CodeBlock'

    def __init__(self, target:Variable, codeBlock: 'CodeBlock'):
        super().__init__(self, target, 'function')
        self.codeBlock = codeBlock

class NewClass(New):
    codeBlock: 'CodeBlock'
    base: List[Variable]                # variables that points to a class object
    def __init__(self, target:Variable, codeBlock: 'CodeBlock'):
        super().__init__(self, target, 'class')
        self.codeBlock = codeBlock

class NewInstance(New):
    codeBlock: 'CodeBlock'
    classType: Variable                 # a variable points to a class object
    def __init__(self, target:Variable, codeBlock: 'CodeBlock'):
        super().__init__(self, target, 'class')
        self.codeBlock = codeBlock

class Call(IR):
    resVariable: Variable
    callee: Variable
    args: list
    keywords: map

    def __init__(self, callee: Variable, args: list, keywords: map):
        self.callee = callee
        self.args = args
        self.keywords = keywords

class CodeBlock:
    name: str
    moduleName: str                             # a unique description of the module to which this code block belongs
    type: str                                   # module, class, function
    IRs = []
    enclosing: 'CodeBlock'                        # reference to enclosing scope

    localVariables = {}                         # a map from name to variable
    globalNames = []                            # a list of names declared global
    # nonlocalNames = []                          # a list of names declared nonlocal
    scopeLevel: int                             # used when type = "function", showing how deep a function is defined, startging with 0
                                                # here, class code block and module code block is ignored in "depth"

    globalVariable: Variable                    # refer to $global
    thisClassVariable: Variable                 # refer to $thisClass

    # posargs and kwargs both store all the arguments
    # using two data structure is for convenience 
    posargs: List[Variable] = []
    kwargs: Dict[str, Variable] = {}
    

    def __init__(self, moduleName:str, type: str, name: str, enclosing: 'CodeBlock'):
        self.moduleName = moduleName
        self.name = name
        self.type = type
        if(enclosing.type != "function"):
            self.enclosing = enclosing.enclosing
            if(self.enclosing != None):
                self.scopeLevel = enclosing.scopeLevel + 1
            else:
                self.scopeLevel = 0

        self.globalVariable = Variable("$global", self)
        if(type == "class"):
            self.thisClassVariable = Variable("$thisClass", self)


    def addIR(self, ir: IR):
        ir.belongsTo = self
        self.IRs.append(ir)
    
    def __str__(self):
        des = self.name + ":\n"
        for ir in self.IRs:
            des += str(ir) + "\n"
        return des
