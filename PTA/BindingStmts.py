from typing import Dict, Set, Tuple

from ..IR.Stmts import Assign, Call, DelAttr, GetAttr, NewClass, SetAttr

from .Pointers import VarPtr


SETATTR = 0
GETATTR = 1
NEWCLASS = 2
CALL = 3
DELATTR = 4

class BindingStmts:
    bindings: Dict[VarPtr, Tuple]
    def __init__(self):
        self.bindings = {}


    def bindSetAttr(self, varPtr: VarPtr, stmt: SetAttr):
        if(varPtr not in self.bindings):
            self.bindings[varPtr] = (set(), set(), set(), set(), set())
        self.bindings[varPtr][SETATTR].add(stmt)

    def bindGetAttr(self, varPtr, stmt):
        if(varPtr not in self.bindings):
            self.bindings[varPtr] = (set(), set(), set(), set(), set())
        self.bindings[varPtr][GETATTR].add(stmt)
    
    def bindNewClass(self, varPtr, stmt, index: int):
        if(varPtr not in self.bindings):
            self.bindings[varPtr] = (set(), set(), set(), set(), set())
        self.bindings[varPtr][NEWCLASS].add((stmt, index))
    
    def bindCall(self, varPtr, stmt):
        if(varPtr not in self.bindings):
            self.bindings[varPtr] = (set(), set(), set(), set(), set())
        self.bindings[varPtr][CALL].add(stmt)
    
    def bindDelAttr(self, varPtr, stmt):
        if(varPtr not in self.bindings):
            self.bindings[varPtr] = (set(), set(), set(), set(), set())
        self.bindings[varPtr][DELATTR].add(stmt)


    def getSetAttr(self, varPtr) -> Set[SetAttr]:
        if(varPtr not in self.bindings):
            return set()
        else:
            return self.bindings[varPtr][SETATTR].copy()

    def getGetAttr(self, varPtr) -> Set[GetAttr]:
        if(varPtr not in self.bindings):
            return set()
        else:
            return self.bindings[varPtr][GETATTR].copy()

    def getNewClass(self, varPtr) -> Set[Tuple[NewClass, int]]:
        if(varPtr not in self.bindings):
            return set()
        else:
            return self.bindings[varPtr][NEWCLASS].copy()

    def getCall(self, varPtr) -> Set[Call]:
        if(varPtr not in self.bindings):
            return set()
        else:
            return self.bindings[varPtr][CALL].copy()

    def getDelAttr(self, varPtr) -> Set[DelAttr]:
        if(varPtr not in self.bindings):
            return set()
        else:
            return self.bindings[varPtr][DELATTR].copy()

    


