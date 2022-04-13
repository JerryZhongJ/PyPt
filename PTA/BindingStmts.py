from typing import Dict, Tuple

from ..IR.Stmts import Assign, Call, GetAttr, NewClass, SetAttr

from .Pointers import VarPtr


ASSIGN_SOURCE = 0
SETATTR_TARGET = 1
SETATTR_SOURCE = 2
GETATTR_SOURCE = 3
CLASS_BASE = 4
CALL_CALLEE = 5

class BindingStmts:
    bindings: Dict[VarPtr, Tuple]
    def __init__(self):
        self.bindings = {}

    def bind(self, varPtr, stmt):
        if(varPtr not in self.bindings):
            self.bindings[varPtr] = (set(), set(), set(), set(), set(), set())
        if(isinstance(stmt, Assign) and stmt.source == varPtr.var):
            self.bindings[varPtr][ASSIGN_SOURCE].add(stmt)
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

    def getAssignAsTarget(self, varPtr):
        if(varPtr not in self.bindings):
            return set()
        else:
            return self.bindings[varPtr][ASSIGN_SOURCE].copy()

    def getAssignAsTarget(self, varPtr):
        if(varPtr not in self.bindings):
            return set()
        else:
            return self.bindings[varPtr][ASSIGN_SOURCE].copy()


