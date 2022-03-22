from typing import Dict, List, Set
import IR


class CodeBlock:
    name: str
    # TODO: implement this
    qualified_name: str
    # type: str                                   # module, class, function
    IRs: List[IR.IR]
    enclosing: 'CodeBlock'                          # reference to enclosing scope, this is used in name resolution. 
                                                    # Only function code block is remained

    globalVariable: IR.Variable                    # $global, all code blocks in a module share a single $global variable 
    

    def __init__(self, name: str, enclosing: 'CodeBlock'):
        self.name = name
        self.IRs = []
        
        if(enclosing is not None and not isinstance(enclosing, FunctionCodeBlock)):
            self.enclosing = enclosing.enclosing
        else:
            self.enclosing = enclosing

        if(self.enclosing is not None):
            self.scopeLevel = enclosing.scopeLevel + 1
        else:
            self.scopeLevel = 0
    
    def __str__(self):
        des = f"{self.qualified_name} ({len(self.IRs)} lines):\n"
        codeBlocks = []
        for ir in self.IRs:
            des += f"{ir}\n"
            if(isinstance(ir, IR.New)):
                codeBlocks.append(ir.codeBlock)
        
        for codeBlock in codeBlocks:
            des += f"\n{codeBlock}"
        return des

class ModuleCodeBlock(CodeBlock):
    moduleName: str

    def __init__(self, moduleName:str):
        super().__init__("", None)
        self.moduleName = moduleName
        self.qualified_name = moduleName
        self.globalVariable = IR.Variable("$global", self)

class FunctionCodeBlock(CodeBlock):
    scopeLevel: int                                     # showing how deep a function is defined, startging with 0
    localVariables: Dict[str, IR.Variable]                 # a map from name to variable
    # posargs and kwargs both store all the arguments
    # using two data structure is for convenience 
    posargs: List[IR.Variable]
    kwargs: Dict[str, IR.Variable]
    declaredGlobal: Set[str]                            # a list of names declared global
    returnVariable: IR.Variable
    def __init__(self, name: str, enclosing:'CodeBlock'):
        super().__init__(name, enclosing)
        self.qualified_name = f"{enclosing.qualified_name}.{name}"
        self.globalVariable = enclosing.globalVariable
        self.localVariables = {}
        self.declaredGlobal = set()
        self.posargs = []
        self.kwargs = {}
        self.returnVariable = IR.Variable("$ret", self)


class ClassCodeBlock(CodeBlock):
    thisClassVariable: IR.Variable                         # refer to $thisClass
    declaredGlobal: Set[str]                            # a list of names declared global
    attributes: Set[str]
    def __init__(self, name:str, enclosing:'CodeBlock'):
        super().__init__(name, enclosing)
        self.qualified_name = f"{enclosing.qualified_name}.{name}"
        self.globalVariable = enclosing.globalVariable
        self.thisClassVariable = IR.Variable("$thisClass", self)