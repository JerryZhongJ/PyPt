
from typing import Dict, List, Set, Tuple

from PyPt.PTA.ClassHiearchy import ClassHiearchy

from .PTA.Objects import ModuleObject

from .PTA.PointToSet import PointToSet


# all modules', classes', functions' attribtues
# relevant to return variable, 
# 
class Summary:
    name: str
    classes: Dict[str, str] # class attributes, mro
    functions: Dict[str, Dict[str, str]] # paramenter, return
    modules: Dict[str, str] # 
    builtins: List[str]
    attrs: Dict[Tuple[str, str], Set[str]]
    flow: List[Tuple[str, str]]
    
    # project: str
    # pointsTo: PointToSet
    # classHiearchy: ClassHiearchy
    def __init__(self):
        pass

    def load():
        pass

    def export(self) -> Dict[str, str]:
        # start from head module
        head = ModuleObject()


    

