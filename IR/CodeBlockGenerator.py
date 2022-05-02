import ast
from typing import Set, Union

from .CodeBlock import ClassCodeBlock, CodeBlock, FunctionCodeBlock, ModuleCodeBlock

from .Stmts import *
from .Scanner import BindingScanner, DeclarationScanner

if typing.TYPE_CHECKING:
    from ModuleManager import ModuleManager

# Wrapper for variable
class VariableNode(ast.AST):
    var: Variable
    def __init__(self, v:Variable):
        self.var = v


# Some utils        
def makeAttribute(v: Variable, attr: str) -> ast.Attribute:
    attribute =  ast.Attribute()
    attribute.value = VariableNode(v)
    attribute.attr = attr
    return attribute

def isLoad(node: ast.AST) -> bool:
    return isinstance(node.ctx, ast.Load)

def isStore(node: ast.AST) -> bool:
    return isinstance(node.ctx, ast.Store)

def isDel(node: ast.AST) -> bool:
    return isinstance(node.ctx, ast.Del)

# codeBlock can be any, but remember that its enclosing and enclosing's enclosing must be function
def resolveName(codeBlock: CodeBlock, name: str) -> Union[VariableNode, ast.Attribute]:
    
    if(isinstance(codeBlock, ModuleCodeBlock)):
        return makeAttribute(codeBlock.globalVariable, name)

    if(isinstance(codeBlock, ClassCodeBlock)):
        if(name in codeBlock.declaredGlobal):
            return makeAttribute(codeBlock.globalVariable, name)
        elif(name in codeBlock.attributes):
            return makeAttribute(codeBlock.thisClassVariable, name)
        else:
            currCodeBlock = codeBlock.enclosing
    else:
        currCodeBlock = codeBlock
    
    # currCodeBlock is function codeblock
    while(currCodeBlock is not None):
        # check if it is global
        if(name in currCodeBlock.declaredGlobal):
            break

        if(name in currCodeBlock.localVariables):
            return VariableNode(currCodeBlock.localVariables[name])

        currCodeBlock = currCodeBlock.enclosing

    return makeAttribute(codeBlock.globalVariable, name)
    


# Name bindings include: 
# formal parameters to functions (not implented here, because LocalScanner only deals with body statements)
# import statements
# class and function definitions (these bind the class or function name in the defining block)
# targets that are identifiers if occurring in an assignment, for loop header, or after as in a with statement or except clause. 

# IR is generated from the bottom of the AST to the top.
# After a subtree is processed, the root will be replaced by the result. This result may be useful to its parent or ancient node.
# The result's type differs according to context. 
# When it is loaded, it can be VaraibleNode
# When it is stored, it can be one of Attribute, Subscript, Starred, Variable, List or Tuple
class CodeBlockGenerator(ast.NodeTransformer):
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
    
    # names are resolved and replaced by variables or attributes as soon as being visited.
    def visit_Name(self, node: ast.Name) -> Union[VariableNode, ast.Attribute]:
        

        res = resolveName(self.codeBlock, node.id)
        if(isLoad(node) and isinstance(res, ast.Attribute)):
            tmp = self.newTmpVariable()
            GetAttr(tmp, res.value.var, res.attr, self.codeBlock)
            return VariableNode(tmp)
        else:
            return res

    def visit_Starred(self, node: ast.Starred) -> Any:
        
        self.generic_visit(node)
        if(isinstance(node.value, ast.Attribute)):
            tmp = self.newTmpVariable()
            if(isLoad(node)):
                GetAttr(tmp, node.value.value.var, node.value.attr, self.codeBlock)
            elif(isStore(node)):
                SetAttr(node.value.value.var, node.value.attr, tmp, self.codeBlock)  
            node.value = VariableNode(tmp)
        return node

    def visit_Constant(self, node: ast.Constant) -> Any:
        

        if(isinstance(node.value, int)):
            type = "int"
        elif(isinstance(node.value, float)):
            type = "float"
        elif(isinstance(node.value, str)):
            type = "str"
        elif(isinstance(node.value, complex)):
            type = "complex"
        elif(node.value == None):
            type = "None"
        else:
            type = "unknown"
        tmp = self.newTmpVariable()
        NewBuiltin(tmp, type, self.codeBlock, node.value)
        return VariableNode(tmp)

    def visit_JoinedStr(self, node: ast.JoinedStr) -> Any:
        

        tmp = self.newTmpVariable()
        NewBuiltin(tmp, "str", self.codeBlock)
        return VariableNode(tmp)

    # every tuple has attribtues $n, where n is a number, and $tupleElements
    # $values refers to the elements whose indexes are mixed together, we can't tell which one is what
    # $tupleElements refer to those that has clear index, for example the first element of a tuple
    def visit_Tuple(self, node: ast.Tuple) -> Any:
        

        self.generic_visit(node)
        if(isLoad(node)):
            tmp = self.newTmpVariable()
            NewBuiltin(tmp, "tuple", self.codeBlock)
                
                
            l = len(node.elts)
            # from the front to the first starred expression
            posIndex = 0
            while(posIndex < l and isinstance(node.elts[posIndex], VariableNode)):
                elt = node.elts[posIndex]
                SetAttr(tmp, f"${posIndex}", elt.var, self.codeBlock)
                SetAttr(tmp, f"$tupleElements", elt.var, self.codeBlock)
                posIndex += 1
            # from the end to the last starred expression
            negIndex = -1
            while(negIndex >= -l and isinstance(node.elts[negIndex], VariableNode)):
                elt = node.elts[negIndex]
                SetAttr(tmp, f"${negIndex}", elt.var, self.codeBlock)
                SetAttr(tmp, f"$tupleElements", elt.var, self.codeBlock)
                negIndex -= 1

            # from the first starred expression to the last starred expression
            for i in range(posIndex, l + negIndex + 1):
                elt = node.elts[i]
                if(isinstance(elt, ast.Starred)):
                    tmp2 = self.newTmpVariable()
                    GetAttr(tmp2, elt.value.var, "$tupleElements", self.codeBlock)
                    GetAttr(tmp2, elt.value.var, "$values", self.codeBlock)
                    SetAttr(tmp, "$values", tmp2, self.codeBlock)
                else:
                    SetAttr(tmp, "$values", elt.var, self.codeBlock)
            
            self._makeIterator(tmp, {makeAttribute(tmp, "$tupleElements"), makeAttribute(tmp, "$values")})
            return VariableNode(tmp)
        elif(isStore(node)):
            return node
    
    def _makeList(self) -> Variable:
        tmp = self.newTmpVariable()
        NewBuiltin(tmp, "list", self.codeBlock)
        self._makeIterator(tmp, {makeAttribute(tmp, "$values")})
        return tmp

    # every list has $values
    def visit_List(self, node: ast.List) -> Any:
        
        self.generic_visit(node)

        if(isLoad(node)):
            tmp = self._makeList()
            
            for elt in node.elts:
                if(isinstance(elt, ast.Starred)):
                    tmp2 = self.newTmpVariable()
                    GetAttr(tmp2, elt.value.var, "$tupleElements", self.codeBlock)
                    GetAttr(tmp2, elt.value.var, "$values", self.codeBlock)
                    SetAttr(tmp, "$values", tmp2, self.codeBlock)
                else:
                    SetAttr(tmp, "$values", elt.var, self.codeBlock)

            return VariableNode(tmp)
        elif(isStore(node)):
            return node
    
    def _makeSet(self) -> Variable:
        tmp = self.newTmpVariable()
        NewBuiltin(tmp, "set", self.codeBlock)
        self._makeIterator(tmp, {makeAttribute(tmp, "$values")})
        return tmp

    # every set has $values
    def visit_Set(self, node: ast.Set) -> Any:
        
        self.generic_visit(node)

        tmp = self._makeSet()
        for elt in node.elts:
            if(isinstance(elt, ast.Starred)):
                tmp2 = self.newTmpVariable()
                GetAttr(tmp2, elt.value.var, "$tupleElements", self.codeBlock)
                GetAttr(tmp2, elt.value.var, "$values", self.codeBlock)
                SetAttr(tmp, "$values", tmp2, self.codeBlock)
            else:
                SetAttr(tmp, "$values", elt.var, self.codeBlock)

        return VariableNode(tmp)

    def _makeDict(self) -> Variable:
        tmp = self.newTmpVariable()
        NewBuiltin(tmp, "dict", self.codeBlock)
        self._makeIterator(tmp, {makeAttribute(tmp, "$keys")})
        return tmp
        
    # every dict has $values and $keys
    def visit_Dict(self, node: ast.Dict) -> Any:
        
        self.generic_visit(node)

        tmp = self._makeDict()
        for key in node.keys:
            if(key):
                SetAttr(tmp, "$keys", key.var, self.codeBlock)

        for value in node.values:
            SetAttr(tmp, "$values", value.var, self.codeBlock)

        
        return VariableNode(tmp)
        
    def visit_BoolOp(self, node: ast.BoolOp) -> Any:
        
        self.generic_visit(node)

        tmp = self.newTmpVariable()
        for value in node.values:
            Assign(tmp, value.var, self.codeBlock)
        return VariableNode(tmp)

    def visit_Compare(self, node: ast.Compare) -> Any:
        
        self.generic_visit(node)

        tmp = self.newTmpVariable()
        NewBuiltin(tmp, "bool", self.codeBlock, value=True)
        NewBuiltin(tmp, "bool", self.codeBlock, value=False)
        return VariableNode(tmp)

    def visit_UnaryOp(self, node: ast.UnaryOp) -> Any:
        
        self.generic_visit(node)

        tmp = self.newTmpVariable()
        NewBuiltin(tmp, "unknown", self.codeBlock)
        return VariableNode(tmp)

    def visit_BinOp(self, node: ast.BinOp) -> Any:
        
        self.generic_visit(node)

        tmp = self.newTmpVariable()
        NewBuiltin(tmp, "unknown", self.codeBlock)
        return VariableNode(tmp)

    def visit_Call(self, node: ast.Call) -> Any:
        
        self.generic_visit(node)

        assert(isinstance(node.func, VariableNode))
        # Starred is not supported so far
        args = [v.var for v in node.args if isinstance(v, VariableNode)]
        keywords = {kw.arg:kw.value.var for kw in node.keywords}
        tmp = self.newTmpVariable()
        Call(tmp, node.func.var, args, keywords, self.codeBlock)
        return VariableNode(tmp)

    def visit_IfExp(self, node: ast.IfExp) -> Any:
        
        self.generic_visit(node)

        tmp = self.newTmpVariable()
        Assign(tmp, node.body.var, self.codeBlock)
        Assign(tmp, node.orelse.var, self.codeBlock)
        return VariableNode(tmp)

    def visit_Attribute(self, node: ast.Attribute) -> Union[VariableNode, ast.Attribute]:
        
        self.generic_visit(node)

        if(isLoad(node)):
            assert(isinstance(node.value, VariableNode))
            tmp = self.newTmpVariable()
            GetAttr(tmp, node.value.var, node.attr, self.codeBlock)
            return VariableNode(tmp)
        elif(isStore(node) or isDel(node)):
            return node
           
    def visit_NamedExpr(self, node: ast.NamedExpr) -> Any:
        
        self.generic_visit(node)
        self._handleAssign(node.target, node.value)
        return node.target

    def visit_Assign(self, node: ast.Assign) -> ast.Assign:
        # assign.targets can only be Attribute, Subscript, Starred, Name, List or Tuple
        # see https://docs.python.org/zh-cn/3.9/library/ast.html
        
        self.generic_visit(node)

        for target in node.targets:
            self._handleAssign(target, node.value)
        
    def visit_AnnAssign(self, node: ast.AnnAssign) -> Any:
        
        self.generic_visit(node)

        if(hasattr(node, "value")):
            self._handleAssign(node.target, node.value)

    # let all subscribable objects have a attribute $values, tuple is an exception  
    def visit_Subscript(self, node: ast.Subscript) -> Any:
        
        node.value = self.visit(node.value)

        if(isLoad(node)):
            tmp = self.newTmpVariable()
            # if it is tuple
            if(isinstance(node.slice, ast.Constant) and isinstance(node.slice.value, int)):
                i = node.slice.value
                # $tmp = v.$i
                GetAttr(tmp, node.value.var, f"${i}", self.codeBlock)
            else:
                GetAttr(tmp, node.value.var, "$tupleElements", self.codeBlock)
            
            # if it is list, set, dict
            GetAttr(tmp, node.value.var, "$values", self.codeBlock)
            return VariableNode(tmp)
        elif(isStore(node)):
            # if it is list, set, dict
            return makeAttribute(node.value.var, "$values")

    # TODO
    def visit_ListComp(self, node: ast.ListComp) -> Any:
        
        self.generic_visit(node)
        tmp = self._makeList()
        SetAttr(tmp, "$values", node.elt.var, self.codeBlock)
        for comp in node.generators:
            self._handleFor(comp.target, comp.iter)
        return VariableNode(tmp)


    def visit_SetComp(self, node: ast.SetComp) -> Any:
        
        self.generic_visit(node)
        tmp = self._makeSet()
        SetAttr(tmp, "$values", node.elt.var, self.codeBlock)
        for comp in node.generators:
            self._handleFor(comp.target, comp.iter)
        return VariableNode(tmp)

    def visit_DictComp(self, node: ast.DictComp) -> Any:
        
        self.generic_visit(node)
        tmp = self._makeDict()
        SetAttr(tmp, "$keys", node.key.var, self.codeBlock)
        SetAttr(tmp, "$value", node.value.var, self.codeBlock)
        for comp in node.generators:
            self._handleFor(comp.target, comp.iter)
        return VariableNode(tmp)

    def _makeGenerator(self, elts: Set, sended: Variable) -> Variable:
        tmp = self.newTmpVariable()
        NewBuiltin(tmp, "generator", self.codeBlock)
        self._makeIterator(tmp, elts)
        # TODO: This is too ugly!
        if(sended):
            # def send(value):
            #    sended = value
            send = FunctionCodeBlock(f"<{tmp.name}>send", self.codeBlock, fake=True)
            value = Variable("value", send)
            send.posargs.append(value)
            send.kwargs["value"] = value
            Assign(sended, value, send)

            # tmp.send = new function
            tmp2 = self.newTmpVariable()
            NewFunction(tmp, send, self.codeBlock)
            SetAttr(tmp2, "send", tmp, self.codeBlock)
        return tmp

    def visit_GeneratorExp(self, node: ast.GeneratorExp) -> Any:
        
        self.generic_visit(node)
        tmp = self._makeGenerator({node.elt}, None)
        for comp in node.generators:
            self._handleFor(comp.target, comp.iter)
        return VariableNode(tmp)

    def visit_Delete(self, node: ast.Delete) -> Any:
        
        self.generic_visit(node)

        for target in node.targets:
            if(isinstance(target, ast.Attribute)):
                DelAttr(target.value.var, target.attr, self.codeBlock)

    def visit_Import(self, node: ast.Import) -> Any:
        
        caller = self.codeBlock.moduleName
        for alias in node.names:
            self.moduleManager.import_hook(alias.name, caller)
            if(alias.asname is None):
                name, _, _ = alias.name.partition(".")
                cb = self.moduleManager.getCodeBlock(name, caller)
            else:
                name = alias.asname
                cb = self.moduleManager.getCodeBlock(alias.name, caller)
            
            
            resolved = resolveName(self.codeBlock, name)
            if(isinstance(resolved, VariableNode)):
                NewModule(resolved.var, cb, self.codeBlock)
            elif(isinstance(resolved, ast.Attribute)):
                tmp = self.newTmpVariable()
                NewModule(tmp, cb, self.codeBlock)
                SetAttr(resolved.value.var, resolved.attr, tmp, self.codeBlock)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> Any:
        
        caller = self.codeBlock.moduleName
        fromlist = [alias.name for alias in node.names]
        self.moduleManager.import_hook(node.module or "", caller, fromlist, level=node.level)
        imported: ModuleCodeBlock = self.moduleManager.getCodeBlock(node.module, caller, level=node.level)
        tmpModule = self.newTmpVariable()
        NewModule(tmpModule, imported, self.codeBlock)
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
             
        if(hasstar and imported):
            # if(not imported.done):
            #     raise Exception(f"Circular import between {self.codeBlock.moduleName} and {imported.moduleName}!")
            for name in imported.globalNames:
                if(name[0] != "_"):
                    # ignore those start with "_"
                    aliases[name] = name

        for newName, oldName in aliases.items():
            resolved = resolveName(self.codeBlock, newName)
            if(isinstance(resolved, VariableNode)):
                GetAttr(resolved.var, tmpModule, oldName, self.codeBlock)
            elif(isinstance(resolved, ast.Attribute)):
                tmp = self.newTmpVariable()
                GetAttr(tmp, tmpModule, oldName, self.codeBlock)
                SetAttr(resolved.value.var, resolved.attr, tmp, self.codeBlock)

    def _handleFor(self, target, iter):
        # $iterMethod = iter.__iter__
        iterMethod = self.newTmpVariable()
        GetAttr(iterMethod, iter.var, "__iter__", self.codeBlock)

        # $iterator = Call iterMethod()
        iterator = self.newTmpVariable()
        Call(iterator, iterMethod, [], {}, self.codeBlock)

        # $nextMethod = $iterator.__next__
        nextMethod = self.newTmpVariable()
        GetAttr(nextMethod, iterator, "__next__", self.codeBlock)

        # value = Call $nextMethod()
        value = self.newTmpVariable()
        Call(value, nextMethod, [], {}, self.codeBlock)

        self._handleAssign(target, VariableNode(value))

    def visit_For(self, node: ast.For) -> Any:
        
        self.generic_visit(node)
        
        self._handleFor(node.target, node.iter)

    def visit_With(self, node: ast.With) -> Any:
        
        self.generic_visit(node)
        for item in node.items:
            if(item.optional_vars):
                self._handleAssign(item.optional_vars, item.context_expr)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
        # v = new_function(codeBlock)
        

        generator = FunctionCodeBlockGenerator(node.name, self.codeBlock, moduleManager=self.moduleManager)
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
            Assign(arg, defaults[i].var, func)
        # for kwargs
        for i in range(len(kw_defaults)):
            arg = func.localVariables[kwonlyargs[i]]
            if(kw_defaults[i]):
                Assign(arg, kw_defaults[i].var, func)

        resolved = resolveName(self.codeBlock, node.name)
        tmp = self.newTmpVariable()

        if(isinstance(resolved, VariableNode)):
            Assign(resolved.var, tmp, self.codeBlock)
        elif(isinstance(resolved, ast.Attribute)):
            SetAttr(resolved.value.var, resolved.attr, tmp, self.codeBlock)

        for decorator in node.decorator_list:
            
            nextTmp = self.newTmpVariable()
            if(isinstance(decorator, ast.Name) and decorator.id == "staticmethod"):
                NewStaticMethod(tmp, nextTmp, self.codeBlock)
            elif(isinstance(decorator, ast.Name) and decorator.id == "classmethod"):
                NewClassMethod(tmp, nextTmp, self.codeBlock)
            else:
                decorator = self.visit(decorator)
                Call(tmp, decorator.var, [nextTmp], {}, self.codeBlock)
            tmp = nextTmp
        NewFunction(tmp, func, self.codeBlock)
        
       

    def visit_Lambda(self, node: ast.Lambda) -> Any:
        

        generator = FunctionCodeBlockGenerator(f"$lambda{self.lambdaCount}", self.codeBlock, moduleManager=self.moduleManager)
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
            Assign(arg, defaults[i].var, func)
        # for kwargs
        for i in kw_defaults:
            arg = func.localVariables[kwonlyargs[i]]
            Assign(arg, kw_defaults[i].var, func)

        tmp = self.newTmpVariable()
        NewFunction(tmp, generator.codeBlock, self.codeBlock)
        return VariableNode(tmp)
    
    def visit_ClassDef(self, node: ast.ClassDef):
        

        generator = ClassCodeBlockGenerator(node.name, self.codeBlock, moduleManager=self.moduleManager)
        generator.parse(node)
        base = [self.visit(b).var for b in node.bases]
        resolved = resolveName(self.codeBlock, node.name)
        if(isinstance(resolved, VariableNode)):
            NewClass(resolved.var, base, generator.codeBlock, self.codeBlock)
        elif(isinstance(resolved, ast.Attribute)):
            tmp = self.newTmpVariable()
            NewClass(tmp, base, generator.codeBlock, self.codeBlock)
            SetAttr(resolved.value.var, resolved.attr, tmp, self.codeBlock)
            
    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> Any:
        return self.visit_FunctionDef(node)

    def visit_Await(self, node: ast.Await) -> Any:
        self.generic_visit(node)
        return node.value

    def visit_AsyncFor(self, node: ast.AsyncFor) -> Any:
        return self.visit_For(node)

    def visit_AsyncWith(self, node: ast.AsyncWith) -> Any:
        return self.visit_With(node)

    def _handleAssign(self, target, value):
        assert(isinstance(value, VariableNode))
        if(isinstance(target, VariableNode)):
            # left = right
            Assign(target.var, value.var, self.codeBlock)
        elif(isinstance(target, ast.Attribute)):
            # left.f = right.f
            assert(isinstance(target.value, VariableNode))
            SetAttr(target.value.var, target.attr, value.var, self.codeBlock)
        elif(isinstance(target, ast.Tuple) or isinstance(target, ast.List)):
            posIndex = 0
            negIndex = -len(target.elts)
            afterStarred = False
            for elt in target.elts:
                if(isinstance(elt, ast.Starred)):
                    afterStarred = True
                    tmp = self._makeList()
                    tmp2 = self.newTmpVariable()
                    # if value is a list
                    GetAttr(tmp2, value.var, "$values", self.codeBlock)
                    # if value is a tuple
                    GetAttr(tmp2, value.var, "$tupleElements", self.codeBlock)
                    SetAttr(tmp, "$values", tmp2, self.codeBlock)
                    Assign(elt.value.var, tmp, self.codeBlock)
                    # TODO
                else:
                    if(afterStarred):
                        i = negIndex
                    else:
                        i = posIndex
                    # value might be a tuple
                    tmp = self.newTmpVariable()
                    GetAttr(tmp, value.var, f"${i}", self.codeBlock)
                    self._handleAssign(elt, VariableNode(tmp))

                    # value might be a list
                    tmp = self.newTmpVariable()
                    GetAttr(tmp, value.var, "$values", self.codeBlock)
                    self._handleAssign(elt, VariableNode(tmp))

                posIndex += 1
                negIndex += 1
        else:
            # I make all subscribtable objects own a attribute $values
            # Subscript is replaced by ast.Attribute
            assert(False)

    # set up __iter__() for a variable 
    def _makeIterator(self, v:Variable, elts:Set[Union[Variable, ast.Attribute]]):
        iter = FunctionCodeBlock(f"{v.name}__iter__", self.codeBlock, fake=True)
        next = FunctionCodeBlock(f"{v.name}__next__", self.codeBlock, fake=True)
        

        # v.__iter__ = new function
        tmp = self.newTmpVariable()
        NewFunction(tmp, iter, self.codeBlock)
        SetAttr(v, "__iter__", tmp, self.codeBlock)
        
        # In __iter__()
        # $1 = new function(__next__)
        # ret = new iterator
        # ret.__next__ = $1
        tmp = Variable("$1", iter)
        NewBuiltin(iter.returnVariable, "iterator", iter)
        NewFunction(tmp, next, iter)
        SetAttr(iter.returnVariable, "__next__", tmp, iter)

        # In __next__(), ret = elts
        for elt in elts:
            if(isinstance(elt, Variable)):
                Assign(next.returnVariable, elt, next)
            elif(isinstance(elt, ast.Attribute)):
                GetAttr(next.returnVariable, elt.value.var, elt.attr, next)

    # TODO: add line and column number into IR
    # TODO: to deal with "from ... import *", a populate graph may be needed


class FunctionCodeBlockGenerator(CodeBlockGenerator):
    codeBlock: FunctionCodeBlock
    yielded: Set[Variable]
    sended: Variable
    def __init__(self, name:str, enclosing: CodeBlock, moduleManager: 'ModuleManager'):
        
        super().__init__(moduleManager)
        self.codeBlock = FunctionCodeBlock(name, enclosing)
        self.yielded = set()
        self.sended = Variable("$sended", self.codeBlock)

    def parse(self, node: ast.AST):
        assert(isinstance(node, ast.FunctionDef) or isinstance(node, ast.Lambda) or isinstance(node, ast.AsyncFunctionDef))
        return super().parse(node)

    def preprocess(self, node):
        # get all locals, including args, function defintion, class Definition
        # remember global and nonlocal
        
        codeBlock = self.codeBlock

        if(isinstance(node, ast.Lambda)):
            node.body = [node.body]
        
        ds = DeclarationScanner()
        
        for stmt in node.body:
            ds.visit(stmt)
        
        codeBlock.declaredGlobal = ds.declaredGlobal
        declaredNames = ds.declaredGlobal | ds.declaredNonlocal

        ls = BindingScanner(declaredNames)
        for stmt in node.body:
            ls.visit(stmt)
        for name in ls.boundNames:
            v = Variable(name, codeBlock)
            codeBlock.localVariables[name] = v

        # args are also local names, not affected by "global" and "nonlocal"
        # for assignment can't be earlier than declarations
        args = node.args

        # posonlyargs
        for arg in args.posonlyargs:
            v = Variable(arg.arg, codeBlock)
            codeBlock.posargs.append(v)
            codeBlock.localVariables[arg.arg] = v
        # args
        
        for arg in args.args:
            v = Variable(arg.arg, codeBlock)
            codeBlock.posargs.append(v)
            codeBlock.kwargs[arg.arg] = v
            codeBlock.localVariables[arg.arg] = v
        

        # kwonlyargs
        for arg in args.kwonlyargs:
            v = Variable(arg.arg, codeBlock)
            codeBlock.kwargs[arg.arg] = v
            codeBlock.localVariables[arg.arg] = v

        if(args.vararg):
            v = Variable(args.vararg.arg, codeBlock)
            # varargs are passed into this list (referenced by tmp)
            # then v points to this list, remember v can point other object
            # this approach can avoid varargs to spread to other object
            vararg = self._makeList()
            tmp = self.newTmpVariable()
            SetAttr(vararg, "$values", tmp, codeBlock)
            Assign(v, vararg, codeBlock)
            codeBlock.vararg = tmp
            codeBlock.localVariables[args.vararg.arg] = v
            

        if(args.kwarg):
            v = Variable(args.kwarg.arg, codeBlock)
            kwarg = self._makeDict()
            tmp = self.newTmpVariable()
            codeBlock.kwarg = tmp
            SetAttr(kwarg, "$values", tmp, codeBlock)
            Assign(v, kwarg, codeBlock)
            codeBlock.localVariables[args.kwarg.arg] = v
        
        # return None
        # NewBuiltin(codeBlock.returnVariable, "NoneType", codeBlock, None)

    def postprocess(self, node: ast.AST):
        

        if(self.yielded):
            # if(None in self.yielded):
            #     tmp = self.newTmpVariable()
            #     NewBuiltin(tmp, "None", self.codeBlock, None)
            #     self.yielded.remove(None)
            #     # self.yielded.add(tmp)

            tmp = self._makeGenerator(self.yielded, self.sended)
            Assign(self.codeBlock.returnVariable, tmp, self.codeBlock)

        super().postprocess(node)

    def visit_Return(self, node: ast.Return) -> Any:
        
        self.generic_visit(node)
        if(node.value):
            Assign(self.codeBlock.returnVariable, node.value.var, self.codeBlock)

    def visit_Yield(self, node: ast.Yield) -> Any:
        
        self.generic_visit(node)
        if(node.value):
            self.yielded.add(node.value.var)
        # else:
        #     self.yielded.add(None)
        return VariableNode(self.sended)


    def visit_YieldFrom(self, node: ast.YieldFrom) -> Any:
        
        self.generic_visit(node)

        # $iterMethod = iter.__iter__
        iterMethod = self.newTmpVariable()
        GetAttr(iterMethod, node.value.var, "__iter__", self.codeBlock)

        # $iterator = Call iterMethod()
        iterator = self.newTmpVariable()
        Call(iterator, iterMethod, [], {}, self.codeBlock)

        # $nextMethod = $iterator.__next__
        nextMethod = self.newTmpVariable()
        GetAttr(nextMethod, iterator, "__next__", self.codeBlock)

        # value = Call $nextMethod()
        value = self.newTmpVariable()
        Call(value, nextMethod, [], {}, self.codeBlock)

        self.yielded.add(value)
        return VariableNode(self.sended)
    

class ClassCodeBlockGenerator(CodeBlockGenerator):
    codeBlock: ClassCodeBlock
    attributes: Set[str]

    def __init__(self, name: str, enclosing: CodeBlock, moduleManager: 'ModuleManager'):
        super().__init__(moduleManager)
        self.codeBlock = ClassCodeBlock(name, enclosing)

    def parse(self, node: ast.AST):
        assert(isinstance(node, ast.ClassDef))
        return super().parse(node)

    def preprocess(self, node: ast.ClassDef):
        ds = DeclarationScanner()
        for stmt in node.body:
            ds.visit(stmt)

        self.codeBlock.declaredGlobal = ds.declaredGlobal
        declaredNames = ds.declaredGlobal | ds.declaredNonlocal

        ls = BindingScanner(declaredNames)
        for stmt in node.body:
            ls.visit(stmt)
        self.codeBlock.attributes = ls.boundNames
        

    # for name loaded, because our analysis is flow-insensitive, we can't tell if this name is loaded before its first assignment.
    # we make conservative guesses, and suggest that this name may resolved to a variable/attribute outside, or an attribute of this class
    def visit_Name(self, node: ast.Name) -> Union[VariableNode, ast.Attribute]:
        

        id = node.id
        codeBlock = self.codeBlock
        if(isLoad(node)):
            # an varaible/attribute outside, or this class's attribute
            if(codeBlock.enclosing is None):
                outside = makeAttribute(codeBlock.globalVariable, id)
            else:
                outside = resolveName(codeBlock.enclosing, id)

            if(id in codeBlock.attributes):
                tmp = self.newTmpVariable()
                # $tmp = $thisClass.attr
                GetAttr(tmp, codeBlock.thisClassVariable, id, codeBlock)
                if(isinstance(outside, VariableNode)):
                    # $tmp = v
                    Assign(tmp, outside.var, codeBlock)
                elif(isinstance(outside, ast.Attribute)):
                    GetAttr(tmp, outside.value.var, outside.attr, codeBlock)
                return VariableNode(tmp)
            elif(isinstance(outside, ast.Attribute)):
                # this name is not one of this class's attributes, the name resolved to a global variable
                tmp = self.newTmpVariable()
                GetAttr(tmp, outside.value.var, outside.attr, codeBlock)
                return VariableNode(tmp)
            else:
                # this name is not one of this class's attributes, the name resolved to a local variable
                return outside

        elif(isStore(node)):
            # return this class's attribute if it is
            return resolveName(codeBlock, id)


class ModuleCodeBlockGenerator(CodeBlockGenerator):
    codeBlock: ModuleCodeBlock
    # module has no enclosing block
    def __init__(self, moduleName: str, moduleManager: 'ModuleManager'):
        super().__init__(moduleManager)
        self.codeBlock = ModuleCodeBlock(moduleName)

    def parse(self, node: ast.AST):
        assert(isinstance(node, ast.Module))
        return super().parse(node)

    def postprocess(self, node: ast.AST):
        super().postprocess(node)
        # self.codeBlock.done = True
    
