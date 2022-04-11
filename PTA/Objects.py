from typing import Any

from PTA.Pointers import VarPtr

from ..IRGeneration.IR import IR
from ..IRGeneration.CodeBlock import ClassCodeBlock, CodeBlock, FunctionCodeBlock
class Object:
    pass

class ModuleObject(Object):
    moduleName: str
    codeBlock: CodeBlock
    def __eq__(self, other):
        return isinstance(other, ModuleObject) and other.moduleName == self.moduleName
    def __hash__(self):
        return hash(self.moduleName)

class ConstObject(Object):
    value: Any
    def __eq__(self, other):
        return isinstance(other, ConstObject) and self.value == other.value
    def __hash__(self):
        return hash(self.value)

class AllocationSiteObject(Object):
    alloc_site: IR
    def __eq__(self, other):
        return isinstance(other, AllocationSiteObject) and self.alloc_site == other.alloc_site
    def __hash__(self):
        return hash(self.alloc_site)
    

class FunctionObject(AllocationSiteObject):
    codeBlock: FunctionCodeBlock

class ClassObject(AllocationSiteObject):
    codeBlock: ClassCodeBlock
    bases: list[VarPtr]

class InstanceObject(AllocationSiteObject):
    type: ClassObject

class BuiltinObject(AllocationSiteObject):
    type: str

class MethodObject(Object):
    selfObj: InstanceObject
    func: FunctionObject
    def __eq__(self, other):
        return isinstance(other, MethodObject) and self.selfObj == other.selfObj and self.func == other.func
    def __hash__(self):
        return hash((self.selfObj, self.func))