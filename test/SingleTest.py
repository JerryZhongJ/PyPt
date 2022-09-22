
import json
from PyPt.PTA import json_utils
from PyPt.PTA.Analysis import Analysis
from PyPt.ModuleManager import ModuleManager

import shutil
import os

def testScript(path, filename):

    resource = os.path.join(os.path.dirname(__file__), "resources")
    # with open(os.path.join(resource, path), "r") as f:
    #     print(ast.dump(ast.parse(f.read()), indent=4))

    moduleManager = ModuleManager(os.path.join(resource, path))
    moduleManager.addEntry(file=filename)
    test(moduleManager)
    
def testModule(moduleName, cwd):
    moduleManager = ModuleManager(cwd, maxDepth=0,verbose=True)
    moduleManager.addEntry(module=moduleName)
    test(moduleManager)

def test(moduleManager: ModuleManager):
    entrys = moduleManager.getEntrys()
    result = os.path.join(os.path.dirname(__file__), "result")
    if(os.path.exists(result)):
        shutil.rmtree(result)
    os.mkdir(result)
    for cb in moduleManager.allCodeBlocks():
        cb.dump(result)

    print("IR generation finish, start PTA...                      ")

    analysis = Analysis(verbose=True)
    analysis.analyze(entrys)
    

    
    with open(os.path.join(result, "Point-To Set.json"), "w") as f:
        f.write(analysis.pointToSet.to_json())

    with open(os.path.join(result, "CallGraph.json"), "w") as f:
        json.dump(analysis.callgraph, f, default=json_utils.default,indent=4)

    with open(os.path.join(result, "Pointer Flow.json"), "w") as f:
        f.write(analysis.pointerFlow.to_json())

    with open(os.path.join(result, "Class Hiearchy.json"), "w") as f:
        f.write(analysis.classHiearchy.to_json())


    # print("Done                                                   ")

# testScript("call/assigned_call", "main.py")
testModule("flask", "/home/jerry/Documents/test/projects/flask/src")
