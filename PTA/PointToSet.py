from re import I
from typing import Dict, Set

from matplotlib.colors import PowerNorm

from ..IR.Stmts import Variable

from .Objects import Object

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
        if(obj in self.attrPtrSet):
            return set()
        else:
            return self.attrPtrSet[obj].keys()
            
        
    
