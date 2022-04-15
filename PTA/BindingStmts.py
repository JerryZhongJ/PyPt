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

    def bind(self, varPtr, stmt):
        if(varPtr not in self.bindings):
            self.bindings[varPtr] = (set(), set(), set(), set(), set())
        elif(isinstance(stmt, SetAttr) and stmt.target == varPtr.var):
            self.bindings[varPtr][SETATTR].add(stmt)
        elif(isinstance(stmt, GetAttr) and stmt.source == varPtr.var):
            self.bindings[varPtr][GETATTR].add(stmt)
        elif(isinstance(stmt, NewClass)):
            for i in range(len(stmt.bases)):
                if(stmt.bases[i] == varPtr.var):
                    self.bindings[varPtr][NEWCLASS].add((stmt, i))
        elif(isinstance(stmt, Call) and stmt.callee == varPtr.var):
            self.bindings[varPtr][CALL].add(stmt)
        elif(isinstance(stmt, DelAttr)):
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
            return self.bindings[varPtr][DelAttr].copy()

    


