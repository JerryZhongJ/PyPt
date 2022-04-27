from CSPTA.CSObjects import CSObject
from CSPTA.Context import ContextChain
from PTA.Pointers import VarPtr


class CSPointer:
    pass

class CSVarPtr(CSPointer):
    ctxChain: ContextChain
    varPtr: VarPtr
    def __init__(self, ctxChain, obj):
        self.ctxChain = ctxChain
        self.obj = obj
    def __eq__(self, other):
        return isinstance(other, CSVarPtr) and self.ctxChain == other.ctxChain and self.varPtr == other.varPtr
    def __hash__(self):
        return hash((self.ctxChain, self.varPtr))

class CSAttrPtr(CSPointer):
    csObject: CSObject
    attr :str

    def __eq__(self, other):
        return isinstance(other, CSAttrPtr) and self.csObject == other.csObject and self.attr == other.attr
    def __hash__(self) -> int:
        return hash((self.csObject, self.attr))