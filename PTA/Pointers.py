import typing


if typing.TYPE_CHECKING:
    from .Objects import Object
from ..IR.Stmts import Variable

class Pointer:
    pass

class VarPtr(Pointer):
    var: Variable

class CIVarPtr(VarPtr):
    
    def __eq__(self, other):
        return isinstance(other, VarPtr) and self.var == other.var

    def __hash__(self):
        return hash(self.var)

    def __init__(self, var):
        self.var = var

    def __str__(self):
        return str(self.var)

    def __repr__(self) -> str:
        return f"VarPtr: {str(self)}"

class AttrPtr(Pointer):
    obj: 'Object'
    attr: str
    
    def __eq__(self, other):
        return isinstance(other, AttrPtr) and self.obj == other.obj and self.attr == other.attr
    def __hash__(self) -> int:
        return hash((self.obj, self.attr))
    
    def __init__(self, obj, attr):
        self.obj = obj
        self.attr = attr
        
    def __str__(self):
        return f"{self.obj}.{self.attr}"
    
    def __repr__(self):
        return f"AttrPtr: {str(self)}"

