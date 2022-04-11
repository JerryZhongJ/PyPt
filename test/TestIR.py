import ast
from ..IRGeneration.CodeBlockGenerator import ModuleCodeBlockGenerator
import shutil
import os
resource = os.path.join(os.path.dirname(__file__), "resources")
result = os.path.join(os.path.dirname(__file__), "result")
def testIR(moduleName):
    
    # with open(os.path.join(resource, f"{moduleName}.py"), "r") as f:
    #     astTree = ast.parse(f.read())
    # generator = ModuleCodeBlockGenerator(moduleName, simplify=False)
    # generator.parse(astTree)
    # path = os.path.join("result/unsimplified/", moduleName)
    # if(os.path.exists(path)):
    #     shutil.rmtree(path)
    # generator.codeBlock.dump("test/result/unsimplified")

    with open(os.path.join(resource ,f"{moduleName}.py"), "r") as f:
        astTree = ast.parse(f.read())
    generator = ModuleCodeBlockGenerator(moduleName, None, simplify=True)
    generator.parse(astTree)
    
    generator.codeBlock.dump(result)


if(os.path.exists(result)):
    shutil.rmtree(result)

# testIR("Def_Ref")

testIR("Expr")

# testIR("Call")

# testIR("BuiltinContainer")

# testIR("For_Generator")

# testIR("Del")