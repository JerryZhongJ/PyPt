from .Objects import Object
from ..IRGeneration.IR import Variable


class Pointer:
    pass
class VarPtr(Pointer):
    var: Variable
    def __eq__(self, other):
        return isinstance(other, VarPtr) and self.var == other.var

    def __hash__(self):
        return hash(self.var)

class AttrPtr(Pointer):
    obj: Object
    field: str

    def __eq__(self, other):
        return isinstance(other, AttrPtr) and self.obj == other.obj and self.field == other.field
    def __hash__(self) -> int:
        return hash((self.obj, self.field))