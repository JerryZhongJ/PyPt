
from collections import defaultdict
import json
from typing import Dict, Set

from PyPt.PTA import json_utils

from ..IR.CodeBlock import CodeBlock


from ..IR.IRStmts import Variable

from .Objects import Object

from .Pointers import AttrPtr, Pointer, VarPtr


class PointToSet:
    varPtrSet: Dict[VarPtr, Set]
    attrPtrSet: Dict[Object, Dict[str, Set]]

    def __init__(self):
        self.varPtrSet = defaultdict(set)
        self.attrPtrSet = defaultdict(lambda: defaultdict(set))

    def put(self, pointer: Pointer, obj: Object) -> bool:
        if(isinstance(pointer, VarPtr)):
            var = pointer
            if(obj not in self.varPtrSet[var]):
                self.varPtrSet[var].add(obj)
                return True
            else:
                return False
        elif(isinstance(pointer, AttrPtr)):
            o = pointer.obj
            f = pointer.attr
            if(obj not in self.attrPtrSet[o][f]):
                self.attrPtrSet[o][f].add(obj)
                return True
            else:
                return False
    
    def putAll(self, pointer: Pointer, objs: Set[Object]) -> Set[Object]:
        if(isinstance(pointer, VarPtr)):
            var = pointer
            
            diff = objs - self.varPtrSet[var]
            self.varPtrSet[var] |= diff
            return diff
        elif(isinstance(pointer, AttrPtr)):
            o = pointer.obj
            f = pointer.attr
            
            diff = objs - self.attrPtrSet[o][f]
            self.attrPtrSet[o][f] |= diff
            return diff

    def get(self, pointer: Pointer) -> Set[Object]:
        if(isinstance(pointer, VarPtr)):
            var = pointer
            return self.varPtrSet[var]

        elif(isinstance(pointer, AttrPtr)):
            o = pointer.obj
            f = pointer.attr
            return self.attrPtrSet[o][f]
            

    def getAllAttr(self, obj: Object):
        
        return self.attrPtrSet[obj].keys()

    
    def to_json(self):
        attrPtrSet = {str(AttrPtr(obj, attr)):objs for obj, d in self.attrPtrSet.items() for attr, objs in d.items()}
        varPtrSet = {str(varPtr): s for varPtr, s in self.varPtrSet.items()}
        return json.dumps(attrPtrSet | varPtrSet, default=json_utils.default, indent=4)