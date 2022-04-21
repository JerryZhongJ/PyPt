
from typing import Dict, Set

from ..IR.CodeBlock import CodeBlock


from ..IR.Stmts import Variable

from .Objects import BuiltinObject, ClassObject, ConstObject, FunctionObject, InstanceObject, ModuleObject, Object

from .Pointers import AttrPtr, Pointer, VarPtr


class PointToSet:
    varPtrSet: Dict[Variable, Set]
    attrPtrSet: Dict[Object, Dict[str, Set]]

    def __init__(self):
        self.varPtrSet = {}
        self.attrPtrSet = {}

    def put(self, pointer: Pointer, obj: Object) -> bool:
        if(isinstance(pointer, VarPtr)):
            var = pointer.var
            if(pointer not in self.varPtrSet):
                self.varPtrSet[var] = set()
            if(obj not in self.varPtrSet[var]):
                self.varPtrSet[var].add(obj)
                return True
            else:
                return False
        elif(isinstance(pointer, AttrPtr)):
            o = pointer.obj
            f = pointer.attr
            if(o not in self.attrPtrSet):
                self.attrPtrSet[o] = {}
            
            if(f not in self.attrPtrSet[o]):
                self.attrPtrSet[o][f] = set()
            
            if(obj not in self.attrPtrSet[o][f]):
                self.attrPtrSet[o][f].add(obj)
                return True
            else:
                return False
    
    def putAll(self, pointer: Pointer, objs: Set[Object]) -> Set[Object]:
        if(isinstance(pointer, VarPtr)):
            var = pointer.var
            if(pointer not in self.varPtrSet):
                self.varPtrSet[var] = set()
            diff = objs - self.varPtrSet[var]
            self.varPtrSet[var] |= objs
            return diff
        elif(isinstance(pointer, AttrPtr)):
            o = pointer.obj
            f = pointer.attr
            if(o not in self.attrPtrSet):
                self.attrPtrSet[o] = {}
            
            if(f not in self.attrPtrSet[o]):
                self.attrPtrSet[o][f] = set()
            
            diff = objs - self.attrPtrSet[o][f]
            self.attrPtrSet[o][f] |= objs
            return diff

    def get(self, pointer: Pointer) -> Set:
        if(isinstance(pointer, VarPtr)):
            v = pointer.var
            if(v not in self.varPtrSet):
                return set()
            else:
                return self.varPtrSet[v].copy()

        elif(isinstance(pointer, AttrPtr)):
            o = pointer.obj
            f = pointer.attr
            try:
                return self.attrPtrSet[o][f].copy()
            except(KeyError):
                return set()

    def getAllAttr(self, obj: Object):
        if(obj not in self.attrPtrSet):
            return set()
        else:
            return self.attrPtrSet[obj].keys()

    
    def dump(self, fp):
    
        pointToSet:Dict[CodeBlock, Dict[Variable, Set[Object]]] = {stmt.belongsTo:{} for stmt in self.varPtrSet}
        for stmt, pointTo in self.varPtrSet.items():
            pointToSet[stmt.belongsTo][stmt] = pointTo

        
        for codeBlock, map in pointToSet.items():
            print(codeBlock.qualified_name + ":", file=fp)
            colwidth = 0
            for var in map:
                w = len(str(var))
                colwidth = w if colwidth < w else colwidth
            for var, objs in map.items():
                objects_str = [str(obj) for obj in objs]
                print(f"{str(var):<{colwidth}} -> {', '.join(objects_str)}", file=fp)
            print("", file=fp)

        for obj, map in self.attrPtrSet.items():
            
            if(map):
                print(str(obj) + ": ", file=fp)
                lines = []
                colwidth = 0
                for attr, objs in map.items():
                    head = f".{attr}"
                    w = len(head)
                    colwidth = w if w > colwidth else colwidth
                    obj_str = [str(obj) for obj in objs]
                    lines.append((head, obj_str))
                for head, obj_str in lines:
                    print(f"{head:<{colwidth}} -> {', '.join(obj_str)}", file=fp)
                print("", file=fp)
                
                


        

        
        
    
