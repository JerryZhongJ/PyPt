import ast
from typing import Union
from IR.ClassCodeBlockGenerator import *
from IR.FunctionCodeBlockGenerator import *
from IR.IR import *


class ModuleCodeBlockGenerator(CodeBlockGenerator):
    # module has no enclosing block
    def __init__(self, moduleName: str):
        super().__init__(moduleName, "module", "", None)

    def parse(self, node: ast.AST):
        assert(isinstance(node, ast.Module))
        return super().parse(node)

    # TODO: may also need to scan locals for dealing with "from ... import *"

     # TODO: any name bindings will be translated into this $global's attributes
    def visit_Import(self, node: ast.Import) -> ast.Import:
        # TODO
        pass

    def visit_ImportFrom(self, node: ast.Import) -> ast.ImportFrom:
        # TODO
        pass

    # for names, they should be translated to this class's attributes
    def visit_Name(self, node: ast.Name) -> Union[VariableNode, ast.Attribute]:
        attr = ast.Attribute()
        attr.value = VariableNode(self.codeBlock.globalVariable)
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
        # $global.funcname = tmp
        Store(self.codeBlock.globalVariable, node.name, tmp, self.codeBlock)
        return node
    
    def visit_ClassDef(self, node: ast.ClassDef):
        generator = ClassCodeBlockGenerator(self.moduleName, node.name, self.codeBlock)
        generator.parse(node)
        tmp = self.newTmpVariable()
        # tmp = new_class
        NewClass(tmp, generator.codeBlock, self.codeBlock)
        # $global.funcname = tmp
        Store(self.codeBlock.globalVariable, node.name, tmp, self.codeBlock)
        return node