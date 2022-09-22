
from collections import defaultdict
from email.mime import base
import json
from typing import Dict, Generator, List, Set, Tuple

from . import json_utils

from .PointToSet import PointToSet
from .Pointers import VarPtr
from .Objects import ClassObject, FakeObject

# Here MRO mean an order in which methods are resolved, a tuple consists of class objects
MRO = Tuple[ClassObject, ...]
SubclassInfo = Tuple[ClassObject, int]
class ClassHiearchy:
    mros: Dict[ClassObject, Set[MRO]]
    subClasses: Dict[ClassObject, Set[SubclassInfo]]
    pointToSet: PointToSet
    def __init__(self, pointToSet):
        self.mros = defaultdict(set)
        self.pointToSet = pointToSet
        self.subClasses = defaultdict(set)

    def addClass(self, classObj: ClassObject) -> Set[MRO]:
        assert(isinstance(classObj, ClassObject))
        if(classObj in self.mros):
            return
        
        bases = classObj.bases
        
        for i in range(len(bases)):
            for baseObj in self.pointToSet.get(bases[i]):
                # TODO: not perfect
                if(baseObj == classObj):
                    continue
                if(isinstance(baseObj, FakeObject)):
                    self.addClass(baseObj)
                self.subClasses[baseObj].add((classObj, i))

        add = self.addBaseMRO(classObj, -1, {})

        return add

        
    def addClassBase(self, classObj: ClassObject, index: int, baseObj: ClassObject) -> Set[MRO]:
        assert(isinstance(classObj, ClassObject))
        if(baseObj == classObj):
            return set()
        if(isinstance(baseObj, FakeObject)):
            self.addClass(baseObj)
        self.subClasses[baseObj].add((classObj, index))
        return self.addBaseMRO(classObj, index, self.mros[baseObj])

    def addBaseMRO(self, classObj: ClassObject, index: int, mroList: Set[MRO]) -> Set[MRO]:
        assert(isinstance(classObj, ClassObject))
        bases = classObj.bases
        # yield mros
        def select(start: int) -> Generator[List[MRO], None, None]:
            if(start == len(bases)):
                yield []
                
            elif(start == index):
                for mro in mroList:
                    for tail in select(start + 1):
                        tail.insert(0, mro)
                        yield tail
            else:
                for obj in self.pointToSet.get(bases[start]):
                    if(not isinstance(obj, ClassObject)):
                        continue
                    for mro in self.mros[obj]:
                        for tail in select(start + 1):
                            tail.insert(0, mro)
                            yield tail

        add = set()
        for mros in select(0):
            order = [mro[0] for mro in mros]
            mros.append(order)
            res = self._c3(classObj, mros)
            
            if(res is not None and res not in self.mros[classObj]):
                assert(res[0] == classObj)
                add.add(res)
                self.mros[classObj].add(res)
                
        if(len(add) == 0):
            return set()

        allAdd = add.copy()
        for subclass, index in self.subClasses[classObj]:
            allAdd |= self.addBaseMRO(subclass, index, add)
        return allAdd

    # return None if it is illegal
    def _c3(self, head, mros: List) -> MRO:
        for i in range(len(mros)):
            mros[i] = list(mros[i])

        for mro in mros:
            if (head in mro):
                # illegal
                return None

        res = []
        mros = [mro for mro in mros if len(mro) != 0]
        while(len(mros) != 0):
            for mro in mros:
                candidate = mro[0]
                
                for another in mros:
                    if(candidate in  another[1:]):
                        break
                else:
                    res.append(candidate)
                    for another in mros:
                        if(another[0] == candidate):
                            del another[0]
                    mros = [mro for mro in mros if len(mro) != 0]
                    break
            else:
                # illegal mro
                return None
            
        return head, *res,

    def getMROs(self, classObj: ClassObject) -> Set[MRO]:
        return self.mros[classObj]

    def to_json(self):
        res = defaultdict(dict)
        for cls, mros in self.mros.items():
            res[str(cls)]["MROs"] = mros
        for cls, subclasses in self.subClasses.items():
            res[str(cls)]["subclasses"] = subclasses
        return json.dumps(res, default=json_utils.default, indent=4)



