from typing import Any, List, Set, Union

from ..CSPTA.Context import emptyContextChain

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
        return hash(self.codeBlock.qualified_name)
    def __init__(self, codeBlock: ModuleCodeBlock):
        self.codeBlock = codeBlock
    def __str__(self):
        return f"Module({self.codeBlock.qualified_name})"
    def __repr__(self):
        return self.__str__()
    def getModuleName(self):
        return self.codeBlock.qualified_name


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

class InstanceMethodObject(Object):
    selfObj: InstanceObject
    func: FunctionObject
    def __eq__(self, other):
        return isinstance(other, InstanceMethodObject) and self.selfObj == other.selfObj and self.func == other.func
    def __hash__(self):
        return hash((self.selfObj, self.func))
    def __init__(self, selfObj, func):
        self.selfObj = selfObj
        self.func = func
    def __str__(self):
        return f"InstanceMethod(self: {self.selfObj}, {self.func})"
    def __repr__(self):
        return self.__str__()


class ClassMethodObject(Object):
    classObj: InstanceObject
    func: FunctionObject
    def __eq__(self, other):
        return isinstance(other, ClassMethodObject) and self.classObj == other.classObj and self.func == other.func
    def __hash__(self):
        return hash((self.classObj, self.func))
    def __init__(self, classObj, func):
        self.classObj = classObj
        self.func = func
    def __str__(self):
        return f"ClassMethod(cls: {self.classObj}, {self.func})"
    def __repr__(self):
        return self.__str__()


class StaticMethodObject(Object):
    
    func: FunctionObject
    def __eq__(self, other):
        return isinstance(other, ClassMethodObject) and self.func == other.func
    def __hash__(self):
        return hash(self.func)
    def __init__(self, func):
        self.func = func
    def __str__(self):
        return f"StaticMethod({self.func})"
    def __repr__(self):
        return self.__str__()


class SuperObject(Object):
    type: ClassObject
    bound: Union[ClassObject, InstanceObject]
    def __eq__(self, other):
        return isinstance(other, SuperObject) and self.type == other.type and self.bound == other.bound
    def __hash__(self):
        return hash((self.type, self.bound))
    def __init__(self, type, bound):
        self.type = type
        self.bound = bound
    def __str__(self):
        return f"Super({self.type}, {self.bound})"
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
        cb = self.alloc_site.belongsTo
        return f"Instance {self.type.getCodeBlock().qualified_name}({cb.qualified_name}-{cb.stmts.index(self.alloc_site)})"
    def __repr__(self):
        return self.__str__()
    

class CIBuiltinObject(CIObject, BuiltinObject):
    alloc_site: NewBuiltin

    def getType(self):
        return self.alloc_site.type
    def getValue(self):
        return self.alloc_site.value
    def __str__(self):
        v = self.getValue() 
        if(v is not None):
            return f"Builtin({v})"
        cb = self.alloc_site.belongsTo
        return f"Builtin {self.getType()}({cb.qualified_name}-{cb.stmts.index(self.alloc_site)})"
    def __repr__(self):
        return self.__str__()

class FakeObject(ModuleObject, ClassObject, FunctionObject):
    class NoMore(Exception):
        pass

    class FakeCodeBlock(ClassCodeBlock, FunctionCodeBlock):
        def __init__(self, name, enclosing):
            if(enclosing == None):
                super(FunctionCodeBlock, self).__init__(name, None, fake=False)
                self.module = self
            else:
                super().__init__(name, enclosing, fake=False)
            self.scopeLevel = 0
    
            

    codeBlock: CodeBlock
    def __eq__(self, other):
        return isinstance(other, FakeObject) and self.codeBlock.qualified_name == other.codeBlock.qualified_name
    def __init__(self, name: str, enclosing: 'FakeObject'):
        if(enclosing):
            depth = 0
            curr = enclosing.codeBlock
            while(curr):
                depth += 1
                curr = curr.enclosing
            if(depth > 5):
                raise FakeObject.NoMore
        self.codeBlock = FakeObject.FakeCodeBlock(name, enclosing and enclosing.codeBlock)
        self.ctxChain = emptyContextChain()
    def __str__(self):
        return f"Fake {self.codeBlock.qualified_name}"
    def __hash__(self):
        return hash(self.codeBlock.qualified_name)
    def getCodeBlock(self) -> CodeBlock:
        return self.codeBlock

    def getBases(self) -> List[VarPtr]:
        return []

    def getAttributes(self) -> Set[str]:
        return set()

    def getModuleName(self):
        return self.codeBlock.qualified_name
    
    