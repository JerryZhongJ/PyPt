import threading
import time
from typing import Dict, List, Set, Tuple, Union
from ..IR.ClassCodeBlock import ClassCodeBlock

from ..IR.ModuleCodeBlock import ModuleCodeBlock

from ..IR.CodeBlock import CodeBlock

from ..IR.IRStmts import Assign, Call, DelAttr, GetAttr, NewBuiltin, NewClass, NewClassMethod, NewFunction, NewModule, NewStaticMethod, NewSuper, SetAttr, Variable
from .ClassHiearchy import MRO, ClassHiearchy
from .Objects import  CIBuiltinObject, CIClassObject, CIFunctionObject, CIInstanceObject, ClassMethodObject, ClassObject, FakeObject, FunctionObject, InstanceObject, InstanceMethodObject, ModuleObject, Object, StaticMethodObject, SuperObject
from .BindingStmts import BindingStmts
from .PointerFlow import PointerFlow
from .Pointers import AttrPtr, Pointer, CIVarPtr
from .CallGraph import CallGraph
from .PointToSet import PointToSet

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
    reachable: Set[CodeBlock]
    # defined: Set[CodeBlock]
    classHiearchy: ClassHiearchy
    persist_attr: Dict[ClassObject, Dict[str, Set[ResolveInfo]]]
    resolved_attr: Dict[Resolver, Set[str]]
    workList: List[Tuple[Pointer, Set[Object]]]
    def __init__(self, verbose=False):
        self.pointToSet = PointToSet()
        self.callgraph = CallGraph()
        self.pointerFlow = PointerFlow()
        self.bindingStmts = BindingStmts()
        # self.defined = set()
        self.reachable = set()
        self.classHiearchy = ClassHiearchy(self.pointToSet)
        self.persist_attr = {}
        self.resolved_attr = {}
        self.workList = []
        self.verbose = verbose

        self.processStmts = {
            "GetAttr": self.processGetAttr,
            "SetAttr": self.processSetAttr,
            "NewClass": self.processNewClass,
            "Call": self.processCall,
            "DelAttr": self.processDelAttr,
            "NewStaticMethod": self.processNewStaticMethod,
            "NewClassMethod": self.processNewClassMethod,
            "NewSuper": self.processNewSuper,
            
        }

    # addAll mean treat all codeblocks in this codeBlock as reachable.
    def addReachable(self, codeBlock: CodeBlock):
        if(codeBlock in self.reachable):
            return
        self.reachable.add(codeBlock)

        # Add codes into the pool
        for stmt in codeBlock.stmts:
            self.workList.append((BIND_STMT, stmt))

        for stmt in codeBlock.stmts:
            if(isinstance(stmt, Assign)):
                sourcePtr = CIVarPtr(stmt.source)
                targetPtr = CIVarPtr(stmt.target)
                self.addFlow(sourcePtr, targetPtr)

            elif(isinstance(stmt, NewModule)):
                if(isinstance(stmt.module, ModuleCodeBlock)):
                    obj = ModuleObject(stmt.module)
                    targetPtr = CIVarPtr(stmt.target)
                    globalPtr = CIVarPtr(stmt.module.globalVariable)
                    self.workList.append((ADD_POINT_TO, targetPtr, {obj}))
                    self.workList.append((ADD_POINT_TO, globalPtr, {obj}))
                    # self.addDefined(stmt.module)
                    self.addReachable(stmt.module)
                    # self.callgraph.put(stmt, stmt.module)
                else:
                    obj = FakeObject(stmt.module, None)
                    targetPtr = CIVarPtr(stmt.target)
                    self.workList.append((ADD_POINT_TO, targetPtr, {obj}))
                
                
            elif(isinstance(stmt, NewFunction)):
                obj = CIFunctionObject(stmt)
                targetPtr = CIVarPtr(stmt.target)
                self.workList.append((ADD_POINT_TO, targetPtr, {obj}))
                

            elif(isinstance(stmt, NewClass)):
                obj = CIClassObject(stmt)
                targetPtr = CIVarPtr(stmt.target)
                thisPtr = CIVarPtr(stmt.codeBlock.thisClassVariable)
                self.workList.append((ADD_POINT_TO, targetPtr, {obj}))
                self.workList.append((ADD_POINT_TO, thisPtr, {obj}))
                
                self.classHiearchy.addClass(obj)
                self.persist_attr[obj] = {}
                for attr in obj.getAttributes():
                    self.persist_attr[obj][attr] = set()
                
                self.addReachable(stmt.codeBlock)
                self.callgraph.put(stmt, stmt.codeBlock)
                

            elif(isinstance(stmt, NewBuiltin)):
                targetPtr = CIVarPtr(stmt.target)
                # if(stmt.value is not None or stmt.type == "NoneType"):
                #     obj = ConstObject(stmt.value)
                # else:
                obj = CIBuiltinObject(stmt)
                self.workList.append((ADD_POINT_TO, targetPtr, {obj}))
        

    def analyze(self, entrys: ModuleCodeBlock):
        for entry in entrys:
            obj = ModuleObject(entry)
            self.workList.append((ADD_POINT_TO, CIVarPtr(entry.globalVariable), {obj}))
            
            self.addReachable(entry)

        
        
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
                if(objs):
                    for succ in self.pointerFlow.getSuccessors(ptr):
                        self.flow(ptr,succ, objs)

                if(not isinstance(ptr, CIVarPtr)):
                    continue

                for opname, process in self.processStmts.items():
                    for stmtInfo in self.bindingStmts.get(opname, ptr):
                        process(stmtInfo, objs)


            if(type == BIND_STMT):
                stmt, = args
                
                if(isinstance(stmt, SetAttr)):
                    # print(f"Bind SetAttr: {stmt.target} - {stmt}")
                    varPtr = CIVarPtr(stmt.target)
                    stmtInfo = (stmt, )
                    self.bindingStmts.bind("SetAttr", varPtr, stmtInfo)
                    self.processSetAttr(stmtInfo, self.pointToSet.get(varPtr))

                elif(isinstance(stmt, GetAttr)):
                    # print(f"Bind GetAttr: {stmt.source} - {stmt}")
                    varPtr = CIVarPtr(stmt.source)
                    stmtInfo = (stmt, )
                    self.bindingStmts.bind("GetAttr", varPtr, stmtInfo)
                    self.processGetAttr(stmtInfo, self.pointToSet.get(varPtr))

                elif(isinstance(stmt, NewClass)):
                    for i in range(len(stmt.bases)):
                        # print(f"Bind Base: {stmt.bases[i]} - {stmt} - {i}")
                        varPtr = CIVarPtr(stmt.bases[i])
                        stmtInfo = (stmt, i)
                        self.bindingStmts.bind("NewClass", varPtr, stmtInfo)
                        self.processNewClass(stmtInfo, self.pointToSet.get(varPtr))

                elif(isinstance(stmt, Call)):
                    # print(f"Bind Call: {stmt.callee} - {stmt}")
                    varPtr = CIVarPtr(stmt.callee)
                    stmtInfo = (stmt, )
                    self.bindingStmts.bind("Call", varPtr, stmtInfo)
                    self.processCall(stmtInfo, self.pointToSet.get(varPtr))

                elif(isinstance(stmt, DelAttr)):
                    # print(f"Bind DelAttr: {stmt.var} - {stmt}")
                    varPtr = CIVarPtr(stmt.var)
                    stmtInfo = (stmt, )
                    self.bindingStmts.bind("DelAttr", varPtr, stmtInfo)
                    self.processDelAttr(stmtInfo, self.pointToSet.get(varPtr))
                
                elif(isinstance(stmt, NewClassMethod)):
                    varPtr = CIVarPtr(stmt.func)
                    stmtInfo = (stmt, )
                    self.bindingStmts.bind("NewClassMethod", varPtr, stmtInfo)
                    self.processNewClassMethod(stmtInfo, self.pointToSet.get(varPtr))

                elif(isinstance(stmt, NewStaticMethod)):
                    varPtr = CIVarPtr(stmt.func)
                    stmtInfo = (stmt, )
                    self.bindingStmts.bind("NewStaticMethod", varPtr, stmtInfo)
                    self.processNewStaticMethod(stmtInfo, self.pointToSet.get(varPtr))

                elif(isinstance(stmt, NewSuper)):
                    
                    varPtr = CIVarPtr(stmt.type)
                    stmtInfo = (stmt, "type")
                    self.bindingStmts.bind("NewSuper", varPtr, stmtInfo)
                    self.processNewSuper(stmtInfo, self.pointToSet.get(varPtr))

                    varPtr = CIVarPtr(stmt.bound)
                    stmtInfo = (stmt, "bound")
                    self.bindingStmts.bind("NewSuper", varPtr, stmtInfo)
                    self.processNewSuper(stmtInfo, self.pointToSet.get(varPtr))

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
                self.persist_attr[parent][attr].add((obj, mro, i))
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

    def processSetAttr(self, stmtInfo: Tuple[SetAttr], objs: Set[Object]):
        stmt,  = *stmtInfo,
        assert(isinstance(stmt, SetAttr))
        for obj in objs:
            attrPtr = AttrPtr(obj, stmt.attr)
            self.addFlow(CIVarPtr(stmt.source), attrPtr)

    def processGetAttr(self, stmtInfo: Tuple[GetAttr], objs: Set[Object]):
        stmt, = *stmtInfo, 
        assert(isinstance(stmt, GetAttr))
        for obj in objs:
            varPtr = CIVarPtr(stmt.target)
            if(isinstance(obj, FakeObject)):
                try:
                    fakeObj = FakeObject(stmt.attr, obj)
                    self.workList.append((ADD_POINT_TO, varPtr, {fakeObj}))
                except(FakeObject.NoMore):
                    pass
            elif(isinstance(obj, InstanceObject)):
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

    def processNewClass(self, stmtInfo: Tuple[NewClass, int], objs: Set[Object]):
        stmt, index = *stmtInfo,
        assert(isinstance(stmt, NewClass))
        mroChange = set()
        for obj in objs:
            if(isinstance(obj, ClassObject)):
                mroChange |= self.classHiearchy.addClassBase(CIClassObject(stmt), index, obj)
        for mro in mroChange:
            classObj = mro[0]
            if(classObj not in self.resolved_attr):
                continue
            for attr in self.resolved_attr[classObj]:
                self.resolveAttribute(classObj, attr, (mro, 0))

    def processCall(self, stmtInfo: Tuple[Call], objs: Set[Object]):
        stmt, = *stmtInfo,
        assert(isinstance(stmt, Call))
        varPtr = CIVarPtr(stmt.target)
        newObjs = set()
        for obj in objs:
            # if(isinstance(obj, FakeObject)):
            #     func = obj.getCodeBlock()
            #     self.callgraph.put(stmt, func)
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
                
                
            elif(isinstance(obj, InstanceMethodObject)):
                func = obj.func.getCodeBlock()
                posParams = [CIVarPtr(param) for param in func.posargs]
                if(len(posParams) == 0):
                    # not a method, just skip
                    continue
                self.workList.append((ADD_POINT_TO, posParams[0], {obj.selfObj}))
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

            elif(isinstance(obj, ClassMethodObject)):
                func = obj.func.getCodeBlock()
                posParams = [CIVarPtr(param) for param in func.posargs]
                if(len(posParams) == 0):
                    # not a method, just skip
                    continue
                self.workList.append((ADD_POINT_TO, posParams[0], {obj.classObj}))
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

            elif(isinstance(obj, StaticMethodObject)):
                func = obj.func.getCodeBlock()
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
           
            elif(isinstance(obj, ClassObject)):
                insObj = CIInstanceObject(stmt, obj)
                
                # target <- instance.attr
                insAttr = AttrPtr(insObj, FAKE_PREFIX + "__init__")
                classAttr = AttrPtr(obj, FAKE_PREFIX + "__init__")
                self.addFlow(classAttr, insAttr)
                self.resolveAttrIfNot(obj, "__init__")

                init = Variable(f"${obj.getCodeBlock().qualified_name}.__init__", stmt.belongsTo)
                initPtr = CIVarPtr(init)
                self.addFlow(insAttr, initPtr)
                newStmt = Call(Variable("", stmt.belongsTo), init, stmt.posargs, stmt.kwargs, stmt.belongsTo)
                self.workList.append((BIND_STMT, newStmt))
                newObjs.add(insObj)
        if(newObjs):
            self.workList.append((ADD_POINT_TO, varPtr, newObjs))
                
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
                self.addFlow(posArgs[i], varParam)
                
        for kw, varPtr in kwArgs.items():
            if(kw in kwParams):
                self.addFlow(varPtr, kwParams[kw])
            elif(kwParam):
                self.addFlow(kwArgs[kw], kwParam)
                
    def processDelAttr(self, stmtInfo: Tuple[DelAttr], objs: Set[Object]):
        stmt,  = *stmtInfo, 
        assert(isinstance(stmt, DelAttr))
        attr = stmt.attr
        for obj in objs:
            if(obj in self.persist_attr
                and attr in self.persist_attr[obj]):
                for resolver, mro, index in self.persist_attr[obj][attr]:
                    self.resolveAttribute(resolver, attr, (mro, index + 1))
                del self.persist_attr[obj][attr]

    def processNewClassMethod(self, stmtInfo: Tuple[NewClassMethod], objs: Set[Object]):
        stmt, = *stmtInfo, 
        assert(isinstance(stmt, NewClassMethod))
        target = CIVarPtr(stmt.target)
        newObjs = set()
        for obj in objs:
            if(isinstance(obj, FunctionObject) and isinstance(stmt.belongsTo, ClassCodeBlock)):
                
                for classObj in self.pointToSet.get(CIVarPtr(stmt.belongsTo.thisClassVariable)):
                    if(isinstance(classObj, ClassObject)):
                        classMethod = ClassMethodObject(classObj, obj)
                        newObjs.add(classMethod)
        if(newObjs):
            self.workList.append((ADD_POINT_TO, target, newObjs))

    def processNewStaticMethod(self, stmtInfo: Tuple[NewStaticMethod], objs: Set[Object]):
        stmt, = *stmtInfo, 
        assert(isinstance(stmt, NewStaticMethod))
        target = CIVarPtr(stmt.target)
        newObjs = set()
        for obj in objs:
            if(isinstance(obj, FunctionObject) and isinstance(stmt.belongsTo, ClassCodeBlock)):
                
                staticMethod = StaticMethodObject(obj)
                newObjs.add(staticMethod)
        if(newObjs):
            self.workList.append((ADD_POINT_TO, target, newObjs))

    def processNewSuper(self, stmtInfo: NewSuper, objs: Set[Object]):
        stmt, operand = *stmtInfo,
        assert(isinstance(stmt, NewSuper))
        if(operand == "type"):
            newObjs = set()
            target = CIVarPtr(stmt.target)
            for obj in objs:
                if(isinstance(obj, ClassObject)):
                    for boundObj in self.pointToSet.get(CIVarPtr(stmt.bound)):
                        newObjs.add(SuperObject(obj, boundObj))
            if(newObjs):
                self.workList.append((ADD_POINT_TO, target, newObjs))
        else:
            newObjs = set()
            target = CIVarPtr(stmt.target)
            for obj in objs:
                if(isinstance(obj, ClassObject) or isinstance(obj, InstanceObject)):
                    for typeObj in self.pointToSet.get(CIVarPtr(stmt.type)):
                        newObjs.add(SuperObject(typeObj, obj))
            if(newObjs):
                self.workList.append((ADD_POINT_TO, target, newObjs))


        


    
        


    