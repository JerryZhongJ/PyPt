
import typing


if typing.TYPE_CHECKING:
    from .Context import ContextChain
from ..IR.Stmts import Variable
from ..PTA.Pointers import VarPtr


class CSVarPtr(VarPtr):
    ctxChain: 'ContextChain'
    var: Variable
    def __init__(self, ctxChain: 'ContextChain', var: Variable):
        self.ctxChain = ctxChain[:var.belongsTo.scopeLevel]
        self.var = var
    def __eq__(self, other):
        return isinstance(other, CSVarPtr) and self.ctxChain == other.ctxChain and self.var == other.var
    def __hash__(self):
        return hash((self.ctxChain, self.var))
    def __str__(self):
        s = ""
        for ctx in self.ctxChain:
            s += ", ".join([str(e) for e in ctx]) + "#"
        return f"{s}#{self.var}"