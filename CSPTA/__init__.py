from typing import Tuple, Union

from ..IR.CodeBlock import CodeBlock

from ..IR.Stmts import Assign, Call, DelAttr, GetAttr, IRStmt, NewBuiltin, NewClass, NewClassMethod, NewFunction, NewModule, NewStaticMethod, SetAttr

from .Context import ContextChain


CSStmt = Tuple[ContextChain, IRStmt]
Stmt = Union[IRStmt, CSStmt]
CSCodeBlock = Tuple[ContextChain, CodeBlock]
CS_Assgin = Tuple[ContextChain, Assign]
CS_SetAttr = Tuple[ContextChain, SetAttr]
CS_GetAttr = Tuple[ContextChain, GetAttr]
CS_DelAttr = Tuple[ContextChain, DelAttr]
CS_NewModule = Tuple[ContextChain, NewModule]
CS_NewClass = Tuple[ContextChain, NewClass]
CS_NewFunction = Tuple[ContextChain, NewFunction]
CS_NewBuiltin = Tuple[ContextChain, NewBuiltin]
CS_Call = Tuple[ContextChain, Call]
CS_NewClassMethod = Tuple[ContextChain, NewClassMethod]
CS_NewStaticMethod = Tuple[ContextChain, NewStaticMethod]
