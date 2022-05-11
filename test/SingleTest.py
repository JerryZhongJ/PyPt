
import json
from PyPt.PTA.Analysis import Analysis
from PyPt.ModuleManager import ModuleManager

import shutil
import os
import ast
def testScript(path):

    resource = os.path.join(os.path.dirname(__file__), "resources")
    # with open(os.path.join(resource, path), "r") as f:
    #     print(ast.dump(ast.parse(f.read()), indent=4))

    moduleManager = ModuleManager()
    moduleManager.start(filepath=os.path.join(resource, path))
    test(moduleManager)
    
def testModule(moduleName, cwd):
    moduleManager = ModuleManager()
    moduleManager.start(module=moduleName, cwd=cwd, dependency=False)
    
    test(moduleManager)

def test(moduleManager: ModuleManager):
    entryCodeBlock = moduleManager.getCodeBlock("__main__")
    result = os.path.join(os.path.dirname(__file__), "result")
    if(os.path.exists(result)):
        shutil.rmtree(result)
    os.mkdir(result)
    for cb in moduleManager.allCodeBlocks():
        cb.dump(result)

    print("IR generation finish, start PTA...                      ")

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

    with open(os.path.join(result, "callgraph.json"), "w") as f:
        json.dump(analysis.callgraph.export(), f, indent=4)

    print("Done                                                   ")

# testScript("iteration/iterator/main.py")
testModule("flask", "/home/jerry/Documents/test_projects/flask/src")
