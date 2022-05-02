from typing import Dict, List, Set, Union


from .Stmts import IRStmt, New, NewClass, NewFunction, Variable
import os


class CodeBlock:
    name: str
    moduleName: str
    qualified_name: str
    # type: str                                   # module, class, function
    stmts: List[IRStmt]
    enclosing: 'CodeBlock'                          # reference to enclosing scope, this is used in name resolution. 
                                                    # Only function code block is remained

    globalVariable: Variable                    # $global, all code blocks in a module share a single $global variable 
    scopeLevel: int                             # indicate that how many context is needed for this codeblock
    fake: bool                                  # this mean if this codeblock really exist in the source code, or it's just made up

    def __init__(self, name: str, enclosing: 'CodeBlock', fake=False):
        self.name = name
        self.stmts = []
        if(enclosing is not None):
            self.moduleName = enclosing.moduleName

        if(enclosing is not None and not isinstance(enclosing, FunctionCodeBlock)):
            self.enclosing = enclosing.enclosing
        else:
            self.enclosing = enclosing
        self.fake = fake

    def addIR(self, ir:IRStmt):
        self.stmts.append(ir)

    def removeIR(self, ir:IRStmt):
        self.stmts.remove(ir)
    
    def dump(self, rootDirectory: str):
        path = self.moduleName.replace(".", "/")
        path = os.path.join(rootDirectory, path)
        if(not os.path.exists(path)):
            os.makedirs(path)
            
        filename = self.qualified_name[len(self.moduleName):] + ".ir"
        path = os.path.join(path, filename)
        with open(path, "w") as f:
            for stmt in self.stmts:
                print(str(stmt), file=f)
                if(isinstance(stmt, NewClass) or isinstance(stmt, NewFunction)):
                    stmt.codeBlock.dump(rootDirectory)
                
    def __hash__(self):
        return hash(self.qualified_name)

    def __repr__(self):
        return f"CodeBlock: {self.qualified_name}"

class ModuleCodeBlock(CodeBlock):
    moduleName: str
    # done: bool
    globalNames: Set[str]
    def __init__(self, moduleName:str, fake=False):
        super().__init__("", None, fake)
        self.moduleName = moduleName
        self.qualified_name = moduleName
        self.globalVariable = Variable("$global", self)
        # self.done = False
        self.globalNames = set()
        self.scopeLevel = 0


class FunctionCodeBlock(CodeBlock):
    scopeLevel: int                                     # showing how deep a function is defined, startging with 0
    localVariables: Dict[str, Variable]                 # a map from name to variable
    # posargs and kwargs both store all the arguments
    # using two data structure is for convenience 
    # posonlyargs: List[Variable]
    posargs: List[Variable]
    kwargs: Dict[str, Variable]
    vararg: Variable
    # kwonlyargs: Dict[str, Variable]
    kwarg: Variable
    declaredGlobal: Set[str]                            # a list of names declared global
    returnVariable: Variable
    def __init__(self, name: str, enclosing:'CodeBlock', fake=False):
        super().__init__(name, enclosing, fake)
        self.qualified_name = f"{enclosing.qualified_name}.{name}"
        self.globalVariable = enclosing.globalVariable
        self.localVariables = {}
        self.declaredGlobal = set()
        # self.posonlyargs = []
        self.posargs = []
        self.kwargs = {}
        # self.kwonlyargs = {}
        self.vararg = None
        self.kwarg = None
        self.returnVariable = Variable("$ret", self)
        if(self.enclosing == None):
            self.scopeLevel = 1
        else:
            self.scopeLevel = enclosing.scopeLevel + 1


class ClassCodeBlock(CodeBlock):
    thisClassVariable: Variable                         # refer to $thisClass
    declaredGlobal: Set[str]                            # a list of names declared global
    attributes: Set[str]
    def __init__(self, name:str, enclosing:'CodeBlock', fake=False):
        super().__init__(name, enclosing, fake=False)
        self.qualified_name = f"{enclosing.qualified_name}.{name}"
        self.globalVariable = enclosing.globalVariable
        self.thisClassVariable = Variable("$thisClass", self)
        self.scopeLevel = enclosing.scopeLevel