import ast
import builtins
from typing import Set, Union
import typing
from xml.dom.minidom import Attr

from numpy import isin
from ..IR.CodeBlock import CodeBlock

from ..IR.FunctionCodeBlock import FunctionCodeBlock

from ..IR.ModuleCodeBlock import ModuleCodeBlock

from ..IR.ClassCodeBlock import ClassCodeBlock

from ..IR.IRStmts import *

if typing.TYPE_CHECKING:
    from PyPt.ModuleManager import ModuleManager

builtin_names = list(builtins.__dict__.keys())

class Attribute:
    var: Variable
    attrName: str
    def __init__(self, var: Variable, attrName: str):
        # assert(isinstance(var, Variable) and isinstance(attrName, str))
        self.var = var
        self.attrName = attrName

class Starred:
    var: Variable
    def __init__(self, var: Variable):
        # assert(isinstance(var, Variable))
        self.var = var

def isLoad(node: ast.AST) -> bool:
    return isinstance(node.ctx, ast.Load)

def isStore(node: ast.AST) -> bool:
    return isinstance(node.ctx, ast.Store)

def isDel(node: ast.AST) -> bool:
    return isinstance(node.ctx, ast.Del)

# codeBlock can be any, but remember that its enclosing and enclosing's enclosing must be function
def resolveName(codeBlock: CodeBlock, name: str) -> Union[Variable, Attribute]:
    

    if(isinstance(codeBlock, ClassCodeBlock)):
        if(name in codeBlock.declaredGlobal):
            return Attribute(codeBlock.module.globalVariable, name)
        elif(name in codeBlock.attributes):
            return Attribute(codeBlock.thisClassVariable, name)
        else:
            currCodeBlock = codeBlock.enclosing
    else:
        currCodeBlock = codeBlock
    
    
    while(not isinstance(currCodeBlock, ModuleCodeBlock)):
        if(isinstance(currCodeBlock, FunctionCodeBlock)):
            # check if it is global
            if(name in currCodeBlock.declaredGlobal):
                # jump to outer most codeBlock
                return Attribute(currCodeBlock.module.globalVariable, name)
            if(name in currCodeBlock.localVariables):
                return currCodeBlock.localVariables[name]

        currCodeBlock = currCodeBlock.enclosing

    return Attribute(currCodeBlock.globalVariable, name)
    


# Name bindings include: 
# formal parameters to functions (not implented here, because LocalScanner only deals with body statements)
# import statements
# class and function definitions (these bind the class or function name in the defining block)
# targets that are identifiers if occurring in an assignment, for loop header, or after as in a with statement or except clause. 

# When it is loaded, it can be Varaible, Starred or None
# When it is stored, it can be one of Attribute, Subscript, Starred, Variable, List or Tuple
class CodeBlockGenerator(ast.NodeVisitor):
    codeBlock: CodeBlock
    tmpVarCount: int
    lambdaCount: int
    tmpVariables: set[Variable]
    simplify: bool
    def __init__(self, moduleManager: 'ModuleManager'):
        # self.root = node
        # print(f"Into {name} @ {moduleName}")
        
        self.tmpVarCount = 0
        self.lambdaCount = 0
        self.tmpVariables = set()
        self.moduleManager = moduleManager

    def visit(self, node: ast.AST):
        node.result = None
        super().visit(node)

    def parse(self, node: ast.AST):
        self.preprocess(node)

        # all of the class, function, module have a body
        # nodes outside the body should be specially treated
        for stmt in node.body:
            self.visit(stmt)
        
        self.postprocess(node)

    def preprocess(self, node:ast.AST):
        pass

    def postprocess(self, node:ast.AST):
        pass

    def newTmpVariable(self) -> Variable:
        name = f"$t{self.tmpVarCount}"
        self.tmpVarCount += 1
        tmp = Variable(name, self.codeBlock, temp=True)
        self.tmpVariables.add(tmp)
        return tmp

    def addAssign(self, target: Variable, source: Variable):
        if(target and source):
            Assign(target, source, self.codeBlock)
        

    def addGetAttr(self, target: Variable, source: Attribute):
        if(target and source.var):
            GetAttr(target, source.var, source.attrName, self.codeBlock)
        

    def addSetAttr(self, target: Attribute, source: Variable):
        if(target.var and source):
            SetAttr(target.var, target.attrName, source, self.codeBlock)
        
    def addNewBuiltin(self, target: Variable, type: str, value: Any=None):
        if(target):
            NewBuiltin(target, type, value, self.codeBlock)
        
    def addCall(self, target: Variable, callee: Variable, args: List[Variable], keywords: Dict[str, Variable]):
        if(target and callee):
            Call(target, callee, args, keywords, self.codeBlock)
        
    def addNewFunction(self, target: Variable, codeBlock: FunctionCodeBlock):
        if(target):
            NewFunction(target, codeBlock, self.codeBlock)
        
    def addNewClass(self, target: Variable, bases: List[Variable], codeBlock: ClassCodeBlock):
        if(target):
            NewClass(target, bases, codeBlock, self.codeBlock)
        
    def addNewModule(self, target: Variable, module: Union[ModuleCodeBlock, str]):
        if(target):
            NewModule(target, module, self.codeBlock)
        
    def addNewSuper(self, target: Variable, type: Variable, bound: Variable):
        if(target and type and bound):
            NewSuper(target, type, bound, self.codeBlock)
        
    def addNewStaticMethod(self, target: Variable, func: Variable):
        if(target and func):
            NewStaticMethod(target, func, self.codeBlock)
        
    # def addNewClassMethod(self, target, func):
    #     if(target and func):
    #         NewClassMethod(target, func, self.codeBlock)
        
    def addDelAttr(self, attr: Attribute):
        if(attr.var):
            DelAttr(attr.var, attr.attrName, self.codeBlock)
        
    # names are resolved and replaced by variables or attributes as soon as being visited.
    def visit_Name(self, node: ast.Name):
        res = resolveName(self.codeBlock, node.id)
        if(isLoad(node) and isinstance(res, Attribute)):
            tmp = self.newTmpVariable()
            self.addGetAttr(tmp, res)
            node.result = tmp
        else:
            node.result = res

    def visit_Starred(self, node: ast.Starred):
        
        self.generic_visit(node)
        
        if(isinstance(node.value.result, Attribute)):
            attr = node.value.result
            tmp = self.newTmpVariable()
            if(isLoad(node)):
                self.addGetAttr(tmp, attr)
            elif(isStore(node)):
                self.addSetAttr(attr, tmp)
            node.result = Starred(tmp)
        else:
            node.result = Starred(node.value.result)

    def visit_Constant(self, node: ast.Constant):
        

        # if(isinstance(node.value, int)):
        #     type = "int"
        # elif(isinstance(node.value, float)):
        #     type = "float"
        # elif(isinstance(node.value, str)):
        #     type = "str"
        # elif(isinstance(node.value, complex)):
        #     type = "complex"
        # elif(node.value == None):
        #     type = "None"
        # else:
        #     type = "unknown"
        # tmp = self.newTmpVariable()
        # self.addNewBuiltin(tmp, type, node.value)
        # node.result = tmp
        node.result = None

    def visit_JoinedStr(self, node: ast.JoinedStr):
        # tmp = self.newTmpVariable()
        # self.addNewBuiltin(tmp, "str")
        node.result = None

    # every tuple has attribtues $n, where n is a number, and $tupleElements
    # $values refers to the elements whose indexes are mixed together, we can't tell which one is what
    # $tupleElements refer to those that has clear index, for example the first element of a tuple
    def visit_Tuple(self, node: ast.Tuple):
        
        self.generic_visit(node)
        if(isLoad(node)):
            tmp = self.newTmpVariable()
            self.addNewBuiltin(tmp, "tuple")
                
            l = len(node.elts)
            # from the front to the first starred expression
            posIndex = 0
            while(posIndex < l and isinstance(node.elts[posIndex].result, Variable)):
                elt = node.elts[posIndex].result
                self.addSetAttr(Attribute(tmp, f"${posIndex}"), elt)
                self.addSetAttr(Attribute(tmp, "$tupleElements"), elt)
                posIndex += 1
            # from the end to the last starred expression
            negIndex = -1
            while(negIndex >= -l and isinstance(node.elts[negIndex].result, Variable)):
                elt = node.elts[negIndex].result
                self.addSetAttr(Attribute(tmp, f"${negIndex}"), elt)
                self.addSetAttr(Attribute(tmp, "$tupleElements"), elt)
                negIndex -= 1

            # from the first starred expression to the last starred expression
            for i in range(posIndex, l + negIndex + 1):
                elt = node.elts[i].result
                if(isinstance(elt, Starred)):
                    tmp2 = self.newTmpVariable()
                    self.addGetAttr(tmp2, Attribute(elt.var, "$tupleElements"))
                    self.addGetAttr(tmp2, Attribute(elt.var, "$values"))
                    self.addSetAttr(Attribute(tmp, "$values"), tmp2)
                else:
                    self.addSetAttr(Attribute(tmp, "$values"), elt)
            
            # self._makeIterator(tmp, {Attribute(tmp, "$tupleElements"), Attribute(tmp, "$values")})
            node.result = tmp
        
    
    # def _makeList(self) -> Variable:
    #     tmp = self.newTmpVariable()
    #     self.addNewBuiltin(tmp, "list")
    #     # self._makeIterator(tmp, {Attribute(tmp, "$values")})
    #     return tmp

    # every list has $values
    def visit_List(self, node: ast.List):
        
        if(isLoad(node)):
            self.visit_Set(node)
        else:
            self.generic_visit(node)

    def visit_Set(self, node: ast.Set):
        self.generic_visit(node)
        tmp = self.newTmpVariable()
        self.addNewBuiltin(tmp, "list")
        
        for elt in node.elts:
            elt = elt.result
            if(isinstance(elt, Starred)):
                tmp2 = self.newTmpVariable()
                self.addGetAttr(tmp2, Attribute(elt.var, "$tupleElements"))
                self.addGetAttr(tmp2, Attribute(elt.var, "$values"))
                self.addSetAttr(Attribute(tmp, "$values"), tmp2)
                
            else:
                self.addSetAttr(Attribute(tmp, "$values"), elt)
                
        node.result = tmp

    def _makeDict(self) -> Variable:
        tmp = self.newTmpVariable()
        self.addNewBuiltin(tmp, "dict")
        # self._makeIterator(tmp, {Attribute(tmp, "$keys")})
        return tmp
        
    # every dict has $values and $keys
    def visit_Dict(self, node: ast.Dict):
        
        self.generic_visit(node)

        tmp = self._makeDict()
        for key in node.keys:
            if(key):
                self.addSetAttr(Attribute(tmp, "$keys"), key.result)
        
        for value in node.values:
            self.addSetAttr(Attribute(tmp, "$values"), value.result)

        node.result = tmp
        
    def visit_BoolOp(self, node: ast.BoolOp):
        
        self.generic_visit(node)

        tmp = self.newTmpVariable()
        for value in node.values:
            self.addAssign(tmp, value.result)
        node.result = tmp

    def visit_Compare(self, node: ast.Compare):
        
        self.generic_visit(node)

        # tmp = self.newTmpVariable()
        # self.add
        # NewBuiltin(tmp, "bool", self.codeBlock, value=True)
        # NewBuiltin(tmp, "bool", self.codeBlock, value=False)
        node.result = None

    def visit_UnaryOp(self, node: ast.UnaryOp):
        
        self.generic_visit(node)

        # tmp = self.newTmpVariable()
        # NewBuiltin(tmp, "unknown", self.codeBlock)
        node.result = None

    def visit_BinOp(self, node: ast.BinOp):
        
        self.generic_visit(node)

        # tmp = self.newTmpVariable()
        # NewBuiltin(tmp, "unknown", self.codeBlock)
        node.result = None

    def visit_Call(self, node: ast.Call):
        # special case: super()
        # TODO: too ugly! model builtin functions in the future
        tmp = self.newTmpVariable()
        if(isinstance(node.func, ast.Name) and node.func.id == "super"):
            type = None
            bound = None
            if(len(node.args) > 0):
                self.visit(node.args[0])
                type = node.args[0].result
            else:
                cb = self.codeBlock
                while(cb):
                    if(isinstance(cb, ClassCodeBlock)):
                        type = cb.thisClassVariable
                        break
                    cb = cb.enclosing

            if(len(node.args) > 1):
                self.visit(node.args[1])
                bound = node.args[1].result
            elif(isinstance(self.codeBlock, FunctionCodeBlock) and len(self.codeBlock.posargs) > 0):
                bound = self.codeBlock.posargs[0]
            
            if(type and bound):
                self.addNewSuper(tmp, type, bound)
                
            
        self.generic_visit(node)
        func = node.func.result
        
        # Starred is not supported so far
        args = [v.result for v in node.args if isinstance(v.result, Variable)]
        keywords = {kw.arg:kw.value.result for kw in node.keywords if isinstance(kw.value.result, Variable)}
        self.addCall(tmp, func, args, keywords)
        node.result = tmp

    def visit_IfExp(self, node: ast.IfExp):
        
        self.generic_visit(node)

        tmp = self.newTmpVariable()
        self.addAssign(tmp, node.body.result)
        self.addAssign(tmp, node.orelse.result)
        node.result = tmp

    def visit_Attribute(self, node: ast.Attribute):
        
        self.generic_visit(node)

        if(isLoad(node)):
            srcVar = node.value.result
            
            tmp = self.newTmpVariable()
            self.addGetAttr(tmp, Attribute(srcVar, node.attr))
            node.result = tmp
        elif(isStore(node) or isDel(node)):
            node.result = Attribute(node.value.result, node.attr)
        
           
    def visit_NamedExpr(self, node: ast.NamedExpr):
        
        self.generic_visit(node)
        self._handleAssign(node.target, node.value.result)
        node.result = node.target.result

    def visit_Assign(self, node: ast.Assign) -> ast.Assign:
        # assign.targets can only be Attribute, Subscript, Starred, Name, List or Tuple
        # see https://docs.python.org/zh-cn/3.9/library/ast.html
        
        self.generic_visit(node)

        for target in node.targets:
            self._handleAssign(target, node.value.result)
        
    def visit_AnnAssign(self, node: ast.AnnAssign):
        
        self.generic_visit(node)

        if(node.value):
            self._handleAssign(node.target, node.value.result)

    # let all subscribable objects have a attribute $values, tuple is an exception  
    def visit_Subscript(self, node: ast.Subscript):
        
        self.visit(node.value)

        if(isLoad(node)):
            tmp = self.newTmpVariable()
            # if it is tuple
            if(isinstance(node.slice, ast.Constant) and isinstance(node.slice.value, int)):
                i = node.slice.value
                # $tmp = v.$i
                self.addGetAttr(tmp, Attribute(node.value.result, f"${i}"))
            else:
                self.addGetAttr(tmp, Attribute(node.value.result, "$tupleElements"))
                
            
            # if it is list, set, dict
            self.addGetAttr(tmp, Attribute(node.value.result, "$values"))
            node.result = tmp
        elif(isStore(node)):
            # if it is list, set, dict
            node.result = Attribute(node.value.result, "$values")

    
    def visit_ListComp(self, node: ast.ListComp):
        
        self.generic_visit(node)
        tmp = self.newTmpVariable()
        self.addNewBuiltin(tmp, "list")
        self.addSetAttr(Attribute(tmp, "$values"), node.elt.result)
        
        for comp in node.generators:
            self._handleFor(comp.target, comp.iter)
        node.result = tmp


    def visit_SetComp(self, node: ast.SetComp):
        self.visit_ListComp(node)

    def visit_DictComp(self, node: ast.DictComp):
        
        self.generic_visit(node)
        tmp = self._makeDict()
        self.addSetAttr(Attribute(tmp, "$keys"), node.key.result)
        self.addSetAttr(Attribute(tmp, "$value"), node.value.result)
        
        for comp in node.generators:
            self._handleFor(comp.target, comp.iter)
        node.result = tmp

    # def _makeGenerator(self, elts: Set, sended: Variable) -> Variable:
    #     tmp = self.newTmpVariable()
    #     self.addNewBuiltin(tmp, "generator")
        
    #     self._makeIterator(tmp, elts)
    #     # TODO: This is too ugly!
    #     if(sended):
    #         # def send(value):
    #         #    sended = value
    #         send = FunctionCodeBlock(f"<{tmp.name}>send", self.codeBlock, fake=True)
    #         value = Variable("value", send)
    #         send.posargs.append(value)
    #         send.kwargs["value"] = value
    #         Assign(sended, value, send)
            
            

    #         # tmp.send = new function
    #         tmp2 = self.newTmpVariable()
    #         self.addNewFunction(tmp, send)
    #         self.addSetAttr(Attribute(tmp2, "send"), tmp)
            
    #         return tmp

    def visit_GeneratorExp(self, node: ast.GeneratorExp):
        
        self.generic_visit(node)
        tmp = self.newTmpVariable()
        self.addNewBuiltin(tmp, "list")
        self.addSetAttr(Attribute(tmp, "$values"), node.elt.result)
        # tmp = self._makeGenerator({node.elt.result}, None)
        for comp in node.generators:
            self._handleFor(comp.target, comp.iter)
        node.result = tmp

    def visit_Delete(self, node: ast.Delete):
        
        self.generic_visit(node)

        for target in node.targets:
            if(isinstance(target.result, Attribute)):
                self.addDelAttr(target.result)
                

    def visit_Import(self, node: ast.Import):
        
        callerName = self.codeBlock.module.name
        for alias in node.names:
            self.moduleManager.import_hook(alias.name, callerName)
            if(alias.asname is None):
                name, _, _ = alias.name.partition(".")
                cb = self.moduleManager.getCodeBlock(name, callerName)
            else:
                name = alias.asname
                cb = self.moduleManager.getCodeBlock(alias.name, callerName)
            
            
            resolved = resolveName(self.codeBlock, name)
            if(isinstance(resolved, Variable)):
                self.addNewModule(resolved, cb)
                
            elif(isinstance(resolved, Attribute)):
                tmp = self.newTmpVariable()
                self.addNewModule(tmp, cb)
                self.addSetAttr(resolved, tmp)
                

    def visit_ImportFrom(self, node: ast.ImportFrom):
        
        callerName = self.codeBlock.module.name
        fromlist = [alias.name for alias in node.names]
        self.moduleManager.import_hook(node.module or "", callerName, fromlist, level=node.level)
        imported = self.moduleManager.getCodeBlock(node.module, callerName, level=node.level)
        tmpModule = self.newTmpVariable()
        self.addNewModule(tmpModule, imported)
        aliases = {}  # local name -> imported name
        hasstar = False
        for alias in node.names:
            if(alias.name == "*"):
                hasstar = True
                continue
            if(alias.asname is None):
                aliases[alias.name] = alias.name
            else:
                aliases[alias.asname] = alias.name
             
        if(hasstar and isinstance(imported, ModuleCodeBlock)):
            # if(not imported.done):
            #     raise Exception(f"Circular import between {self.codeBlock.moduleName} and {imported.moduleName}!")
            for name in imported.globalNames:
                if(name not in builtin_names and name[0] != "_"):
                    # ignore those start with "_"
                    aliases[name] = name

        for newName, oldName in aliases.items():
            resolved = resolveName(self.codeBlock, newName)
            if(isinstance(resolved, Variable)):
                self.addGetAttr(resolved, Attribute(tmpModule, oldName))
                
            elif(isinstance(resolved, Attribute)):
                tmp = self.newTmpVariable()
                self.addGetAttr(tmp, Attribute(tmpModule, oldName))
                self.addSetAttr(resolved, tmp)
                

    def _handleFor(self, target, iter):
        # $iterMethod = iter.__iter__
        tmp = self.newTmpVariable()
        
        self.addGetAttr(tmp, Attribute(iter.result, "$values"))
        self.addGetAttr(tmp, Attribute(iter.result, "$tupleElements"))
        self.addGetAttr(tmp, Attribute(iter.result, "$keys"))
        self._handleAssign(target, tmp)

    def visit_For(self, node: ast.For):
        self.generic_visit(node)
        self._handleFor(node.target, node.iter)

    def visit_With(self, node: ast.With):
        
        self.generic_visit(node)
        for item in node.items:
            if(item.optional_vars):
                self._handleAssign(item.optional_vars, item.context_expr.result)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        # v = new_function(codeBlock)
        
        from .FunctionGenerator import FunctionGenerator
        generator = FunctionGenerator(node.name, self.codeBlock, moduleManager=self.moduleManager)
        generator.parse(node)
        func = generator.codeBlock

        # default parameters
        self.generic_visit(node.args)
        posargs = [arg.arg for arg in node.args.posonlyargs] + [arg.arg for arg in node.args.args]
        kwonlyargs = [arg.arg for arg in node.args.kwonlyargs]
        defaults = node.args.defaults
        kw_defaults = node.args.kw_defaults
        # for posargs
        start = len(posargs) - len(defaults)
        for i in range(len(defaults)):
            arg = func.localVariables[posargs[start + i]]
            generator.addAssign(arg, defaults[i].result)
        # for kwargs
        for i in range(len(kw_defaults)):
            arg = func.localVariables[kwonlyargs[i]]
            if(kw_defaults[i]):
                generator.addAssign(arg, kw_defaults[i].result)


        resolved = resolveName(self.codeBlock, node.name)
        tmp = self.newTmpVariable()

        if(isinstance(resolved, Variable)):
            self.addAssign(resolved, tmp)
        elif(isinstance(resolved, Attribute)):
            self.addSetAttr(resolved, tmp)
            

        for decorator in node.decorator_list:
            
            nextTmp = self.newTmpVariable()
            if(isinstance(decorator, ast.Name) and decorator.id == "staticmethod"):
                self.addNewStaticMethod(tmp, nextTmp) 
            elif(isinstance(decorator, ast.Name) and decorator.id == "classmethod"):
                # self.addNewClassMethod(tmp, nextTmp)
                nextTmp = tmp
            else:
                self.visit(decorator)
                self.addCall(tmp, decorator.result, [nextTmp], {})
                
            tmp = nextTmp
        self.addNewFunction(tmp, func)
       

    def visit_Lambda(self, node: ast.Lambda):
        
        from .FunctionGenerator import FunctionGenerator
        generator = FunctionGenerator(f"$lambda{self.lambdaCount}", self.codeBlock, moduleManager=self.moduleManager)
        self.lambdaCount += 1

        generator.parse(node)
        func = generator.codeBlock

        # default parameters
        self.generic_visit(node.args)
        posargs = [arg.arg for arg in node.args.posonlyargs] + [arg.arg for arg in node.args.args]
        kwonlyargs = [arg.arg for arg in node.args.kwonlyargs]
        defaults = node.args.defaults
        kw_defaults = node.args.kw_defaults
        # for posargs
        start = len(posargs) - len(defaults)
        for i in range(len(defaults)):
            arg = func.localVariables[posargs[start + i]]
            generator.addAssign(arg, defaults[i].result)
            
        # for kwargs
        for i in range(len(kw_defaults)):
            if(not kwonlyargs[i]):
                continue
            arg = func.localVariables[kwonlyargs[i]]
            generator.addAssign(arg, kw_defaults[i].result)

        tmp = self.newTmpVariable()
        self.addNewFunction(tmp, func)

        node.result = tmp
    
    def visit_ClassDef(self, node: ast.ClassDef):
        from .ClassGenerator import ClassGenerator
        generator = ClassGenerator(node.name, self.codeBlock, moduleManager=self.moduleManager)
        generator.parse(node)
        # TODO: a better way to deal with it when base is a starred?
        bases = []
        for base in node.bases:
            self.visit(base)
            if(isinstance(base.result, Variable)):
                bases.append(base.result)

        resolved = resolveName(self.codeBlock, node.name)
        if(isinstance(resolved, Variable)):
            self.addNewClass(resolved, bases, generator.codeBlock)
        elif(isinstance(resolved, Attribute)):
            tmp = self.newTmpVariable()
            self.addNewClass(tmp, bases, generator.codeBlock)
            self.addSetAttr(resolved, tmp)
            
    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self.visit_FunctionDef(node)

    def visit_Await(self, node: ast.Await):
        self.generic_visit(node)
        node.result = node.value.result

    def visit_AsyncFor(self, node: ast.AsyncFor):
        self.visit_For(node)

    def visit_AsyncWith(self, node: ast.AsyncWith):
        self.visit_With(node)

    def _handleAssign(self, target: ast.AST, value: Variable):
        
        assert(not value or isinstance(value, Variable))
        if(isinstance(target, ast.Name) or isinstance(target, ast.Attribute) 
            or isinstance(target, ast.NamedExpr) or isinstance(target, ast.Subscript)):
            # left = right
            left = target.result
            if(isinstance(left, Variable)):
                self.addAssign(left, value)
            
            elif(isinstance(left, Attribute)):
                self.addSetAttr(left, value)
                
        elif(isinstance(target, ast.Tuple) or isinstance(target, ast.List)):
            posIndex = 0
            negIndex = -len(target.elts)
            afterStarred = False
            for elt in target.elts:
                
                if(isinstance(elt.result, Starred)):
                    afterStarred = True
                    tmp = self.newTmpVariable()
                    self.addNewBuiltin(tmp, "list")
                    tmp2 = self.newTmpVariable()
                    # if value is a list
                    self.addGetAttr(tmp2, Attribute(value, "$values"))
                    
                    # if value is a tuple
                    self.addGetAttr(tmp2, Attribute(value, "$tupleElements"))
                    self.addSetAttr(Attribute(tmp, "$values"), tmp2)
                    self.addAssign(elt.result.var, tmp)
                    
                else:
                    if(afterStarred):
                        i = negIndex
                    else:
                        i = posIndex
                    # value might be a tuple
                    tmp = self.newTmpVariable()
                    self.addGetAttr(tmp, Attribute(value, f"${i}"))
                    self._handleAssign(elt, tmp)

                    # value might be a list
                    tmp = self.newTmpVariable()
                    self.addGetAttr(tmp, Attribute(value, "$values"))
                    self._handleAssign(elt, tmp)

                posIndex += 1
                negIndex += 1
        else:
            # I make all subscribtable objects own a attribute $values
            # Subscript is replaced by ast.Attribute
            assert(False)

    # set up __iter__() for a variable 
    # def _makeIterator(self, v:Variable, elts:Set[Union[Variable, Attribute]]):
    #     if(not v):
    #         return

    #     iter = FunctionCodeBlock(f"{v.name}__iter__", self.codeBlock, fake=True)
    #     next = FunctionCodeBlock(f"{v.name}__next__", self.codeBlock, fake=True)
        

    #     # v.__iter__ = new function
    #     tmp = self.newTmpVariable()
    #     self.addNewFunction(tmp, iter)
    #     self.addSetAttr(Attribute(v, "__iter__"), tmp)
        
        
    #     # In __iter__()
    #     # $1 = new function(__next__)
    #     # v.__next__ = $1
    #     # ret = v
    #     tmp = Variable("$1", iter)
        
    #     NewBuiltin(iter.returnVariable, "iterator", None, iter)
    #     NewFunction(tmp, next, iter)
    #     SetAttr(v, "__next__", tmp, iter)
    #     Assign(iter.returnVariable, v, iter)

    #     # In __next__(), ret = elts
    #     for elt in elts:
    #         if(isinstance(elt, Variable)):
    #             Assign(next.returnVariable, elt, next)
    #         elif(isinstance(elt, Attribute)):
    #             GetAttr(next.returnVariable, elt.var, elt.attrName, next)

    # TODO: add line and column number into IR


