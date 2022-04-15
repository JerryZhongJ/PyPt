from typing import Dict, List, Set, Tuple
from ..IR.CodeBlock import CodeBlock, FunctionCodeBlock, ModuleCodeBlock
from ..IR.Stmts import Assign, Call, DelAttr, GetAttr, NewBuiltin, NewClass, NewFunction, NewModule, SetAttr
from .ClassHiearchy import MRO, ClassHiearchy
from .Objects import BuiltinObject, ClassObject, ConstObject, FunctionObject, InstanceObject, MethodObject, ModuleObject, Object
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
    persist_attr: Dict[ClassObject, Dict[str, Set[ResolveInfo]]]
    workList: List[Tuple[Pointer, Set[Object]]]
    def __init__(self):
        self.pointToSet = PointToSet()
        self.callgraph = CallGraph()
        self.pointerFlow = PointerFlow()
        self.bindingStmts = BindingStmts()
        self.definedCodeBlocks = set()
        self.classHiearchy = ClassHiearchy(self.pointToSet)
        self.persist_attr = {}
        self.workList = []

    def addReachable(self, codeBlock):
        for stmt in codeBlock:
            if(isinstance(stmt, Assign)):
                self.addFlow(stmt.source, stmt.target)
            elif(isinstance(stmt, NewModule)):
                obj = ModuleObject(stmt.codeBlock)
                varPtr = VarPtr(stmt.target)
                self.workList.append((varPtr, {obj}))
                self.addDefined(stmt.codeBlock)
                self.addReachable(stmt.codeBlock)
            elif(isinstance(stmt, NewFunction)):
                obj = FunctionObject(stmt)
                varPtr = VarPtr(stmt.target)
                self.workList.append((varPtr, {obj}))
                self.addDefined(stmt.codeBlock)
            elif(isinstance(stmt, NewClass)):
                obj = ClassObject(stmt)
                varPtr = VarPtr(stmt.target)
                self.workList.append((varPtr, {obj}))
                self.addDefined(stmt.codeBlock)
                self.addReachable(stmt.codeBlock)
                self.classHiearchy.addClass(obj)
                self.persist_attr[obj] = obj.getAttributes()
            elif(isinstance(stmt, NewBuiltin)):
                if(stmt.value or stmt.type == "NoneType"):
                    obj = ConstObject(stmt.value)
                else:
                    obj = BuiltinObject(stmt)
                self.workList.append(varPtr, {obj})

    def addDefined(self, codeBlock: CodeBlock):
        if(codeBlock in self.definedCodeBlocks):
            return
        for stmt in codeBlock:
            if(isinstance(stmt, SetAttr)):
                varPtr = VarPtr(stmt.target)
                self.bindingStmts.bind(varPtr, stmt)
                self.processSetAttr(stmt, self.pointToSet.get(varPtr))
            elif(isinstance(stmt, GetAttr)):
                varPtr = VarPtr(stmt.source)
                self.bindingStmts.bind(varPtr, stmt)
                self.processGetAttr(stmt, self.pointToSet.get(varPtr))
            elif(isinstance(stmt, NewClass)):
                for i in range(len(stmt.bases)):
                    varPtr = VarPtr(stmt.bases[i])
                    self.bindingStmts.bind(varPtr, stmt)
                    self.processNewClass(stmt, i, self.pointToSet.get(varPtr))
            elif(isinstance(stmt, Call)):
                self.bindingStmts(VarPtr(stmt.callee), stmt)
                # TODO
            elif(isinstance(stmt, DelAttr)):
                self.bindingStmts(VarPtr(stmt.var), stmt)
                # TODO

    def analyze(self, entry: ModuleCodeBlock):
        self.addDefined(entry)
        self.addReachable(entry)

        while(len(self.workList) != 0):
            ptr, objs = self.workList[0]
            del self.workList[0]
            self.propagate(ptr, objs)

            if(not isinstance(ptr, VarPtr)):
                continue

            for stmt in self.bindingStmts.getSetAttr(ptr):
                self.processSetAttr(stmt, objs)

            for stmt in self.bindingStmts.getGetAttr(ptr):
               self.processGetAttr(stmt, objs)

            for stmt, index in self.bindingStmts.getNewClass(ptr):
                self.processNewClass(stmt, index, objs)
            
    def addFlow(self, source, target):
        if(self.pointerFlow.put(source, target)):
            objs = self.pointToSet.get(source)
            self.workList.append((target, objs))

        

    def propagate(self, pointer: Pointer, objs: Set) -> Set:
        # Special condition: when source is a class object's attribute 
        # and target is an instance object's attribute
        # and the object is a function
        diff = self.pointToSet.putAll(pointer, objs)
        for succ in self.pointerFlow.getSuccessors(pointer):
            objs = diff
            if(isinstance(pointer, AttrPtr) and isinstance(pointer.obj, ClassObject) 
                and isinstance(succ, AttrPtr) and isinstance(succ.obj, InstanceObject)):
                ins = succ.obj
                objs = {MethodObject(ins, obj) for obj in objs if isinstance(obj, FunctionObject)}

            self.workList.append((succ, objs))
        
    # classObj.$r_attr <- parent.attr
    # where parent is the first class that has this attr as its persistent attributes along MRO
    def resolveAttribute(self, classObj: ClassObject, attr: str, resolveInfo: ResolveInfo=None):
        assert(classObj, ClassObject)
        if(not resolveInfo):
            if((RESOLVED_PREFIX + attr) in self.pointToSet.getAllAttr(classObj)):
                return
            for mro in self.classHiearchy.getMROs(classObj):
                self.resolveAttribute(classObj, attr, (mro, 0))
        else:
            mro, i = resolveInfo
            childAttr = AttrPtr(classObj, RESOLVED_PREFIX + attr)
            while(i < len(mro)):
                parent = mro[i]
                parentAttr = AttrPtr(parent, attr)
                self.addFlow(parentAttr, childAttr)
                if(attr in self.persist_attr[parent]):
                    self.persist_attr[parent][attr].add((mro, i))
                    break

    

    def processSetAttr(self, stmt: SetAttr, objs: Set[Object]):
        for obj in objs:
            attrPtr = AttrPtr(obj, stmt.attr)
            self.addFlow(VarPtr(stmt.source), attrPtr)

    def processGetAttr(self, stmt: GetAttr, objs: Set[Object]):
        for obj in objs:
            varPtr = VarPtr(stmt.target)
            if(isinstance(obj, InstanceObject)):
                # target <- instance.attr
                insAttr = AttrPtr(obj, stmt.attr)
                self.addFlow(insAttr, varPtr)
                for classObj in self.pointToSet.get(obj.getType()):
                    if(not isinstance(classObj, ClassObject)):
                        continue
                    self.resolveAttribute(classObj, stmt.attr)
                    # instance.attr <- class.$r_attr
                    classAttr = AttrPtr(classObj, RESOLVED_PREFIX + stmt.attr)
                    self.addFlow(classAttr, insAttr)

            elif(isinstance(obj, ClassObject)):
                self.resolveAttribute(classObj, stmt.attr)
                # instance.attr <- class.$r_attr
                classAttr = AttrPtr(obj, RESOLVED_PREFIX + stmt.attr)
                self.addFlow(classAttr, varPtr)
            else:
                attrPtr = AttrPtr(obj, stmt.attr)
                self.addFlow(attrPtr, varPtr)

    def processNewClass(self, stmt: NewClass, index: int, objs: Set[Object]):
        for obj in objs:
            mroChange = self.classHiearchy.addClassBase(ClassObject(stmt), index, obj)
            for mro in mroChange:
                classObj = mro[0]
                for attr in self.pointToSet.getAllAttr(classObj):
                    if(isResolved(attr)):
                        continue
                    self.resolveAttribute(classObj, attr, mro, 0)

