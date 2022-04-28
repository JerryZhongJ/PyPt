from typing import Dict, List, Set, Tuple, Union
from ..IR.CodeBlock import CodeBlock, FunctionCodeBlock, ModuleCodeBlock
from ..IR.Stmts import Assign, Call, DelAttr, GetAttr, IRStmt, NewBuiltin, NewClass, NewFunction, NewModule, SetAttr, Variable
from .ClassHiearchy import MRO, ClassHiearchy
from .Objects import BuiltinObject, CIBuiltinObject, CIClassObject, CIFunctionObject, CIInstanceObject, ClassObject, FunctionObject, InstanceObject, MethodObject, ModuleObject, Object
from .BindingStmts import BindingStmts
from .PointerFlow import PointerFlow
from .Pointers import AttrPtr, Pointer, CIVarPtr
from .CallGraph import CallGraph
from .PointToSet import PointToSet

FAKE_PREFIX = "$r_"

def isFakeAttr(attr: str):
    return attr.startswith(FAKE_PREFIX)
ResolveInfo = Tuple[MRO, int]
class Analysis:
    pointToSet: PointToSet
    callgraph: CallGraph
    pointerFlow: PointerFlow
    bindingStmts: BindingStmts
    reachable: Set[CodeBlock]
    # defined: Set[CodeBlock]
    classHiearchy: ClassHiearchy
    persist_attr: Dict[ClassObject, Dict[str, Set[ResolveInfo]]]
    workList: List[Tuple[Pointer, Set[Object]]]
    def __init__(self):
        self.pointToSet = PointToSet()
        self.callgraph = CallGraph()
        self.pointerFlow = PointerFlow()
        self.bindingStmts = BindingStmts()
        self.defined = set()
        self.reachable = set()
        self.classHiearchy = ClassHiearchy(self.pointToSet)
        self.persist_attr = {}
        self.workList = []

    def addReachable(self, codeBlock: CodeBlock):
        if(codeBlock in self.reachable):
            return
        self.reachable.add(codeBlock)

        # Add codes into the pool
        for stmt in codeBlock.stmts:
            self.addStmt(stmt)

        for stmt in codeBlock.stmts:
            if(isinstance(stmt, Assign)):
                sourcePtr = CIVarPtr(stmt.source)
                targetPtr = CIVarPtr(stmt.target)
                self.addFlow(sourcePtr, targetPtr)

            elif(isinstance(stmt, NewModule)):
                obj = ModuleObject(stmt.codeBlock)
                targetPtr = CIVarPtr(stmt.target)
                globalPtr = CIVarPtr(stmt.codeBlock.globalVariable)
                self.workList.append((targetPtr, {obj}))
                self.workList.append((globalPtr, {obj}))
                self.addReachable(stmt.codeBlock)
                self.callgraph.put(stmt, stmt.codeBlock)
                
            elif(isinstance(stmt, NewFunction)):
                obj = CIFunctionObject(stmt)
                targetPtr = CIVarPtr(stmt.target)
                self.workList.append((targetPtr, {obj}))

            elif(isinstance(stmt, NewClass)):
                obj = CIClassObject(stmt)
                targetPtr = CIVarPtr(stmt.target)
                thisPtr = CIVarPtr(stmt.codeBlock.thisClassVariable)
                self.workList.append((targetPtr, {obj}))
                self.workList.append((thisPtr, {obj}))
                
                self.addReachable(stmt.codeBlock)
                self.callgraph.put(stmt, stmt.codeBlock)
                
                self.classHiearchy.addClass(obj)
                self.persist_attr[obj] = {}
                for attr in obj.getAttributes():
                    self.persist_attr[obj][attr] = set()

            elif(isinstance(stmt, NewBuiltin)):
                targetPtr = CIVarPtr(stmt.target)
                # if(stmt.value is not None or stmt.type == "NoneType"):
                #     obj = ConstObject(stmt.value)
                # else:
                obj = CIBuiltinObject(stmt)
                self.workList.append((targetPtr, {obj}))

    def addStmt(self, stmt: IRStmt):
        if(isinstance(stmt, SetAttr)):
            # print(f"Bind SetAttr: {stmt.target} - {stmt}")
            varPtr = CIVarPtr(stmt.target)
            self.bindingStmts.bindSetAttr(varPtr, stmt)
            self.processSetAttr(stmt, self.pointToSet.get(varPtr))

        elif(isinstance(stmt, GetAttr)):
            # print(f"Bind GetAttr: {stmt.source} - {stmt}")
            varPtr = CIVarPtr(stmt.source)
            self.bindingStmts.bindGetAttr(varPtr, stmt)
            self.processGetAttr(stmt, self.pointToSet.get(varPtr))

        elif(isinstance(stmt, NewClass)):
            for i in range(len(stmt.bases)):
                # print(f"Bind Base: {stmt.bases[i]} - {stmt} - {i}")
                varPtr = CIVarPtr(stmt.bases[i])
                self.bindingStmts.bindNewClass(varPtr, stmt, i)
                self.processNewClass(stmt, i, self.pointToSet.get(varPtr))

        elif(isinstance(stmt, Call)):
            # print(f"Bind Call: {stmt.callee} - {stmt}")
            varPtr = CIVarPtr(stmt.callee)
            self.bindingStmts.bindCall(varPtr, stmt)
            self.processCall(stmt, self.pointToSet.get(varPtr))

        elif(isinstance(stmt, DelAttr)):
            # print(f"Bind DelAttr: {stmt.var} - {stmt}")
            varPtr = CIVarPtr(stmt.var)
            self.bindingStmts.bindDelAttr(varPtr, stmt)
            self.processDelAttr(stmt, self.pointToSet.get(varPtr))

    def analyze(self, entry: ModuleCodeBlock):
        entryModule = ModuleObject(entry)
        self.workList.append((CIVarPtr(entry.globalVariable), {entryModule}))

        self.addReachable(entry)

        while(len(self.workList) > 0):
            ptr, objs = self.workList[0]
            del self.workList[0]

            if(len(objs) == 0):
                continue

            self.propagate(ptr, objs)

            if(not isinstance(ptr, CIVarPtr)):
                continue

            for stmt in self.bindingStmts.getSetAttr(ptr):
                self.processSetAttr(stmt, objs)

            for stmt in self.bindingStmts.getGetAttr(ptr):
               self.processGetAttr(stmt, objs)

            for stmt, index in self.bindingStmts.getNewClass(ptr):
                self.processNewClass(stmt, index, objs)

            for stmt in self.bindingStmts.getCall(ptr):
                self.processCall(stmt, objs)

            for stmt in self.bindingStmts.getDelAttr(ptr):
                self.processDelAttr(stmt, objs)
            
    def addFlow(self, source: Pointer, target: Pointer):
        if(self.pointerFlow.put(source, target)):
            # print(f"Add Flow:{source} -> {target}")
            objs = self.pointToSet.get(source)
            self.flow(source, target, objs)

    # Some objects flow from source to target
    # this function is needed because some transforming need to be done
    def flow(self, source: Pointer, target: Pointer, objs: Set[Object]):
        # do some transform
        newObjs = objs
        if(isinstance(source, AttrPtr) and isinstance(source.obj, ClassObject) 
            and isinstance(target, AttrPtr) and isinstance(target.obj, InstanceObject)):
            ins = target.obj
            newObjs = {MethodObject(ins, obj) if isinstance(obj, FunctionObject) else obj for obj in objs}
        self.workList.append((target, newObjs))

    def propagate(self, pointer: Pointer, objs: Set[Object]) -> Set:
        # Special condition: when source is a class object's attribute 
        # and target is an instance object's attribute
        # and the object is a function
        # print(f"Propagate {pointer} -> {', '.join([str(obj) for obj in objs])}")
        diff = self.pointToSet.putAll(pointer, objs)
        for succ in self.pointerFlow.getSuccessors(pointer):
            self.flow(pointer, succ, diff)
        
    # classObj.$r_attr <- parent.attr
    # where parent is the first class that has this attr as its persistent attributes along MRO
    def resolveAttribute(self, classObj: ClassObject, attr: str, resolveInfo: ResolveInfo):
        # if(not resolveInfo):
        #     if((FAKE_PREFIX + attr) in self.pointToSet.getAllAttr(classObj)):
                
        #         return
        #     for mro in self.classHiearchy.getMROs(classObj):
        #         self.resolveAttribute(classObj, attr, (mro, 0))
        # else:
        mro, start = resolveInfo
        childAttr = AttrPtr(classObj, FAKE_PREFIX + attr)
        for i in range(start, len(mro)):
            parent = mro[i]
            parentAttr = AttrPtr(parent, attr)
            self.addFlow(parentAttr, childAttr)
            if(attr in self.persist_attr[parent]):
                self.persist_attr[parent][attr].add((mro, i))
                break

    def resolveAttrIfNot(self, classObj: ClassObject, attr: str):
        if(FAKE_PREFIX + attr not in self.pointToSet.getAllAttr(classObj)):
            for mro in self.classHiearchy.getMROs(classObj):
                self.resolveAttribute(classObj, attr, (mro, 0))

    def processSetAttr(self, stmt: SetAttr, objs: Set[Object]):
        # print(f"Process SetAttr: {stmt}")
        assert(stmt, SetAttr)
        for obj in objs:
            attrPtr = AttrPtr(obj, stmt.attr)
            self.addFlow(CIVarPtr(stmt.source), attrPtr)

    def processGetAttr(self, stmt: GetAttr, objs: Set[Object]):
        # print(f"Process GetAttr: {stmt}")
        assert(stmt, GetAttr)
        for obj in objs:
            varPtr = CIVarPtr(stmt.target)
            if(isinstance(obj, InstanceObject)):
                # target <- instance.attr
                insAttr = AttrPtr(obj, stmt.attr)
                self.addFlow(insAttr, varPtr)
                classObj = obj.type
                self.resolveAttrIfNot(classObj, stmt.attr)
                # instance.attr <- class.$r_attr
                classAttr = AttrPtr(classObj, FAKE_PREFIX + stmt.attr)
                self.addFlow(classAttr, insAttr)

            elif(isinstance(obj, ClassObject)):
                self.resolveAttrIfNot(obj, stmt.attr)
                # instance.attr <- class.$r_attr
                classAttr = AttrPtr(obj, FAKE_PREFIX + stmt.attr)
                self.addFlow(classAttr, varPtr)
            else:
                attrPtr = AttrPtr(obj, stmt.attr)
                self.addFlow(attrPtr, varPtr)

    def processNewClass(self, stmt: NewClass, index: int, objs: Set[Object]):
        # print(f"Process NewClass: {stmt}")
        assert(stmt, NewClass)
        mroChange = set()
        for obj in objs:
            mroChange |= self.classHiearchy.addClassBase(CIClassObject(stmt), index, obj)
        for mro in mroChange:
            classObj = mro[0]
            for attr in self.pointToSet.getAllAttr(classObj):
                if(isFakeAttr(attr)):
                    attr = attr[len(FAKE_PREFIX):]
                    self.resolveAttribute(classObj, attr, mro, 0)

    def processCall(self, stmt: Call, objs: Set[Object]):
        # print(f"Process Call: {stmt}")
        assert(stmt, Call)
        varPtr = CIVarPtr(stmt.target)
        for obj in objs:
            if(isinstance(obj, FunctionObject)):
                func = obj.getCodeBlock()
                self.matchArgParam(posArgs=         [CIVarPtr(posArg) for posArg in stmt.posargs],
                                    kwArgs=         {kw:CIVarPtr(kwarg) for kw, kwarg in stmt.kwargs.items()},
                                    posParams=      [CIVarPtr(param) for param in func.posargs],
                                    kwParams=       {kw:CIVarPtr(kwOnlyParam) for kw, kwOnlyParam in func.kwargs.items()},
                                    varParam=       CIVarPtr(func.vararg) if func.vararg else None,
                                    kwParam=        CIVarPtr(func.kwarg) if func.kwarg else None)
                retVar = CIVarPtr(func.returnVariable)
                resVar = CIVarPtr(stmt.target)
                self.addFlow(retVar, resVar)
                self.addReachable(func)
                self.callgraph.put(stmt, func)
                
                
            elif(isinstance(obj, MethodObject)):
                func = obj.func.getCodeBlock()
                posParams = [CIVarPtr(param) for param in func.posargs]
                
                self.workList.append((posParams[0], {obj.selfObj}))
                del posParams[0]
                self.matchArgParam(posArgs=         [CIVarPtr(posArg) for posArg in stmt.posargs],
                                    kwArgs=         {kw:CIVarPtr(kwarg) for kw, kwarg in stmt.kwargs.items()},
                                    posParams=      posParams,
                                    kwParams=       {kw:CIVarPtr(kwOnlyParam) for kw, kwOnlyParam in func.kwargs.items()},
                                    varParam=       CIVarPtr(func.vararg) if func.vararg else None,
                                    kwParam=        CIVarPtr(func.kwarg) if func.kwarg else None)
                retVar = CIVarPtr(func.returnVariable)
                resVar = CIVarPtr(stmt.target)
                self.addFlow(retVar, resVar)
                self.callgraph.put(stmt, func)
                self.addReachable(func)
           
            elif(isinstance(obj, ClassObject)):
                insObj = CIInstanceObject(stmt, obj)
                varPtr = CIVarPtr(stmt.target)
                # target <- instance.attr
                insAttr = AttrPtr(insObj, "__init__")
                classAttr = AttrPtr(obj, FAKE_PREFIX + "__init__")
                self.addFlow(classAttr, insAttr)
                self.resolveAttrIfNot(obj, "__init__")

                init = Variable(f"{obj.getCodeBlock().qualified_name}.__init__", stmt.belongsTo)
                initPtr = CIVarPtr(init)
                self.addFlow(insAttr, initPtr)
                self.addStmt(Call(Variable("", stmt.belongsTo), init, stmt.posargs, stmt.kwargs, stmt.belongsTo))
                
                self.workList.append((varPtr, {insObj}))
                
    def matchArgParam(self, / , posArgs: List[CIVarPtr], 
                                kwArgs: Dict[str, CIVarPtr], 
                                posParams: List[CIVarPtr], 
                                kwParams: Dict[str, CIVarPtr],
                                varParam: CIVarPtr, kwParam: CIVarPtr):
    
        posCount = len(posParams)
        for i in range(len(posArgs)):
            if(i < posCount):
                self.addFlow(posArgs[i], posParams[i])
            elif(varParam):
                self.addStmt(SetAttr(varParam.var, "$values", posArgs[i].var, varParam.var.belongsTo))
                
        
        for kw, varPtr in kwArgs.items():
            if(kw in kwParams):
                self.addFlow(varPtr, kwParams[kw])
            elif(kwParam):
                self.addStmt(SetAttr(kwParam.var, "$values", varPtr.var, kwParam.var.belongsTo)) 


    def processDelAttr(self, stmt: DelAttr, objs: Set[Object]):
        # print(f"Process DelAttr: {stmt}")
        assert(stmt, DelAttr)
        attr = stmt.attr
        for obj in objs:
            if(isinstance(obj, ClassObject) and attr in self.persist_attr[obj]):
                for mro, index in self.persist_attr[obj][attr]:
                    self.resolveAttribute(mro[0], attr, (mro, index + 1))
                del self.persist_attr[obj][attr]

    def getResult(self) -> Tuple[PointToSet, CallGraph, PointerFlow]:
        return self.pointToSet, self.callgraph, self.pointerFlow