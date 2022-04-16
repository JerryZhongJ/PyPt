from msilib.schema import Class
from typing import Dict, Generator, List, Set, Tuple
from ..IR.CodeBlock import CodeBlock, FunctionCodeBlock, ModuleCodeBlock
from ..IR.Stmts import Assign, Call, DelAttr, GetAttr, NewBuiltin, NewClass, NewFunction, NewModule, SetAttr, Variable
# from .ClassHiearchy import MRO, ClassHiearchy
from .Objects import BuiltinObject, ClassObject, ConstObject, FunctionObject, InstanceObject, MethodObject, ModuleObject, Object
from .BindingStmts import BindingStmts
from .PointerFlow import PointerFlow
from .Pointers import AttrPtr, Pointer, VarPtr
from .CallGraph import CallGraph
from .PointToSet import PointToSet

RESOLVED_PREFIX = "$r_"
MRO = Tuple[ClassObject]

def isResolved(attr: str):
    return attr.startswith(RESOLVED_PREFIX)
ResolveInfo = Tuple[ClassObject, int]
class Analysis:
    pointToSet: PointToSet
    callgraph: CallGraph
    pointerFlow: PointerFlow
    bindingStmts: BindingStmts
    definedCodeBlocks: Set[CodeBlock]
    # classHiearchy: ClassHiearchy
    persist_attr: Dict[ClassObject, Dict[str, Set[ResolveInfo]]]
    workList: List[Tuple[Pointer, Set[Object]]]
    def __init__(self):
        self.pointToSet = PointToSet()
        self.callgraph = CallGraph()
        self.pointerFlow = PointerFlow()
        self.bindingStmts = BindingStmts()
        self.definedCodeBlocks = set()
        # self.classHiearchy = ClassHiearchy(self.pointToSet)
        self.persist_attr = {}
        self.workList = []

    def addReachable(self, codeBlock):
        if(self.callgraph.isReachable(codeBlock)):
            return
        for stmt in codeBlock:
            if(isinstance(stmt, Assign)):
                targetVar = VarPtr(stmt.target)
                sourceVar = VarPtr(stmt.source)
                self.addFlow(sourceVar, targetVar)
            elif(isinstance(stmt, NewModule)):
                obj = ModuleObject(stmt.codeBlock)
                globalVar = VarPtr(stmt.codeBlock.globalVariable)
                self.workList.append((globalVar, {obj}))
                targetVar = VarPtr(stmt.target)
                self.workList.append((targetVar, {obj}))
                self.addDefined(stmt.codeBlock)
                self.addReachable(stmt.codeBlock)
            elif(isinstance(stmt, NewFunction)):
                obj = FunctionObject(stmt)
                targetVar = VarPtr(stmt.target)
                self.workList.append((targetVar, {obj}))
                self.addDefined(stmt.codeBlock)
            elif(isinstance(stmt, NewClass)):
                
                self.addDefined(stmt.codeBlock)
                self.addReachable(stmt.codeBlock)
            elif(isinstance(stmt, NewBuiltin)):
                targetVar = VarPtr(stmt.target)
                if(stmt.value or stmt.type == "NoneType"):
                    obj = ConstObject(stmt.value)
                else:
                    obj = BuiltinObject(stmt)
                self.workList.append(targetVar, {obj})

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
    def resolveAttribute(self, classObj: ClassObject, attr: str, mroIndex: int = 0):
        assert(classObj, ClassObject)
        
        mro = classObj.mro
        childAttr = AttrPtr(classObj, RESOLVED_PREFIX + attr)
        while(mroIndex < len(mro)):
            parent = mro[mroIndex]
            parentAttr = AttrPtr(parent, attr)
            self.addFlow(parentAttr, childAttr)
            if(attr in self.persist_attr[parent]):
                self.persist_attr[parent][attr].add((classObj, mroIndex))
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
                classObj = obj.type
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
        
        def select(start: int) -> Generator[List[ClassObject], None, None]:
            if(start == len(stmt.bases)):
                yield []
            else:
                if(start != index):
                    varPtr = VarPtr(stmt.bases[start])
                    objs = self.pointToSet.get(varPtr)

                for obj in objs:
                    if(not isinstance(obj, ClassObject)):
                        continue
                    for tail in select(start + 1):
                        tail.insert(0, obj)
                        yield tail

        classObjs = set()
        for bases in select(0):
            mros = [base.mro for base in bases]
            mro = self.c3_merge(mros)
            if(mro):
                classObj = ClassObject(stmt, mro)
                self.persist_attr[classObj] = {}
                for attr in classObj.getAttributes():
                    self.persist_attr[classObj][attr] = set()
                classObjs.add(classObj)
            
        targetVar = VarPtr(stmt.target)
        self.workList.append((targetVar, classObjs))
        thisClass = VarPtr(stmt.codeBlock.thisClassVariable)
        self.workList.append((thisClass, classObjs))
        

    def processCall(self, stmt: Call, objs: Set[Object]):
        varPtr = VarPtr(stmt.target)
        for obj in objs:
            if(isinstance(obj, FunctionObject)):
                func = obj.getCodeBlock()
                self.matchArgParam(posArgs=         [VarPtr(posArg) for posArg in stmt.posargs],
                                    kwArgs=         {kw:VarPtr(kwarg) for kw, kwarg in stmt.kwargs.items()},
                                    posonlyParams=  [VarPtr(posonlyParam) for posonlyParam in func.posonlyargs],
                                    params=         [VarPtr(param) for param in func.args],
                                    kwonlyParams=   [VarPtr(kwonlyParam) for kwonlyParam in func.kwonlyargs],
                                    varParam=       VarPtr(func.vararg) if func.vararg else None,
                                    kwParam=        VarPtr(func.kwarg) if func.kwarg else None)
                retVar = VarPtr(func.returnVariable)
                resVar = VarPtr(stmt.target)
                self.addFlow(retVar, resVar)
            elif(isinstance(obj, MethodObject)):
                func = obj.func.getCodeBlock()
                posonlyParams = [VarPtr(posonlyParam) for posonlyParam in func.posonlyargs]
                params = [VarPtr(param) for param in func.args]
                if(len(posonlyParams) > 0):
                    self.workList.append((posonlyParams[0], {obj.selfObj}))
                    del posonlyParams[0]
                
                else:
                    self.workList.append((params[0], {obj.selfObj}))
                    del params[0]
                self.matchArgParam(posArgs=         [VarPtr(posArg) for posArg in stmt.posargs],
                                    kwArgs=         {kw:VarPtr(kwarg) for kw, kwarg in stmt.kwargs.items()},
                                    posonlyParams=  posonlyParams,
                                    params=         params,
                                    kwonlyParams=   [VarPtr(kwonlyParam) for kwonlyParam in func.kwonlyargs],
                                    varParam=       VarPtr(func.vararg) if func.vararg else None,
                                    kwParam=        VarPtr(func.kwarg) if func.kwarg else None)
                retVar = VarPtr(func.returnVariable)
                resVar = VarPtr(stmt.target)
                self.addFlow(retVar, resVar)
            elif(isinstance(obj, ClassObject)):
                ins = InstanceObject(stmt, obj)
                self.workList.append((varPtr, {ins}))
                
    def matchArgParam(self, / , posArgs: List[VarPtr], 
                                kwArgs: Dict[str, VarPtr], 
                                posonlyParams: List[VarPtr], 
                                params: List[VarPtr], 
                                kwonlyParams: List[VarPtr], 
                                varParam: VarPtr, kwParam: VarPtr):
        pass
        # TODO

    def processDelAttr(self, stmt: DelAttr, objs: Set[Object]):
        attr = stmt.attr
        for obj in objs:
            if(isinstance(obj, ClassObject) and attr in self.persist_attr[obj]):
                for subclass, index in self.persist_attr[attr]:
                    self.resolveAttribute(subclass, attr, index + 1)
                del self.persist_attr[obj][attr]

        

    def c3_merge(self, mros) -> MRO:
        nexts = {}
        inDegrees = {}
        for mro in mros:
            for i in range(len(mro)):
                if(mro[i] not in nexts):
                    nexts[mro[i]] = set()
                    inDegrees[mro[i]] = 0
        
        for mro in mros:
            for i in range(len(mro) - 1):
                nexts[mro[i]].add(mro[i + 1])
                inDegrees[mro[i + 1]] += 1

        mro = []
        while(len(inDegrees) != 0):
            select = None
            for obj, degree in inDegrees.items():
                if(degree == 0):
                    if(select != None):
                        # illegal
                        return 
                    select = obj
            if(select == None):
                return 
            mro.append(select)
            for next in nexts[obj]:
                inDegrees[next] -= 1

            del nexts[obj]
            del inDegrees[obj]
        return *mro,

    
        


