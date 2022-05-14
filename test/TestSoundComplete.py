import json
import os
from typing import Dict, List
import unittest

from PyPt.PTA.Analysis import Analysis as PTA
from PyPt.CSPTA.Analysis import Analysis as CSPTA

from PyPt.ModuleManager import ModuleManager

def isSound(output, groundtruth):
    for caller, callees in groundtruth.items():
        if(callees and caller not in output):
            return False
        for callee in callees:
            if(callee not in output[caller]):
                return False
    return True
            

def isComplete(output, groundtruth):
    for caller, callees in output.items():
        if(callees and caller not in groundtruth):
            return False
        for callee in callees:
            if(callee not in groundtruth[caller]):
                return False
    return True
    
class Test:
    def __init__(self, name):
        self.name = name
        self.total = 0
        self.sound = 0
        self.complete = 0

    
    
    def test(self, analysisType, path: str):
        self.total += 1
        # get output
        moduleManager = ModuleManager(path)
        moduleManager.addEntry(file="main.py")
        entrys = moduleManager.getEntrys()
        analysis = analysisType()
        analysis.analyze(entrys)
        output = analysis.callgraph.export()

        # get expected output
        expectedPath = os.path.join(path, "callgraph.json")
        with open(expectedPath, "r") as f:
            expected = json.load(f)
        
        if(isSound(output, expected)):
            self.sound +=  1

        if(isComplete(output, expected)):
            self.complete += 1

    def print(self):
        print(f"{self.name}: {self.sound}/{self.total}, {self.complete}/{self.total}")


if __name__ == "__main__":


    resourcePath = os.path.join(os.path.dirname(__file__), "resources")

    for item in os.listdir(resourcePath):
        itemPath = os.path.join(resourcePath, item)
        
        if(not os.path.isdir(itemPath)):
            continue
        testName = "".join([s.capitalize() for s in item.split("_")])
        test = Test(testName)
        for subitem in os.listdir(itemPath):
            subitemPath = os.path.join(itemPath, subitem)
            
            if(not os.path.isdir(subitemPath)):
                continue
            test.test(CSPTA, subitemPath)
        test.print()
        
