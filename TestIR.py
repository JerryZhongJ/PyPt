import ast
from IRGeneration.CodeBlockGenerator import ModuleCodeBlockGenerator
with open("test/resources/Def&Ref.py", "r") as f:
    astTree = ast.parse(f.read())
    # print(f.read())

# print(ast.dump(astTree, indent=4))
generator = ModuleCodeBlockGenerator("Def&Ref", simplify=False)
generator.parse(astTree)
generator.codeBlock.dump("result/unsimplified")