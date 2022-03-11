
import ast
from typing import Union
from IR.ClassCodeBlockGenerator import *
from IR.CodeBlockGenerator import *
from IR.DeclarationScanner import *
from IR.IR import *
from IR.LocalScanner import *

class FunctionCodeBlockGenerator(CodeBlockGenerator):
    def __init__(self, moduleName: str, name:str, enclosing: CodeBlock):
        
        super().__init__(moduleName, "function", name, enclosing)

    def parse(self, node: ast.AST):
        assert(isinstance(node, ast.FunctionDef))
        return super().parse(node)

    def preprocess(self, node:ast.FunctionDef):
        # get all locals, including args, function defintion, class Definition
        # remember global and nonlocal
        ds = DeclarationScanner()
        for stmt in node.body:
            ds.visit(stmt)
        globalNames = ds.globalNames
        self.codeBlock.globalNames = globalNames
        nonlocalNames = ds.nonlocalNames
        declaredNames = globalNames | nonlocalNames

        ls = LocalScanner(declaredNames)
        for stmt in node.body:
            ls.visit(stmt)
        localNames = ls.localNames
        for name in localNames:
            v = Variable(name, self.codeBlock)
            self.codeBlock.localVariables[name] = v

        # args are also local names, not affected by "global" and "nonlocal"
        # for assignment can't be earlier than declarations
        args = node.args
        for arg in args.posonlyargs + args.args + args.kwonlyargs + [args.vararg, args.kwarg]:
            if(arg != None):
                # add to locals
                v = Variable(arg.arg, self.codeBlock)
                self.codeBlock.localVariables[arg.arg] = v

                # add to args
                # TODO: consider vararg and kwarg
                self.codeBlock.posargs.append(v)
                self.codeBlock.kwargs[arg.arg] = v

    # names are resolved and replaced by variables or attributes as soon as being visited.
    def visit_Name(self, node: ast.Name) -> Union[VariableNode, ast.Attribute]:
        return self.resolveName(node.id)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
        # v = new_function(codeBlock)
        generator = FunctionCodeBlockGenerator(self.moduleName, node.name, self.codeBlock)
        generator.parse(node)
        v = self.codeBlock.localVariables[node.name]
        NewFunction(v, generator.codeBlock, self.codeBlock)
        return node
    
    def visit_ClassDef(self, node: ast.ClassDef):
        generator = ClassCodeBlockGenerator(self.moduleName, node.name, self.codeBlock)
        generator.parse(node)
        v = self.codeBlock.localVariables[node.name]
        NewClass(v, generator.codeBlock, self.codeBlock)
        return node