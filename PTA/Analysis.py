from typing import Dict, List, Set, Tuple, Union
from ..IR.CodeBlock import ClassCodeBlock, CodeBlock, FunctionCodeBlock, ModuleCodeBlock
from ..IR.Stmts import Assign, Call, DelAttr, GetAttr, IRStmt, NewBuiltin, NewClass, NewClassMethod, NewFunction, NewModule, NewStaticMethod, NewSuper, SetAttr, Variable
from .ClassHiearchy import MRO, ClassHiearchy
from .Objects import  CIBuiltinObject, CIClassObject, CIFunctionObject, CIInstanceObject, ClassMethodObject, ClassObject, FakeObject, FunctionObject, InstanceObject, InstanceMethodObject, ModuleObject, Object, StaticMethodObject, SuperObject
from .BindingStmts import BindingStmts
from .PointerFlow import PointerFlow
from .Pointers import AttrPtr, Pointer, CIVarPtr, VarPtr
from .CallGraph import CICallGraph, CallGraph
from .PointToSet import PointToSet

FAKE_PREFIX = "$r_"
builtin_functions = ["abs", "aiter", "all", "any", "anext", "ascii", "bin", "bool", "breakpoint", "bytearray", "bytes", "callable", "chr", "classmethod", "compile", "complex", "delattr", "dict", "dir", "divmod", "enumerate", "eval", "exec", "filter", "float", "format", "frozenset", "getattr", "globals", "hasattr", "hash", "help", "hex", "id", "input", "int", "isinstance", "issubclass", "iter", "len", "list", "locals", "map", "max", "memoryview", "min", "next", "object", "oct", "open", "ord", "pow", "print", "property", "range", "repr", "reversed", "round", "set", "setattr", "slice", "sorted", "staticmethod", "str", "sum", "super", "tuple", "type", "vars", "zip", "__import__"]

def isFakeAttr(attr: str):
    return attr.startswith(FAKE_PREFIX)

Resolver = Union[ClassObject, SuperObject]
ResolveInfo = Tuple[Resolver, MRO, int]


class Analysis:
    pointToSet: PointToSet
    callgraph: CallGraph
    pointerFlow: PointerFlow
    bindingStmts: BindingStmts
    reachable: Set[CodeBlock]
   
    classHiearchy: ClassHiearchy
    persist_attr: Dict[ClassObject, Dict[str, Set[ResolveInfo]]]
    resolved_attr: Dict[Resolver, Set[str]]
    workList: List[Tuple[Pointer, Set[Object]]]
    def __init__(self, verbose=False):
        self.pointToSet = PointToSet()
        self.callgraph = CICallGraph()
        self.pointerFlow = PointerFlow()
        self.bindingStmts = BindingStmts()
        self.defined = set()
        self.reachable = set()
        self.classHiearchy = ClassHiearchy(self.pointToSet)
        self.persist_attr = {}
        self.resolved_attr = {}
        self.workList = []
        self.verbose = verbose

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
                if(isinstance(stmt.module, ModuleCodeBlock)):
                    obj = ModuleObject(stmt.module)
                    targetPtr = CIVarPtr(stmt.target)
                    globalPtr = CIVarPtr(stmt.module.globalVariable)
                    self.workList.append((targetPtr, {obj}))
                    self.workList.append((globalPtr, {obj}))
                    self.addReachable(stmt.module)
                    # self.callgraph.put(stmt, stmt.codeBlock)
                else:
                    obj = FakeObject(stmt.module, None)
                    targetPtr = CIVarPtr(stmt.target)
                    self.workList.append((targetPtr, {obj}))
                
                
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
                # self.callgraph.put(stmt, stmt.codeBlock)
                
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
        
        elif(isinstance(stmt, NewClassMethod)):
            varPtr = CIVarPtr(stmt.func)
            self.bindingStmts.bindNewClassMethod(varPtr, stmt)
            self.processNewClassMethod(stmt, self.pointToSet.get(varPtr))

        elif(isinstance(stmt, NewStaticMethod)):
            varPtr = CIVarPtr(stmt.func)
            self.bindingStmts.bindNewStaticMethod(varPtr, stmt)
            self.processNewStaticMethod(stmt, self.pointToSet.get(varPtr))

        elif(isinstance(stmt, NewSuper)):
            
            varPtr = CIVarPtr(stmt.type)
            self.bindingStmts.bindNewSuper_type(varPtr, stmt)
            self.processNewSuper_type(stmt, self.pointToSet.get(varPtr))

            varPtr = CIVarPtr(stmt.bound)
            self.bindingStmts.bindNewSuper_bound(varPtr, stmt)
            self.processNewSuper_bound(stmt, self.pointToSet.get(varPtr))

    def analyze(self, entry: ModuleCodeBlock):
        entryModule = ModuleObject(entry)
        self.workList.append((CIVarPtr(entry.globalVariable), {entryModule}))

        self.addReachable(entry)

        while(len(self.workList) > 0):
            if(self.verbose):
                print(f"\rPTA worklist remains {len(self.workList)} to process.            ", end="")

            ptr, objs = self.workList[0]
            del self.workList[0]

            if(len(objs) == 0):
                continue

            objs = self.pointToSet.putAll(ptr, objs)
            if(objs):
                for succ in self.pointerFlow.getSuccessors(ptr):
                    self.flow(ptr,succ, objs)

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

            for stmt in self.bindingStmts.getNewClassMethod(ptr):
                self.processNewClassMethod(stmt, objs)

            for stmt in self.bindingStmts.getNewStaticMethod(ptr):
                self.processNewStaticMethod(stmt, objs)

            for stmt in self.bindingStmts.getNewSuper_type(ptr):
                self.processNewSuper_type(stmt, objs)

            for stmt in self.bindingStmts.getNewSuper_bound(ptr):
                self.processNewSuper_bound(stmt, objs)


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

        self.workList.append((target, newObjs))

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

    def processSetAttr(self, stmt: SetAttr, objs: Set[Object]):
        # print(f"Process SetAttr: {stmt}")
        assert(isinstance(stmt, SetAttr))
        for obj in objs:
            attrPtr = AttrPtr(obj, stmt.attr)
            self.addFlow(CIVarPtr(stmt.source), attrPtr)

    def processGetAttr(self, stmt: GetAttr, objs: Set[Object]):
        # print(f"Process GetAttr: {stmt}")
        assert(isinstance(stmt, GetAttr))
        for obj in objs:
            varPtr = CIVarPtr(stmt.target)
            if(isinstance(obj, FakeObject)):
                try:
                    fakeObj = FakeObject(stmt.attr, obj)
                    self.workList.append((varPtr, {fakeObj}))
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

    def processNewClass(self, stmt: NewClass, index: int, objs: Set[Object]):
        # print(f"Process NewClass: {stmt}")
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

    def processCall(self, stmt: Call, objs: Set[Object]):
        # print(f"Process Call: {stmt}")
        assert(isinstance(stmt, Call))
        varPtr = CIVarPtr(stmt.target)
        newObjs = set()
        for obj in objs:
            if(isinstance(obj, FakeObject)):
                func = obj.getCodeBlock()
                self.callgraph.put(stmt, func)
            elif(isinstance(obj, FunctionObject)):
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

            elif(isinstance(obj, ClassMethodObject)):
                func = obj.func.getCodeBlock()
                posParams = [CIVarPtr(param) for param in func.posargs]
                
                self.workList.append((posParams[0], {obj.classObj}))
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
                self.addStmt(Call(Variable("", stmt.belongsTo), init, stmt.posargs, stmt.kwargs, stmt.belongsTo))
                newObjs.add(insObj)
        if(newObjs):
            self.workList.append((varPtr, newObjs))
                
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
                # self.addStmt(SetAttr(varParam.var, "$values", posArgs[i].var, varParam.var.belongsTo))
                
        
        for kw, varPtr in kwArgs.items():
            if(kw in kwParams):
                self.addFlow(varPtr, kwParams[kw])
            elif(kwParam):
                self.addFlow(kwArgs[kw], kwParam)
                # self.addStmt(SetAttr(kwParam.var, "$values", varPtr.var, kwParam.var.belongsTo)) 


    def processDelAttr(self, stmt: DelAttr, objs: Set[Object]):
        # print(f"Process DelAttr: {stmt}")
        assert(isinstance(stmt, DelAttr))
        attr = stmt.attr
        for obj in objs:
            if(isinstance(obj, ClassObject) and attr in self.persist_attr[obj]):
                for resolver, mro, index in self.persist_attr[obj][attr]:
                    self.resolveAttribute(resolver, attr, (mro, index + 1))
                del self.persist_attr[obj][attr]

    def processNewClassMethod(self, stmt: NewClassMethod, objs: Set[Object]):
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
            self.workList.append((target, newObjs))

    def processNewStaticMethod(self, stmt: NewStaticMethod, objs: Set[Object]):
        assert(isinstance(stmt, NewStaticMethod))
        target = CIVarPtr(stmt.target)
        newObjs = set()
        for obj in objs:
            if(isinstance(obj, FunctionObject) and isinstance(stmt.belongsTo, ClassCodeBlock)):
                
                staticMethod = StaticMethodObject(obj)
                newObjs.add(staticMethod)
        if(newObjs):
            self.workList.append((target, newObjs))

    def processNewSuper_type(self, stmt: NewSuper, objs: Set[Object]):
        assert(isinstance(stmt, NewSuper))
        newObjs = set()
        target = CIVarPtr(stmt.target)
        for obj in objs:
            if(isinstance(obj, ClassObject)):
                for boundObj in self.pointToSet.get(CIVarPtr(stmt.bound)):
                    newObjs.add(SuperObject(obj, boundObj))
        if(newObjs):
            self.workList.append((target, newObjs))

    def processNewSuper_bound(self, stmt: NewSuper, objs: Set[Object]):
        assert(isinstance(stmt, NewSuper))
        newObjs = set()
        target = CIVarPtr(stmt.target)
        for obj in objs:
            if(isinstance(obj, ClassObject) or isinstance(obj, InstanceObject)):
                for typeObj in self.pointToSet.get(CIVarPtr(stmt.type)):
                    newObjs.add(SuperObject(typeObj, obj))
        if(newObjs):
            self.workList.append((target, newObjs))


    
        


    