from typing import Dict, List, Set, Tuple, Union
import typing

from .CSCallGraph import CSCallGraph
if typing.TYPE_CHECKING:
    from . import CS_Call, CS_DelAttr, CS_GetAttr, CS_NewClass, CS_SetAttr, CSCodeBlock, CSStmt, CS_NewClassMethod, CS_NewStaticMethod, CS_NewSuper

from ..PTA.Objects import ClassMethodObject, ClassObject, FakeObject, FunctionObject, InstanceObject, InstanceMethodObject, ModuleObject, Object, StaticMethodObject, SuperObject
from .CSPointers import CSVarPtr

from .Context import emptyContextChain, selectContext

from ..PTA.Pointers import   AttrPtr, Pointer

from .CSObjects import CSBuiltinObject, CSClassObject, CSFunctionObject, CSInstanceObject, CSObject
from ..PTA.BindingStmts import BindingStmts

from ..PTA.PointerFlow import PointerFlow

from ..PTA.CallGraph import CallGraph

from ..PTA.PointToSet import PointToSet

from ..PTA.ClassHiearchy import MRO, ClassHiearchy
from ..IR.CodeBlock import ClassCodeBlock, CodeBlock, FunctionCodeBlock, ModuleCodeBlock
from ..IR.Stmts import Assign, Call, DelAttr, GetAttr, IRStmt, NewBuiltin, NewClass, NewClassMethod, NewFunction, NewModule, NewStaticMethod, NewSuper, SetAttr, Variable


FAKE_PREFIX = "$r_"
builtin_functions = ["abs", "aiter", "all", "any", "anext", "ascii", "bin", "bool", "breakpoint", "bytearray", "bytes", "callable", "chr", "classmethod", "compile", "complex", "delattr", "dict", "dir", "divmod", "enumerate", "eval", "exec", "filter", "float", "format", "frozenset", "getattr", "globals", "hasattr", "hash", "help", "hex", "id", "input", "int", "isinstance", "issubclass", "iter", "len", "list", "locals", "map", "max", "memoryview", "min", "next", "object", "oct", "open", "ord", "pow", "print", "property", "range", "repr", "reversed", "round", "set", "setattr", "slice", "sorted", "staticmethod", "str", "sum", "super", "tuple", "type", "vars", "zip", "__import__"]


def isFakeAttr(attr: str):
    return attr.startswith(FAKE_PREFIX)


Resolver = Union[ClassObject, SuperObject]
ResolveInfo = Tuple[Resolver, MRO, int]

ADD_POINT_TO = 1
BIND_STMT = 2

class Analysis:
    pointToSet: PointToSet
    callgraph: CallGraph
    pointerFlow: PointerFlow
    bindingStmts: BindingStmts
    reachable: Set['CSCodeBlock']
    resolved_attr: Dict[Resolver, Set[str]]
    classHiearchy: ClassHiearchy
    persist_attr: Dict[CSClassObject, Dict[str, Set[ResolveInfo]]]
    workList: List[Tuple[Pointer, Set[Object]]]
    def __init__(self, verbose=False):
        self.pointToSet = PointToSet()
        self.callgraph = CSCallGraph()
        self.pointerFlow = PointerFlow()
        self.bindingStmts = BindingStmts()
        self.defined = set()
        self.reachable = set()
        self.classHiearchy = ClassHiearchy(self.pointToSet)
        self.resolved_attr = {}
        self.persist_attr = {}
        self.workList = []
        self.verbose = verbose

    def addReachable(self, csCodeBlock: 'CSCodeBlock'):
        if(csCodeBlock in self.reachable):
            return
        self.reachable.add(csCodeBlock)

        ctx, codeBlock = csCodeBlock
        # Add codes into the pool
        for stmt in codeBlock.stmts:
            csStmt = (ctx, stmt)
            self.workList.append((BIND_STMT, csStmt))

        for stmt in codeBlock.stmts:
            csStmt = (ctx, stmt)
            if(isinstance(stmt, Assign)):
                sourcePtr = CSVarPtr(ctx ,stmt.source)
                targetPtr = CSVarPtr(ctx, stmt.target)
                self.addFlow(sourcePtr, targetPtr)

            elif(isinstance(stmt, NewModule)):
                if(isinstance(stmt.module, ModuleCodeBlock)):
                    obj = ModuleObject(stmt.module)

                    targetPtr = CSVarPtr(ctx, stmt.target)
                    globalPtr = CSVarPtr(ctx, stmt.module.globalVariable)

                    self.workList.append((ADD_POINT_TO, targetPtr, {obj}))
                    self.workList.append((ADD_POINT_TO, globalPtr, {obj}))

                    csCodeBlock = (emptyContextChain(), stmt.module)
                    self.addReachable(csCodeBlock)
                    # self.callgraph.put(csStmt, csCodeBlock)
                else:
                    obj = FakeObject(stmt.module, None)
                    targetPtr = CSVarPtr(ctx, stmt.target)
                    self.workList.append((ADD_POINT_TO, targetPtr, {obj}))
                
            elif(isinstance(stmt, NewFunction)):
                obj = CSFunctionObject(csStmt)
                targetPtr = CSVarPtr(ctx, stmt.target)
                self.workList.append((ADD_POINT_TO, targetPtr, {obj}))

            elif(isinstance(stmt, NewClass)):
                obj = CSClassObject(csStmt)
                targetPtr = CSVarPtr(ctx, stmt.target)

                thisPtr = CSVarPtr(ctx, stmt.codeBlock.thisClassVariable)
                self.workList.append((ADD_POINT_TO, targetPtr, {obj}))
                self.workList.append((ADD_POINT_TO, thisPtr, {obj}))
                
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
                self.workList.append((ADD_POINT_TO, targetPtr, {obj}))

    
    def analyze(self, entrys: ModuleCodeBlock):
        for entry in entrys:
            obj = ModuleObject(entry)
            self.workList.append((ADD_POINT_TO, CSVarPtr(emptyContextChain(), entry.globalVariable), {obj}))

            self.addReachable((emptyContextChain(), entry))

        while(len(self.workList) > 0):
            if(self.verbose):
                print(f"PTA worklist remains {len(self.workList)} to process.                \r", end="")
            type, *args = self.workList[0]
            del self.workList[0]

            if(type == ADD_POINT_TO):
                ptr, objs = args

                if(len(objs) == 0):
                    continue
                
                objs = self.pointToSet.putAll(ptr, objs)
                for succ in self.pointerFlow.getSuccessors(ptr):
                    self.flow(ptr, succ, objs)

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
                
                for csStmt in self.bindingStmts.getNewClassMethod(ptr):
                    self.processNewClassMethod(csStmt, objs)

                for csStmt in self.bindingStmts.getNewStaticMethod(ptr):
                    self.processNewStaticMethod(csStmt, objs)

                for csStmt in self.bindingStmts.getNewSuper_type(ptr):
                    self.processNewSuper_type(csStmt, objs)

                for csStmt in self.bindingStmts.getNewSuper_bound(ptr):
                    self.processNewSuper_bound(csStmt, objs)
            
            if(type == BIND_STMT):
                csStmt,  = args
                ctx, stmt = csStmt

                if(isinstance(stmt, SetAttr)):
                    # print(f"Bind SetAttr: {stmt.target} - {csStmt}")
                    varPtr = CSVarPtr(ctx, stmt.target)
                    self.bindingStmts.bindSetAttr(varPtr, csStmt)
                    self.processSetAttr(csStmt, self.pointToSet.get(varPtr))

                elif(isinstance(stmt, GetAttr)):
                    # print(f"Bind GetAttr: {stmt.source} - {csStmt}")
                    varPtr = CSVarPtr(ctx, stmt.source)
                    self.bindingStmts.bindGetAttr(varPtr, csStmt)
                    self.processGetAttr(csStmt, self.pointToSet.get(varPtr))

                elif(isinstance(stmt, NewClass)):
                    for i in range(len(stmt.bases)):
                        # print(f"Bind Base: {stmt.bases[i]} - {csStmt} - {i}")
                        varPtr = CSVarPtr(ctx, stmt.bases[i])
                        self.bindingStmts.bindNewClass(varPtr, csStmt, i)
                        self.processNewClass(csStmt, i, self.pointToSet.get(varPtr))

                elif(isinstance(stmt, Call)):
                    # print(f"Bind Call: {stmt.callee} - {csStmt}")
                    varPtr = CSVarPtr(ctx, stmt.callee)
                    self.bindingStmts.bindCall(varPtr, csStmt)
                    self.processCall(csStmt, self.pointToSet.get(varPtr))

                elif(isinstance(stmt, DelAttr)):
                    # print(f"Bind DelAttr: {stmt.var} - {csStmt}")
                    varPtr = CSVarPtr(ctx, stmt.var)
                    self.bindingStmts.bindDelAttr(varPtr, csStmt)
                    self.processDelAttr(csStmt, self.pointToSet.get(varPtr))

                elif(isinstance(stmt, NewClassMethod)):
                    varPtr = CSVarPtr(ctx, stmt.func)
                    self.bindingStmts.bindNewClassMethod(varPtr, csStmt)
                    self.processNewClassMethod(csStmt, self.pointToSet.get(varPtr))

                elif(isinstance(stmt, NewStaticMethod)):
                    varPtr = CSVarPtr(ctx, stmt.func)
                    self.bindingStmts.bindNewStaticMethod(varPtr, csStmt)
                    self.processNewStaticMethod(csStmt, self.pointToSet.get(varPtr))

                elif(isinstance(stmt, NewSuper)):
                    
                    varPtr = CSVarPtr(ctx, stmt.type)
                    self.bindingStmts.bindNewSuper_type(varPtr, csStmt)
                    self.processNewSuper_type(csStmt, self.pointToSet.get(varPtr))

                    varPtr = CSVarPtr(ctx, stmt.bound)
                    self.bindingStmts.bindNewSuper_bound(varPtr, csStmt)
                    self.processNewSuper_bound(csStmt, self.pointToSet.get(varPtr))


            
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
        if(isinstance(target, AttrPtr) and isFakeAttr(target.attr)):

            if(isinstance(target.obj, InstanceObject)):
                newObjs = self.transformObj_Instance(target.obj, objs)
                
            elif(isinstance(target.obj, ClassObject)):
                newObjs = self.transformObj_Class(target.obj, objs)
            elif(isinstance(target.obj, SuperObject)):
                if(isinstance(target.obj.bound, InstanceObject)):
                    newObjs = self.transformObj_Instance(target.obj.bound, objs)
                else:
                    newObjs = self.transformObj_Class(target.obj.bound, objs)

        self.workList.append((ADD_POINT_TO, target, newObjs))

    def transformObj_Instance(self, insObj: InstanceObject, objs) -> Set[Object]:
        newObjs = set()
        for obj in objs:
            if(isinstance(obj, FunctionObject)):
                newObjs.add(InstanceMethodObject(insObj, obj))
            elif(isinstance(obj, ClassMethodObject)):
                func = obj.func
                newObjs.add(ClassMethodObject(insObj.type, func))
            else:
                newObjs.add(obj)
        return newObjs

    def transformObj_Class(self, classObj: ClassObject, objs) -> Set[Object]:
        newObjs = set()
        for obj in objs:
            if(isinstance(obj, ClassMethodObject)):
                func = obj.func
                newObjs.add(ClassMethodObject(classObj, func))
            else:
                newObjs.add(obj)
        return newObjs

    
        
        
    # classObj.$r_attr <- parent.attr
    # where parent is the first class that has this attr as its persistent attributes along MRO
    def resolveAttribute(self, obj: Resolver, attr: str, resolveInfo: Tuple[MRO, int]):
       
        mro, start = resolveInfo
        childAttr = AttrPtr(obj, FAKE_PREFIX + attr)
        for i in range(start, len(mro)):
            parent = mro[i]
            parentAttr = AttrPtr(parent, attr)
            self.addFlow(parentAttr, childAttr)
            try:
                self.persist_attr[parent][attr].add((mro, i))
                break
            except(KeyError):
                pass

    def resolveAttrIfNot(self, obj: Resolver, attr: str):
        if(obj in self.resolved_attr):
            if(attr in self.resolved_attr[obj]):
                return
        else:
            self.resolved_attr[obj] = set()

        self.resolved_attr[obj].add(attr)

        if(isinstance(obj, ClassObject)):
            classObj = obj
        elif(isinstance(obj, SuperObject)):
            if(isinstance(obj.bound, InstanceObject)):
                classObj = obj.bound.type
            else:
                classObj = obj.bound

        for mro in self.classHiearchy.getMROs(classObj):
            if(isinstance(obj, ClassObject)):
                start = 0
            elif(isinstance(obj, SuperObject)):
                for start in range(len(mro)):
                    if(mro[start] == obj.type):
                        # start from the one right after type
                        start += 1
                        break
            self.resolveAttribute(obj, attr, (mro, start))

    def processSetAttr(self, csStmt: 'CS_SetAttr', objs: Set[CSObject]):
        # print(f"Process SetAttr: {csStmt}")
        assert(isinstance(csStmt[1], SetAttr))
        ctx, stmt = csStmt
        for obj in objs:
            attrPtr = AttrPtr(obj, stmt.attr)
            self.addFlow(CSVarPtr(ctx, stmt.source), attrPtr)

    def processGetAttr(self, csStmt: 'CS_GetAttr', objs: Set[Object]):
        # print(f"Process GetAttr: {csStmt}")
        assert(isinstance(csStmt[1], GetAttr))
        ctx, stmt = csStmt
        for obj in objs:
            varPtr = CSVarPtr(ctx, stmt.target)
            if(isinstance(obj, FakeObject)):
                try:
                    fakeObj = FakeObject(stmt.attr, obj)
                    self.workList.append((ADD_POINT_TO, varPtr, {fakeObj}))
                except(FakeObject.NoMore):
                    pass
            if(isinstance(obj, InstanceObject)):
                # target <- instance.attr
                insAttr = AttrPtr(obj, stmt.attr)
                insResAttr = AttrPtr(obj, FAKE_PREFIX + stmt.attr)
                self.addFlow(insAttr, varPtr)
                self.addFlow(insResAttr, varPtr)
                classObj = obj.type
                self.resolveAttrIfNot(classObj, stmt.attr)
                # instance.attr <- class.$r_attr
                classAttr = AttrPtr(classObj, FAKE_PREFIX + stmt.attr)
                self.addFlow(classAttr, insResAttr)

            elif(isinstance(obj, ClassObject)):
                self.resolveAttrIfNot(obj, stmt.attr)
                # instance.attr <- class.$r_attr
                classAttr = AttrPtr(obj, FAKE_PREFIX + stmt.attr)
                self.addFlow(classAttr, varPtr)

            elif(isinstance(obj, SuperObject)):
                self.resolveAttrIfNot(obj, stmt.attr)
                # instance.attr <- class.$r_attr
                superAttr = AttrPtr(obj, FAKE_PREFIX + stmt.attr)
                self.addFlow(superAttr, varPtr)

            else:
                attrPtr = AttrPtr(obj, stmt.attr)
                self.addFlow(attrPtr, varPtr)

    def processNewClass(self, csStmt: 'CS_NewClass', index:int, objs: Set[Object]):
        # print(f"Process NewClass: {csStmt}")
        assert(isinstance(csStmt[1], NewClass))
        ctx, stmt = csStmt
        mroChange = set()
        for obj in objs:
            if(isinstance(obj, ClassObject)):
                mroChange |= self.classHiearchy.addClassBase(CSClassObject(csStmt), index, obj)
        for mro in mroChange:
            classObj = mro[0]
            if(classObj not in self.resolved_attr):
                continue
            for attr in self.resolved_attr[classObj]:
                self.resolveAttribute(classObj, attr, (mro, 0))

    def processCall(self, csStmt: 'CS_Call', objs: Set[Object]):
        # print(f"Process Call: {csStmt}")
        assert(isinstance(csStmt[1], Call))
        ctx, stmt = csStmt
        varPtr = CSVarPtr(ctx, stmt.target)
        newObjs = set()
        for obj in objs:
            # if(isinstance(obj, FakeObject)):
            #     func = obj.getCodeBlock()
            #     csCodeBlock = (emptyContextChain(), func)
            #     self.callgraph.put(csStmt, csCodeBlock)
            if(isinstance(obj, FunctionObject)):
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
                
                
            elif(isinstance(obj, InstanceMethodObject)):
                func = obj.func.getCodeBlock()
                tailCTX = selectContext(csStmt, obj.selfObj)
                newCTX = *obj.func.ctxChain, tailCTX
                posParams = [CSVarPtr(newCTX, param) for param in func.posargs]
                if(len(posParams) == 0):
                    # not a method, just skip
                    continue

                self.workList.append((ADD_POINT_TO, posParams[0], {obj.selfObj}))
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
                
            elif(isinstance(obj, ClassMethodObject)):
                func = obj.func.getCodeBlock()
                tailCTX = selectContext(csStmt, obj.classObj)
                newCTX = *obj.func.ctxChain, tailCTX
                posParams = [CSVarPtr(newCTX, param) for param in func.posargs]
                
                if(len(posParams) == 0):
                    # not a method, just skip
                    continue
                self.workList.append((ADD_POINT_TO, posParams[0], {obj.classObj}))
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

            elif(isinstance(obj, StaticMethodObject)):
                func = obj.func.getCodeBlock()
                tailCTX = selectContext(csStmt, None)
                newCTX = *obj.func.ctxChain, tailCTX
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

            elif(isinstance(obj, ClassObject)):
                insObj = CSInstanceObject(csStmt, obj)
                # target <- instance.attr
                insAttr = AttrPtr(insObj, FAKE_PREFIX + "__init__")
                classAttr = AttrPtr(obj, FAKE_PREFIX + "__init__")
                self.addFlow(classAttr, insAttr)
                self.resolveAttrIfNot(obj, "__init__")

                init = Variable(f"${obj.getCodeBlock().qualified_name}.__init__", stmt.belongsTo)
                initPtr = CSVarPtr(ctx, init)
                self.addFlow(insAttr, initPtr)
                newStmt = (ctx, Call(Variable("", stmt.belongsTo), init, stmt.posargs, stmt.kwargs, stmt.belongsTo))
                self.workList.append((BIND_STMT, newStmt))
                
                newObjs.add(insObj)
        if(newObjs):
            self.workList.append((ADD_POINT_TO, varPtr, newObjs))
                
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
                self.addFlow(posArgs[i], varParam)
                
                
        
        for kw, varPtr in kwArgs.items():
            if(kw in kwParams):
                self.addFlow(varPtr, kwParams[kw])
            elif(kwParam):
                self.addFlow(kwArgs[kw], kwParam)
                


    def processDelAttr(self, csStmt: 'CS_DelAttr', objs: Set[CSObject]):
        # print(f"Process DelAttr: {csStmt}")
        assert(isinstance(csStmt[1], DelAttr))
        ctx, stmt = csStmt
        attr = stmt.attr
        for obj in objs:
            if(obj in self.persist_attr and attr in self.persist_attr[obj]):
                for mro, index in self.persist_attr[obj][attr]:
                    self.resolveAttribute(mro[0], attr, (mro, index + 1))
                del self.persist_attr[obj][attr]

    def processNewClassMethod(self, csStmt: 'CS_NewClassMethod', objs: Set[Object]):
        assert(isinstance(csStmt[1], NewClassMethod))
        ctx, stmt = csStmt
        target = CSVarPtr(ctx, stmt.target)
        newObjs = set()
        for obj in objs:
            if(isinstance(obj, FunctionObject) and isinstance(stmt.belongsTo, ClassCodeBlock)):
                for classObj in self.pointToSet.get(CSVarPtr(ctx, stmt.belongsTo.thisClassVariable)):
                    if(isinstance(classObj, ClassObject)):
                        classMethod = ClassMethodObject(classObj, obj)
                        newObjs.add(classMethod)
        if(newObjs):
            self.workList.append((ADD_POINT_TO, target, newObjs))

    def processNewStaticMethod(self, csStmt: 'CS_NewStaticMethod', objs: Set[Object]):
        assert(isinstance(csStmt[1], NewStaticMethod))
        ctx, stmt = csStmt
        newObjs = set()
        target = CSVarPtr(ctx, stmt.target)
        for obj in objs:
            if(isinstance(obj, FunctionObject) and isinstance(stmt.belongsTo, ClassCodeBlock)):
                staticMethod = StaticMethodObject(obj)
                newObjs.add(staticMethod)
        self.workList.append((ADD_POINT_TO, target, newObjs))

    def processNewSuper_type(self, csStmt: 'CS_NewSuper', objs: Set[Object]):
        assert(isinstance(csStmt[1], NewSuper))
        ctx, stmt = csStmt
        newObjs = set()
        target = CSVarPtr(ctx, stmt.target)
        for obj in objs:
            if(isinstance(obj, ClassObject)):
                for boundObj in self.pointToSet.get(CSVarPtr(ctx, stmt.bound)):
                    newObjs.add(SuperObject(obj, boundObj))
        if(newObjs):
            self.workList.append((ADD_POINT_TO, target, newObjs))

    def processNewSuper_bound(self, csStmt: 'CS_NewSuper', objs: Set[Object]):
        assert(isinstance(csStmt[1], NewSuper))
        ctx, stmt = csStmt
        newObjs = set()
        target = CSVarPtr(ctx, stmt.target)
        for obj in objs:
            if(isinstance(obj, ClassObject) or isinstance(obj, InstanceObject)):
                for typeObj in self.pointToSet.get(CSVarPtr(ctx, stmt.type)):
                    newObjs.add(SuperObject(typeObj, obj))
        if(newObjs):  
            self.workList.append((ADD_POINT_TO, target, newObjs))

    