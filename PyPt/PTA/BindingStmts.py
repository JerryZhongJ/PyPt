from collections import defaultdict
from typing import Dict, Set, Tuple

from ..IR.IRStmts import Assign, Call, DelAttr, GetAttr, IRStmt, NewClass, NewClassMethod, NewStaticMethod, NewSuper, SetAttr, NewFunction

from .Pointers import VarPtr


class BindingStmts:
    bindings: Tuple[Dict[VarPtr, Set], ...]
    def __init__(self):
        opnames = ["GetAttr",
            "SetAttr",
            "NewClass",
            "Call",
            "DelAttr",
            "NewStaticMethod",
            "NewClassMethod",
            "NewSuper"]
        self.bindings = {}
        for opname in opnames:
            self.bindings[opname] = defaultdict(set)

    def bind(self, opname, varPtr: VarPtr, stmtInfo: IRStmt):
        self.bindings[opname][varPtr].add(stmtInfo)

    def get(self, opname, varPtr: VarPtr):
        return self.bindings[opname][varPtr]