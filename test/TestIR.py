import ast
from IRGeneration.CodeBlockGenerator import ModuleCodeBlockGenerator
import shutil
import os
def testIR(moduleName):

    with open(f"test/resources/{moduleName}.py", "r") as f:
        astTree = ast.parse(f.read())
    generator = ModuleCodeBlockGenerator(moduleName, simplify=False)
    generator.parse(astTree)
    path = os.path.join("result/unsimplified/", moduleName)
    if(os.path.exists(path)):
        shutil.rmtree(path)
    generator.codeBlock.dump("test/result/unsimplified")

    with open(f"test/resources/{moduleName}.py", "r") as f:
        astTree = ast.parse(f.read())
    generator = ModuleCodeBlockGenerator(moduleName, simplify=True)
    generator.parse(astTree)
    path = os.path.join("test/result/simplified/", moduleName)
    if(os.path.exists(path)):
        shutil.rmtree(path)
    generator.codeBlock.dump("test/result/simplified")