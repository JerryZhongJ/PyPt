import ast
from typing import Any, Set
import typing

from ..IR.ClassCodeBlock import ClassCodeBlock

from .DeclarationScanner import DeclarationScanner
from .BindingScanner import BindingScanner
from ..IR.CodeBlock import CodeBlock

from ..IR.IRStmts import Assign, Call, GetAttr, SetAttr, Variable
from ..IR.FunctionCodeBlock import FunctionCodeBlock
from .CodeBlockGenerator import Attribute, CodeBlockGenerator

if typing.TYPE_CHECKING:
    from ..ModuleManager import ModuleManager


class FunctionGenerator(CodeBlockGenerator):
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
        super().preprocess(node)
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
            vararg = self.newTmpVariable()
            self.addNewBuiltin(vararg, "list")
            tmp = self.newTmpVariable()
            self.addSetAttr(Attribute(vararg, "$values"), tmp)
            self.addAssign(v, vararg)
            
            codeBlock.vararg = tmp
            codeBlock.localVariables[args.vararg.arg] = v
            

        if(args.kwarg):
            v = Variable(args.kwarg.arg, codeBlock)
            kwarg = self._makeDict()
            tmp = self.newTmpVariable()
            codeBlock.kwarg = tmp
            self.addSetAttr(Attribute(kwarg, "$values"), tmp)
            self.addAssign(v, kwarg)
            codeBlock.localVariables[args.kwarg.arg] = v

        if(isinstance(codeBlock.enclosing, ClassCodeBlock) 
            and isinstance(node, ast.FunctionDef) and len(codeBlock.posargs) > 0):
            for decorator in node.decorator_list:
                if(isinstance(decorator, ast.Name) and decorator.id == "staticmethod"):
                    break
            else:
                enclosingClass = codeBlock.enclosing
                self.addAssign(codeBlock.posargs[0], enclosingClass.thisClassVariable)
        

    def postprocess(self, node: ast.AST):
        

        if(self.yielded):

            # tmp = self._makeGenerator(self.yielded, self.sended)
            tmp = self.newTmpVariable()
            self.addNewBuiltin(tmp, "list")
            for yielded in self.yielded:
                self.addSetAttr(Attribute(tmp, "$values"), yielded)
            self.addAssign(self.codeBlock.returnVariable, tmp)

        super().postprocess(node)

    def visit_Return(self, node: ast.Return) -> Any:
        
        self.generic_visit(node)
        if(node.value):
            self.addAssign(self.codeBlock.returnVariable, node.value.result)

    def visit_Yield(self, node: ast.Yield) -> Any:
        
        self.generic_visit(node)
        if(node.value):
            self.yielded.add(node.value.result)
        # else:
        #     self.yielded.add(None)
        # node.result = self.sended
        


    def visit_YieldFrom(self, node: ast.YieldFrom) -> Any:
        
        self.generic_visit(node)
        tmp = self.newTmpVariable()
        self.addGetAttr(tmp, Attribute(node.value.result, "$values"))
        
        self.yielded.add(tmp)
        # node.result = self.sended
