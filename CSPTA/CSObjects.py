


from PTA.Objects import Object
from .Context import ContextChain


class CSObject:
    ctxChain: ContextChain
    obj: Object
    def __init__(self, ctxChain, obj):
        self.ctxChain = ctxChain
        self.obj = obj
    def __eq__(self, other):
        return isinstance(other, CSObject) and self.ctxChain == other.ctxChain and self.obj == other.obj
    def __hash__(self):
        return hash((self.ctxChain, self.obj))