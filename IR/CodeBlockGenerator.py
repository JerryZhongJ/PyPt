import ast
from typing import Set, Union

from numpy import isin
from .CodeBlock import ClassCodeBlock, CodeBlock, FunctionCodeBlock, ModuleCodeBlock

from .Stmts import *
from .Scanner import BindingScanner, DeclarationScanner



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

def getSrcPos(node: ast.AST) -> bool:
    return node.lineno, node.col_offset, node.end_lineno, node.end_col_offset

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
    def __init__(self, moduleManager: 'ModuleManager', simplify=True):
        # self.root = node
        # print(f"Into {name} @ {moduleName}")
        
        self.tmpVarCount = 0
        self.lambdaCount = 0
        self.tmpVariables = set()
        self.moduleManager = moduleManager
        self.simplify = simplify

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
        if(not self.simplify):
            return

        change = True
        while(change):
            change = False
            for tmp in self.tmpVariables:
                allUses = tmp.usingIRs[USED_BY_VAR] + tmp.usingIRs[USED_OTHERS]
                allDefines = tmp.usingIRs[DEFINED_WITH_VAR] + tmp.usingIRs[DEFINED_OTHERS]
                all = allUses + allDefines
                # not used tmp variables
                if(len(allUses) == 0):
                    for define in allDefines:
                        define: IRStmt
                        if(not isinstance(define, Call)):
                            define.destroy()
                            change = True

                def sameCodeBlock(IRs: set) -> bool:
                    for ir in IRs:
                        if(ir.belongsTo != self.codeBlock):
                            return False
                    return True
                
                # if $tmp is used only once, and it is v = $tmp, then all defined $tmp can be replaced by v

                if(len(tmp.usingIRs[USED_BY_VAR]) == 1 and len(tmp.usingIRs[USED_OTHERS]) == 0 
                    and sameCodeBlock(all)):

                    use = tmp.usingIRs[USED_BY_VAR][0]
                    v = use.target
                    for define in allDefines:
                        assert(define.target == tmp)
                        define.setTarget(v)
                    use.destroy()
                    change = True

                # if $tmp is defined only once, and it is $tmp = v, then all used $tmp can be replaced by v

                if(len(tmp.usingIRs[DEFINED_WITH_VAR]) == 1 and len(tmp.usingIRs[DEFINED_OTHERS]) == 0
                    and sameCodeBlock(all)):

                    define = tmp.usingIRs[DEFINED_WITH_VAR][0]
                    v = define.source
                    for use in allUses:
                        if(isinstance(use, Assign)):
                            use.setSource(v)
                        elif(isinstance(use, SetAttr)):
                            if(use.target == tmp):
                                use.setTarget(v)
                            if(use.source == tmp):
                                use.setSource(v)
                        elif(isinstance(use, GetAttr)):
                            use.setSource(v)
                        elif(isinstance(use, Call)):
                            if(use.callee == tmp):
                                use.setCallee(v)
                            for arg in use.args:
                                if(arg == tmp):
                                    use.setArg(use.args.index(arg), v)
                            for key, arg in use.keywords.items():
                                if(arg == tmp):
                                    use.setKeyword(key, v)
                        elif(isinstance(use, NewClass)):
                            for base in use.bases:
                                if(base == tmp):
                                    use.setBase(use.bases.index(base), v)
                        elif(isinstance(use, DelAttr)):
                            use.setVar(v)
                        else:
                            assert(False)
                    define.destroy()
                    change = True

    def newTmpVariable(self) -> Variable:
        name = f"$t{self.tmpVarCount}"
        self.tmpVarCount += 1
        tmp = Variable(name, self.codeBlock, temp=True)
        self.tmpVariables.add(tmp)
        return tmp
    
    # names are resolved and replaced by variables or attributes as soon as being visited.
    def visit_Name(self, node: ast.Name) -> Union[VariableNode, ast.Attribute]:
        srcPos = getSrcPos(node)

        res = resolveName(self.codeBlock, node.id)
        if(isLoad(node) and isinstance(res, ast.Attribute)):
            tmp = self.newTmpVariable()
            GetAttr(tmp, res.value.var, res.attr, self.codeBlock, srcPos)
            return VariableNode(tmp)
        else:
            return res

    def visit_Starred(self, node: ast.Starred) -> Any:
        srcPos = getSrcPos(node)
        self.generic_visit(node)
        if(isinstance(node.value, ast.Attribute)):
            tmp = self.newTmpVariable()
            GetAttr(tmp, node.value.value.var, node.value.attr, self.codeBlock, srcPos)   
            node.value = VariableNode(tmp)
        return node

    def visit_Constant(self, node: ast.Constant) -> Any:
        srcPos = getSrcPos(node)

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
        NewBuiltin(tmp, type, self.codeBlock, srcPos, node.value)
        return VariableNode(tmp)

    def visit_JoinedStr(self, node: ast.JoinedStr) -> Any:
        srcPos = getSrcPos(node)

        tmp = self.newTmpVariable()
        NewBuiltin(tmp, "str", self.codeBlock, srcPos)
        return VariableNode(tmp)

    # every tuple has attribtues $n, where n is a number, and $tupleElements
    # why is called $tupleElements not $values, 
    # because when i get some item from something, i simply refer to its $values
    # however, when it comes to tuple, i hope elements can be seperated possibly, by refer to its $n
    def visit_Tuple(self, node: ast.Tuple) -> Any:
        srcPos = getSrcPos(node)

        self.generic_visit(node)
        if(isLoad(node)):
            tmp = self.newTmpVariable()
            NewBuiltin(tmp, "tuple", self.codeBlock, srcPos)
            
            for elt in node.elts:
                if(isinstance(elt, ast.Starred)):
                    tmp2 = self.newTmpVariable()
                    GetAttr(tmp2, elt.value.var, "$tupleElements", self.codeBlock, srcPos)
                    GetAttr(tmp2, elt.value.var, "$values", self.codeBlock, srcPos)
                    SetAttr(tmp, "$tupleElements", tmp2, self.codeBlock, srcPos)
                else:
                    SetAttr(tmp, f"$tupleElements", elt.var, self.codeBlock, srcPos)
                
            l = len(node.elts)
            posIndex = 0
            while(posIndex < l and isinstance(node.elts[posIndex], VariableNode)):
                SetAttr(tmp, f"${posIndex}", node.elts[posIndex].var, self.codeBlock, srcPos)
                posIndex += 1

            negIndex = -1
            while(negIndex >= -l and isinstance(node.elts[negIndex], VariableNode)):
                SetAttr(tmp, f"${negIndex}", node.elts[negIndex].var, self.codeBlock, srcPos)
                negIndex -= 1
            
            
            self._makeIterator(tmp, {makeAttribute(tmp, "$tupleElements")}, srcPos)
            return VariableNode(tmp)
        elif(isStore(node)):
            return node
    
    def _makeList(self, srcPos) -> Variable:
        tmp = self.newTmpVariable()
        NewBuiltin(tmp, "list", self.codeBlock, srcPos)
        self._makeIterator(tmp, {makeAttribute(tmp, "$values")}, srcPos)
        return tmp

    # every list has $values
    def visit_List(self, node: ast.List) -> Any:
        srcPos = getSrcPos(node)
        self.generic_visit(node)

        if(isLoad(node)):
            tmp = self._makeList(srcPos)
            
            for elt in node.elts:
                if(isinstance(elt, ast.Starred)):
                    tmp2 = self.newTmpVariable()
                    GetAttr(tmp2, elt.value.var, "$tupleElements", self.codeBlock, srcPos)
                    GetAttr(tmp2, elt.value.var, "$values", self.codeBlock, srcPos)
                    SetAttr(tmp, "$values", tmp2, self.codeBlock, srcPos)
                else:
                    SetAttr(tmp, "$values", elt.var, self.codeBlock, srcPos)

            return VariableNode(tmp)
        elif(isStore(node)):
            return node
    
    def _makeSet(self, srcPos) -> Variable:
        tmp = self.newTmpVariable()
        NewBuiltin(tmp, "set", self.codeBlock, srcPos)
        self._makeIterator(tmp, {makeAttribute(tmp, "$values")}, srcPos)
        return tmp

    # every set has $values
    def visit_Set(self, node: ast.Set) -> Any:
        srcPos = getSrcPos(node)
        self.generic_visit(node)

        tmp = self._makeSet(srcPos)
        for elt in node.elts:
            if(isinstance(elt, ast.Starred)):
                tmp2 = self.newTmpVariable()
                GetAttr(tmp2, elt.value.var, "$tupleElements", self.codeBlock, srcPos)
                GetAttr(tmp2, elt.value.var, "$values", self.codeBlock, srcPos)
                SetAttr(tmp, "$values", tmp2, self.codeBlock, srcPos)
            else:
                SetAttr(tmp, "$values", elt.var, self.codeBlock, srcPos)

        return VariableNode(tmp)

    def _makeDict(self, srcPos) -> Variable:
        tmp = self.newTmpVariable()
        NewBuiltin(tmp, "dict", self.codeBlock, srcPos)
        self._makeIterator(tmp, {makeAttribute(tmp, "$keys")}, srcPos)
        return tmp
        
    # every dict has $values and $keys
    def visit_Dict(self, node: ast.Dict) -> Any:
        srcPos = getSrcPos(node)
        self.generic_visit(node)

        tmp = self._makeDict(srcPos)
        for key in node.keys:
            if(key):
                SetAttr(tmp, "$keys", key.var, self.codeBlock, srcPos)

        for value in node.values:
            SetAttr(tmp, "$values", value.var, self.codeBlock, srcPos)

        
        return VariableNode(tmp)
        
    def visit_BoolOp(self, node: ast.BoolOp) -> Any:
        srcPos = getSrcPos(node)
        self.generic_visit(node)

        tmp = self.newTmpVariable()
        for value in node.values:
            Assign(tmp, value.var, self.codeBlock, srcPos)
        return VariableNode(tmp)

    def visit_Compare(self, node: ast.Compare) -> Any:
        srcPos = getSrcPos(node)
        self.generic_visit(node)

        tmp = self.newTmpVariable()
        NewBuiltin(tmp, "bool", self.codeBlock, srcPos, value=True)
        NewBuiltin(tmp, "bool", self.codeBlock, srcPos, value=False)
        return VariableNode(tmp)

    def visit_UnaryOp(self, node: ast.UnaryOp) -> Any:
        srcPos = getSrcPos(node)
        self.generic_visit(node)

        tmp = self.newTmpVariable()
        NewBuiltin(tmp, "unknown", self.codeBlock, srcPos)
        return VariableNode(tmp)

    def visit_BinOp(self, node: ast.BinOp) -> Any:
        srcPos = getSrcPos(node)
        self.generic_visit(node)

        tmp = self.newTmpVariable()
        NewBuiltin(tmp, "unknown", self.codeBlock, srcPos)
        return VariableNode(tmp)

    def visit_Call(self, node: ast.Call) -> Any:
        srcPos = getSrcPos(node)
        self.generic_visit(node)

        assert(isinstance(node.func, VariableNode))
        # Starred is not supported so far
        args = [v.var for v in node.args if isinstance(v, VariableNode)]
        keywords = {kw.arg:kw.value.var for kw in node.keywords}
        tmp = self.newTmpVariable()
        Call(tmp, node.func.var, args, keywords, self.codeBlock, srcPos)
        return VariableNode(tmp)

    def visit_IfExp(self, node: ast.IfExp) -> Any:
        srcPos = getSrcPos(node)
        self.generic_visit(node)

        tmp = self.newTmpVariable()
        Assign(tmp, node.body.var, self.codeBlock, srcPos)
        Assign(tmp, node.orelse.var, self.codeBlock, srcPos)
        return VariableNode(tmp)

    def visit_Attribute(self, node: ast.Attribute) -> Union[VariableNode, ast.Attribute]:
        srcPos = getSrcPos(node)
        self.generic_visit(node)

        if(isLoad(node)):
            assert(isinstance(node.value, VariableNode))
            tmp = self.newTmpVariable()
            GetAttr(tmp, node.value.var, node.attr, self.codeBlock, srcPos)
            return VariableNode(tmp)
        elif(isStore(node) or isDel(node)):
            return node
           
    def visit_NamedExpr(self, node: ast.NamedExpr) -> Any:
        srcPos = getSrcPos(node)
        self.generic_visit(node)
        self._handleAssign(node.target, node.value, srcPos)
        return node.target

    def visit_Assign(self, node: ast.Assign) -> ast.Assign:
        # assign.targets can only be Attribute, Subscript, Starred, Name, List or Tuple
        # see https://docs.python.org/zh-cn/3.9/library/ast.html
        srcPos = getSrcPos(node)
        self.generic_visit(node)

        for target in node.targets:
            self._handleAssign(target, node.value, srcPos)
        
    def visit_AnnAssign(self, node: ast.AnnAssign) -> Any:
        srcPos = getSrcPos(node)
        self.generic_visit(node)

        if(hasattr(node, "value")):
            self._handleAssign(node.target, node.value, srcPos)

    # let all subscribable objects have a attribute $values, tuple is an exception  
    def visit_Subscript(self, node: ast.Subscript) -> Any:
        srcPos = getSrcPos(node)
        node.value = self.visit(node.value)

        if(isLoad(node)):
            tmp = self.newTmpVariable()
            # if it is tuple
            if(isinstance(node.slice, ast.Constant) and isinstance(node.slice.value, int)):
                i = node.slice.value
                # $tmp = v.$i
                GetAttr(tmp, node.value.var, f"${i}", self.codeBlock,srcPos)
            else:
                GetAttr(tmp, node.value.var, "$tupleElements", self.codeBlock, srcPos)
            
            # if it is list, set, dict
            GetAttr(tmp, node.value.var, "$values", self.codeBlock, srcPos)
            return VariableNode(tmp)
        elif(isStore(node)):
            # if it is list, set, dict
            return makeAttribute(node.value.var, "$values")

    # TODO
    def visit_ListComp(self, node: ast.ListComp) -> Any:
        srcPos = getSrcPos(node)
        self.generic_visit(node)
        tmp = self._makeList(srcPos)
        SetAttr(tmp, "$values", node.elt.var, self.codeBlock, srcPos)
        for comp in node.generators:
            self._handleFor(comp.target, comp.iter, srcPos)
        return VariableNode(tmp)


    def visit_SetComp(self, node: ast.SetComp) -> Any:
        srcPos = getSrcPos(node)
        self.generic_visit(node)
        tmp = self._makeSet(srcPos)
        SetAttr(tmp, "$values", node.elt.var, self.codeBlock, srcPos)
        for comp in node.generators:
            self._handleFor(comp.target, comp.iter, srcPos)
        return VariableNode(tmp)

    def visit_DictComp(self, node: ast.DictComp) -> Any:
        srcPos = getSrcPos(node)
        self.generic_visit(node)
        tmp = self._makeDict(srcPos)
        SetAttr(tmp, "$keys", node.key.var, self.codeBlock, srcPos)
        SetAttr(tmp, "$value", node.value.var, self.codeBlock, srcPos)
        for comp in node.generators:
            self._handleFor(comp.target, comp.iter, srcPos)
        return VariableNode(tmp)

    def _makeGenerator(self, elts: Set, sended: Variable, srcPos) -> Variable:
        tmp = self.newTmpVariable()
        NewBuiltin(tmp, "generator", self.codeBlock, srcPos)
        self._makeIterator(tmp, elts, srcPos)
        # TODO: This is too ugly!
        if(sended):
            # def send(value):
            #    sended = value
            send = FunctionCodeBlock(f"<{tmp.name}>send", self.codeBlock)
            value = Variable("value", send)
            send.args[0] = value
            send.args["value"] = value
            Assign(sended, value, send, srcPos)

            # tmp.send = new function
            tmp2 = self.newTmpVariable()
            NewFunction(tmp, send, self.codeBlock, srcPos)
            SetAttr(tmp2, "send", tmp, self.codeBlock, srcPos)
        return tmp

    def visit_GeneratorExp(self, node: ast.GeneratorExp) -> Any:
        srcPos = getSrcPos(node)
        self.generic_visit(node)
        tmp = self._makeGenerator({node.elt}, None, srcPos)
        for comp in node.generators:
            self._handleFor(comp.target, comp.iter, srcPos)
        return VariableNode(tmp)

    def visit_Delete(self, node: ast.Delete) -> Any:
        srcPos = getSrcPos(node)
        self.generic_visit(node)

        for target in node.targets:
            if(isinstance(target, ast.Attribute)):
                DelAttr(target.value.var, target.attr, self.codeBlock, srcPos)

    def visit_Import(self, node: ast.Import) -> Any:
        srcPos = getSrcPos(node)
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
                NewModule(resolved.var, cb, self.codeBlock, srcPos)
            elif(isinstance(resolved, ast.Attribute)):
                tmp = self.newTmpVariable()
                NewModule(tmp, cb, self.codeBlock, srcPos)
                SetAttr(resolved.value.var, resolved.attr, tmp, self.codeBlock, srcPos)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> Any:
        srcPos = getSrcPos(node)
        caller = self.codeBlock.moduleName
        fromlist = [alias.name for alias in node.names]
        self.moduleManager.import_hook(node.module or "", caller, fromlist, level=node.level)
        imported: ModuleCodeBlock = self.moduleManager.getCodeBlock(node.module, caller, level=node.level)
        tmpModule = self.newTmpVariable()
        NewModule(tmpModule, imported, self.codeBlock, srcPos)
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
                GetAttr(resolved.var, tmpModule, oldName, self.codeBlock, srcPos)
            elif(isinstance(resolved, ast.Attribute)):
                tmp = self.newTmpVariable()
                GetAttr(tmp, tmpModule, oldName, self.codeBlock, srcPos)
                SetAttr(resolved.value.var, resolved.attr, tmp, self.codeBlock, srcPos)

    def _handleFor(self, target, iter, srcPos):
        # $iterMethod = iter.__iter__
        iterMethod = self.newTmpVariable()
        GetAttr(iterMethod, iter.var, "__iter__", self.codeBlock, srcPos)

        # $iterator = Call iterMethod()
        iterator = self.newTmpVariable()
        Call(iterator, iterMethod, [], {}, self.codeBlock, srcPos)

        # $nextMethod = $iterator.__next__
        nextMethod = self.newTmpVariable()
        GetAttr(nextMethod, iterator, "__next__", self.codeBlock, srcPos)

        # value = Call $nextMethod()
        value = self.newTmpVariable()
        Call(value, nextMethod, [], {}, self.codeBlock, srcPos)

        self._handleAssign(target, VariableNode(value), srcPos)

    def visit_For(self, node: ast.For) -> Any:
        srcPos = getSrcPos(node)
        self.generic_visit(node)
        
        self._handleFor(node.target, node.iter, srcPos)

    def visit_With(self, node: ast.With) -> Any:
        srcPos = getSrcPos(node)
        self.generic_visit(node)
        for item in node.items:
            if(item.optional_vars):
                self._handleAssign(item.optional_vars, item.context_expr, srcPos)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
        # v = new_function(codeBlock)
        srcPos = getSrcPos(node)

        generator = FunctionCodeBlockGenerator(node.name, self.codeBlock, moduleManager=self.moduleManager, simplify=self.simplify)
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
            Assign(arg, defaults[i].var, func, srcPos)
        # for kwargs
        for i in range(len(kw_defaults)):
            arg = func.localVariables[kwonlyargs[i]]
            if(kw_defaults[i]):
                Assign(arg, kw_defaults[i].var, func, srcPos)

        resolved = resolveName(self.codeBlock, node.name)
        if(isinstance(resolved, VariableNode)):
            NewFunction(resolved.var, func, self.codeBlock, srcPos)
        elif(isinstance(resolved, ast.Attribute)):
            tmp = self.newTmpVariable()
            NewFunction(tmp, func, self.codeBlock, srcPos)
            SetAttr(resolved.value.var, resolved.attr, tmp, self.codeBlock, srcPos)
       

    def visit_Lambda(self, node: ast.Lambda) -> Any:
        srcPos = getSrcPos(node)

        generator = FunctionCodeBlockGenerator(f"$lambda{self.lambdaCount}", self.codeBlock, moduleManager=self.moduleManager, simplify=self.simplify)
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
            Assign(arg, defaults[i].var, func, srcPos)
        # for kwargs
        for i in kw_defaults:
            arg = func.localVariables[kwonlyargs[i]]
            Assign(arg, kw_defaults[i].var, func, srcPos)

        tmp = self.newTmpVariable()
        NewFunction(tmp, generator.codeBlock, self.codeBlock, srcPos)
        return VariableNode(tmp)
    
    def visit_ClassDef(self, node: ast.ClassDef):
        srcPos = getSrcPos(node)

        generator = ClassCodeBlockGenerator(node.name, self.codeBlock, moduleManager=self.moduleManager, simplify=self.simplify)
        generator.parse(node)
        base = [self.visit(b).var for b in node.bases]
        resolved = resolveName(self.codeBlock, node.name)
        if(isinstance(resolved, VariableNode)):
            NewClass(resolved.var, base, generator.codeBlock, self.codeBlock, srcPos)
        elif(isinstance(resolved, ast.Attribute)):
            tmp = self.newTmpVariable()
            NewClass(tmp, base, generator.codeBlock, self.codeBlock, srcPos)
            SetAttr(resolved.value.var, resolved.attr, tmp, self.codeBlock, srcPos)
    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> Any:
        return self.visit_FunctionDef(node)

    def visit_Await(self, node: ast.Await) -> Any:
        self.generic_visit(node)
        return node.value

    def visit_AsyncFor(self, node: ast.AsyncFor) -> Any:
        return self.visit_For(node)

    def visit_AsyncWith(self, node: ast.AsyncWith) -> Any:
        return self.visit_With(node)

    def _handleAssign(self, target, value, srcPos):
        assert(isinstance(value, VariableNode))
        if(isinstance(target, VariableNode)):
            # left = right
            Assign(target.var, value.var, self.codeBlock, srcPos)
        elif(isinstance(target, ast.Attribute)):
            # left.f = right.f
            assert(isinstance(target.value, VariableNode))
            SetAttr(target.value.var, target.attr, value.var, self.codeBlock, srcPos)
        elif(isinstance(target, ast.Tuple) or isinstance(target, ast.List)):
            posIndex = 0
            negIndex = -len(target.elts)
            afterStarred = False
            for elt in target.elts:
                if(isinstance(elt, ast.Starred)):
                    afterStarred = True
                    tmp = self._makeList(srcPos)
                    tmp2 = self.newTmpVariable()
                    # if value is a list
                    GetAttr(tmp2, value.var, "$values", self.codeBlock, srcPos)
                    # if value is a tuple
                    GetAttr(tmp2, value.var, "$tupleElements", self.codeBlock, srcPos)
                    SetAttr(tmp, "$values", tmp2, self.codeBlock, srcPos)
                    Assign(elt.value.var, tmp, self.codeBlock, srcPos)
                    # TODO
                else:
                    if(afterStarred):
                        i = negIndex
                    else:
                        i = posIndex
                    # value might be a tuple
                    tmp = self.newTmpVariable()
                    GetAttr(tmp, value.var, f"${i}", self.codeBlock, srcPos)
                    i += 1
                    self._handleAssign(elt, VariableNode(tmp), srcPos)

                    # value might be a list
                    tmp = self.newTmpVariable()
                    GetAttr(tmp, value.var, "$values", self.codeBlock, srcPos)
                    self._handleAssign(elt, VariableNode(tmp), srcPos)

                posIndex += 1
                negIndex += 1
        else:
            # I make all subscribtable objects own a attribute $values
            # Subscript is replaced by ast.Attribute
            assert(False)

    # set up __iter__() for a variable 
    def _makeIterator(self, v:Variable, elts:Set[Union[Variable, ast.Attribute]], srcPos):
        iter = FunctionCodeBlock(f"<{v.name}>__iter__", self.codeBlock)
        next = FunctionCodeBlock(f"<{v.name}>__next__", self.codeBlock)
        

        # v.__iter__ = new function
        tmp = self.newTmpVariable()
        NewFunction(tmp, iter, self.codeBlock, srcPos)
        SetAttr(v, "__iter__", tmp, self.codeBlock, srcPos)
        
        # In __iter__()
        # $1 = new function(__next__)
        # ret = new iterator
        # ret.__next__ = $1
        tmp = Variable("$1", iter)
        NewBuiltin(iter.returnVariable, "iterator", iter, srcPos)
        NewFunction(tmp, next, iter, srcPos)
        SetAttr(iter.returnVariable, "__next__", tmp, iter, srcPos)

        # In __next__(), ret = elts
        for elt in elts:
            if(isinstance(elt, Variable)):
                Assign(next.returnVariable, elt, next, srcPos)
            elif(isinstance(elt, ast.Attribute)):
                GetAttr(next.returnVariable, elt.value.var, elt.attr, next, srcPos)

    # TODO: add line and column number into IR
    # TODO: to deal with "from ... import *", a populate graph may be needed


class FunctionCodeBlockGenerator(CodeBlockGenerator):
    codeBlock: FunctionCodeBlock
    yielded: Set[Variable]
    sended: Variable
    def __init__(self, name:str, enclosing: CodeBlock, moduleManager: 'ModuleManager', simplify=True):
        
        super().__init__(moduleManager, simplify)
        self.codeBlock = FunctionCodeBlock(name, enclosing)
        self.yielded = set()
        self.sended = Variable("$sended", self.codeBlock)

    def parse(self, node: ast.AST):
        assert(isinstance(node, ast.FunctionDef) or isinstance(node, ast.Lambda) or isinstance(node, ast.AsyncFunctionDef))
        return super().parse(node)

    def preprocess(self, node):
        # get all locals, including args, function defintion, class Definition
        # remember global and nonlocal
        srcPos = getSrcPos(node)
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
            codeBlock.posonlyargs.append(v)
            codeBlock.localVariables[arg.arg] = v
        # args
        i = len(args.posonlyargs)
        for arg in args.args:
            v = Variable(arg.arg, codeBlock)
            codeBlock.args[i] = v
            codeBlock.args[arg.arg] = v
            codeBlock.localVariables[arg.arg] = v
            i += 1

        # kwonlyargs
        for arg in args.kwonlyargs:
            v = Variable(arg.arg, codeBlock)
            codeBlock.kwonlyargs[arg.arg] = v
            codeBlock.localVariables[arg.arg] = v

        if(args.vararg):
            v = Variable(args.vararg.arg, codeBlock)
            # varargs are passed into this list (referenced by tmp)
            # then v points to this list, remember v can point other object
            # this approach can avoid varargs to spread to other object
            tmp = self._makeList(srcPos)
            Assign(v, tmp, codeBlock, srcPos)
            codeBlock.vararg = tmp
            codeBlock.localVariables[args.vararg.arg] = v
            

        if(args.kwarg):
            v = Variable(args.kwarg.arg, codeBlock)
            tmp = self._makeDict(srcPos)
            codeBlock.kwarg = tmp
            Assign(v, tmp, codeBlock, srcPos)
            codeBlock.localVariables[args.kwarg.arg] = v
        
        # return None
        NewBuiltin(codeBlock.returnVariable, "NoneType", codeBlock, srcPos, None)

    def postprocess(self, node: ast.AST):
        srcPos = getSrcPos(node)

        if(self.yielded):
            if(None in self.yielded):
                tmp = self.newTmpVariable()
                NewBuiltin(tmp, "None", self.codeBlock, srcPos, None)
                self.yielded.remove(None)
                self.yielded.add(tmp)

            tmp = self._makeGenerator(self.yielded, self.sended, srcPos)
            Assign(self.codeBlock.returnVariable, tmp, self.codeBlock, srcPos)

        super().postprocess(node)

    def visit_Return(self, node: ast.Return) -> Any:
        srcPos = getSrcPos(node)
        self.generic_visit(node)
        if(node.value):
            Assign(self.codeBlock.returnVariable, node.value.var, self.codeBlock, srcPos)

    def visit_Yield(self, node: ast.Yield) -> Any:
        srcPos = getSrcPos(node)
        self.generic_visit(node)
        if(node.value):
            self.yielded.add(node.value.var)
        else:
            self.yielded.add(None)
        return VariableNode(self.sended)


    def visit_YieldFrom(self, node: ast.YieldFrom) -> Any:
        srcPos = getSrcPos(node)
        self.generic_visit(node)

        # $iterMethod = iter.__iter__
        iterMethod = self.newTmpVariable()
        GetAttr(iterMethod, node.value.var, "__iter__", self.codeBlock, srcPos)

        # $iterator = Call iterMethod()
        iterator = self.newTmpVariable()
        Call(iterator, iterMethod, [], {}, self.codeBlock, srcPos)

        # $nextMethod = $iterator.__next__
        nextMethod = self.newTmpVariable()
        GetAttr(nextMethod, iterator, "__next__", self.codeBlock, srcPos)

        # value = Call $nextMethod()
        value = self.newTmpVariable()
        Call(value, nextMethod, [], {}, self.codeBlock, srcPos)

        self.yielded.add(value)
        return VariableNode(self.sended)
    

class ClassCodeBlockGenerator(CodeBlockGenerator):
    codeBlock: ClassCodeBlock
    attributes: Set[str]

    def __init__(self, name: str, enclosing: CodeBlock, moduleManager: 'ModuleManager', simplify=True):
        super().__init__(moduleManager, simplify)
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
        srcPos = getSrcPos(node)

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
                GetAttr(tmp, codeBlock.thisClassVariable, id, codeBlock, srcPos)
                if(isinstance(outside, VariableNode)):
                    # $tmp = v
                    Assign(tmp, outside.var, codeBlock, srcPos)
                elif(isinstance(outside, ast.Attribute)):
                    GetAttr(tmp, outside.value.var, outside.attr, codeBlock, srcPos)
                return VariableNode(tmp)
            elif(isinstance(outside, ast.Attribute)):
                # this name is not one of this class's attributes, the name resolved to a global variable
                tmp = self.newTmpVariable()
                GetAttr(tmp, outside.value.var, outside.attr, codeBlock, srcPos)
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
    def __init__(self, moduleName: str, moduleManager: 'ModuleManager',simplify=True):
        super().__init__(moduleManager, simplify)
        self.codeBlock = ModuleCodeBlock(moduleName)

    def parse(self, node: ast.AST):
        assert(isinstance(node, ast.Module))
        return super().parse(node)

    def postprocess(self, node: ast.AST):
        super().postprocess(node)
        # self.codeBlock.done = True
    
