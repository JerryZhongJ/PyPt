import typing


if typing.TYPE_CHECKING:
    from .Objects import Object
from ..IR.IRStmts import Variable

class Pointer:
    id: str
    def __repr__(self) -> str:
        return f"VarPtr: {self.id}"
    def __eq__(self, other):
        return isinstance(other, Pointer) and self.id == other.id

    def __hash__(self):
        return hash(self.id)

class VarPtr(Pointer):
    
    def __init__(self, var: Variable = None, id: str = None):
        if(var):
            self.id = var.id
        else:
            self.id = id


    

class AttrPtr(Pointer):
    obj: 'Object'
    attr: str
    
    def __init__(self, obj, attr):
        self.obj = obj
        self.attr = attr
        self.id = f"<{obj}>.attr"
        



