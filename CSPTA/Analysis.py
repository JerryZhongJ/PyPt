from typing import Dict, List, Set, Tuple, Union
import typing
if typing.TYPE_CHECKING:
    from . import CS_Call, CS_DelAttr, CS_GetAttr, CS_NewClass, CS_SetAttr, CSCodeBlock, CSStmt

from ..PTA.Objects import ClassObject, FunctionObject, InstanceObject, MethodObject, ModuleObject, Object
from ..CSPTA.CSPointers import CSVarPtr

from .Context import emptyContextChain, selectContext

from ..PTA.Pointers import   AttrPtr, Pointer

from .CSObjects import CSBuiltinObject, CSClassObject, CSFunctionObject, CSInstanceObject, CSObject
from ..PTA.BindingStmts import BindingStmts

from ..PTA.PointerFlow import PointerFlow

from ..PTA.CallGraph import CallGraph

from ..PTA.PointToSet import PointToSet

from ..PTA.ClassHiearchy import MRO, ClassHiearchy
from ..IR.CodeBlock import CodeBlock, FunctionCodeBlock, ModuleCodeBlock
from ..IR.Stmts import Assign, Call, DelAttr, GetAttr, IRStmt, NewBuiltin, NewClass, NewFunction, NewModule, SetAttr, Variable


FAKE_PREFIX = "$r_"




def isFakeAttr(attr: str):
    return attr.startswith(FAKE_PREFIX)
ResolveInfo = Tuple[MRO, int]
class Analysis:
    pointToSet: PointToSet
    callgraph: CallGraph
    pointerFlow: PointerFlow
    bindingStmts: BindingStmts
    reachable: Set['CSCodeBlock']
    # defined: Set[CodeBlock]
    classHiearchy: ClassHiearchy
    persist_attr: Dict[CSClassObject, Dict[str, Set[ResolveInfo]]]
    workList: List[Tuple[Pointer, Set[Object]]]
    def __init__(self):
        self.pointToSet = PointToSet()
        self.callgraph = CallGraph(cs=True)
        self.pointerFlow = PointerFlow()
        self.bindingStmts = BindingStmts()
        self.defined = set()
        self.reachable = set()
        self.classHiearchy = ClassHiearchy(self.pointToSet)
        self.persist_attr = {}
        self.workList = []

    def addReachable(self, csCodeBlock: 'CSCodeBlock'):
        if(csCodeBlock in self.reachable):
            return
        self.reachable.add(csCodeBlock)

        ctx, codeBlock = csCodeBlock
        # Add codes into the pool
        for stmt in codeBlock.stmts:
            csStmt = (ctx, stmt)
            self.addStmt(csStmt)

        for stmt in codeBlock.stmts:
            csStmt = (ctx, stmt)
            if(isinstance(stmt, Assign)):
                sourcePtr = CSVarPtr(ctx ,stmt.source)
                targetPtr = CSVarPtr(ctx, stmt.target)
                self.addFlow(sourcePtr, targetPtr)

            elif(isinstance(stmt, NewModule)):
                
                obj = ModuleObject(stmt.codeBlock)

                targetPtr = CSVarPtr(ctx, stmt.target)
                globalPtr = CSVarPtr(ctx, stmt.codeBlock.globalVariable)

                self.workList.append((targetPtr, {obj}))
                self.workList.append((globalPtr, {obj}))

                csCodeBlock = (emptyContextChain(), stmt.codeBlock)
                self.addReachable(csCodeBlock)
                self.callgraph.put(stmt, stmt.codeBlock)
                
            elif(isinstance(stmt, NewFunction)):
                obj = CSFunctionObject(csStmt)
                targetPtr = CSVarPtr(ctx, stmt.target)
                self.workList.append((targetPtr, {obj}))

            elif(isinstance(stmt, NewClass)):
                obj = CSClassObject(csStmt)
                targetPtr = CSVarPtr(ctx, stmt.target)

                thisPtr = CSVarPtr(ctx, stmt.codeBlock.thisClassVariable)
                self.workList.append((targetPtr, {obj}))
                self.workList.append((thisPtr, {obj}))
                
                csCodeBlock = (ctx, stmt.codeBlock)
                self.addReachable(csCodeBlock)
                self.callgraph.put(csStmt, csCodeBlock)
                
                self.classHiearchy.addClass(obj)
                self.persist_attr[obj] = {}
                for attr in obj.getAttributes():
                    self.persist_attr[obj][attr] = set()

            elif(isinstance(stmt, NewBuiltin)):
                targetPtr = CSVarPtr(ctx, stmt.target)
                # if(stmt.value is not None or stmt.type == "NoneType"):
                #     obj = ConstObject(stmt.value)
                # else:
                obj = CSBuiltinObject(csStmt)
                self.workList.append((targetPtr, {obj}))

    def addStmt(self, csStmt: 'CSStmt'):
        ctx, stmt = csStmt
        if(isinstance(stmt, SetAttr)):
            print(f"Bind SetAttr: {stmt.target} - {csStmt}")
            varPtr = CSVarPtr(ctx, stmt.target)
            self.bindingStmts.bindSetAttr(varPtr, csStmt)
            self.processSetAttr(csStmt, self.pointToSet.get(varPtr))

        elif(isinstance(stmt, GetAttr)):
            print(f"Bind GetAttr: {stmt.source} - {csStmt}")
            varPtr = CSVarPtr(ctx, stmt.source)
            self.bindingStmts.bindGetAttr(varPtr, csStmt)
            self.processGetAttr(csStmt, self.pointToSet.get(varPtr))

        elif(isinstance(stmt, NewClass)):
            for i in range(len(stmt.bases)):
                print(f"Bind Base: {stmt.bases[i]} - {csStmt} - {i}")
                varPtr = CSVarPtr(ctx, stmt.bases[i])
                self.bindingStmts.bindNewClass(varPtr, csStmt, i)
                self.processNewClass(csStmt, i, self.pointToSet.get(varPtr))

        elif(isinstance(stmt, Call)):
            print(f"Bind Call: {stmt.callee} - {csStmt}")
            varPtr = CSVarPtr(ctx, stmt.callee)
            self.bindingStmts.bindCall(varPtr, csStmt)
            self.processCall(csStmt, self.pointToSet.get(varPtr))

        elif(isinstance(stmt, DelAttr)):
            print(f"Bind DelAttr: {stmt.var} - {csStmt}")
            varPtr = CSVarPtr(ctx, stmt.var)
            self.bindingStmts.bindDelAttr(varPtr, csStmt)
            self.processDelAttr(csStmt, self.pointToSet.get(varPtr))

    def analyze(self, entry: ModuleCodeBlock):
        entryModule = ModuleObject(entry)
        self.workList.append((CSVarPtr(emptyContextChain(), entry.globalVariable), {entryModule}))

        self.addReachable((emptyContextChain(), entry))

        while(len(self.workList) > 0):
            ptr, objs = self.workList[0]
            del self.workList[0]

            if(len(objs) == 0):
                continue

            self.propagate(ptr, objs)

            if(not isinstance(ptr, CSVarPtr)):
                continue

            for csStmt in self.bindingStmts.getSetAttr(ptr):
                self.processSetAttr(csStmt, objs)

            for csStmt in self.bindingStmts.getGetAttr(ptr):
               self.processGetAttr(csStmt, objs)

            for csStmt, index in self.bindingStmts.getNewClass(ptr):
                self.processNewClass(csStmt, index, objs)

            for csStmt in self.bindingStmts.getCall(ptr):
                self.processCall(csStmt, objs)

            for csStmt in self.bindingStmts.getDelAttr(ptr):
                self.processDelAttr(csStmt, objs)
            
    def addFlow(self, source: Pointer, target: Pointer):
        if(self.pointerFlow.put(source, target)):
            print(f"Add Flow:{source} -> {target}")
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
        print(f"Propagate {pointer} -> {', '.join([str(obj) for obj in objs])}")
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

    def processSetAttr(self, csStmt: 'CS_SetAttr', objs: Set[CSObject]):
        print(f"Process SetAttr: {csStmt}")
        assert(csStmt[1], SetAttr)
        ctx, stmt = csStmt
        for obj in objs:
            attrPtr = AttrPtr(obj, stmt.attr)
            self.addFlow(CSVarPtr(ctx, stmt.source), attrPtr)

    def processGetAttr(self, csStmt: 'CS_GetAttr', objs: Set[Object]):
        print(f"Process GetAttr: {csStmt}")
        assert(csStmt[1], GetAttr)
        ctx, stmt = csStmt
        for obj in objs:
            varPtr = CSVarPtr(ctx, stmt.target)
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

    def processNewClass(self, csStmt: 'CS_NewClass', index:int, objs: Set[Object]):
        print(f"Process NewClass: {csStmt}")
        assert(csStmt[1], NewClass)
        ctx, stmt = csStmt
        mroChange = set()
        for obj in objs:
            mroChange |= self.classHiearchy.addClassBase(CSClassObject(csStmt), index, obj)
        for mro in mroChange:
            classObj = mro[0]
            for attr in self.pointToSet.getAllAttr(classObj):
                if(isFakeAttr(attr)):
                    attr = attr[len(FAKE_PREFIX):]
                    self.resolveAttribute(classObj, attr, mro, 0)

    def processCall(self, csStmt: 'CS_Call', objs: Set[Object]):
        print(f"Process Call: {csStmt}")
        assert(csStmt[1], Call)
        ctx, stmt = csStmt
        varPtr = CSVarPtr(ctx, stmt.target)
        for obj in objs:
            if(isinstance(obj, CSFunctionObject)):
                func = obj.getCodeBlock()
                tailCTX = selectContext(csStmt, None)
                newCTX = *obj.ctxChain, tailCTX
                self.matchArgParam(posArgs=         [CSVarPtr(ctx, posArg) for posArg in stmt.posargs],
                                    kwArgs=         {kw:CSVarPtr(ctx, kwarg) for kw, kwarg in stmt.kwargs.items()},
                                    posParams=      [CSVarPtr(newCTX, param) for param in func.posargs],
                                    kwParams=       {kw:CSVarPtr(newCTX, kwOnlyParam) for kw, kwOnlyParam in func.kwargs.items()},
                                    varParam=       CSVarPtr(newCTX, func.vararg) if func.vararg else None,
                                    kwParam=        CSVarPtr(newCTX, func.kwarg) if func.kwarg else None)
                retVar = CSVarPtr(newCTX, func.returnVariable)
                resVar = CSVarPtr(ctx, stmt.target)
                self.addFlow(retVar, resVar)
                csCodeBlock = (newCTX, func)
                self.addReachable(csCodeBlock)
                self.callgraph.put(csStmt, csCodeBlock)
                
                
            elif(isinstance(obj, MethodObject)):
                func = obj.func.getCodeBlock()
                tailCTX = selectContext(csStmt, obj.selfObj)
                newCTX = *obj.func.ctxChain, tailCTX
                posParams = [CSVarPtr(newCTX, param) for param in func.posargs]
                
                self.workList.append((posParams[0], {obj.selfObj}))
                del posParams[0]
                self.matchArgParam(posArgs=         [CSVarPtr(ctx, posArg) for posArg in stmt.posargs],
                                    kwArgs=         {kw:CSVarPtr(ctx, kwarg) for kw, kwarg in stmt.kwargs.items()},
                                    posParams=      posParams,
                                    kwParams=       {kw:CSVarPtr(newCTX, kwOnlyParam) for kw, kwOnlyParam in func.kwargs.items()},
                                    varParam=       CSVarPtr(newCTX, func.vararg) if func.vararg else None,
                                    kwParam=        CSVarPtr(newCTX, func.kwarg) if func.kwarg else None)
                retVar = CSVarPtr(newCTX, func.returnVariable)
                resVar = CSVarPtr(ctx, stmt.target)
                self.addFlow(retVar, resVar)
                csCodeBlock = (newCTX, func)
                self.addReachable(csCodeBlock)
                self.callgraph.put(csStmt, csCodeBlock)
                
           
            elif(isinstance(obj, ClassObject)):
                insObj = CSInstanceObject(csStmt, obj)
                varPtr = CSVarPtr(ctx, stmt.target)
                # target <- instance.attr
                insAttr = AttrPtr(insObj, "__init__")
                classAttr = AttrPtr(obj, FAKE_PREFIX + "__init__")
                self.addFlow(classAttr, insAttr)
                self.resolveAttrIfNot(obj, "__init__")

                init = Variable(f"{obj.getCodeBlock().qualified_name}.__init__", stmt.belongsTo)
                initPtr = CSVarPtr(ctx, init)
                self.addFlow(insAttr, initPtr)
                self.addStmt((ctx, Call(Variable("", stmt.belongsTo), init, stmt.posargs, stmt.kwargs, stmt.belongsTo)))
                
                self.workList.append((varPtr, {insObj}))
                
    def matchArgParam(self, / , posArgs: List[CSVarPtr], 
                                kwArgs: Dict[str, CSVarPtr], 
                                posParams: List[CSVarPtr], 
                                kwParams: Dict[str, CSVarPtr],
                                varParam: CSVarPtr, kwParam: CSVarPtr):
    
        posCount = len(posParams)
        for i in range(len(posArgs)):
            if(i < posCount):
                self.addFlow(posArgs[i], posParams[i])
            elif(varParam):
                csStmt = varParam.ctxChain, SetAttr(varParam.var, "$values", posArgs[i].var, varParam.var.belongsTo)
                self.addStmt(csStmt)
                
        
        for kw, varPtr in kwArgs.items():
            if(kw in kwParams):
                self.addFlow(varPtr, kwParams[kw])
            elif(kwParam):
                csStmt = kwParam.ctxChain, SetAttr(kwParam.var, "$values", varPtr.var, kwParam.var.belongsTo)
                self.addStmt(csStmt) 


    def processDelAttr(self, csStmt: 'CS_DelAttr', objs: Set[CSObject]):
        print(f"Process DelAttr: {csStmt}")
        assert(csStmt[1], DelAttr)
        ctx, stmt = csStmt
        attr = stmt.attr
        for obj in objs:
            if(isinstance(obj, ClassObject) and attr in self.persist_attr[obj]):
                for mro, index in self.persist_attr[obj][attr]:
                    self.resolveAttribute(mro[0], attr, (mro, index + 1))
                del self.persist_attr[obj][attr]

    def getResult(self) -> Tuple[PointToSet, CallGraph, PointerFlow]:
        return self.pointToSet, self.callgraph, self.pointerFlow