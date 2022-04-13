from IR.Stmts import Call
from PTA.PointerFlow import PointerFlow
from .CallGraph import CallGraph
from .PointToSet import PointToSet


class Analysis:
    pointToSet: PointToSet
    callgraph: CallGraph
    pointerFlow: PointerFlow
    def __init__(self):
        self.pointToSet = PointToSet()
        self.callgraph = CallGraph()
        self.pointerFlow = PointerFlow()
    def addReachable(self, codeBlock):
        pass

    def addDefined(self, codeBlock):
        pass

    def analyze(self):
        pass

    def propagate(self, )