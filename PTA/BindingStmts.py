from typing import Dict, Set, Tuple

from ..IR.Stmts import Assign, Call, DelAttr, GetAttr, NewClass, NewClassMethod, NewStaticMethod, SetAttr

from .Pointers import VarPtr


SETATTR = 0
GETATTR = 1
NEWCLASS = 2
CALL = 3
DELATTR = 4
NEWSTATICMETHOD = 5
NEWCLASSMETHOD = 6
class BindingStmts:
    bindings: Tuple[Dict[VarPtr, Set], ...]
    def __init__(self):
        self.bindings = {}, {}, {}, {}, {}, {}, {}


    def bindSetAttr(self, varPtr: VarPtr, stmt: SetAttr):
        if(varPtr not in self.bindings[SETATTR]):
            self.bindings[SETATTR][varPtr] = set()
        self.bindings[SETATTR][varPtr].add(stmt)

    def bindGetAttr(self, varPtr, stmt):
        if(varPtr not in self.bindings[GETATTR]):
            self.bindings[GETATTR][varPtr] = set()
        self.bindings[GETATTR][varPtr].add(stmt)
    
    def bindNewClass(self, varPtr, stmt, index: int):
        if(varPtr not in self.bindings[NEWCLASS]):
            self.bindings[NEWCLASS][varPtr] = set()
        self.bindings[NEWCLASS][varPtr].add((stmt, index))
    
    def bindCall(self, varPtr, stmt):
        if(varPtr not in self.bindings[CALL]):
            self.bindings[CALL][varPtr] = set()
        self.bindings[CALL][varPtr].add(stmt)
    
    def bindDelAttr(self, varPtr, stmt):
        if(varPtr not in self.bindings[DELATTR]):
            self.bindings[DELATTR][varPtr] = set()
        self.bindings[DELATTR][varPtr].add(stmt)

    def bindNewStaticMethod(self, varPtr, stmt):
        if(varPtr not in self.bindings[NEWSTATICMETHOD]):
            self.bindings[NEWSTATICMETHOD][varPtr] = set()
        self.bindings[NEWSTATICMETHOD][varPtr].add(stmt)

    def bindNewClassMethod(self, varPtr, stmt):
        if(varPtr not in self.bindings[NEWCLASSMETHOD]):
            self.bindings[NEWCLASSMETHOD][varPtr] = set()
        self.bindings[NEWCLASSMETHOD][varPtr].add(stmt)

    def getSetAttr(self, varPtr) -> Set[SetAttr]:
        if(varPtr not in self.bindings[SETATTR]):
            return set()
        else:
            return self.bindings[SETATTR][varPtr]

    def getGetAttr(self, varPtr) -> Set[GetAttr]:
        if(varPtr not in self.bindings[GETATTR]):
            return set()
        else:
            return self.bindings[GETATTR][varPtr]

    def getNewClass(self, varPtr) -> Set[Tuple[NewClass, int]]:
        if(varPtr not in self.bindings[NEWCLASS]):
            return set()
        else:
            return self.bindings[NEWCLASS][varPtr]

    def getNewClassMethod(self, varPtr) -> Set[Tuple[NewClassMethod, int]]:
        if(varPtr not in self.bindings[NEWCLASSMETHOD]):
            return set()
        else:
            return self.bindings[NEWCLASSMETHOD][varPtr]

    def getNewStaticMethod(self, varPtr) -> Set[Tuple[NewStaticMethod, int]]:
        if(varPtr not in self.bindings[NEWSTATICMETHOD]):
            return set()
        else:
            return self.bindings[NEWSTATICMETHOD][varPtr]

    def getCall(self, varPtr) -> Set[Call]:
        if(varPtr not in self.bindings[CALL]):
            return set()
        else:
            return self.bindings[CALL][varPtr]

    def getDelAttr(self, varPtr) -> Set[DelAttr]:
        if(varPtr not in self.bindings):
            return set()
        else:
            return self.bindings[varPtr][DELATTR]

    


