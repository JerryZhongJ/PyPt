import ast
from typing import Any, Set
import typing

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
            vararg = self._makeList()
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
        node.result = self.sended
        


    def visit_YieldFrom(self, node: ast.YieldFrom) -> Any:
        
        self.generic_visit(node)

        # $iterMethod = iter.__iter__
        iterMethod = self.newTmpVariable()
        self.addGetAttr(iterMethod, Attribute(node.value.result, "__iter__"))
        

        # $iterator = Call iterMethod()
        iterator = self.newTmpVariable()
        self.addCall(iterator, iterMethod, [], {})

        # $nextMethod = $iterator.__next__
        nextMethod = self.newTmpVariable()
        self.addGetAttr(nextMethod, Attribute(iterator, "__next__"))

        # value = Call $nextMethod()
        value = self.newTmpVariable()
        self.addCall(value, nextMethod, [], {})
        
        self.yielded.add(value)
        node.result = self.sended
