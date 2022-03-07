from distutils.command.build_scripts import first_line_re
from typing import KeysView
from typing_extensions import Self


class Variable:
    name = ""                       # a simple description of this variable
    belongsTo = None                # CodeBlock to which it belongs

    def __str__(self):
        return self.name

    def __init__(self, name: str, belongsTo: CodeBlock):
        self.name = name
        self.belongsTo = belongsTo

class IR:
    belongsTo = None                # CodeBlock to which this IR belongs


class Assign(IR):
    target = None
    source = None

    def __init__(self, target: Variable, source: Variable):
        self.target = target
        self.source = source

    def __str__(self):
        return str(self.target) + " = " + str(self.source)


# target.fieldName = source
class Store(IR):
    target = None
    source = None
    fieldName = ""

    def __init__(self, target: Variable, fieldName: str, source: Variable):
        self.target = target
        self.source = source
        self.fieldName = fieldName

    def __str__(self):
        return str(self.target) + "." + self.fieldName + " = " + str(self.source)

# target = source.fieldName
class Load(IR):
    target = None
    source = None
    fieldName = ""

    def __init__(self, target: Variable, source: Variable, fieldName: str):
        self.target = target
        self.source = source
        self.fieldName = fieldName

    def __str__(self):
        return str(self.target) + " = " + str(self.source) + "." + self.fieldName

# target = New ...
class New(IR):
    target = None
    objType = ""                    # module, function, class, method, instance, builtin
    args = None                     # extra infomation to describe this object 

    def __init__(self, target: Variable, objType: str, args: tuple):
        self.target = target
        self.objType = objType
        self.args = args

    def __str__(self):
        des = str(self.target) + " = new " + self.objType + "("
        for arg in self.args:
            des += str(arg) + ", "
        des = des[:-2] + ")"
        return des

class Call(IR):
    callee = None
    args = None
    keywords = None
    
    def __init__(self, callee: Variable, args: list, keywords: map):
        self.callee = callee
        self.args = args
        self.keywords = keywords

class CodeBlock:
    name = ""
    moduleName = ""                 # a unique description of the module to which this code block belongs
    type = ""                       # module, class, function
    IRs = []

    enclosing = None                # reference to enclosing scope
    localVariables = {}             # a map from name to variable
    globalNames = []                # a list of names declared global
    nonlocalNames = []              # a list of names declared nonlocal
    scopeLevel = 0                  # used when type = "function", showing how deep a function is defined, startging with 0
                                    # here, class code block and module code block is ignored in "depth"

    globalVariable = None          # refer to $global
    thisClassVariable = None        # refer to $thisClass


    def __init__(self, name: str, type: str):
        self.name = name
        self.type = type
        globalVariable = Variable(name + ":$global", self)
        if(type == "class"):
            thisClassVariable = Variable(name + ":$thisClass", self)

    def addIR(self, ir: IR):
        ir.belongsTo = self
        self.IRs.append(ir)
    
    def __str__(self):
        des = self.name + ":\n"
        for ir in self.IRs:
            des += str(ir) + "\n"
        return des
