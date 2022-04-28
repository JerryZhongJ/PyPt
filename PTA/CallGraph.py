import os
from typing import Dict, Set

from ..CSPTA import CSCodeBlock, CSStmt

from ..IR.CodeBlock import ClassCodeBlock, CodeBlock, FunctionCodeBlock, ModuleCodeBlock

from ..IR.Stmts import Call, NewClass, NewModule, IRStmt


class CallGraph:
    callgraph: Dict[IRStmt, Set[CodeBlock]]          # three kinds: NewClass, NewModule, Call
    # reachable: Set[CodeBlock]
    def __init__(self, cs=False):
        self.callgraph = {}
        self.reachable = set()
        self.cs = cs
    def put(self, stmt: IRStmt, codeBlock:CodeBlock) -> bool:
        # assert(isinstance(stmt, NewModule) and isinstance(codeBlock, ModuleCodeBlock) or
        #        isinstance(stmt, NewClass) and isinstance(codeBlock, ClassCodeBlock) or
        #        isinstance(stmt, Call) and isinstance(codeBlock, FunctionCodeBlock))
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
        if(not self.cs):
            callgraph:Dict[CodeBlock, Dict[IRStmt, Set[CodeBlock]]] = {stmt.belongsTo:{} for stmt in self.callgraph}
            for stmt, callees in self.callgraph.items():
                callgraph[stmt.belongsTo][stmt] = callees
            for caller, map in callgraph.items():

                print(caller.qualified_name + ":", file=fp)    
            
                for stmt, callees in map.items():
                    head = f"{stmt} -> "
                    w = len(head)
                    
                    for callee in callees:
                        print(f"{head:<{w}}{callee.qualified_name}", file=fp)
                        head = ""
                    
                print("", file=fp)
        else:
            callgraph:Dict[CodeBlock, Dict[CSStmt, Set[CSCodeBlock]]] = {stmt[1].belongsTo:{} for stmt in self.callgraph}
            for stmt, callees in self.callgraph.items():
                callgraph[stmt[1].belongsTo][stmt] = callees
            for caller, map in callgraph.items():

                print(caller.qualified_name + ":", file=fp)    
            
                for stmt, callees in map.items():
                    head = f"{stmt} -> "
                    w = len(head)
                    
                    for callee in callees:
                        s = ""
                        for ctx in callee[0]:
                            s += ", ".join([str(e) for e in ctx]) + "#"
                        print(f"{head:<{w}}{s}{callee[1].qualified_name}", file=fp)
                        head = ""
                print("", file=fp)
    
