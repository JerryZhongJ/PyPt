from typing import List, Set, Tuple
import typing
if typing.TYPE_CHECKING:
    from . import CSStmt
from .Context import ContextChain

from .CSPointers import CSVarPtr

from ..IR.CodeBlock import ClassCodeBlock, FunctionCodeBlock

from ..PTA.Objects import BuiltinObject, ClassObject, FunctionObject, InstanceObject

from ..IR.Stmts import Call, IRStmt, NewBuiltin, NewClass, NewFunction


    


class CSObject:
    ctxChain: ContextChain
    alloc_site: IRStmt
    def __init__ (self, alloc_site: 'CSStmt'):
        self.alloc_site = alloc_site[1]
        self.ctxChain = alloc_site[0]
    def __eq__(self, other):
        return isinstance(other, CSObject) and self.alloc_site == other.alloc_site and self.ctxChain == other.ctxChain
    def __hash__(self):
        return hash(self.alloc_site)

class CSFunctionObject(CSObject, FunctionObject):
    alloc_site:  NewFunction
    def getCodeBlock(self) -> FunctionCodeBlock:
        return self.alloc_site.codeBlock
    def __str__(self):
        return f"Function({self.getCodeBlock().qualified_name})"
    def __repr__(self):
        return self.__str__()

class CSClassObject(CSObject, ClassObject):
    alloc_site: NewClass
    def getCodeBlock(self) -> ClassCodeBlock:
        return self.alloc_site.codeBlock
    def getBases(self) -> List[CSVarPtr]:
        return [CSVarPtr(self.ctxChain, base) for base in self.alloc_site.bases]

    def getAttributes(self) -> Set[str]:
        return self.getCodeBlock().attributes

    def __str__(self):
        return f"Class({self.getCodeBlock().qualified_name})"
    def __repr__(self):
        return self.__str__()


class CSInstanceObject(CSObject, InstanceObject):
    alloc_site: Call
    type: CSClassObject
    
    def __hash__(self):
        return CSObject.__hash__(self) ^ InstanceObject.__hash__(self)
    
    def __eq__(self, other):
        return CSObject.__eq__(self, other) and InstanceObject.__eq__(self, other)

    def __init__(self, alloc_site, type):
        self.ctxChain = alloc_site[0]
        self.alloc_site = alloc_site[1]
        self.type = type

    def __str__(self):
        # TODO
        return f"Instance {self.type.getCodeBlock().qualified_name}({self.alloc_site})"
    def __repr__(self):
        return self.__str__()
    

class CSBuiltinObject(CSObject, BuiltinObject):
    alloc_site: NewBuiltin

    def getType(self):
        return self.alloc_site.type

    def __str__(self):
        return f"Builtin({self.alloc_site})"
    def __repr__(self):
        return self.__str__()