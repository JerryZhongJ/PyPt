
from typing import Dict, Set

from ..IR.CodeBlock import CodeBlock


from ..IR.Stmts import Variable

from .Objects import Object

from .Pointers import AttrPtr, Pointer, VarPtr


class PointToSet:
    varPtrSet: Dict[VarPtr, Set]
    attrPtrSet: Dict[Object, Dict[str, Set]]

    def __init__(self):
        self.varPtrSet = {}
        self.attrPtrSet = {}

    def put(self, pointer: Pointer, obj: Object) -> bool:
        if(isinstance(pointer, VarPtr)):
            var = pointer
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
            var = pointer
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

    def get(self, pointer: Pointer) -> Set[Object]:
        if(isinstance(pointer, VarPtr)):
            var = pointer
            if(var not in self.varPtrSet):
                return set()
            else:
                return self.varPtrSet[var].copy()

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
    
        pointToSet:Dict[CodeBlock, Dict[VarPtr, Set[Object]]] = {varPtr.var.belongsTo:{} for varPtr in self.varPtrSet}
        for varPtr, pointTo in self.varPtrSet.items():
            pointToSet[varPtr.var.belongsTo][varPtr] = pointTo

        
        for codeBlock, map in pointToSet.items():
            print(codeBlock.qualified_name + ":", file=fp)
            
            
            for var, objs in map.items():
                head = f"{var} -> "
                w = len(head)
                
                for obj in objs:
                    print(f"{head:<{w}}{obj}", file=fp)
                    head = ""
                
            print("", file=fp)

        for obj, map in self.attrPtrSet.items():
            
            if(map):
                print(str(obj) + ": ", file=fp)
            
                for attr, objs in map.items():
                    head = f".{attr} -> "
                    w = len(head)
                    
                    for obj in objs:
                        print(f"{head:<{w}}{obj}", file=fp)
                        head = ""
                print("", file=fp)
                
                


        

        
        
    
