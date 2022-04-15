from typing import Any, List, Set

from .Pointers import VarPtr

from ..IR.Stmts import IRStmt, Call, NewBuiltin, NewClass, NewFunction
from ..IR.CodeBlock import ClassCodeBlock, CodeBlock, FunctionCodeBlock, ModuleCodeBlock

# Object is the representation of object entity, and should not contain any analysis data
# Object's attributes' value remain static during the analysis
class Object:
    pass

class ModuleObject(Object):
    codeBlock: ModuleCodeBlock
    def __eq__(self, other):
        return isinstance(other, ModuleObject) and other.codeBlock == self.codeBlock
    def __hash__(self):
        return hash(self.moduleName)
    def __init__(self, codeBlock: ModuleCodeBlock):
        self.codeBlock
    def getModuleName(self):
        return self.codeBlock.moduleName


class ConstObject(Object):
    value: Any
    def __eq__(self, other):
        return isinstance(other, ConstObject) and self.value == other.value
    def __hash__(self):
        return hash(self.value)
    def __init__(self, value):
        self.value = value

class AllocationSiteObject(Object):
    alloc_site: IRStmt
    def __eq__(self, other):
        return isinstance(other, AllocationSiteObject) and self.alloc_site == other.alloc_site
    def __hash__(self):
        return hash(self.alloc_site)
    def __init__(self, alloc_site):
        self.alloc_site = alloc_site
    

class FunctionObject(AllocationSiteObject):
    alloc_site: NewFunction
    def getCodeBlock(self) -> FunctionCodeBlock:
        return self.alloc_site.codeBlock

class ClassObject(AllocationSiteObject):
    alloc_site: NewClass
    def getCodeBlock(self) -> ClassCodeBlock:
        return self.alloc_site.codeBlock
    def getBases(self) -> List[VarPtr]:
        return [VarPtr(base) for base in self.alloc_site.bases]

    def getAttributes(self) -> Set[str]:
        return self.getCodeBlock().attributes


class InstanceObject(AllocationSiteObject):
    alloc_site: Call
    def getType(self):
        return VarPtr(self.alloc_site.callee)

    

class BuiltinObject(AllocationSiteObject):
    alloc_site: NewBuiltin
    
    

class MethodObject(Object):
    selfObj: InstanceObject
    func: FunctionObject
    def __eq__(self, other):
        return isinstance(other, MethodObject) and self.selfObj == other.selfObj and self.func == other.func
    def __hash__(self):
        return hash((self.selfObj, self.func))
    def __init__(self, selfObj, func):
        self.selfObj = selfObj
        self.func = func