from typing import Any, Dict

from ..IRGeneration.IR import IR
from .Objects import AllocationSiteObject, ConstObject, MethodObject, ModuleObject


class ObjectManager:
    constObjects: Dict[Any, ConstObject]
    moduleObjects: Dict[str, ModuleObject]
    allocationObjects: Dict[IR, AllocationSiteObject]
    methodObjects: Dict[tuple, MethodObject]

    def getConstObject(self, value):
        if(value )
    