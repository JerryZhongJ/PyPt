from typing import Set
from .CodeBlock import CodeBlock
from .IRStmts import Variable


class ClassCodeBlock(CodeBlock):
    thisClassVariable: Variable                         # refer to $thisClass
    declaredGlobal: Set[str]                            # a list of names declared global
    attributes: Set[str]
    def __init__(self, name:str, enclosing:'CodeBlock', fake=False):
        super().__init__(name, enclosing, fake=False)
        self.module = enclosing.module
        self.thisClassVariable = Variable("$thisClass", self)
        self.scopeLevel = enclosing.scopeLevel