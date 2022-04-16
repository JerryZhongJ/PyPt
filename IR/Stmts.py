
from typing import Any, Dict, List, Tuple

DEFINED_WITH_VAR = 0
DEFINED_OTHERS = 1
USED_BY_VAR = 2
USED_OTHERS = 3

class Variable:
    name: str                           # variable name
    belongsTo: 'CodeBlock'                # 'CodeBlock' to which it belongs
    # TODO: implement this
    qualified_name: str
    isTmp: bool

    def __str__(self):
        return self.qualified_name

    def __repr__(self):
        return self.__str__()

    def __init__(self, name: str, belongsTo: 'CodeBlock', temp=False):
        self.name = name
        self.belongsTo = belongsTo
        self.qualified_name = f"<{belongsTo.qualified_name}>{name}"
        self.isTmp = temp
        if(temp):
            self.usingIRs = ([], [], [], [])

class IRStmt:
    belongsTo: 'CodeBlock'                 # 'CodeBlock' to which this IR belongs
    srcPos: Tuple[int]

    def __init__(self, belongsTo: 'CodeBlock', srcPos: Tuple[int]):
        self.belongsTo = belongsTo
        belongsTo.IRs.append(self)
        self.srcPos = srcPos

    def destroy(self):
        self.belongsTo.IRs.remove(self)

    def __str__(self):
        return f"({self.srcPos[0]}:{self.srcPos[1]},\t{self.srcPos[2]}:{self.srcPos[3]})\t{self._text()}"

    def __repr__(self):
        return self._text()
    


class Assign(IRStmt):
    target: Variable
    source: Variable

    def __init__(self, target: Variable, source: Variable, belongsTo: 'CodeBlock', srcPos: Tuple[int]):
        super().__init__(belongsTo, srcPos)

        self.setTarget(target)
        self.setSource(source)

    def _unsetTarget(self):
        if(not hasattr(self, "target")):
            return

        if(self.target.isTmp):
            self.target.usingIRs[DEFINED_WITH_VAR].remove(self)
        del self.target

    def _unsetSource(self):
        if(not hasattr(self, "source")):
            return 

        if(self.source.isTmp):
            self.source.usingIRs[USED_BY_VAR].remove(self)
        del self.source

    def setTarget(self, target):
        self._unsetTarget()
        if(target.isTmp):
            target.usingIRs[DEFINED_WITH_VAR].append(self)
        self.target = target

    def setSource(self, source):
        self._unsetSource()
        if(source.isTmp):
            source.usingIRs[USED_BY_VAR].append(self)
        self.source = source

    def destroy(self):
        self._unsetTarget()
        self._unsetSource()
        super().destroy()

    def _text(self):
        return f"{self.target} = {self.source}"


# target.attr = source
class SetAttr(IRStmt):
    target: Variable
    source: Variable
    attr: str

    def __init__(self, target: Variable, attr: str, source: Variable, belongsTo: 'CodeBlock', srcPos: Tuple[int]):
        super().__init__(belongsTo, srcPos)
        self.setTarget(target)
        self.setSource(source)
        self.attr = attr
        # $global.attr = v
        if(target == belongsTo.globalVariable):
            target.belongsTo.globalNames.add(attr)

    def _unsetTarget(self):
        if(not hasattr(self, "target")):
            return
        if(self.target.isTmp):
            self.target.usingIRs[USED_OTHERS].remove(self)
        del self.target

    def _unsetSource(self):
        if(not hasattr(self, "source")):
            return
        if(self.source.isTmp):
            self.source.usingIRs[USED_OTHERS].remove(self)
        del self.source

    def setTarget(self, target):
        self._unsetTarget()
        if(target.isTmp):
            target.usingIRs[USED_OTHERS].append(self)
        self.target = target
    
    def setSource(self, source):
        self._unsetSource()
        if(source.isTmp):
            source.usingIRs[USED_OTHERS].append(self)
        self.source = source

    def destroy(self):
        self._unsetTarget()
        self._unsetSource()
        super().destroy()

    def _text(self):
        return  f"{self.target}.{self.attr} = {self.source}"

# target = source.attr
class GetAttr(IRStmt):
    target: Variable
    source: Variable
    attr: str

    def __init__(self, target: Variable, source: Variable, attr: str, belongsTo: 'CodeBlock', srcPos: Tuple[int]):
        super().__init__(belongsTo, srcPos)
        self.setTarget(target)
        self.setSource(source)
        self.attr = attr

    def _unsetTarget(self):
        if(not hasattr(self, "target")):
            return
        if(self.target.isTmp):
            self.target.usingIRs[DEFINED_OTHERS].remove(self)
        del self.target

    def _unsetSource(self):
        if(not hasattr(self, "source")):
            return 
        if(self.source.isTmp):
            self.source.usingIRs[USED_OTHERS].remove(self)
        del self.source

    def setTarget(self, target):
        self._unsetTarget()
        if(target.isTmp):
            target.usingIRs[DEFINED_OTHERS].append(self)
        self.target = target

    def setSource(self, source):
        self._unsetSource()
        if(source.isTmp):
            source.usingIRs[USED_OTHERS].append(self)
        self.source = source
        

    def destroy(self):
        self._unsetTarget()
        self._unsetSource()
        super().destroy()

    def _text(self):
        return f"{self.target} = {self.source}.{self.attr}"

# target = New ...
class New(IRStmt):
    target: Variable
    objType:str                             # module, function, class, method, instance, builtin

    def __init__(self, target: Variable, objType: str, belongsTo: 'CodeBlock', srcPos: Tuple[int]):
        super().__init__(belongsTo, srcPos)
        self.setTarget(target)
        self.objType = objType

        
    def _unsetTarget(self):
        if(not hasattr(self, "target")):
            return
        if(self.target.isTmp):
            self.target.usingIRs[DEFINED_OTHERS].remove(self)
        del self.target

    def setTarget(self, target):
        self._unsetTarget()
        if(target.isTmp):
            target.usingIRs[DEFINED_OTHERS].append(self)
        self.target = target

    def destroy(self):
        self._unsetTarget()
        super().destroy()
        
class NewModule(New):
    codeBlock: 'CodeBlock'                  

    def __init__(self, target:Variable, codeBlock: 'CodeBlock', belongsTo: 'CodeBlock', srcPos: Tuple[int]):
        super().__init__(target, 'module', belongsTo, srcPos)
        self.codeBlock = codeBlock

    def _text(self):
        return f"{self.target} = NewModule {self.codeBlock.moduleName if self.codeBlock else ''}"

class NewFunction(New):
    codeBlock: 'CodeBlock'

    def __init__(self, target:Variable, codeBlock: 'CodeBlock', belongsTo: 'CodeBlock', srcPos: Tuple[int]):
        super().__init__(target, 'function', belongsTo, srcPos)
        self.codeBlock = codeBlock

    def _text(self):
        return f"{self.target} = NewFunction"

class NewClass(New):
    codeBlock: 'CodeBlock'
    bases: List[Variable]                # variables that points to a class object

    def __init__(self, target:Variable, bases:List[Variable], codeBlock: 'CodeBlock', belongsTo: 'CodeBlock', srcPos: Tuple[int]):
        super().__init__(target, 'class', belongsTo, srcPos)
        self.codeBlock = codeBlock
        self.bases = [None] * len(bases)
        for i in range(len(bases)):
            self.setBase(i, bases[i])

    def _unsetBase(self, index):
        if(self.bases[index] is None):
            return
        if(self.bases[index].isTmp):
            self.bases[index].usingIRs[USED_OTHERS].remove(self)
        self.bases[index] = None

    def setBase(self, index, base):
        self._unsetBase(index)
        if(base.isTmp):
           base.usingIRs[USED_OTHERS].append(self)
        self.bases[index] = base

    def destroy(self):
        for i in range(len(self.bases)):
            self._unsetBase(i)
        super().destroy()

    def _text(self):
        bases = [str(b) for b in self.bases]
        return f"{self.target} = NewClass ({', '.join(bases)})"
        


class NewBuiltin(New):
    type: str
    value: Any                          # optional, for example the value of str, int, double can be use
    def __init__(self, target:Variable, type: str, belongsTo: 'CodeBlock', srcPos: Tuple[int], value: Any=None):
        super().__init__(target, 'builtin', belongsTo, srcPos)
        self.type = type
        self.value = value

    def _text(self):
        return f"{self.target} = New {self.type}" + (f" ({self.value})" if self.value is not None else "")


# Important: calling a class object equarls to creating an instance! 
# adding a function/module code block should add all class code block inside!
class Call(IRStmt):
    target: Variable               
    callee: Variable
    posargs: List[Variable]
    kwargs: Dict[str, Variable]

    def __init__(self, target: Variable, callee: Variable, args: List[Variable], keywords: Dict[str, Variable], belongsTo: 'CodeBlock', srcPos: Tuple[int]):
        super().__init__(belongsTo, srcPos)
        self.setTarget(target)
        self.setCallee(callee)
        self.posargs = [None] * len(args)
        for i in range(len(args)):
            self.setArg(i, args[i])
        self.kwargs = {}
        for key, arg in keywords.items():
            self.setKeyword(key, arg)

    def _unsetTarget(self):
        if(not hasattr(self, "target")):
            return
        if(self.target.isTmp):
            self.target.usingIRs[DEFINED_OTHERS].remove(self)
        del self.target
    
    def _unsetCallee(self):
        if(not hasattr(self, "callee")):
            return
        if(self.callee.isTmp):
            self.callee.usingIRs[USED_OTHERS].remove(self)
        del self.callee

    def _unsetArg(self, index):
        if(self.posargs[index] is None):
            return
        if(self.posargs[index].isTmp):
            self.posargs[index].usingIRs[USED_OTHERS].remove(self)
        self.posargs[index] = None

    def _unsetKeyword(self, key):
        if(key not in self.kwargs):
            return
        if(self.kwargs[key].isTmp):
            self.kwargs[key].usingIRs[USED_OTHERS].remove(self)
        del self.kwargs[key]

    def setTarget(self, target):
        self._unsetTarget()
        if(target.isTmp):
            target.usingIRs[DEFINED_OTHERS].append(self)
        self.target = target

    def setCallee(self, callee):
        self._unsetCallee()
        if(callee.isTmp):
            callee.usingIRs[USED_OTHERS].append(self)
        self.callee = callee

    def setArg(self, index, arg):
        self._unsetArg(index)
        if(arg.isTmp):
            arg.usingIRs[USED_OTHERS].append(self)
        self.posargs[index] = arg
    
    def setKeyword(self, key, arg):
        self._unsetKeyword(key)
        if(arg.isTmp):
            arg.usingIRs[USED_OTHERS].append(self)
        self.kwargs[key] = arg

    def destroy(self):
        self._unsetTarget()
        self._unsetCallee()
        for i in range(len(self.posargs)):
            self._unsetArg(i)
        for key in self.kwargs:
            self._unsetKeyword(key)
        super().destroy()

    def _text(self):
        args = [str(arg) for arg in self.posargs]
        kws = [f"{kw}={arg}" for kw, arg in self.kwargs.items()]
        args += kws
        return f"{self.target} = Call {self.callee} ({', '.join(args)})"
        

class DelAttr(IRStmt):
    var: Variable
    attr: str
    
    def __init__(self, v: Variable, attr: str, belongsTo: 'CodeBlock', srcPos: Tuple[int]):
        super().__init__(belongsTo, srcPos)
        self.setVar(v)
        self.attr = attr

        
    def _unsetVar(self):
        if(not hasattr(self, "var")):
            return
        if(self.var.isTmp):
            self.var.usingIRs[USED_OTHERS].remove(self)
        del self.var

    def setVar(self, var):
        self._unsetVar()
        if(var.isTmp):
            var.usingIRs[USED_OTHERS].append(self)
        self.var = var

    def destroy(self):
        self._unsetVar()
        super().destroy()

    def _text(self):
        return f"Del {self.var}.{self.attr}"
        

# TODO: GET_ITEM(from, index), SET_ITEM(to, index), to support list, tuple, set, dict
# TODO: GET_ITER(v)

