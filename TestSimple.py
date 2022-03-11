import ast
from textwrap import indent
from IR.ModuleCodeBlockGenerator import ModuleCodeBlockGenerator
with open("test/resources/simple.py", "r") as f:
    astTree = ast.parse(f.read())
    # print(f.read())

# print(ast.dump(astTree, indent=4))
generator = ModuleCodeBlockGenerator("simple")
generator.parse(astTree)
print(generator.codeBlock)