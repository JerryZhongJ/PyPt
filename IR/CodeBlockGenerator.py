import ast
from typing import Set, Union
from .IR import *


# Wrapper for variable
class VariableNode(ast.AST):
    var: Variable
    def __init__(self, v:Variable):
        self.var = v

def resolveName(name: str, start: CodeBlock) -> Union[VariableNode, ast.Attribute]:
     # for every function from intermost to outermost
    currCodeBlock = start
    while(currCodeBlock != None):
        # check if it is global
        if(name in currCodeBlock.globalNames):
            break
        if(name in currCodeBlock.localVariables):
            return VariableNode(currCodeBlock.localVariables[name])

    # then it is global
    # TODO: distinguish global and builtin
    v = VariableNode(start.globalVariable)
    attr =  ast.Attribute()
    attr.value = v
    attr.attr = name
    attr.ctx = ast.Store()
    return attr

# Name bindings include: 
# formal parameters to functions (not implented here, because LocalScanner only deals with body statements)
# import statements
# class and function definitions (these bind the class or function name in the defining block)
# targets that are identifiers if occurring in an assignment, for loop header, or after as in a with statement or except clause. 
class CodeBlockGenerator(ast.NodeTransformer):
    codeBlock: CodeBlock
    moduleName: str
    tmpVarCount = 0

    def __init__(self, moduleName:str, type: str, name: str, enclosing: CodeBlock=None):
        # self.root = node
        self.moduleName = moduleName
        self.codeBlock = CodeBlock(moduleName, type, name, enclosing)

    def parse(self, node: ast.AST):
        self.preprocess(node)
        # all of the class, function, module have a body
        # nodes outside the body should be specially treated
        self.visit(node.body)
        self.postprocess(node)

    def preprocess(self, node:ast.AST):
        pass

    def postprocess(self, node:ast.AST):
        # TODO: do some simplfying
        pass

    def newTmpVariable(self) -> Variable:
        name = f"$t{len(self.tmpVarCount)}"
        self.tmpVarCount += 1
        return Variable(name, self)
    
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
                elif(isinstance(right, ast.Attribute)):
                    # left = right.f
                    assert(isinstance(right.value, VariableNode))
                    ir = Load(left.var, right.value.var, right.attr)
                    self.codeBlock.addIR(ir)
            elif(isinstance(left, ast.Attribute)):
                if(isinstance(right, VariableNode)):
                    # left.f = right.f
                    assert(isinstance(left.value, VariableNode))
                    ir = Store(left.value.var, left.attr, right.var)
                    self.codeBlock.addIR(ir)
                elif(isinstance(right, ast.Attribute)):
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
                # TODO: more conditions
                assert(False)
            
            return node

    def visit_Attribute(self, node: ast.Attribute) -> Union[VariableNode, ast.Attribute]:
        super().generic_visit(node)
        
        if(isinstance(node.value, VariableNode)):
            # v.f -> v.f
            return node
        elif(isinstance(node.value, ast.Attribute)):
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
    def __init__(self, moduleName: str, name:str, enclosing: CodeBlock):
        
        super().__init__(moduleName, "function", name, enclosing)

    def parse(self, node: ast.AST):
        assert(isinstance(node, ast.FunctionDef))
        return super().parse(node)

    def preprocess(self, node:ast.FunctionDef):
        # get all locals, including args, function defintion, class Definition
        # remember global and nonlocal
        ds = DeclarationScanner()
        ds.visit(node.body)
        globalNames = ds.globalNames
        self.codeBlock.globalNames = globalNames
        nonlocalNames = ds.nonlocalNames
        declaredNames = globalNames | nonlocalNames

        ls = LocalScanner(declaredNames)
        ls.visit(node.body)
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
        return resolveName(node.id, self.codeBlock)
        
    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
        # v = new_function(codeBlock)
        generator = FunctionCodeBlockGenerator(self.moduleName, node.name, self.codeBlock)
        generator.parse(node)
        v = self.codeBlock.localVariables[node.name]
        ir = NewFunction(v, generator.codeBlock)
        self.codeBlock.addIR(ir)
        return node
    
    def visit_ClassDef(self, node: ast.ClassDef):
        generator = ClassCodeBlockGenerator(self.moduleName, node.name, self.codeBlock)
        generator.parse(node)
        v = self.codeBlock.localVariables[node.name]
        ir = NewClass(v, generator.codeBlock)
        self.codeBlock.addIR(ir)
        return node

class ModuleCodeBlockGenerator(CodeBlockGenerator):
    # module has no enclosing block
    def __init__(self, moduleName: str):
        super().__init__(moduleName, "module", "", None)

    def parse(self, node: ast.AST):
        assert(isinstance(node, ast.Module))
        return super().parse(node)

    # TODO: may also need to scan locals for dealing with "from ... import *"

class ClassCodeBlockGenerator(CodeBlockGenerator):
    def __init__(self, moduleName: str, name: str, enclosing: CodeBlock):
        super().__init__(moduleName, "class", name, enclosing)

    def parse(self, node: ast.AST):
        assert(isinstance(node, ast.ClassDef))
        return super().parse(node)
    # TODO: any name bindings will be translated into this class's attributes
     
    # for names stored, they should be translated to this class's attributes
    # for names loaded, they should be resolved into this class's attributes and outer scope's variable
    def visit_Name(self, node: ast.Name) -> Union[VariableNode, ast.Attribute]:
        if(isinstance(node.ctx, ast.Load)):
            tmp = self.newTmpVariable()
            outer = resolveName(node.id, self.codeBlock.enclosing)
            if(isinstance(outer, VariableNode)):
                ir = Assign(tmp, outer)
            elif(isinstance(outer, ast.Attribute)):
                ir = Load(tmp, outer.value, outer.attr)
            self.codeBlock.addIR(ir)
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
        ir = NewFunction(tmp, generator.codeBlock)
        # $thisClass.funcname = tmp
        ir2 = Store(self.codeBlock.thisClassVariable, node.name, tmp)
        self.codeBlock.addIR(ir)
        self.codeBlock.addIR(ir2)
        return node
    
    def visit_ClassDef(self, node: ast.ClassDef):
        generator = ClassCodeBlockGenerator(self.moduleName, node.name, self.codeBlock)
        generator.parse(node)
        tmp = self.newTmpVariable()
        # tmp = new_class
        ir = NewClass(tmp, generator.codeBlock)
        # $thisClass.funcname = tmp
        ir2 = Store(self.codeBlock.thisClassVariable, node.name, tmp)
        self.codeBlock.addIR(ir)
        self.codeBlock.addIR(ir2)
        return node

class DeclarationScanner(ast.NodeVisitor):
    globalNames: Set[str] = set()
    nonlocalNames: Set[str] = set()
    # nodes under module, function, class is not considered
    def visit_Module(self, node: ast.Module) -> Any:
        pass
    def visit_FunctionDef(self, node: ast.FunctionDef) -> Any:
        pass
    def visit_ClassDef(self, node: ast.ClassDef) -> Any:
        pass

    def visit_Global(self, node: ast.Global) -> Any:
        self.globalNames.add(node.names)

    def visit_Nonlocal(self, node: ast.Nonlocal) -> Any:
        self.nonlocalNames.add(node.names)

# If a name binding operation occurs anywhere within a code block, 
# all uses of the name within the block are treated as references to the current block.
# See https://docs.python.org/3.9/reference/executionmodel.html

class LocalScanner(ast.NodeVisitor):
    declaredNames: Set[str]
    localNames: Set[str] = set()
    def __init__(self, declaredNames):
        self.declaredNames = declaredNames

    def visit_Module(self, node: ast.Module) -> Any:
        pass
    def visit_FunctionDef(self, node: ast.FunctionDef) -> Any:
        if(node.name not in self.declaredNames):
            self.localNames.add(node.name)
        # no generic visit

    def visit_ClassDef(self, node: ast.ClassDef) -> Any:
        if(node.name not in self.declaredNames):
            self.localNames.add(node.name)
        # no generic visit

    def visit_Import(self, node: ast.Import) -> Any:
        for alias in node.names:
            if(alias.asname == None and alias.name not in self.declaredNames):
                self.localNames.add(alias.name)
            elif(alias.asname != None and alias.asname not in self.declaredNames):
                self.localNames.add(alias.asname)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> Any:
        for alias in node.names:
            if(alias.asname == None and alias.name not in self.declaredNames):
                self.localNames.add(alias.name)
            elif(alias.asname != None and alias.asname not in self.declaredNames):
                self.localNames.add(alias.asname)

    def visit_Name(self, node: ast.Name) -> Any:
        if(isinstance(node.ctx, ast.Store) and node.id not in self.declaredNames):
            self.localNames.add(node.id)