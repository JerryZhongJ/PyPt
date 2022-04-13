from typing import Dict, Set

from PTA.Pointers import Pointer


class PointerFlow:
    edges: Dict[Pointer, Set[Pointer]]

    def __init__(self):
        self.edges = {}

    def put(self, source, target) -> bool:
        if(source not in self.edges):
            self.edges[source] = set()
        if(target not in self.edges):
            self.edges[source].add(target)
            return True
        else:
            return False

    def getSuccessors(self, source) -> set:
        if(source not in self.edges):
            return set()
        else:
            return self.edges[source].copy()
            
