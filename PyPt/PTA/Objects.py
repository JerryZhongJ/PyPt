from typing import Any, List, Set, Tuple, Union

from tblib import Code
from ..IR.ClassCodeBlock import ClassCodeBlock
from ..IR.CodeBlock import CodeBlock
from ..IR.FunctionCodeBlock import FunctionCodeBlock

from ..IR.ModuleCodeBlock import ModuleCodeBlock

from .Pointers import VarPtr, VarPtr

from ..IR.IRStmts import GetAttr, NewBuiltin, NewClass, NewFunction

# Object's information should remain static as the pta proceeds.
# Objects have loose relation with IR, but contain all the necessary information in the IR, and can be easily exported. 
# That means even without IR, objects can be still represented, and pta can still run. 

class Object:
    id: str
    def __init__(self, objType: str):
        self.objType = objType

    def __str__(self):
        return self.qualified_name if hasattr(self, 'qualified_name') else self.id

    def __eq__(self, other):
        return isinstance(other, Object) and self.id == other.id

    def __hash__(self):
        return hash(self.id) 

    def __repr__(self):
        return self.id

class ModuleObject(Object):
    # codeBlock: ModuleCodeBlock
    qualified_name: str

    def __init__(self, codeBlock: ModuleCodeBlock):
        super().__init__("Module")
        # self.codeBlock = codeBlock
        self.id = f"Module({codeBlock.id})"
        self.qualified_name = codeBlock.qualified_name



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




# class InstanceObject(Object):
#     type: ClassObject
#     def __eq__(self, other):
#         return isinstance(other, InstanceObject) and self.type == other.type
#     def __hash__(self):
#         return hash(self.type)


# class CIObject(Object):
#     alloc_site: IRStmt
    # def __eq__(self, other):
    #     return isinstance(other, CIObject) and self.alloc_site == other.alloc_site
    # def __hash__(self):
    #     return hash(self.alloc_site)
    # def __init__(self, alloc_site):
    #     self.alloc_site = alloc_site

class FunctionObject(Object):
    codeBlock: FunctionCodeBlock    # used 

    # necessary info in IR
    qualified_name: str

    def __init__(self, alloc_site: NewFunction=None, id: str=None, qualified_name: str=None):
        super().__init__("Function")
        if(alloc_site):
            self.codeBlock = alloc_site.codeBlock
            func = self.codeBlock
            self.id = f"Function({func.id})"
            self.qualified_name = func.qualified_name
            self.retVar = VarPtr(func.returnVariable)
            self.posParams = [VarPtr(posarg) for posarg in func.posargs]
            self.kwParams = {kw:VarPtr(kwOnlyParam) for kw, kwOnlyParam in func.kwargs.items()}
            self.varParam = VarPtr(func.vararg) if func.vararg else None
            self.kwParam = VarPtr(func.kwarg) if func.kwarg else None
        else:
            self.id = id
            self.qualified_name = qualified_name
            self.codeBlock = None
            

    
    
class ClassObject(Object):
    # alloc_site: NewClass
    qualified_name: str
    bases: List[VarPtr]
    attributes: List[str]
   
    def __init__(self, alloc_site: NewClass=None, id: str=None, qualified_name: str=None):
        super().__init__("Class")
        if(alloc_site):
            # self.codeBlock = alloc_site.codeBlock
            codeBlock = alloc_site.codeBlock
            self.id = f"Class({codeBlock.id})"
            self.bases = [VarPtr(base) for base in alloc_site.bases]
            self.attributes = codeBlock.attributes
            self.qualified_name = codeBlock.qualified_name
        else:
            assert(id and qualified_name)
            self.id = id
            self.qualified_name = qualified_name
            # self.alloc_site = alloc_site

# class CIInstanceObject(CIObject, InstanceObject):
#     alloc_site: Call
#     type: ClassObject
    
#     def __hash__(self):
#         return CIObject.__hash__(self) ^ InstanceObject.__hash__(self)
    
#     def __eq__(self, other):
#         return CIObject.__eq__(self, other) and InstanceObject.__eq__(self, other)

#     def __init__(self, alloc_site, type):
#         self.alloc_site = alloc_site
#         self.type = type

#     def __str__(self):
#         cb = self.alloc_site.belongsTo
#         return f"Instance {self.type.getCodeBlock().qualified_name}({cb.qualified_name}-{cb.stmts.index(self.alloc_site)})"
#     def __repr__(self):
#         return self.__str__()
    

class BuiltinObject(Object):
    
    def __init__(self, alloc_site):
        self.id = f"{alloc_site.belongsTo.id}.{alloc_site.id})"

# class InstanceMethodObject(Object):
#     selfObj: InstanceObject
#     func: FunctionObject
#     def __eq__(self, other):
#         return isinstance(other, InstanceMethodObject) and self.selfObj == other.selfObj and self.func == other.func
#     def __hash__(self):
#         return hash((self.selfObj, self.func))
#     def __init__(self, selfObj, func):
#         self.selfObj = selfObj
#         self.func = func
#     def __str__(self):
#         return f"InstanceMethod(self: {self.selfObj}, {self.func})"
#     def __repr__(self):
#         return self.__str__()


class ClassMethodObject(Object):
    classObj: ClassObject
    func: FunctionObject
    
    def __init__(self, classObj, func):
        self.classObj = classObj
        self.func = func
        self.id = f"ClassMethod({classObj.id},{func.id})"
    

class StaticMethodObject(Object):
    
    func: FunctionObject
    
    def __init__(self, func):
        self.func = func
        self.id = f"StaticMethod({func.id})"

    

class SuperObject(Object):
    type: ClassObject
    bound: ClassObject
   
    def __init__(self, type, bound):
        self.type = type
        self.bound = bound
        self.id = f"Super({type.id},{bound.id})"
    



class FakeObject(ModuleObject, ClassObject, FunctionObject):
    # class NoMore(Exception):
    #     pass

    # class FakeCodeBlock(ClassCodeBlock, FunctionCodeBlock):
    #     def __init__(self, name, enclosing):
    #         if(enclosing == None):
    #             super(FunctionCodeBlock, self).__init__(name, None, fake=False)
    #             self.module = self
    #         else:
    #             super().__init__(name, enclosing, fake=False)
    #         self.scopeLevel = 0
    
    GetEdge = Tuple[VarPtr, VarPtr, str]
    id: str
    # codeBlock: CodeBlock
    prefix: 'FakeObject'
    cause: GetEdge

    
    def __init__(self, prefix: 'FakeObject', /, getEdge: GetEdge=None, name:str =None):
        if(prefix):
            assert(getEdge)
            self.cause = getEdge
            target, source, attr = getEdge
            fo = prefix
            while(fo.cause):
                if(fo.cause == getEdge):
                    self.prefix = fo.prefix
                    break
                fo = fo.prefix
            else:
                self.prefix = prefix

            self.id = self.prefix.id[:-1]
        else:
            assert(name)
            self.cause = None
            self.prefix = None
            self.id = name
        
        

    
    