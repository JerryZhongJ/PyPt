
import json
import os
from PyPt.CSPTA.Analysis import Analysis as csAnalysis
from PyPt.PTA.Analysis import Analysis

from PyPt.ModuleManager import ModuleManager, ModuleNotFoundException
from PyPt.PTA.CallGraph import CallGraph


if __name__ == "__main__":
    project = "scrapy"
    src = ""
    moduleMode = True
    entrys = ["scrapy"]

    cwd = os.path.join(f"/home/jerry/Documents/test_projects/{project}", src)

    mm = ModuleManager(cwd, verbose=True, dependency=True)
   
    try:
        if(moduleMode):
            for module in entrys:
                mm.addEntry(module=module)
        else:
            for file in entrys:
                mm.addEntry(file=file)

    except ModuleNotFoundException as e:
        print(f"Error: {e}")
        exit()
    except ValueError as e:
        print(f"Error: {e}")
        exit()


    entrys = mm.getEntrys()
    
    print("IR generation is done, start CI Point-to Analysis...                ")

    fp_pta = open(f"/home/jerry/Documents/test_results/{project}_PyPt.json", "w")
    analysis = Analysis(verbose=True)
    analysis.analyze(entrys)
    callgraph = analysis.callgraph.export()
    callgraph = {k:v for k, v in callgraph.items() if k.startswith(project)} 
    json.dump(callgraph, fp_pta, indent=4)
    fp_pta.close()

    print("Start CS Point-to Analysis...                ")

    fp_cspta = open(f"/home/jerry/Documents/test_results/{project}_csPyPt.json", "w")
    analysis = csAnalysis(verbose=True)
    analysis.analyze(entrys)
    callgraph = analysis.callgraph.export()
    callgraph = {k:v for k, v in callgraph.items() if k.startswith(project)} 
    json.dump(callgraph, fp_cspta, indent=4)
    fp_cspta.close()

    print("All done.")

    
    