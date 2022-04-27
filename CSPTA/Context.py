from typing import Any, Tuple, Union
import typing

if typing.TYPE_CHECKING:
    from . import CSStmt
    from .CSObjects import CSObject

from ..IR.Stmts import IRStmt

CTX_LENGTH = 2

# 2-callsite
class ContextElement:
    feature: IRStmt
    def __init__(self, feature):
        self.feature = feature
    def __eq__(self, other):
        return isinstance(other, ContextElement) and self.feature == other.feature
    def __hash__(self):
        return hash(self.feature)
    def __str__(self):
        return f"{self.feature.belongsTo.name}-{self.feature.belongsTo.stmts.index(self.feature)}"

Context = Tuple[ContextElement, ...]
ContextChain = Tuple[Context, ...]


def emptyContextChain():
    return ()

# callsite
def selectContext(csCallSite: 'CSStmt', selfObj: 'CSObject') -> Context:
    ctx, callsite = csCallSite
    if(len(ctx) == 0):
        tail = [None] * CTX_LENGTH
        tail = *tail,
    else:
        tail = ctx[-1]
    return *tail[1:], ContextElement(callsite)
