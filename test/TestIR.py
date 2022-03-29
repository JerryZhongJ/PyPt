import ast
from IRGeneration.CodeBlockGenerator import ModuleCodeBlockGenerator
import shutil

def testIR(moduleName):

    with open(f"test/resources/{moduleName}.py", "r") as f:
        astTree = ast.parse(f.read())
    generator = ModuleCodeBlockGenerator(moduleName, simplify=False)
    generator.parse(astTree)
    shutil.rmtree("result/unsimplified")
    generator.codeBlock.dump("result/unsimplified")

    with open(f"test/resources/{moduleName}.py", "r") as f:
        astTree = ast.parse(f.read())
    generator = ModuleCodeBlockGenerator(moduleName, simplify=True)
    generator.parse(astTree)
    shutil.rmtree("result/simplified")
    generator.codeBlock.dump("result/simplified")