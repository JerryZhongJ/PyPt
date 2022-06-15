import ast
from typing import Set, Union
import typing

from ..IR.IRStmts import Assign, GetAttr, Variable

from .DeclarationScanner import DeclarationScanner
from .BindingScanner import BindingScanner

from ..IR.CodeBlock import CodeBlock
from ..IR.ClassCodeBlock import ClassCodeBlock

from .CodeBlockGenerator import Attribute, CodeBlockGenerator, isLoad, isStore, resolveName

if typing.TYPE_CHECKING:
    from ..ModuleManager import ModuleManager

class ClassGenerator(CodeBlockGenerator):
    codeBlock: ClassCodeBlock
    attributes: Set[str]

    def __init__(self, name: str, enclosing: CodeBlock, moduleManager: 'ModuleManager'):
        super().__init__(moduleManager)
        self.codeBlock = ClassCodeBlock(name, enclosing)

    def parse(self, node: ast.AST):
        assert(isinstance(node, ast.ClassDef))
        return super().parse(node)

    def preprocess(self, node: ast.ClassDef):
        super().preprocess(node)
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
    def visit_Name(self, node: ast.Name):
        id = node.id
        codeBlock = self.codeBlock
        if(isLoad(node)):
            # an varaible/attribute outside, or this class's attribute
            
            if(id in codeBlock.attributes):
                outside = resolveName(codeBlock.enclosing, id)
                tmp = self.newTmpVariable()
                # $tmp = $thisClass.attr
                self.addGetAttr(tmp, Attribute(codeBlock.thisClassVariable, id))
                
                if(isinstance(outside, Variable)):
                    # $tmp = v
                    self.addAssign(tmp, outside)
                elif(isinstance(outside, Attribute)):
                    self.addGetAttr(tmp, outside)
                node.result = tmp
            else:
                outside = resolveName(codeBlock, id)
                if(isinstance(outside, Attribute)):
                # this name is not one of this class's attributes, the name resolved to a global variable
                    tmp = self.newTmpVariable()
                    self.addGetAttr(tmp, outside)
                    node.result = tmp
                else:
                    # this name is not one of this class's attributes, the name resolved to a local variable
                    node.result = outside
                    

        elif(isStore(node)):
            # return this class's attribute if it is
            node.result = resolveName(codeBlock, id)
            
