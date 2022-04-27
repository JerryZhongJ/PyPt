from typing import Any, Tuple, Union

from IR.Stmts import IRStmt
from ..PTA.Objects import Object

from ..PTA.Pointers import Pointer, VarPtr


class ContextElement:
    feature: Any
    def __init__(self, feature):
        self.feature
    def __eq__(self, other):
        return isinstance(other, ContextElement) and self.feature == other.feature
    def __hash__(self):
        return hash(self.feature)
    def __str__(self):
        return ""

Context = Tuple[ContextElement, ...]
ContextChain = Tuple[Context, ...]



def sliceContextChain(ctxChain: ContextChain, varPtr: VarPtr):
    return ctxChain[:varPtr.var.belongsTo.scopeLevel]

def select(ctxChain: ContextChain, callsite: IRStmt):
    pass
