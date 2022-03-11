import ast
from typing import Set, Union

from IR.IR import *



# Wrapper for variable
class VariableNode(ast.AST):
    var: Variable
    def __init__(self, v:Variable):
        self.var = v

# Name bindings include: 
# formal parameters to functions (not implented here, because LocalScanner only deals with body statements)
# import statements
# class and function definitions (these bind the class or function name in the defining block)
# targets that are identifiers if occurring in an assignment, for loop header, or after as in a with statement or except clause. 
class CodeBlockGenerator(ast.NodeTransformer):
    codeBlock: CodeBlock
    moduleName: str
    tmpVarCount: int

    def __init__(self, moduleName:str, type: str, name: str, enclosing: CodeBlock=None):
        # self.root = node
        # print(f"Into {name} @ {moduleName}")
        self.moduleName = moduleName
        self.tmpVarCount = 0
        self.codeBlock = CodeBlock(moduleName, type, name, enclosing)

    def parse(self, node: ast.AST):
        # print(f"preprocess {self.codeBlock.name} @ {self.codeBlock.moduleName}")
        self.preprocess(node)
        # all of the class, function, module have a body
        # nodes outside the body should be specially treated
        # print(f"process {self.codeBlock.name} @ {self.codeBlock.moduleName}")
        for stmt in node.body:
            self.visit(stmt)
        # print(f"postprocess {self.codeBlock.name} @ {self.codeBlock.moduleName}")
        self.postprocess(node)
        # print(f"exit {self.codeBlock.name} @ {self.codeBlock.moduleName}")

    def preprocess(self, node:ast.AST):
        pass

    def postprocess(self, node:ast.AST):
        # TODO: do some simplfying
        pass

    def newTmpVariable(self) -> Variable:
        name = f"$t{self.tmpVarCount}"
        self.tmpVarCount += 1
        return Variable(name, self.codeBlock)

    def resolveName(self, name: str) -> Union[VariableNode, ast.Attribute]:
        # for every function from intermost to outermost
        currCodeBlock = self.codeBlock
        while(currCodeBlock != None):
            # check if it is global
            if(name in currCodeBlock.globalNames):
                break
            if(name in currCodeBlock.localVariables):
                return VariableNode(currCodeBlock.localVariables[name])
            currCodeBlock = currCodeBlock.enclosing

        # then it is global
        # TODO: distinguish global and builtin
        v = VariableNode(self.codeBlock.globalVariable)
        attr =  ast.Attribute()
        attr.value = v
        attr.attr = name
        attr.ctx = ast.Store()
        return attr
    
    def visit_Assign(self, node: ast.Assign) -> ast.Assign:
        # assign.targets can only be Attribute, Subscript, Starred, Name, List or Tuple
        # see https://docs.python.org/zh-cn/3.9/library/ast.html
        self.generic_visit(node)
        # print("Assign")
        right = node.value
        tmp: Variable = None           # used when left and right are both attributes
        for left in node.targets:
            if(isinstance(left, VariableNode)):
                if(isinstance(right, VariableNode)):
                    # left = right
                    Assign(left.var, right.var, self.codeBlock)
                elif(isinstance(right, ast.Attribute)):
                    # left = right.f
                    assert(isinstance(right.value, VariableNode))
                    Load(left.var, right.value.var, right.attr, self.codeBlock)
            elif(isinstance(left, ast.Attribute)):
                if(isinstance(right, VariableNode)):
                    # left.f = right.f
                    assert(isinstance(left.value, VariableNode))
                    Store(left.value.var, left.attr, right.var, self.codeBlock)
                elif(isinstance(right, ast.Attribute)):
                    # left.f = right.f
                    assert(isinstance(left.value, VariableNode))
                    assert(isinstance(right.value, VariableNode))
                    if(tmp == None):
                        # tmp = right.f
                        tmp = self.newTmpVariable()
                        Load(tmp, right.value.var, right.attr, self.codeBlock)
                    # left.f = tmp
                    Store(left.value.var, left.attr, tmp, self.codeBlock)
            else:
                # TODO: more conditions
                assert(False)
            
        return node

    def visit_Attribute(self, node: ast.Attribute) -> Union[VariableNode, ast.Attribute]:
        self.generic_visit(node)
        # print("Attribute")
        if(isinstance(node.value, VariableNode)):
            # v.f -> v.f
            return node
        elif(isinstance(node.value, ast.Attribute)):
            # v.f0.f1 -> tmp = v.f0 + tmp.f
            v: VariableNode = node.value.value
            assert(isinstance(v, VariableNode))
            tmp = self.newTmpVariable()
            Load(tmp, v.var, node.value.attr, self.codeBlock)
            node.value = VariableNode(tmp)
            return node
        else:
            assert(False)

        

    # TODO: add line and column number into IR
    # TODO: to deal with "from ... import *", a populate graph may be needed

    





