from typing import Dict, Set, Tuple
from IR.CodeBlock import CodeBlock
from IR.Stmts import Call, DelAttr, GetAttr, NewClass, SetAttr
from PTA.ClassHiearchy import MRO, ClassHiearchy
from .Objects import ClassObject
from .BindingStmts import BindingStmts
from .PointerFlow import PointerFlow
from .Pointers import AttrPtr, Pointer, VarPtr
from .CallGraph import CallGraph
from .PointToSet import PointToSet

RESOLVED_PREFIX = "$r_"

def isResolved(attr: str):
    return attr.startswith(RESOLVED_PREFIX)
ResolveInfo = Tuple[MRO, int]
class Analysis:
    pointToSet: PointToSet
    callgraph: CallGraph
    pointerFlow: PointerFlow
    bindingStmts: BindingStmts
    definedCodeBlocks: Set[CodeBlock]
    classHiearchy: ClassHiearchy
    persist_attr: Dict[ClassObject, Dict[str, ResolveInfo]]
    def __init__(self):
        self.pointToSet = PointToSet()
        self.callgraph = CallGraph()
        self.pointerFlow = PointerFlow()
        self.bindingStmts = BindingStmts()
        self.definedCodeBlocks = set()
        self.classHiearchy = ClassHiearchy(self.pointToSet)
        self.persist_attr = {}
    def addReachable(self, codeBlock):
        pass

    def addDefined(self, codeBlock: CodeBlock):
        if(codeBlock in self.definedCodeBlocks):
            return
        for stmt in codeBlock:
            if(isinstance(stmt, SetAttr)):
                self.bindingStmts.bind(VarPtr(stmt.source), stmt)
                self.bindingStmts.bind(VarPtr(stmt.target), stmt)
            elif(isinstance(stmt, GetAttr)):
                self.bindingStmts.bind(VarPtr(stmt.source), stmt)
            elif(isinstance(stmt, NewClass)):
                for base in stmt.bases:
                    self.bindingStmts.bind(VarPtr(base), stmt)
            elif(isinstance(stmt, Call)):
                self.bindingStmts(VarPtr(stmt.callee), stmt)
            elif(isinstance(stmt, DelAttr)):
                self.bindingStmts(VarPtr(stmt.var), stmt)

    def analyze(self):
        pass

    def propagate(self, pointer: Pointer, pointTo: Set) -> Set:
        # Special condition: when source is a class object's attribute 
        # and target is an instance object's attribute
        # and the object is a function
        pass

    def resolveAttribute(self, classObj: ClassObject, attr: str, resolveInfo: ResolveInfo=None):
        
        if(not resolveInfo):
            if((RESOLVED_PREFIX + attr) in self.pointToSet.getAllAttr(classObj)):
                return
            for mro in self.classHiearchy.getMROs(classObj):
                self.resolveAttribute(classObj, attr, (mro, 0))
        else:
            mro, i = resolveInfo
            while(i < len(mro)):
                resAttr = AttrPtr(classObj, RESOLVED_PREFIX + attr)
                targetAttr = AttrPtr(mro[i], attr)
                self.pointerFlow.put(targetAttr, resAttr)
                if(attr in self.persist_attr[mro[i]]):
                    break

        
