import ast
from typing import Union

from IR.CodeBlockGenerator import *
from IR.FunctionCodeBlockGenerator import *


class ClassCodeBlockGenerator(CodeBlockGenerator):
    def __init__(self, moduleName: str, name: str, enclosing: CodeBlock):
        super().__init__(moduleName, "class", name, enclosing)

    def parse(self, node: ast.AST):
        assert(isinstance(node, ast.ClassDef))
        return super().parse(node)


    # TODO: any name bindings will be translated into this class's attributes
    def visit_Import(self, node: ast.Import) -> ast.Import:
        # TODO
        pass

    def visit_ImportFrom(self, node: ast.Import) -> ast.ImportFrom:
        # TODO
        pass

    # for names stored, they should be translated to this class's attributes
    # for names loaded, they should be resolved into this class's attributes and outer scope's variable
    def visit_Name(self, node: ast.Name) -> Union[VariableNode, ast.Attribute]:
        if(isinstance(node.ctx, ast.Load)):
            tmp = self.newTmpVariable()
            outer = self.resolveName(node.id)
            if(isinstance(outer, VariableNode)):
                Assign(tmp, outer.var, self.codeBlock)
            elif(isinstance(outer, ast.Attribute)):
                Load(tmp, outer.value.var, outer.attr, self.codeBlock)
            return VariableNode(tmp)
        elif(isinstance(node.ctx, ast.Store)):
            attr = ast.Attribute()
            attr.value = VariableNode(self.codeBlock.thisClassVariable)
            attr.attr = node.id
            attr.ctx = ast.Store()
            return attr
            
    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
        # v = new_function(codeBlock)
        generator = FunctionCodeBlockGenerator(self.moduleName, node.name, self.codeBlock)
        generator.parse(node)
        tmp = self.newTmpVariable()
        # tmp = new_function
        NewFunction(tmp, generator.codeBlock, self.codeBlock)
        # $thisClass.funcname = tmp
        Store(self.codeBlock.thisClassVariable, node.name, tmp, self.codeBlock)
        return node
    
    def visit_ClassDef(self, node: ast.ClassDef):
        generator = ClassCodeBlockGenerator(self.moduleName, node.name, self.codeBlock)
        generator.parse(node)
        tmp = self.newTmpVariable()
        # tmp = new_class
        NewClass(tmp, generator.codeBlock, self.codeBlock)
        # $thisClass.funcname = tmp
        Store(self.codeBlock.thisClassVariable, node.name, tmp, self.codeBlock)
        return node