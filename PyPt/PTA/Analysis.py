from collections import defaultdict

from typing import Dict, List, Set, Tuple, Union

from PyPt.PTA.ObjectPool import OBJ_BUILTIN, OBJ_CLASS, OBJ_CLASS_METHOD, OBJ_FAKE, OBJ_FUNCTION, OBJ_MODULE, OBJ_STATIC_METHOD, OBJ_SUPER, ObjectPool

from .AttrGraph import AttrGraph
from ..IR.ClassCodeBlock import ClassCodeBlock

from ..IR.ModuleCodeBlock import ModuleCodeBlock

from ..IR.CodeBlock import CodeBlock

from ..IR.IRStmts import Assign, Call, DelAttr, GetAttr, IRStmt, NewBuiltin, NewClass, NewFunction, NewModule, NewStaticMethod, NewSuper, SetAttr, Variable
from .ClassHiearchy import MRO, ClassHiearchy
from .Objects import BuiltinObject, ClassMethodObject, ClassObject, FakeObject, FunctionObject,  ModuleObject, Object, StaticMethodObject, SuperObject
from .BindingStmts import BindingStmts
from .PointerFlow import PointerFlow
from .Pointers import AttrPtr, Pointer, VarPtr
from .PointToSet import PointToSet

FAKE_PREFIX = "$r_"
# builtin_functions = ["abs", "aiter", "all", "any", "anext", "ascii", "bin", "bool", "breakpoint", "bytearray", "bytes", "callable", "chr", "classmethod", "compile", "complex", "delattr", "dict", "dir", "divmod", "enumerate", "eval", "exec", "filter", "float", "format", "frozenset", "getattr", "globals", "hasattr", "hash", "help", "hex", "id", "input", "int", "isinstance", "issubclass", "iter", "len", "list", "locals", "map", "max", "memoryview", "min", "next", "object", "oct", "open", "ord", "pow", "print", "property", "range", "repr", "reversed", "round", "set", "setattr", "slice", "sorted", "staticmethod", "str", "sum", "super", "tuple", "type", "vars", "zip", "__import__"]

def isFakeAttr(attr: str):
    return attr.startswith(FAKE_PREFIX)

Resolver = Union[ClassObject, SuperObject]
ResolveInfo = Tuple[Resolver, MRO, int]

ADD_POINTS_TO = 1
BIND_STMT = 2

class Analysis:
    pointToSet: PointToSet
    callgraph: Dict[str, Set[str]]
    pointerFlow: PointerFlow
    attrGraph: AttrGraph
    
    
    # defined: Set[CodeBlock]
    classHiearchy: ClassHiearchy
    persist_attr: Dict[ClassObject, Dict[str, Set[ResolveInfo]]]
    resolved_attr: Dict[Resolver, Set[str]]
    workList: List[Tuple[Pointer, Set[Object]]]
    def __init__(self, verbose=False):
        self.pointToSet = PointToSet()
        self.callgraph = defaultdict(set)
        self.pointerFlow = PointerFlow()
        self.attrGraph = AttrGraph()
        self.bindingStmts = BindingStmts()
        self.objectPool = ObjectPool()
        self.reachable = set()
        self.classHiearchy = ClassHiearchy(self.pointToSet)
        self.persist_attr = defaultdict(dict)
        self.resolved_attr = defaultdict(set)
        self.workList = []
        self.verbose = verbose

        self.processStmts = {
            # "GetAttr": self.processGetAttr,
            # "SetAttr": self.processSetAttr,
            "NewClass": self.processNewClass,
            "Call": self.processCall,
            "DelAttr": self.processDelAttr,
            "NewStaticMethod": self.processNewStaticMethod,
            # "NewClassMethod": self.processNewClassMethod,
            "NewSuper": self.processNewSuper,
            
        }

    # addAll mean treat all codeblocks in this codeBlock as reachable.
    def addReachable(self, codeBlock: CodeBlock):
        if(not codeBlock or codeBlock in self.reachable):
            return
        self.reachable.add(codeBlock)

        # Add codes into the pool
        for stmt in codeBlock.stmts:
            self.workList.append((BIND_STMT, stmt))

        for stmt in codeBlock.stmts:
            if(isinstance(stmt, Assign)):
                sourcePtr = VarPtr.create(stmt.source)
                targetPtr = VarPtr.create(stmt.target)
                self.addFlow(sourcePtr, targetPtr)

            elif(isinstance(stmt, GetAttr)):
                sourcePtr = VarPtr.create(stmt.source)
                targetPtr = VarPtr.create(stmt.target)
                self.attrGraph.putGet(targetPtr, sourcePtr, stmt.attr)
                self.addGetEdge(targetPtr, sourcePtr, stmt.attr, self.pointToSet.get(sourcePtr))
            
            elif(isinstance(stmt, SetAttr)):
                sourcePtr = VarPtr.create(stmt.source)
                targetPtr = VarPtr.create(stmt.target)
                self.attrGraph.putSet(targetPtr, sourcePtr, stmt.attr)
                self.addSetEdge(targetPtr, sourcePtr, stmt.attr, self.pointToSet.get(targetPtr))

            elif(isinstance(stmt, NewModule)):
                if(isinstance(stmt.module, ModuleCodeBlock)):
                    obj = self.objectPool.create(OBJ_MODULE, stmt.module)
                    targetPtr = VarPtr.create(stmt.target)
                    globalPtr = VarPtr.create(stmt.module.globalVariable)
                    self.workList.append((ADD_POINTS_TO, targetPtr, {obj}))
                    self.workList.append((ADD_POINTS_TO, globalPtr, {obj}))
                    # self.addDefined(stmt.module)
                    self.addReachable(stmt.module)
                    # self.callgraph.put(stmt, stmt.module)
                else:
                    obj = self.objectPool.create(OBJ_FAKE, stmt.module)
                    targetPtr = VarPtr.create(stmt.target)
                    self.workList.append((ADD_POINTS_TO, targetPtr, {obj}))
                
                
            elif(isinstance(stmt, NewFunction)):
                obj = self.objectPool.create(OBJ_FUNCTION, stmt)
                targetPtr = VarPtr.create(stmt.target)
                self.workList.append((ADD_POINTS_TO, targetPtr, {obj}))
                

            elif(isinstance(stmt, NewClass)):
                obj = self.objectPool.create(OBJ_CLASS, stmt)
                targetPtr = VarPtr.create(stmt.target)
                thisPtr = VarPtr.create(stmt.codeBlock.thisClassVariable)
                self.workList.append((ADD_POINTS_TO, targetPtr, {obj}))
                self.workList.append((ADD_POINTS_TO, thisPtr, {obj}))
                
                self.classHiearchy.addClass(obj)
                
                for attr in obj.attributes:
                    self.persist_attr[obj][attr] = set()
                
                self.addReachable(stmt.codeBlock)
                # self.callgraph.put(stmt, stmt.codeBlock)
                self.addCallEdge(stmt, obj.readable_name)

            elif(isinstance(stmt, NewBuiltin)):
                targetPtr = VarPtr.create(stmt.target)
                # if(stmt.value is not None or stmt.type == "NoneType"):
                #     obj = ConstObject(stmt.value)
                # else:
                obj = self.objectPool.create(OBJ_BUILTIN, stmt)
                self.workList.append((ADD_POINTS_TO, targetPtr, {obj}))
        

    def analyze(self, entrys: CodeBlock):
        for entry in entrys:
            if(isinstance(entry, ModuleCodeBlock)):
                obj = self.objectPool.create(OBJ_MODULE, entry)
                self.workList.append((ADD_POINTS_TO, VarPtr.create(entry.globalVariable), {obj}))
            self.addReachable(entry)

        
        while(len(self.workList) > 0):

            if(self.verbose):
                print(f"PTA worklist remains {len(self.workList):<10} to process.                \r", end="")

            type, *args = self.workList[0]
            del self.workList[0]

            if(type == ADD_POINTS_TO):
                ptr, objs = args
                if(len(objs) == 0):
                    continue

                objs = self.pointToSet.putAll(ptr, objs)
                if(objs):
                    for succ in self.pointerFlow.successors(ptr):
                        self.flow(ptr,succ, objs)

                if(not isinstance(ptr, VarPtr)):
                    continue
                for target, attr in self.attrGraph.getTargets(ptr):
                    self.addGetEdge(target, ptr, attr, objs)
                
                for source, attr in self.attrGraph.setSources(ptr):
                    self.addSetEdge(ptr, source, attr, objs)

                for opname, process in self.processStmts.items():
                    for stmtInfo in self.bindingStmts.get(opname, ptr):
                        process(stmtInfo, objs)


            if(type == BIND_STMT):
                stmt, = args
                
                # if(isinstance(stmt, SetAttr)):
                #     # print(f"Bind SetAttr: {stmt.target} - {stmt}")
                #     varPtr = VarPtr.create(stmt.target)
                #     stmtInfo = (stmt, )
                #     self.bindingStmts.bind("SetAttr", varPtr, stmtInfo)
                #     self.processSetAttr(stmtInfo, self.pointToSet.get(varPtr))

                # elif(isinstance(stmt, GetAttr)):
                #     # print(f"Bind GetAttr: {stmt.source} - {stmt}")
                #     varPtr = VarPtr.create(stmt.source)
                #     stmtInfo = (stmt, )
                #     self.bindingStmts.bind("GetAttr", varPtr, stmtInfo)
                #     self.processGetAttr(stmtInfo, self.pointToSet.get(varPtr))

                if(isinstance(stmt, NewClass)):
                    for i in range(len(stmt.bases)):
                        # print(f"Bind Base: {stmt.bases[i]} - {stmt} - {i}")
                        varPtr = VarPtr.create(stmt.bases[i])
                        stmtInfo = (stmt, i)
                        self.bindingStmts.bind("NewClass", varPtr, stmtInfo)
                        self.processNewClass(stmtInfo, self.pointToSet.get(varPtr))

                elif(isinstance(stmt, Call)):
                    # print(f"Bind Call: {stmt.callee} - {stmt}")
                    varPtr = VarPtr.create(stmt.callee)
                    stmtInfo = (stmt, )
                    self.bindingStmts.bind("Call", varPtr, stmtInfo)
                    self.processCall(stmtInfo, self.pointToSet.get(varPtr))

                elif(isinstance(stmt, DelAttr)):
                    # print(f"Bind DelAttr: {stmt.var} - {stmt}")
                    varPtr = VarPtr.create(stmt.var)
                    stmtInfo = (stmt, )
                    self.bindingStmts.bind("DelAttr", varPtr, stmtInfo)
                    self.processDelAttr(stmtInfo, self.pointToSet.get(varPtr))
                
                # elif(isinstance(stmt, NewClassMethod)):
                #     varPtr = VarPtr.create(stmt.func)
                #     stmtInfo = (stmt, )
                #     self.bindingStmts.bind("NewClassMethod", varPtr, stmtInfo)
                #     self.processNewClassMethod(stmtInfo, self.pointToSet.get(varPtr))

                elif(isinstance(stmt, NewStaticMethod)):
                    varPtr = VarPtr.create(stmt.func)
                    stmtInfo = (stmt, )
                    self.bindingStmts.bind("NewStaticMethod", varPtr, stmtInfo)
                    self.processNewStaticMethod(stmtInfo, self.pointToSet.get(varPtr))

                elif(isinstance(stmt, NewSuper)):
                    
                    varPtr = VarPtr.create(stmt.type)
                    stmtInfo = (stmt, "type")
                    self.bindingStmts.bind("NewSuper", varPtr, stmtInfo)
                    self.processNewSuper(stmtInfo, self.pointToSet.get(varPtr))

                    varPtr = VarPtr.create(stmt.bound)
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

            if(isinstance(target.obj, ClassObject)):
                newObjs = self.transformObj_Class(target.obj, objs)
            elif(isinstance(target.obj, SuperObject)):
                
                newObjs = self.transformObj_Class(target.obj.bound, objs)

        self.workList.append((ADD_POINTS_TO, target, newObjs))

    # def transformObj_Instance(self, insObj: InstanceObject, objs) -> Set[Object]:
    #     newObjs = set()
    #     for obj in objs:
    #         if(isinstance(obj, FunctionObject)):
    #             newObjs.add(InstanceMethodObject(insObj, obj))
    #         elif(isinstance(obj, ClassMethodObject)):
    #             func = obj.func
    #             newObjs.add(ClassMethodObject(insObj.type, func))
    #         else:
    #             newObjs.add(obj)
    #     return newObjs

    def transformObj_Class(self, classObj: ClassObject, objs) -> Set[Object]:
        newObjs = set()
        for obj in objs:
            # if(isinstance(obj, ClassMethodObject)):
            #     func = obj.func
            #     newObjs.add(ClassMethodObject(classObj, func))
            # else:
            #     newObjs.add(obj)
            if(isinstance(obj, FunctionObject)):
                newObj = self.objectPool.create(OBJ_CLASS_METHOD, classObj, obj)
                newObjs.add(newObj)
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

        
        if(attr in self.resolved_attr[obj]):
            return
        

        self.resolved_attr[obj].add(attr)
        if(isinstance(obj, ClassObject)):
            classObj = obj
        elif(isinstance(obj, SuperObject)):
            # if(isinstance(obj.bound, InstanceObject)):
            #     classObj = obj.bound.type
            # else:
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

    def addSetEdge(self, target: VarPtr, source: VarPtr, attr: str, objs: Set[Object]):
        # stmt,  = *stmtInfo,
        # assert(isinstance(stmt, SetAttr))
        for obj in objs:
            attrPtr = AttrPtr(obj, attr)
            self.addFlow(source, attrPtr)

    def addGetEdge(self, target: VarPtr, source: VarPtr, attr:str, objs: Set[Object]):
        # stmt, = *stmtInfo, 
        # assert(isinstance(stmt, GetAttr))
        for obj in objs:
            
            if(isinstance(obj, FakeObject)):
               
                fakeObj = self.objectPool.create(OBJ_FAKE, obj, (source, target, attr))
                self.workList.append((ADD_POINTS_TO, target, {fakeObj}))
                
            # elif(isinstance(obj, InstanceObject)):
            #     # target <- instance.attr
            #     insAttr = AttrPtr(obj, stmt.attr)
            #     insResAttr = AttrPtr(obj, FAKE_PREFIX + stmt.attr)
            #     self.addFlow(insAttr, varPtr)
            #     self.addFlow(insResAttr, varPtr)
            #     classObj = obj.type
            #     self.resolveAttrIfNot(classObj, stmt.attr)
            #     # instance.attr <- class.$r_attr
            #     classAttr = AttrPtr(classObj, FAKE_PREFIX + stmt.attr)
            #     self.addFlow(classAttr, insResAttr)

            if(isinstance(obj, ClassObject)):
                self.resolveAttrIfNot(obj, attr)
                # instance.attr <- class.$r_attr
                classAttr = AttrPtr(obj, FAKE_PREFIX + attr)
                self.addFlow(classAttr, target)

            elif(isinstance(obj, SuperObject)):
                self.resolveAttrIfNot(obj, attr)
                # instance.attr <- class.$r_attr
                superAttr = AttrPtr(obj, FAKE_PREFIX + attr)
                self.addFlow(superAttr, target)

            else:
                attrPtr = AttrPtr(obj, attr)
                self.addFlow(attrPtr, target)

    def processNewClass(self, stmtInfo: Tuple[NewClass, int], objs: Set[Object]):
        stmt, index = *stmtInfo,
        assert(isinstance(stmt, NewClass))
        mroChange = set()
        for obj in objs:
            if(isinstance(obj, ClassObject)):
                cls = self.objectPool.create(OBJ_CLASS, stmt)
                mroChange |= self.classHiearchy.addClassBase(cls, index, obj)
        for mro in mroChange:
            classObj = mro[0]
            
            for attr in self.resolved_attr[classObj]:
                self.resolveAttribute(classObj, attr, (mro, 0))

    def processCall(self, stmtInfo: Tuple[Call], objs: Set[Object]):
        stmt, = *stmtInfo,
        assert(isinstance(stmt, Call))
        varPtr = VarPtr.create(stmt.target)
        newObjs = set()
        for obj in objs:
            # if(isinstance(obj, FakeObject)):
            #     func = obj.getCodeBlock()
            #     self.callgraph.put(stmt, func)
            if(isinstance(obj, FunctionObject)):
                
                self.matchArgParam(posArgs=         [VarPtr.create(posArg) for posArg in stmt.posargs],
                                    kwArgs=         {kw:VarPtr.create(kwarg) for kw, kwarg in stmt.kwargs.items()},
                                    posParams=      obj.posParams,
                                    kwParams=       obj.kwParams,
                                    varParam=       obj.varParam,
                                    kwParam=        obj.kwParam)
                retVar = obj.retVar
                resVar = VarPtr.create(stmt.target)
                self.addFlow(retVar, resVar)
                self.addReachable(obj.codeBlock)
                self.addCallEdge(stmt, obj.readable_name)
                
                
            # elif(isinstance(obj, InstanceMethodObject)):
            #     func = obj.func.getCodeBlock()
            #     posParams = [VarPtr.create(param) for param in func.posargs]
            #     if(len(posParams) == 0):
            #         # not a method, just skip
            #         continue
            #     self.workList.append((ADD_POINT_TO, posParams[0], {obj.selfObj}))
            #     del posParams[0]
            #     self.matchArgParam(posArgs=         [VarPtr.create(posArg) for posArg in stmt.posargs],
            #                         kwArgs=         {kw:VarPtr.create(kwarg) for kw, kwarg in stmt.kwargs.items()},
            #                         posParams=      posParams,
            #                         kwParams=       {kw:VarPtr.create(kwOnlyParam) for kw, kwOnlyParam in func.kwargs.items()},
            #                         varParam=       VarPtr.create(func.vararg) if func.vararg else None,
            #                         kwParam=        VarPtr.create(func.kwarg) if func.kwarg else None)
            #     retVar = VarPtr.create(func.returnVariable)
            #     resVar = VarPtr.create(stmt.target)
            #     self.addFlow(retVar, resVar)
            #     self.callgraph.put(stmt, func)
            #     self.addReachable(func)

            elif(isinstance(obj, ClassMethodObject)):
                funcObj = obj.func
                posParams = funcObj.posParams[:]
                if(len(posParams) == 0):
                    # not a method, just skip
                    continue
                self.workList.append((ADD_POINTS_TO, posParams[0], {obj.classObj}))
                del posParams[0]
                self.matchArgParam(posArgs=         [VarPtr.create(posArg) for posArg in stmt.posargs],
                                    kwArgs=         {kw:VarPtr.create(kwarg) for kw, kwarg in stmt.kwargs.items()},
                                    posParams=      posParams,
                                    kwParams=       funcObj.kwParams,
                                    varParam=       funcObj.varParam,
                                    kwParam=        funcObj.kwParam)
                retVar = funcObj.retVar
                resVar = VarPtr.create(stmt.target)
                self.addFlow(retVar, resVar)
                self.addCallEdge(stmt, funcObj.readable_name)
                self.addReachable(funcObj.codeBlock)

            elif(isinstance(obj, StaticMethodObject)):
                funcObj = obj.func
                self.matchArgParam(posArgs=         [VarPtr.create(posArg) for posArg in stmt.posargs],
                                    kwArgs=         {kw:VarPtr.create(kwarg) for kw, kwarg in stmt.kwargs.items()},
                                    posParams=      funcObj.posParams,
                                    kwParams=       funcObj.kwParams,
                                    varParam=       funcObj.varParam,
                                    kwParam=        funcObj.kwParam)
                retVar = funcObj.retVar
                resVar = VarPtr.create(stmt.target)
                self.addFlow(retVar, resVar)
                self.addReachable(funcObj.codeBlock)
                self.addCallEdge(stmt, funcObj.readable_name)
           
            elif(isinstance(obj, ClassObject)):
                # insObj = CIInstanceObject(stmt, obj)
                
                # target <- instance.attr
                # insAttr = AttrPtr(insObj, FAKE_PREFIX + "__init__")
                classAttr = AttrPtr(obj, FAKE_PREFIX + "__init__")
                # self.addFlow(classAttr, insAttr)
                self.resolveAttrIfNot(obj, "__init__")

                init = Variable(f"$init_method_of_{obj.id}", stmt.belongsTo)
                initPtr = VarPtr.create(init)
                self.addFlow(classAttr, initPtr)
                newStmt = Call(Variable("", stmt.belongsTo), init, stmt.posargs, stmt.kwargs, stmt.belongsTo, stmt.belongsTo.getNewID())
                self.workList.append((BIND_STMT, newStmt))
                newObjs.add(obj)
        if(newObjs):
            self.workList.append((ADD_POINTS_TO, varPtr, newObjs))
                
    def matchArgParam(self, / , posArgs: List[VarPtr], 
                                kwArgs: Dict[str, VarPtr], 
                                posParams: List[VarPtr], 
                                kwParams: Dict[str, VarPtr],
                                varParam: VarPtr, kwParam: VarPtr):
    
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
            if(attr in self.persist_attr[obj]):
                for resolver, mro, index in self.persist_attr[obj][attr]:
                    self.resolveAttribute(resolver, attr, (mro, index + 1))
                del self.persist_attr[obj][attr]

    # def processNewClassMethod(self, stmtInfo: Tuple[NewClassMethod], objs: Set[Object]):
    #     stmt, = *stmtInfo, 
    #     assert(isinstance(stmt, NewClassMethod))
    #     target = VarPtr.create(stmt.target)
    #     newObjs = set()
    #     for obj in objs:
    #         if(isinstance(obj, FunctionObject) and isinstance(stmt.belongsTo, ClassCodeBlock)):
                
    #             for classObj in self.pointToSet.get(VarPtr.create(stmt.belongsTo.thisClassVariable)):
    #                 if(isinstance(classObj, ClassObject)):
    #                     classMethod = ClassMethodObject(classObj, obj)
    #                     newObjs.add(classMethod)
    #     if(newObjs):
    #         self.workList.append((ADD_POINT_TO, target, newObjs))

    def processNewStaticMethod(self, stmtInfo: Tuple[NewStaticMethod], objs: Set[Object]):
        stmt, = *stmtInfo, 
        assert(isinstance(stmt, NewStaticMethod))
        target = VarPtr.create(stmt.target)
        newObjs = set()
        for obj in objs:
            if(isinstance(obj, FunctionObject) and isinstance(stmt.belongsTo, ClassCodeBlock)):
                
                staticMethod = self.objectPool.create(OBJ_STATIC_METHOD, obj)
                newObjs.add(staticMethod)
        if(newObjs):
            self.workList.append((ADD_POINTS_TO, target, newObjs))

    def processNewSuper(self, stmtInfo: NewSuper, objs: Set[Object]):
        stmt, operand = *stmtInfo,
        assert(isinstance(stmt, NewSuper))
        if(operand == "type"):
            newObjs = set()
            target = VarPtr.create(stmt.target)
            for obj in objs:
                if(isinstance(obj, ClassObject)):
                    for boundObj in self.pointToSet.get(VarPtr.create(stmt.bound)):
                        newObj = self.objectPool.create(OBJ_SUPER, obj, boundObj)
                        newObjs.add(newObj)
            if(newObjs):
                self.workList.append((ADD_POINTS_TO, target, newObjs))
        else:
            newObjs = set()
            target = VarPtr.create(stmt.target)
            for obj in objs:
                if(isinstance(obj, ClassObject)):
                    for typeObj in self.pointToSet.get(VarPtr.create(stmt.type)):
                        newObj = self.objectPool.create(OBJ_SUPER, typeObj, obj)
                        newObjs.add(newObj)
            if(newObjs):
                self.workList.append((ADD_POINTS_TO, target, newObjs))

    def addCallEdge(self, callsite: IRStmt, callee: str):
        self.callgraph[callsite.belongsTo.readable_name].add(callee)


        


    
        


    