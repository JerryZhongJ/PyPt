from typing import Any, List, Set

from .Pointers import CIVarPtr, VarPtr

from ..IR.Stmts import IRStmt, Call, NewBuiltin, NewClass, NewFunction
from ..IR.CodeBlock import ClassCodeBlock, CodeBlock, FunctionCodeBlock, ModuleCodeBlock

# Object is the representation of object entity, and should not contain any analysis data
# Object's attributes' values should be limited!
class Object:
    pass

class ModuleObject(Object):
    codeBlock: ModuleCodeBlock
    def __eq__(self, other):
        return isinstance(other, ModuleObject) and other.codeBlock == self.codeBlock
    def __hash__(self):
        return hash(self.codeBlock.moduleName)
    def __init__(self, codeBlock: ModuleCodeBlock):
        self.codeBlock = codeBlock
    def getModuleName(self):
        return self.codeBlock.moduleName
    def __str__(self):
        return f"Module({self.codeBlock.moduleName})"
    def __repr__(self):
        return self.__str__()


# class ConstObject(Object):
#     value: Any
#     def __eq__(self, other):
#         return isinstance(other, ConstObject) and self.value == other.value
#     def __hash__(self):
#         return hash(self.value)
#     def __init__(self, value):
#         self.value = value
#     def __str__(self):
#         return f"Const({self.value})"
#     def __repr__(self):
#         return self.__str__()


class ClassObject(Object):
    def getCodeBlock(self) -> ClassCodeBlock:
        pass
    def getBases(self) -> List[VarPtr]:
        pass
    def getAttributes(self) -> Set[str]:
        pass

class FunctionObject(Object):
    def getCodeBlock(self) -> FunctionCodeBlock:
        pass

class InstanceObject(Object):
    type: ClassObject
    def __eq__(self, other):
        return isinstance(other, InstanceObject) and self.type == other.type
    def __hash__(self):
        return hash(self.type)

class BuiltinObject(Object):
    def getType(self) -> str:
        pass

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
    def __str__(self):
        return f"Method(self: {self.selfObj}, {self.func})"
    def __repr__(self):
        return self.__str__()

class CIObject(Object):
    alloc_site: IRStmt
    def __eq__(self, other):
        return isinstance(other, CIObject) and self.alloc_site == other.alloc_site
    def __hash__(self):
        return hash(self.alloc_site)
    def __init__(self, alloc_site):
        self.alloc_site = alloc_site

class CIFunctionObject(CIObject, FunctionObject):
    alloc_site: NewFunction
    def getCodeBlock(self) -> FunctionCodeBlock:
        return self.alloc_site.codeBlock
    def __str__(self):
        return f"Function({self.getCodeBlock().qualified_name})"
    def __repr__(self):
        return self.__str__()

class CIClassObject(CIObject, ClassObject):
    alloc_site: NewClass
    def getCodeBlock(self) -> ClassCodeBlock:
        return self.alloc_site.codeBlock
    def getBases(self) -> List[CIVarPtr]:
        return [CIVarPtr(base) for base in self.alloc_site.bases]

    def getAttributes(self) -> Set[str]:
        return self.getCodeBlock().attributes

    def __str__(self):
        return f"Class({self.getCodeBlock().qualified_name})"
    def __repr__(self):
        return self.__str__()


class CIInstanceObject(CIObject, InstanceObject):
    alloc_site: Call
    type: ClassObject
    
    def __hash__(self):
        return CIObject.__hash__(self) ^ InstanceObject.__hash__(self)
    
    def __eq__(self, other):
        return CIObject.__eq__(self, other) and InstanceObject.__eq__(self, other)

    def __init__(self, alloc_site, type):
        self.alloc_site = alloc_site
        self.type = type

    def __str__(self):
        return f"Instance {self.type.getCodeBlock().qualified_name}({self.alloc_site})"
    def __repr__(self):
        return self.__str__()
    

class CIBuiltinObject(CIObject, BuiltinObject):
    alloc_site: NewBuiltin

    def getType(self):
        return self.alloc_site.type

    def __str__(self):
        return f"Builtin({self.alloc_site})"
    def __repr__(self):
        return self.__str__()
    
    