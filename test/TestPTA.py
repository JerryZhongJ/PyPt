import json
import os
from typing import Dict, List
import unittest

from ..PTA.Analysis import Analysis

from ..ModuleManager import ModuleManager


    
class TestPTA(unittest.TestCase):


    def assertEqual(self, first: Dict[str, List], second: Dict[str, List]) -> None:
        for l in first.values():
            l.sort()

        for l in second.values():
            l.sort()
        super().assertEqual(first, second)
    
    def _test(self, path: str):

        # get output
        moduleManager = ModuleManager()
        moduleManager.start(path, "script")
        entry = moduleManager.getEntry()
        entry = moduleManager.getCodeBlock(entry)
        analysis = Analysis()
        analysis.analyze(entry)
        output = analysis.getFormattedCallGraph()

        # get expected output
        expectedPath = os.path.join(os.path.dirname(path), "callgraph.json")
        with open(expectedPath, "r") as f:
            expected = json.load(f)
        
        self.assertEqual(output, expected)


if __name__ == "__main__":
    def getTemplate(path):
        return lambda self: self._test(os.path.join(path, "main.py"))

    exclude = [("builtins", "types"), ("builtins", "map"), ("mro", "super_call"), ("generators", "iterable"), ("decorators", "assigned")]
    resourcePath = os.path.join(os.path.dirname(__file__), "resources")
    for item in os.listdir(resourcePath):
        itemPath = os.path.join(resourcePath, item)
        if(not os.path.isdir(itemPath)):
            continue
        for subitem in os.listdir(itemPath):
            subitemPath = os.path.join(itemPath, subitem)
            if(not os.path.isdir(subitemPath)):
                continue
            if((item, subitem) in exclude):
                continue
            
            setattr(TestPTA, f"test_{item}_{subitem}", getTemplate(subitemPath))
    
    unittest.main()
