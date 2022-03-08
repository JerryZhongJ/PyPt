import ast
from inspect import Attribute
from typing import Union
from .IR import *

# Wrapper for variable
class VariableNode(ast.Node):
    var: Variable
    def __init__(self, v:Variable):
        self.var = v

    
class CodeBlockGenerator(ast.NodeTransformer):
    codeBlock: CodeBlock
    moduleName: str
    tmpVarCount = 0
    def __init__(self, moduleName:str, node: ast.Node, enclosing: CodeBlock=None):
        self.root = node
        if(isinstance(node, ast.Module)):
            type = "module"
            name = ""
        elif(isinstance(node, ast.FunctionDef)):
            type = "function"
            name = node.name
        elif(isinstance(node, ast.ClassDef)):
            type = "class"
            name = node.name
        else:
            raise Exception("Initialize Code Block Generator with module node, funtion node or a class node!")
            
        
        self.codeBlock = CodeBlock(moduleName, type, name, enclosing)

    def run(self):
        self.preprocess()
        # all of the class, function, module have a body
        # nodes outside the body should be specially treated
        self.visit(self.root.body)
        self.postprocess()

    def preprocess(self):
        pass

    def postprocess(self):
        # TODO: do some simplfying
        pass

    # names are resolved and replaced by variables or attributes as soon as being visited.
    def visit_Name(self, node: ast.Name) -> Union[VariableNode, Attribute]:

        # for every function from intermost to outermost
        currCodeBlock = self.codeBlock
        while(currCodeBlock != None):
            # check if it is global
            if(node.id in currCodeBlock.globalNames):
                break
            if(node.id in currCodeBlock.localVariables):
                return VariableNode(currCodeBlock.localVariables[node.id])

        # then it is global
        # TODO: distinguish global and builtin
        if(isinstance(node.ctx, ast.Load)):
            # add '$tmp = $global.name'
            # return '$tmp'
            v = self.newTmpVariable()
            ir = Load(v, self.codeBlock.globalVariable, node.id)
            self.codeBlock.addIR(ir)
            return VariableNode(v)
        elif(isinstance(node.ctx, ast.Store)):
            v = VariableNode(self.codeBlock.globalVariable)
            attr =  ast.Attribute()
            attr.value = v
            attr.attr = node.id
            attr.ctx = ast.Store()
            return attr

    def newTmpVariable(self) -> Variable:
        name = f"$t{len(self.tmpVarCount)}"
        self.tmpVarCount += 1
        return Variable(name, self)
    
    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
        if(node == self.root):
            generator = FunctionCodeBlockGenerator(self.moduleName, node, self.codeBlock)
            generator.run()
            
        return node
    
    
    def visit_Assign(self, node: ast.Assign) -> ast.Assign:
        # assign.targets can only be Attribute, Subscript, Starred, Name, List or Tuple
        # see https://docs.python.org/zh-cn/3.9/library/ast.html
        super().generic_visit(node)
        right = node.value
        tmp: Variable = None           # used when left and right are both attributes
        for left in node.targets:
            if(isinstance(left, VariableNode)):
                if(isinstance(right, VariableNode)):
                    # left = right
                    ir = Assign(left.var, right.var)
                    self.codeBlock.addIR(ir)
                elif(isinstance(right, Attribute)):
                    # left = right.f
                    assert(isinstance(right.value, VariableNode))
                    ir = Load(left.var, right.value.var, right.attr)
                    self.codeBlock.addIR(ir)
            elif(isinstance(left, Attribute)):
                if(isinstance(right, VariableNode)):
                    # left.f = right.f
                    assert(isinstance(left.value, VariableNode))
                    ir = Store(left.value.var, left.attr, right.var)
                    self.codeBlock.addIR(ir)
                elif(isinstance(right, Attribute)):
                    # left.f = right.f
                    assert(isinstance(left.value, VariableNode))
                    assert(isinstance(right.value, VariableNode))
                    if(tmp == None):
                        # tmp = right.f
                        tmp = self.newTmpVariable()
                        ir = Load(tmp, right.value.var, right.attr)
                        self.codeBlock.addIR(ir)
                    # left.f = tmp
                    ir = Store(left.value.var, left.attr, tmp)
                    self.codeBlock.addIR(ir)
            else:
                # TODO
                assert(False)
            
            return node

    def visit_Attribute(self, node: ast.Attribute) -> Union[VariableNode, Attribute]:
        super().generic_visit(node)
        
        if(isinstance(node.value, VariableNode)):
            # v.f -> v.f
            return node
        elif(isinstance(node.value, Attribute)):
            # v.f0.f1 -> tmp = v.f0 + tmp.f
            v: VariableNode = node.value.value
            assert(isinstance(v, VariableNode))
            tmp = self.newTmpVariable()
            ir = Load(tmp, v.var, node.value.attr)
            node.value = VariableNode(tmp)
            return node
        else:
            assert(False)

        

    # TODO: add line and column number into IR

    
class FunctionCodeBlockGenerator(CodeBlockGenerator):
    def preprocess(self):
        # get all locals, including args, function defintion
        # remember global and nonlocal
        pass

class ModuleCodeBlockGenerator(CodeBlockGenerator):
    pass

class ClassCodeBlockGenerator(CodeBlockGenerator):
    pass