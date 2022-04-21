import os
from typing import Dict, Set

from ..IR.CodeBlock import ClassCodeBlock, CodeBlock, FunctionCodeBlock, ModuleCodeBlock

from ..IR.Stmts import Call, IRStmt, NewClass, NewModule


class CallGraph:
    callgraph: Dict[IRStmt, Set[CodeBlock]]          # three kinds: NewClass, NewModule, Call
    # reachable: Set[CodeBlock]
    def __init__(self):
        self.callgraph = {}
        self.reachable = set()

    def put(self, stmt: IRStmt, codeBlock:CodeBlock) -> bool:
        assert(isinstance(stmt, NewModule) and isinstance(codeBlock, ModuleCodeBlock) or
               isinstance(stmt, NewClass) and isinstance(codeBlock, ClassCodeBlock) or
               isinstance(stmt, Call) and isinstance(codeBlock, FunctionCodeBlock))
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

    # def isReachable(self, codeBlock: CodeBlock):
    #     return codeBlock in self.reachable

    def dump(self, fp):
        callgraph:Dict[CodeBlock, Dict[IRStmt, Set[CodeBlock]]] = {stmt.belongsTo:{} for stmt in self.callgraph}
        for stmt, callees in self.callgraph.items():
            callgraph[stmt.belongsTo][stmt] = callees
        for caller, map in callgraph.items():

            print(caller.qualified_name + ":", file=fp)    
            
            colwidth = 0
            for stmt in map:
                w = len(str(stmt))
                colwidth = w if colwidth < w else colwidth
            for stmt, callees in map.items():
                callees = [callee.qualified_name for callee in callees]
                print(f"{str(stmt):<{colwidth}} -> {', '.join(callees)}", file=fp)
            print("", file=fp)

    
