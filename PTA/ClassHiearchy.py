
from email.mime import base
from typing import Dict, Generator, List, Set, Tuple

from .PointToSet import PointToSet
from .Pointers import VarPtr
from .Objects import ClassObject

# Here MRO mean an order in which methods are resolved, a tuple consists of class objects
MRO = Tuple[ClassObject, ...]
SubclassInfo = Tuple[ClassObject, int]
class ClassHiearchy:
    mros: Dict[ClassObject, Set[MRO]]
    subClasses: Dict[ClassObject, Set[SubclassInfo]]
    pointToSet: PointToSet
    def __init__(self, pointToSet):
        self.mros = {}
        self.pointToSet = pointToSet
        self.subClasses = {}

    def addClass(self, classObj: ClassObject) -> Set[MRO]:
        assert(isinstance(classObj, ClassObject))
        if(classObj in self.mros):
            return
        self.mros[classObj] = set()
        self.subClasses[classObj] = set()
        bases = classObj.getBases()
        
        for i in range(len(bases)):
            for baseObj in self.pointToSet.get(bases[i]):
                self.subClasses[baseObj].add((classObj, i))

        add = self.addBaseMRO(classObj, -1, {})

        return add

        
    def addClassBase(self, classObj: ClassObject, index: int, baseObj: ClassObject) -> Set[MRO]:
        assert(isinstance(classObj, ClassObject))
        self.subClasses[baseObj].add((classObj, index))
        return self.addBaseMRO(classObj, index, self.mros[baseObj])

    def addBaseMRO(self, classObj: ClassObject, index: int, mroList: Set[MRO]) -> Set[MRO]:
        assert(isinstance(classObj, ClassObject))
        bases = classObj.getBases()
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
                    for mro in self.mros[obj]:
                        for tail in select(start + 1):
                            tail.insert(0, mro)
                            yield tail

        add = set()
        for mros in select(0):
            order = [classObj] + [mro[0] for mro in mros]
            mros.append(order)
            res = self._c3(mros)
            
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
    def _c3(self, mros) -> MRO:
        nexts = {}
        inDegrees = {}
        for mro in mros:
            for i in range(len(mro)):
                if(mro[i] not in nexts):
                    nexts[mro[i]] = set()
                    inDegrees[mro[i]] = 0
        
        for mro in mros:
            for i in range(len(mro) - 1):
                nexts[mro[i]].add(mro[i + 1])
                inDegrees[mro[i + 1]] += 1

        mro = []
        while(len(inDegrees) != 0):
            selected = None
            for obj, degree in inDegrees.items():
                if(degree == 0):
                    if(selected != None):
                        # illegal
                        return 
                    selected = obj
            if(selected == None):
                return 
            mro.append(selected)
            for next in nexts[selected]:
                inDegrees[next] -= 1

            del nexts[selected]
            del inDegrees[selected]
        return *mro,

    def getMROs(self, classObj: ClassObject) -> Set[MRO]:
        if(classObj in self.mros):
            return self.mros[classObj].copy()
        else:
            return set()



