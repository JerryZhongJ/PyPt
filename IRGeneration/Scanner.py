import ast
from typing import Set

class DeclarationScanner(ast.NodeVisitor):
    declaredGlobal: Set[str]
    declaredNonlocal: Set[str]
    # nodes under module, function, class is not considered
    def __init__(self):
        self.declaredGlobal = set()
        self.declaredNonlocal = set()

    def visit_Module(self, node: ast.Module) -> None:
        pass
    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        pass
    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        pass

    def visit_Global(self, node: ast.Global) -> None:
        self.declaredGlobal |= set(node.names)

    def visit_Nonlocal(self, node: ast.Nonlocal) -> None:
        self.declaredNonlocal |= set(node.names)


# If a name binding operation occurs Nonewhere within a code block, 
# all uses of the name within the block are treated as references to the current block.
# See https://docs.python.org/3.9/reference/executionmodel.html
class BindingScanner(ast.NodeVisitor):
    
    declaredNames: Set[str]
    boundNames: Set[str]

    def __init__(self, declaredNames):
        self.declaredNames = declaredNames
        self.boundNames = set()

    def visit_Module(self, node: ast.Module) -> None:
        pass
    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        if(node.name not in self.declaredNames):
            self.boundNames.add(node.name)
        # no generic visit

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        if(node.name not in self.declaredNames):
            self.boundNames.add(node.name)
        # no generic visit

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            if(alias.asname is None and alias.name not in self.declaredNames):
                self.boundNames.add(alias.name)
            elif(alias.asname is not None and alias.asname not in self.declaredNames):
                self.boundNames.add(alias.asname)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        for alias in node.names:
            if(alias.asname is None and alias.name not in self.declaredNames):
                self.boundNames.add(alias.name)
            elif(alias.asname is not None and alias.asname not in self.declaredNames):
                self.boundNames.add(alias.asname)

    def visit_Name(self, node: ast.Name) -> None:
        if(isinstance(node.ctx, ast.Store) and node.id not in self.declaredNames):
            self.boundNames.add(node.id)