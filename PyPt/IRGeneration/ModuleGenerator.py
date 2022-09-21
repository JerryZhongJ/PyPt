import ast
import builtins
import typing
from ..IR.ModuleCodeBlock import ModuleCodeBlock
from .CodeGenerator import CodeBlockGenerator


if typing.TYPE_CHECKING:
    from ..ModuleManager import ModuleManager
    
builtin_names = list(builtins.__dict__.keys())

class ModuleGenerator(CodeBlockGenerator):
    codeBlock: ModuleCodeBlock
    # module has no enclosing block
    def __init__(self, codeBlock: ModuleCodeBlock, moduleManager: 'ModuleManager'):
        super().__init__(moduleManager)
        self.codeBlock = codeBlock

    def preprocess(self, node: ast.Module):
        node.body.append(ast.ImportFrom(module="builtins", names=[ast.alias(name=name) for name in builtin_names], level=0))
        
    def parse(self, node: ast.AST):
        assert(isinstance(node, ast.Module))
        return super().parse(node)
