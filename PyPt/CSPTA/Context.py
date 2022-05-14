from typing import Any, Tuple, Union
import typing

if typing.TYPE_CHECKING:
    from . import CSStmt
    from .CSObjects import CSObject

from ..IR.Stmts import IRStmt

CTX_LENGTH = 1

# 2-callsite
class ContextElement:
    key: IRStmt
    def __init__(self, key):
        self.key = key
    def __eq__(self, other):
        return isinstance(other, ContextElement) and self.key == other.key
    def __hash__(self):
        return hash(self.key)
    def __str__(self):
        return f"{self.key.belongsTo.qualified_name}-{self.key.belongsTo.stmts.index(self.key)}"


# Context consists of ContextElement, the newest are placed at the end, the first which is ctx[0] is the oldest
# when context is full, the first element is dropped
Context = Tuple[ContextElement, ...]

# Context Chains consist of contexts, whose numbers are the same as codeblocks' scopeLevel, and therefore are not fixed.
# The first context is the outermost function's, 
ContextChain = Tuple[Context, ...]


def emptyContextChain():
    return ()

# callsite
def selectContext(csCallSite: 'CSStmt', selfObj: 'CSObject') -> Context:
    # return selectCallSiteContext(csCallSite, selfObj)
    return selectMixedContext(csCallSite, selfObj)

def selectCallSiteContext(csCallSite: 'CSStmt', selfObj: 'CSObject') -> Context:
    ctx, callsite = csCallSite
    if(len(ctx) == 0):
        tail = [None] * CTX_LENGTH
        tail = *tail,
    else:
        tail = ctx[-1]
    return *tail[1:], ContextElement(callsite)

def selectObjectContext(csCallSite: 'CSStmt', selfObj: 'CSObject') -> Context:
    if(selfObj is None):
        ctx, callsite = csCallSite
        if(len(ctx) == 0):
            tail = [None] * CTX_LENGTH
            tail = *tail,
        else:
            tail = ctx[-1]
        return tail
    else:
        ctx, alloc_site = selfObj.ctxChain, selfObj.alloc_site
        if(len(ctx) == 0):
            tail = [None] * CTX_LENGTH
            tail = *tail,
        else:
            tail = ctx[-1]
        return *tail[1:], ContextElement(alloc_site)

def selectMixedContext(csCallSite: 'CSStmt', selfObj: 'CSObject') -> Context:
    if(selfObj):
        return selectObjectContext(csCallSite, selfObj)
    else:
        return selectCallSiteContext(csCallSite, selfObj)
