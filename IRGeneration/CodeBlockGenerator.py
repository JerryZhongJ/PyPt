import ast
from typing import Set, Union
from IRGeneration.CodeBlock import ClassCodeBlock, CodeBlock, FunctionCodeBlock, ModuleCodeBlock

from IRGeneration.IR import *
from IRGeneration.Scanner import BindingScanner, DeclarationScanner

# Wrapper for variable
class VariableNode(ast.AST):
    var: Variable
    def __init__(self, v:Variable):
        self.var = v

# represent a builtin object, for example "a = 1 + b", the result of "1 + b" is an object
class BuiltinObjectNode(ast.AST):
    type: str
    def __init__(self, type:str):
        self.type = type

# Some utils        
def makeAttribute(v: Variable, attr: str) -> ast.Attribute:
    attribute =  ast.Attribute()
    attribute.value = VariableNode(v)
    attribute.attr = attr
    return attribute

# codeBlock can be any, but remember that its enclosing and enclosing's enclosing must be function
def resolveName(codeBlock: CodeBlock, name: str, globalVariable: Variable=None) -> Union[VariableNode, ast.Attribute]:
    
    currCodeBlock = codeBlock
    
    while(currCodeBlock != None):
        # check if it is global
        if(isinstance(codeBlock, ModuleCodeBlock)):
            return makeAttribute(codeBlock.globalVariable, name)

        if(name in currCodeBlock.declaredGlobal):
            break

        if(isinstance(codeBlock, FunctionCodeBlock) and name in currCodeBlock.localVariables):
            return VariableNode(currCodeBlock.localVariables[name])

        if(isinstance(codeBlock, ClassCodeBlock) and name in codeBlock.attributes):
            return makeAttribute(codeBlock.thisClassVariable, name)

        currCodeBlock = currCodeBlock.enclosing

    # then it is global
    # TODO: distinguish global and builtin
    if(globalVariable == None):
        globalVariable = codeBlock.globalVariable
    return makeAttribute(globalVariable, name)


# Name bindings include: 
# formal parameters to functions (not implented here, because LocalScanner only deals with body statements)
# import statements
# class and function definitions (these bind the class or function name in the defining block)
# targets that are identifiers if occurring in an assignment, for loop header, or after as in a with statement or except clause. 

# IR is generated from the bottom of the AST to the top.
# After a subtree is processed, the root will be replaced by the result. This result may be useful to its parent or ancient node.
# The result includes: VariableNode, Attribute, BuiltinObjectNode, List, Tuple.
class CodeBlockGenerator(ast.NodeTransformer):
    codeBlock: CodeBlock
    tmpVarCount: int

    def __init__(self):
        # self.root = node
        # print(f"Into {name} @ {moduleName}")
        
        self.tmpVarCount = 0
        

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

    
    
    # names are resolved and replaced by variables or attributes as soon as being visited.
    def visit_Name(self, node: ast.Name) -> Union[VariableNode, ast.Attribute]:
        return resolveName(self.codeBlock, node.id)

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

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
        # v = new_function(codeBlock)
        generator = FunctionCodeBlockGenerator(node.name, self.codeBlock)
        generator.parse(node)
        # it may be declared global or nonlocal
        resolved = resolveName(self.codeBlock, node.name)
        if(isinstance(resolved, VariableNode)):
            NewFunction(resolved.var, generator.codeBlock, self.codeBlock)
        elif(isinstance(resolved, ast.Attribute)):
            tmp = self.newTmpVariable()
            NewFunction(tmp, generator.codeBlock, self.codeBlock)
            Store(resolved.value.var, resolved.attr, tmp, self.codeBlock)
        return node
    
    def visit_ClassDef(self, node: ast.ClassDef):
        generator = ClassCodeBlockGenerator(node.name, self.codeBlock)
        generator.parse(node)
        resolved = resolveName(self.codeBlock, node.name)
        if(isinstance(resolved, VariableNode)):
            NewClass(resolved.var, generator.codeBlock, self.codeBlock)
        elif(isinstance(resolved, ast.Attribute)):
            tmp = self.newTmpVariable()
            NewClass(tmp, generator.codeBlock, self.codeBlock)
            Store(resolved.value.var, resolved.attr, tmp, self.codeBlock)
        return node

    # TODO: add line and column number into IR
    # TODO: to deal with "from ... import *", a populate graph may be needed



class FunctionCodeBlockGenerator(CodeBlockGenerator):
    codeBlock: FunctionCodeBlock
    def __init__(self, name:str, enclosing: CodeBlock):
        
        super().__init__()
        self.codeBlock = FunctionCodeBlock(name, enclosing)

    def parse(self, node: ast.AST):
        assert(isinstance(node, ast.FunctionDef))
        return super().parse(node)

    def preprocess(self, node:ast.FunctionDef):
        # get all locals, including args, function defintion, class Definition
        # remember global and nonlocal
        ds = DeclarationScanner()
        for stmt in node.body:
            ds.visit(stmt)
        
        self.codeBlock.declaredGlobal = ds.declaredGlobal
        declaredNames = ds.declaredGlobal | ds.declaredNonlocal

        ls = BindingScanner(declaredNames)
        for stmt in node.body:
            ls.visit(stmt)
        for name in ls.boundNames:
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
    





class ClassCodeBlockGenerator(CodeBlockGenerator):
    codeBlock: ClassCodeBlock
    attributes: Set[str]

    def __init__(self, name: str, enclosing: CodeBlock):
        super().__init__()
        self.codeBlock = ClassCodeBlock(name, enclosing)

    def parse(self, node: ast.AST):
        assert(isinstance(node, ast.ClassDef))
        return super().parse(node)

    def preprocess(self, node: ast.ClassDef):
        ds = DeclarationScanner()
        for stmt in node.body:
            ds.visit(stmt)

        self.codeBlock.declaredGlobal = ds.declaredGlobal
        declaredNames = ds.declaredGlobal | ds.declaredNonlocal

        ls = BindingScanner(declaredNames)
        for stmt in node.body:
            ls.visit(stmt)
        self.codeBlock.attributes = ls.boundNames
        

    # for name loaded, because our analysis is flow-insensitive, we can't tell if this name is loaded before first assignment.
    # we make conservative guess, and suggest that this name may resolved to a variable/attribute outside, or an attribute of this class
    def visit_Name(self, node: ast.Name) -> Union[VariableNode, ast.Attribute]:
        if(isinstance(node.ctx, ast.Load)):
            outside = resolveName(self.codeBlock.enclosing, node.id, self.codeBlock.globalVariable)

            if(node.id in self.codeBlock.attributes):
                tmp = self.newTmpVariable()
                # $tmp = $thisClass.attr
                Load(tmp, self.codeBlock.thisClassVariable, node.id, self.codeBlock)
                if(isinstance(outside, VariableNode)):
                    # $tmp = v
                    Assign(tmp, outside.var)
                elif(isinstance(outside, ast.Attribute)):
                    Load(tmp, outside.value.var, outside.attr, self.codeBlock)
                return VariableNode(tmp)
            else:
                # just return outside variable / attribute
                return outside

        elif(isinstance(node.ctx, ast.Store)):
            # Not every stored name is attributes, except those declared global or nonlocal
            return resolveName(self.codeBlock, node.id)



class ModuleCodeBlockGenerator(CodeBlockGenerator):
    codeBlock: ModuleCodeBlock
    # module has no enclosing block
    def __init__(self, moduleName: str):
        super().__init__()
        self.codeBlock = ModuleCodeBlock(moduleName)

    def parse(self, node: ast.AST):
        assert(isinstance(node, ast.Module))
        return super().parse(node)

    # TODO: may also need to scan locals for dealing with "from ... import *"

     # TODO: any name bindings will be translated into this $global's attributes

