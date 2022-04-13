from typing import Dict, Set

from ..IR.CodeBlock import ClassCodeBlock, CodeBlock, FunctionCodeBlock, ModuleCodeBlock

from ..IR.Stmts import Call, IRStmt, NewClass, NewModule


class CallGraph:
    callgraph: Dict[IRStmt, Set[CodeBlock]]          # three kinds: NewClass, NewModule, Call
    reachable: Set[CodeBlock]
    def __init__(self):
        self.callgraph = {}
        self.reachable = set()

    def put(self, stmt: IRStmt, codeBlock:CodeBlock) -> bool:
        assert(isinstance(stmt, NewModule) and isinstance(ModuleCodeBlock) or
               isinstance(stmt, NewClass) and isinstance(ClassCodeBlock) or
               isinstance(stmt, Call) and isinstance(FunctionCodeBlock))
        if(stmt not in self.callgraph):
            self.callgraph[stmt] = set()
        if(codeBlock not in self.callgraph[stmt]):
            self.callgraph[stmt].add(codeBlock)
            return True
        else:
            return False

    def get(self, stmt: IRStmt) -> Set:
        if(stmt not in self.callgraph):
            return set()
        else:
            return self.callgraph[stmt].copy()

    def isReachable(self, codeBlock: CodeBlock):
        return codeBlock in self.reachable

    
