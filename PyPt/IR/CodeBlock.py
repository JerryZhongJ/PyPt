from typing import Dict, List, Set, Union
import typing
from .IRStmts import IRStmt, NewClass, NewFunction, Variable
import os

if typing.TYPE_CHECKING:
    from .ModuleCodeBlock import ModuleCodeBlock


class CodeBlock:
    module: 'ModuleCodeBlock'
    qualified_name: str
    id: str
    stmts: List[IRStmt]
    enclosing: 'CodeBlock'                          # reference to enclosing scope, this is used in name resolution. 
                                                    # Only function code block is remained
    scopeLevel: int                             # indicate that how many context is needed for this codeblock
    fake: bool                                  # this mean if this codeblock really exist in the source code, or it's just made up

    
    def __init__(self, name: str, enclosing: 'CodeBlock', fake=False):
        # self.name = name
        if(enclosing):
            self.qualified_name = f"{enclosing.qualified_name}.{name}"
        else:
            self.qualified_name = name
        self.stmts = []
        self.enclosing = enclosing
        self.fake = fake
        self.newID = 0
        self.newTmp = 0

    def addIR(self, ir:IRStmt):
        ir.belongsTo = self
        self.stmts.append(ir)

    def removeIR(self, ir:IRStmt):
        self.stmts.remove(ir)

    def getNewID(self):
        tmp = self.newID
        self.newID += 1
        return tmp

    def newTmpVariable(self) -> Variable:
        name = f"$t{self.newTmp}"
        self.newTmp += 1
        tmp = Variable(name, self, temp=True)
        return tmp
    
    def dump(self, rootDirectory: str):
        moduleName = self.module.qualified_name
        path = moduleName.replace(".", "/")
        path = os.path.join(rootDirectory, path)
        if(not os.path.exists(path)):
            os.makedirs(path)
            
        filename = self.qualified_name[len(moduleName):] + ".ir"
        path = os.path.join(path, filename)
        with open(path, "w") as f:
            for stmt in self.stmts:
                print(str(stmt), file=f)
                if(isinstance(stmt, NewClass) or isinstance(stmt, NewFunction)):
                    stmt.codeBlock.dump(rootDirectory)
    
    def __eq__(self, other):
        return isinstance(other, CodeBlock) and self.id == other.id
        
    def __hash__(self):
        return hash(self.id)

    def __repr__(self):
        return f"CodeBlock: {self.id}"
