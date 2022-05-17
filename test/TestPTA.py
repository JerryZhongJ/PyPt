import json
import os
from typing import Dict, List
import unittest

from PyPt.PTA.Analysis import Analysis as PTA
from PyPt.CSPTA.Analysis import Analysis as CSPTA

from PyPt.ModuleManager import ModuleManager


    
class TestBase(unittest.TestCase):
    def setUp(self) -> None:
        self.maxDiff = None

    def assertEqual(self, first: Dict[str, list], second: Dict[str, List]) -> None:
        first = {k:v for k, v in first.items() if v}
        second = {k:v for k, v in second.items() if v}
        for v in first.values():
            v.sort()
        for v in second.values():
            v.sort()
        super().assertEqual(first, second)
    
    def _test(self, analysisType, path: str):

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
        
        self.assertEqual(output, expected)


if __name__ == "__main__":
    def getPTATest(path):
        return lambda self: self._test(PTA, path)

    def getCSPTATest(path):
        return lambda self: self._test(CSPTA, path)


    resourcePath = os.path.join(os.path.dirname(__file__), "resources")
    tests = []
    for item in os.listdir(resourcePath):
        itemPath = os.path.join(resourcePath, item)
        
        if(not os.path.isdir(itemPath)):
            continue
        clsName = "".join([s.capitalize() for s in item.split("_")])
        attrs = {}
        for subitem in os.listdir(itemPath):
            subitemPath = os.path.join(itemPath, subitem)
            attrName = "test" + "".join([s.capitalize() for s in subitem.split("_")])
            if(not os.path.isdir(subitemPath)):
                continue
            attrs[attrName] = getPTATest(subitemPath)
        globals()[clsName]  = type(clsName, (TestBase, ), attrs)
    unittest.main(verbosity=2)
