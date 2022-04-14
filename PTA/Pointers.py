from pydoc import resolve
from .Objects import Object
from ..IR.Stmts import Variable


class Pointer:
    pass
class VarPtr(Pointer):
    var: Variable
    def __eq__(self, other):
        return isinstance(other, VarPtr) and self.var == other.var

    def __hash__(self):
        return hash(self.var)

    def __init__(self, var):
        self.var = var

class AttrPtr(Pointer):
    obj: Object
    attr: str
    
    def __eq__(self, other):
        return isinstance(other, AttrPtr) and self.obj == other.obj and self.attr == other.attr
    def __hash__(self) -> int:
        return hash((self.obj, self.attr))
    
    def __init__(self, obj, attr):
        self.obj = obj
        self.attr = attr
        