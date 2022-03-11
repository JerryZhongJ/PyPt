import ast
from typing import Set

class DeclarationScanner(ast.NodeVisitor):
    globalNames: Set[str]
    nonlocalNames: Set[str]
    # nodes under module, function, class is not considered
    def __init__(self):
        self.globalNames = set()
        self.nonlocalNames = set()

    def visit_Module(self, node: ast.Module) -> None:
        pass
    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        pass
    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        pass

    def visit_Global(self, node: ast.Global) -> None:
        self.globalNames |= set(node.names)

    def visit_Nonlocal(self, node: ast.Nonlocal) -> None:
        self.nonlocalNames |= set(node.names)