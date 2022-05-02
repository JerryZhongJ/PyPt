
from ..ModuleManager import ModuleManager

import shutil
import os

resource = os.path.join(os.path.dirname(__file__), "resources")
result = os.path.join(os.path.dirname(__file__), "result")
moduleManager = ModuleManager()
moduleManager.start(os.path.join(resource, "Numpy.py"), mode="script")

if(os.path.exists(result)):
    shutil.rmtree(result)
for cb in moduleManager.allCodeBlocks():
    print(cb.moduleName)
    cb.dump(result)
    