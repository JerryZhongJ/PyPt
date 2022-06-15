from typing import List, Set, Tuple
import typing

if typing.TYPE_CHECKING:
    from . import CSStmt
from .Context import ContextChain

from .CSPointers import CSVarPtr

from ..IR.ClassCodeBlock import ClassCodeBlock
from ..IR.FunctionCodeBlock import FunctionCodeBlock

from ..PTA.Objects import BuiltinObject, ClassObject, FunctionObject, InstanceObject

from ..IR.IRStmts import Call, IRStmt, NewBuiltin, NewClass, NewFunction


    


class CSObject:
    ctxChain: ContextChain
    alloc_site: IRStmt
    def __init__ (self, cs_alloc_site: 'CSStmt'):
        self.alloc_site = cs_alloc_site[1]
        self.ctxChain = cs_alloc_site[0]
    def __eq__(self, other):
        return isinstance(other, CSObject) and self.alloc_site == other.alloc_site and self.ctxChain == other.ctxChain
    def __hash__(self):
        return hash((self.ctxChain, self.alloc_site))

class CSFunctionObject(CSObject, FunctionObject):
    alloc_site:  NewFunction
    def getCodeBlock(self) -> FunctionCodeBlock:
        return self.alloc_site.codeBlock
    def __str__(self):
        ctxChain_str = ", ".join(["#".join([str(e) for e in ctx if e]) for ctx in self.ctxChain])
        return f"({ctxChain_str})Function({self.getCodeBlock().qualified_name})"
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
        ctxChain_str = ", ".join(["#".join([str(e) for e in ctx if e]) for ctx in self.ctxChain])
        return f"({ctxChain_str})Class({self.getCodeBlock().qualified_name})"
    def __repr__(self):
        return self.__str__()


class CSInstanceObject(CSObject, InstanceObject):
    alloc_site: Call
    type: CSClassObject
    
    def __hash__(self):
        return CSObject.__hash__(self) ^ InstanceObject.__hash__(self)
    
    def __eq__(self, other):
        return CSObject.__eq__(self, other) and InstanceObject.__eq__(self, other)

    def __init__(self, alloc_site: 'CSStmt', type: ClassObject):
        self.ctxChain = alloc_site[0]
        self.alloc_site = alloc_site[1]
        self.type = type

    def __str__(self):
        ctxChain_str = ", ".join(["#".join([str(e) for e in ctx if e]) for ctx in self.ctxChain])
        return f"({ctxChain_str})Instance {self.type.getCodeBlock().qualified_name}({self.alloc_site})"
    def __repr__(self):
        return self.__str__()
    

class CSBuiltinObject(CSObject, BuiltinObject):
    alloc_site: NewBuiltin

    def getType(self):
        return self.alloc_site.type

    def __str__(self):
        ctxChain_str = ", ".join(["#".join([str(e) for e in ctx if e]) for ctx in self.ctxChain])
        return f"({ctxChain_str})Builtin({self.alloc_site})"
    def __repr__(self):
        return self.__str__()