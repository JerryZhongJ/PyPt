
from ...PTA.Analysis import Analysis
from ...ModuleManager import ModuleManager

import shutil
import os

def test(moduleName):

    resource = os.path.join(os.path.dirname(__file__), "resources")
    result = os.path.join(os.path.dirname(__file__), "result")
    moduleManager = ModuleManager()
    moduleManager.start(os.path.join(resource, moduleName + ".py"), mode="script")

    if(os.path.exists(result)):
        shutil.rmtree(result)
    os.mkdir(result)
    
    entry = moduleManager.getCodeBlock("__main__")
    entry.dump(result)
    print("")
    print("IR generation finish, start PTA...")

    analysis = Analysis()
    analysis.analyze(entry)
    pointToSet, callgraph, pointerFlow = analysis.getResult()

    
    with open(os.path.join(result, "Point-To Set.txt"), "w") as f:
        pointToSet.dump(f)

    with open(os.path.join(result, "CallGraph.txt"), "w") as f:
        callgraph.dump(f)

    with open(os.path.join(result, "Pointer Flow.txt"), "w") as f:
        pointerFlow.dump(f)
    print("")
    print("Done")

# test("Basic")
# test("ArgMatch")
# test("MRO")
# test("Container")
# test("Sensitive")
# test("Numpy")
