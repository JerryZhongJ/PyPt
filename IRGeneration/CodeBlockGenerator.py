import ast
from inspect import Attribute
from typing import Set, Union
from IRGeneration.CodeBlock import ClassCodeBlock, CodeBlock, FunctionCodeBlock, ModuleCodeBlock

from IRGeneration.IR import *
from IRGeneration.Scanner import BindingScanner, DeclarationScanner

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

# codeBlock can be any, but remember that its enclosing and enclosing's enclosing must be function
def resolveName(codeBlock: CodeBlock, name: str, globalVariable: Variable=None) -> Union[VariableNode, ast.Attribute]:
    
    currCodeBlock = codeBlock
    
    while(currCodeBlock is not None):
        # check if it is global
        if(isinstance(codeBlock, ModuleCodeBlock)):
            return makeAttribute(codeBlock.globalVariable, name)

        if(name in currCodeBlock.declaredGlobal):
            break

        if(isinstance(codeBlock, FunctionCodeBlock) and name in currCodeBlock.localVariables):
            return VariableNode(currCodeBlock.localVariables[name])

        if(isinstance(codeBlock, ClassCodeBlock) and name in codeBlock.attributes):
            return makeAttribute(codeBlock.thisClassVariable, name)

        currCodeBlock = currCodeBlock.enclosing

    # then it is global
    # TODO: distinguish global and builtin
    if(globalVariable is None):
        globalVariable = codeBlock.globalVariable
    return makeAttribute(globalVariable, name)


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

    def __init__(self):
        # self.root = node
        # print(f"Into {name} @ {moduleName}")
        
        self.tmpVarCount = 0
        

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
        # TODO: do some simplfying
        pass

    def newTmpVariable(self) -> Variable:
        name = f"$t{self.tmpVarCount}"
        self.tmpVarCount += 1
        return Variable(name, self.codeBlock, temp=True)
    
    # names are resolved and replaced by variables or attributes as soon as being visited.
    def visit_Name(self, node: ast.Name) -> Union[VariableNode, ast.Attribute]:
        res = resolveName(self.codeBlock, node.id)
        if(isinstance(node.ctx, ast.Load) and isinstance(res, ast.Attribute)):
            tmp = self.newTmpVariable()
            Load(tmp, res.value.var, res.attr, self.codeBlock)
            return VariableNode(tmp)
        else:
            return res

    def visit_Assign(self, node: ast.Assign) -> ast.Assign:
        # assign.targets can only be Attribute, Subscript, Starred, Name, List or Tuple
        # see https://docs.python.org/zh-cn/3.9/library/ast.html
        self.generic_visit(node)
        for target in node.targets:
            self._handleAssign(target, node.value)
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

    def visit_Tuple(self, node: ast.Tuple) -> Any:
        self.generic_visit(node)
        if(isinstance(node.ctx, ast.Load)):
            tmp = self.newTmpVariable()
            NewBuiltin(tmp, "tuple", self.codeBlock)
            i = 0
            for elt in node.elts:
                assert(isinstance(elt, VariableNode))
                Store(tmp, f"${i}", elt, self.codeBlock)
                i += 1
            return VariableNode(tmp)
        elif(isinstance(node.ctx, ast.Store)):
            return node
    
    def visit_List(self, node: ast.List) -> Any:
        self.generic_visit(node)
        if(isinstance(node.ctx, ast.Load)):
            tmp = self.newTmpVariable()
            NewBuiltin(tmp, "list", self.codeBlock)
            for elt in node.elts:
                assert(isinstance(elt, VariableNode))
                Store(tmp, "$elements", elt, self.codeBlock)
            return VariableNode(tmp)
        elif(isinstance(node.ctx, ast.Store)):
            return node

    def visit_Set(self, node: ast.Set) -> Any:
        self.generic_visit(node)
        tmp = self.newTmpVariable()
        NewBuiltin(tmp, "set", self.codeBlock)
        for elt in node.elts:
            assert(isinstance(elt, VariableNode))
            Store(tmp, "$elements", elt, self.codeBlock)
        return VariableNode(tmp)

    def visit_Dict(self, node: ast.Dict) -> Any:
        self.generic_visit(node)
        tmp = self.newTmpVariable()
        NewBuiltin(tmp, "dict", self.codeBlock)
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
        args = [v.var for v in node.args]
        keywords = {arg:v.var for arg, v in node.keywords}
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

        if(isinstance(node.ctx, ast.Load)):
            assert(isinstance(node.value, VariableNode))
            tmp = self.newTmpVariable()
            Load(tmp, node.value.var, node.attr, self.codeBlock)
            return VariableNode(tmp)
        elif(isinstance(node.ctx, ast.Store)):
            return node
        else:
            assert(False)
        
    def visit_NamedExpr(self, node: ast.NamedExpr) -> Any:
        self.generic_visit(node)
        self._handleAssign(node.target, node.value)
        return node.target

    def visit_AnnAssign(self, node: ast.AnnAssign) -> Any:
        self.generic_visit(node)
        if(hasattr(node, "value")):
            self._handleAssign(node.target, node.value)
        

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
        # v = new_function(codeBlock)
        generator = FunctionCodeBlockGenerator(node.name, self.codeBlock)
        generator.parse(node)
        resolved = resolveName(self.codeBlock, node.name)
        if(isinstance(resolved, VariableNode)):
            NewFunction(resolved.var, generator.codeBlock, self.codeBlock)
        elif(isinstance(resolved, ast.Attribute)):
            tmp = self.newTmpVariable()
            NewFunction(tmp, generator.codeBlock, self.codeBlock)
            Store(resolved.value.var, resolved.attr, tmp, self.codeBlock)
        return node
    
    def visit_ClassDef(self, node: ast.ClassDef):
        generator = ClassCodeBlockGenerator(node.name, self.codeBlock)
        generator.parse(node)
        base = [self.visit(b).var for b in self.bases]
        resolved = resolveName(self.codeBlock, node.name)
        if(isinstance(resolved, VariableNode)):
            NewClass(resolved.var, base, generator.codeBlock, self.codeBlock)
            Call(None, resolved.var, [], {}, self.codeBlock)
        elif(isinstance(resolved, ast.Attribute)):
            tmp = self.newTmpVariable()
            NewClass(tmp, base, generator.codeBlock, self.codeBlock)
            Store(resolved.value.var, resolved.attr, tmp, self.codeBlock)
            Call(None, tmp, [], {}, self.codeBlock)
        return node

    def _handleAssign(self, target, value):
        assert(isinstance(value, VariableNode))
        if(isinstance(target, VariableNode)):
            # left = right
            Assign(target.var, value.var, self.codeBlock)
        elif(isinstance(target, ast.Attribute)):
            # left.f = right.f
            assert(isinstance(target.value, VariableNode))
            Store(target.value.var, target.attr, value.var, self.codeBlock)
        elif(isinstance(target, ast.Tuple) or isinstance(target, ast.List)):
            i = 0
            for elt in target.elts:
                # value might be a tuple
                tmp = self.newTmpVariable()
                Load(tmp, value.var, f"${i}", self.codeBlock)
                i += 1
                self._handleAssign(elt, VariableNode(tmp))

                # value might be a list
                tmp = self.newTmpVariable()
                Load(tmp, value.var, "$elements", self.codeBlock)
                self._handleAssign(elt, VariableNode(tmp))
        else:
            # TODO: more conditions
            assert(False)
    # TODO: add line and column number into IR
    # TODO: to deal with "from ... import *", a populate graph may be needed


class FunctionCodeBlockGenerator(CodeBlockGenerator):
    codeBlock: FunctionCodeBlock
    def __init__(self, name:str, enclosing: CodeBlock):
        
        super().__init__()
        self.codeBlock = FunctionCodeBlock(name, enclosing)

    def parse(self, node: ast.AST):
        assert(isinstance(node, ast.FunctionDef))
        return super().parse(node)

    def preprocess(self, node:ast.FunctionDef):
        # get all locals, including args, function defintion, class Definition
        # remember global and nonlocal
        ds = DeclarationScanner()
        for stmt in node.body:
            ds.visit(stmt)
        
        self.codeBlock.declaredGlobal = ds.declaredGlobal
        declaredNames = ds.declaredGlobal | ds.declaredNonlocal

        ls = BindingScanner(declaredNames)
        for stmt in node.body:
            ls.visit(stmt)
        for name in ls.boundNames:
            v = Variable(name, self.codeBlock)
            self.codeBlock.localVariables[name] = v

        # args are also local names, not affected by "global" and "nonlocal"
        # for assignment can't be earlier than declarations
        args = node.args
        for arg in args.posonlyargs + args.args + args.kwonlyargs + [args.vararg, args.kwarg]:
            if(arg is not None):
                # add to locals
                v = Variable(arg.arg, self.codeBlock)
                self.codeBlock.localVariables[arg.arg] = v

                # add to args
                # TODO: default args
                # TODO: consider vararg and kwarg
                self.codeBlock.posargs.append(v)
                self.codeBlock.kwargs[arg.arg] = v

        # return None
        NewBuiltin(self.codeBlock.returnVariable, "None", self.codeBlock, None)
    

class ClassCodeBlockGenerator(CodeBlockGenerator):
    codeBlock: ClassCodeBlock
    attributes: Set[str]

    def __init__(self, name: str, enclosing: CodeBlock):
        super().__init__()
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
        if(isinstance(node.ctx, ast.Load)):
            # an varaible/attribute outside, or this class's attribute
            outside = resolveName(self.codeBlock.enclosing, id, self.codeBlock.globalVariable)

            if(id in self.codeBlock.attributes):
                tmp = self.newTmpVariable()
                # $tmp = $thisClass.attr
                Load(tmp, self.codeBlock.thisClassVariable, id, self.codeBlock)
                if(isinstance(outside, VariableNode)):
                    # $tmp = v
                    Assign(tmp, outside.var, self.codeBlock)
                elif(isinstance(outside, ast.Attribute)):
                    Load(tmp, outside.value.var, outside.attr, self.codeBlock)
                return VariableNode(tmp)
            elif(isinstance(outside, ast.Attribute)):
                # this name is not one of this class's attributes, the name resolved to a global variable
                tmp = self.newTmpVariable()
                Load(tmp, outside.value.var, outside.attr, self.codeBlock)
                return VariableNode(tmp)
            else:
                # this name is not one of this class's attributes, the name resolved to a local variable
                return outside

        elif(isinstance(node.ctx, ast.Store)):
            # return this class's attribute if it is
            return resolveName(self.codeBlock, id)


class ModuleCodeBlockGenerator(CodeBlockGenerator):
    codeBlock: ModuleCodeBlock
    # module has no enclosing block
    def __init__(self, moduleName: str):
        super().__init__()
        self.codeBlock = ModuleCodeBlock(moduleName)

    def parse(self, node: ast.AST):
        assert(isinstance(node, ast.Module))
        return super().parse(node)

    def postprocess(self, node: ast.AST):
        super().postprocess(node)
        # TODO: scan all the code in this block and subblock(function, class)
        # determine all the store of global names
        pass
    

