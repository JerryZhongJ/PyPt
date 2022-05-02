
from ..CSPTA.Analysis import Analysis
from ..ModuleManager import ModuleManager

import shutil
import os
import ast
def testScript(path):

    resource = os.path.join(os.path.dirname(__file__), "resources")
    # with open(os.path.join(resource, path), "r") as f:
    #     print(ast.dump(ast.parse(f.read()), indent=4))

    moduleManager = ModuleManager()
    moduleManager.start(os.path.join(resource, path), mode="script")
    test(moduleManager)
    
def testModule(moduleName):
    moduleManager = ModuleManager()
    moduleManager.start(moduleName, mode="module")
    
    test(moduleManager)

def test(moduleManager: ModuleManager):
    entry = moduleManager.getEntry()
    entryCodeBlock = moduleManager.getCodeBlock(entry)
    result = os.path.join(os.path.dirname(__file__), "result")
    if(os.path.exists(result)):
        shutil.rmtree(result)
    os.mkdir(result)
    for cb in moduleManager.allCodeBlocks():
        cb.dump(result)

    print("")
    print("IR generation finish, start PTA...")

    analysis = Analysis()
    analysis.analyze(entryCodeBlock)
    

    
    with open(os.path.join(result, "Point-To Set.txt"), "w") as f:
        analysis.pointToSet.dump(f)

    with open(os.path.join(result, "CallGraph.txt"), "w") as f:
        analysis.callgraph.dump(f)

    with open(os.path.join(result, "Pointer Flow.txt"), "w") as f:
        analysis.pointerFlow.dump(f)

    with open(os.path.join(result, "Class Hiearchy.txt"), "w") as f:
        analysis.classHiearchy.dump(f)

    print("")
    print("Done")

testScript("classes/assigned_self_call/main.py")
# test("ArgMatch")
# testScript("MRO")
# test("Container")
# test("Sensitive")
# test("Numpy")
# testModule("pycg")
