
from typing import Dict, Set
from . import CSCodeBlock, CSStmt
from ..PTA.CallGraph import CallGraph
from ..IR.CodeBlock import CodeBlock
from ..IR.IRStmts import IRStmt


class CSCallGraph(CallGraph):
    callgraph: Dict[CSStmt, Set[CSCodeBlock]]          # three kinds: NewClass, NewModule, Call

    def foldToStmt(self) -> Dict[CodeBlock, Dict[IRStmt, Set[CodeBlock]]]:
        callgraph = {}
        for csStmt, csCallees in self.callgraph.items():
            stmt = csStmt[1]
            caller = stmt.belongsTo
            if(caller not in callgraph):
                callgraph[caller] = {}
           
            if(stmt not in callgraph[caller]):
                callgraph[caller][stmt] = set()
            callgraph[caller][stmt] |= {callee for ctx, callee in csCallees}
        return callgraph

    def foldToCodeBlock(self) -> Dict[CodeBlock, Set[CodeBlock]]:
        callgraph = {}
        for csStmt, csCallees in self.callgraph.items():
            stmt = csStmt[1]
            caller = stmt.belongsTo
            if(caller not in callgraph):
                callgraph[caller] = set()
            callgraph[caller] |= {callee for ctx, callee in csCallees}
        return callgraph