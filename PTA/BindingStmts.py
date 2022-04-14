from typing import Dict, Set, Tuple

from ..IR.Stmts import Assign, Call, DelAttr, GetAttr, NewClass, SetAttr

from .Pointers import VarPtr


SETATTR_TARGET = 0
SETATTR_SOURCE = 1
GETATTR_SOURCE = 2
CLASS_BASE = 3
CALL_CALLEE = 4
DELATTR_TARGET = 5

class BindingStmts:
    bindings: Dict[VarPtr, Tuple]
    def __init__(self):
        self.bindings = {}

    def bind(self, varPtr, stmt):
        if(varPtr not in self.bindings):
            self.bindings[varPtr] = (set(), set(), set(), set(), set(), set())
        elif(isinstance(stmt, SetAttr) and stmt.source == varPtr.var):
            self.bindings[varPtr][SETATTR_SOURCE].add(stmt)
        elif(isinstance(stmt, SetAttr) and stmt.target == varPtr.var):
            self.bindings[varPtr][SETATTR_TARGET].add(stmt)
        elif(isinstance(stmt, GetAttr) and stmt.source == varPtr.var):
            self.bindings[varPtr][GETATTR_SOURCE].add(stmt)
        elif(isinstance(stmt, NewClass)):
            for i in range(len(stmt.bases)):
                if(stmt.bases[i] == varPtr.var):
                    self.bindings[varPtr][CLASS_BASE].add((stmt, i))
        elif(isinstance(stmt, Call) and stmt.callee == varPtr.var):
            self.bindings[varPtr][CALL_CALLEE].add(stmt)
        elif(isinstance(stmt, DelAttr)):
            self.bindings[varPtr][DELATTR_TARGET].add(stmt)


    def getSetAttrAsSource(self, varPtr) -> Set[SetAttr]:
        if(varPtr not in self.bindings):
            return set()
        else:
            return self.bindings[varPtr][SETATTR_SOURCE].copy()

    def getSetAttrAsTarget(self, varPtr) -> Set[SetAttr]:
        if(varPtr not in self.bindings):
            return set()
        else:
            return self.bindings[varPtr][SETATTR_TARGET].copy()

    def getGetAttrAsSource(self, varPtr) -> Set[GetAttr]:
        if(varPtr not in self.bindings):
            return set()
        else:
            return self.bindings[varPtr][GETATTR_SOURCE].copy()

    def getNewClassAsBase(self, varPtr) -> Set[Tuple[NewClass, int]]:
        if(varPtr not in self.bindings):
            return set()
        else:
            return self.bindings[varPtr][CLASS_BASE].copy()

    def getCallAsCallee(self, varPtr) -> Set[Call]:
        if(varPtr not in self.bindings):
            return set()
        else:
            return self.bindings[varPtr][CALL_CALLEE].copy()

    def getDelAttrAsTarget(self, varPtr) -> Set[DelAttr]:
        if(varPtr not in self.bindings):
            return set()
        else:
            return self.bindings[varPtr][DelAttr].copy()

    


