import os
from subprocess import call
from typing import Dict, List, Set, Union

from ..CSPTA import CSCodeBlock, CSStmt

from ..IR.CodeBlock import ClassCodeBlock, CodeBlock, FunctionCodeBlock, ModuleCodeBlock

from ..IR.Stmts import Call, NewClass, NewModule, IRStmt


class CallGraph:
    
    # reachable: Set[CodeBlock]
    def __init__(self):
        self.callgraph = {}
        
        
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
            return self.callgraph[stmt]

    def foldToStmt(self) -> Dict[CodeBlock, Dict[IRStmt, Set[CodeBlock]]]:
        pass

    def foldToCodeBlock(self) -> Dict[CodeBlock, Set[CodeBlock]]:
        pass

    def dump(self, fp) -> Dict[CodeBlock, Dict[IRStmt, Set[CodeBlock]]]:
        callgraph = self.foldToStmt()
        for caller, map in callgraph.items():

            print(caller.qualified_name + ":", file=fp)    
            for stmt, callees in map.items():
                head = f"{stmt} -> "
                w = len(head)
                
                for callee in callees:
                    print(f"{head:<{w}}{callee.qualified_name}", file=fp)
                    head = ""
                
            print("", file=fp)

        # return a dict of callgraph, formed with str
    def export(self) -> Dict[str, List[str]]:
        tmp = self.foldToCodeBlock()
        callgraph = {}
        for caller, callees in tmp.items():
            callgraph[caller.qualified_name] = [callee.qualified_name for callee in callees if not callee.fake]
        
        return callgraph

    def foldToStmt(self) -> Dict[CodeBlock, Dict[IRStmt, Set[CodeBlock]]]:
        callgraph = {}
        for stmt, callees in self.callgraph.items():
            caller = stmt.belongsTo
            if(caller not in callgraph):
                callgraph[caller] = {}
            callgraph[caller][stmt] = callees
        return callgraph

    def foldToCodeBlock(self) -> Dict[CodeBlock, Set[CodeBlock]]:
        callgraph = {}
        for stmt, callees in self.callgraph.items():
            caller = stmt.belongsTo
            if(caller not in callgraph):
                callgraph[caller] = set()
            callgraph[caller] |= callees
        return callgraph
        
                

class CICallGraph(CallGraph):
    callgraph: Dict[IRStmt, Set[CodeBlock]]          # three kinds: NewClass, NewModule, Call

    def foldToStmt(self) -> Dict[CodeBlock, Dict[IRStmt, Set[CodeBlock]]]:
        callgraph = {}
        for stmt, callees in self.callgraph.items():
            caller = stmt.belongsTo
            if(caller not in callgraph):
                callgraph[caller] = {}
            callgraph[caller][stmt] = callees
        return callgraph

    def foldToCodeBlock(self) -> Dict[CodeBlock, Set[CodeBlock]]:
        callgraph = {}
        for stmt, callees in self.callgraph.items():
            caller = stmt.belongsTo
            if(caller not in callgraph):
                callgraph[caller] = set()
            callgraph[caller] |= callees
        return callgraph


                
            
