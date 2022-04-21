from typing import Dict, Set
from .Pointers import Pointer


class PointerFlow:
    forward: Dict[Pointer, Set[Pointer]]
    backward: Dict[Pointer, Set[Pointer]]
    def __init__(self):
        self.forward = {}
        self.backward = {}

    def put(self, source: Pointer, target: Pointer) -> bool:
        if(source not in self.forward):
            self.forward[source] = set()
        if(target not in self.backward):
            self.backward[target] = set()

        if(target not in self.forward[source]):
            self.forward[source].add(target)
            self.backward[target].add(source)
            return True
        else:
            return False

    def getSuccessors(self, source) -> set:
        if(source not in self.forward):
            return set()
        else:
            return self.forward[source].copy()

    def dump(self, fp):
        print("-> :", file=fp)
        
        for ptr, allSucc in self.forward.items():
            succ_str = [str(succ) for succ in allSucc]
            print(f"{ptr}    -> {', '.join(succ_str)}", file=fp)
            

        print("", file=fp)
        print("<- :", file=fp)
        
        for ptr, allProc in self.backward.items():
            pred_str = [str(pred) for pred in allProc]
            print(f"{ptr}    <- {', '.join(pred_str)}", file=fp)
