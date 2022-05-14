"""This file is based on python3.9/modulefinder.py"""

import dis
from typing import List, Union
import importlib._bootstrap_external
import importlib.machinery
import marshal
import os
import io
import sys
import ast

from .IR.CodeBlock import CodeBlock, ModuleCodeBlock
from .IR.CodeBlockGenerator import ModuleCodeBlockGenerator
from .IR.Stmts import NewModule, SetAttr, Variable

LOAD_CONST = dis.opmap['LOAD_CONST']
IMPORT_NAME = dis.opmap['IMPORT_NAME']
STORE_NAME = dis.opmap['STORE_NAME']
STORE_GLOBAL = dis.opmap['STORE_GLOBAL']
STORE_OPS = STORE_NAME, STORE_GLOBAL
EXTENDED_ARG = dis.EXTENDED_ARG

# Old imp constants:

_SEARCH_ERROR = 0
_PY_SOURCE = 1
_PY_COMPILED = 2
_C_EXTENSION = 3
_PKG_DIRECTORY = 5
_C_BUILTIN = 6
_PY_FROZEN = 7

# Modulefinder does a good job at simulating Python's, but it can not
# handle __path__ modifications packages make at runtime.  Therefore there
# is a mechanism whereby you can register extra paths in this map for a
# package, and it will be honored.


def _find_module(name, path=None):
    """An importlib reimplementation of imp.find_module (for our purposes)."""

    # It's necessary to clear the caches for our Finder first, in case any
    # modules are being added/deleted/modified at runtime. In particular,
    # test_modulefinder.py changes file tree contents in a cache-breaking way:

    importlib.machinery.PathFinder.invalidate_caches()

    spec = importlib.machinery.PathFinder.find_spec(name, path)

    if spec is None or spec.loader is None:
        raise ImportError("No module named {name!r}".format(name=name), name=name)

    # Some special cases:

    if spec.loader is importlib.machinery.BuiltinImporter:
        return None, None, ("", "", _C_BUILTIN)

    if spec.loader is importlib.machinery.FrozenImporter:
        return None, None, ("", "", _PY_FROZEN)

    file_path = spec.origin

    if spec.loader.is_package(name):
        return None, os.path.dirname(file_path), ("", "", _PKG_DIRECTORY)

    if isinstance(spec.loader, importlib.machinery.SourceFileLoader):
        kind = _PY_SOURCE

    elif isinstance(spec.loader, importlib.machinery.ExtensionFileLoader):
        kind = _C_EXTENSION

    elif isinstance(spec.loader, importlib.machinery.SourcelessFileLoader):
        kind = _PY_COMPILED

    else:  # Should never happen.
        return None, None, ("", "", _SEARCH_ERROR)

    file = io.open_code(file_path)
    suffix = os.path.splitext(file_path)[-1]

    return file, file_path, (suffix, "rb", kind)


class Module:

    def __init__(self, name, file=None, path=None):
        self.__name__ = name
        self.__file__ = file
        self.__path__ = path
        self.__codeBlock__ = None
        
        # # The set of global names that are assigned to in the module.
        # # This includes those names imported through starimports of
        # # Python modules.
        # self.globalnames = {}
        # # The set of starimports this module did that could not be
        # # resolved, ie. a starimport from a non-Python module.
        # self.starimports = {}

    def __repr__(self):
        s = "Module(%r" % (self.__name__,)
        if self.__file__ is not None:
            s = s + ", %r" % (self.__file__,)
        if self.__path__ is not None:
            s = s + ", %r" % (self.__path__,)
        s = s + ")"
        return s

class ModuleManager:

    def __init__(self,cwd=None, /, maxDepth=9999, verbose=False):
        
        if(cwd):
            self.cwd = [cwd]
        else:
            self.cwd = [os.getcwd()]

        self.externalPath = sys.path[1:]
        self.modules = {}
        self.badmodules = {}
        self.verbose = verbose
        self.maxDepth = maxDepth
        self.entrys = []
        
    def addEntry(self, /, file=None, module=None) -> None:
        

        if(file):
            filepath = os.path.join(self.path[0], file)
            
            try:
                with io.open_code(filepath) as fp:
                    stuff = ("", "rb", _PY_SOURCE)
                    m = self.load_module(f'__main{len(self.entrys) if self.entrys else ""}__', fp, filepath, stuff)
                    self.entrys.append(m)
            except(IOError):
                raise ModuleNotFoundException(f"Can't open file {filepath}. Please check if the file exists.")

        if(module):
            try:
                self._import_hook(module, None)
            except(ImportError):
                raise ModuleNotFoundException(f"Can't import {module}. Please check if this module exists.")
            
            if(self.modules[module].__path__):
                try:
                    self._import_hook(module + ".__main__", None)
                    self.entrys.append(self.modules[module + ".__main__"])
                except(ImportError):
                    raise ModuleNotFoundException(f"{module} is a package, but {module}.__main__ can't be imported. Please check if it exists.")
            
    def getEntrys(self) -> List[CodeBlock]:
        return [m.__codeBlock__ for m in self.entrys]


    def getCodeBlock(self, name: str, callerName: str=None, level: int=0) -> Union[ModuleCodeBlock, str]:
        callerName = callerName and self.modules[callerName]
        parent = self.determine_parent(callerName, level)
        if parent and name:
            fqname = parent.__name__ + "." + name
        elif parent:
            fqname = parent.__name__
        else:
            fqname = name

        if(fqname in self.modules):
            return self.modules[fqname].__codeBlock__
        else:
            return fqname
        


    def allCodeBlocks(self):
        return [m.__codeBlock__ for m in self.modules.values() if m.__codeBlock__ is not None]
        
    def load_file(self, pathname):
        dir, name = os.path.split(pathname)
        name, ext = os.path.splitext(name)
        with io.open_code(pathname) as fp:
            stuff = (ext, "rb", _PY_SOURCE)
            self.load_module(name, fp, pathname, stuff)

    # import all the module in the quarlified name, and those in fromlist
    # if this is "import", return the head module
    # if this is "import ... from",  import fromlist and return None
    def _import_hook(self, name, caller=None, fromlist=None, level=0) -> None:
        
        parent = self.determine_parent(caller, level=level)
        # q is imported, tail is not
        q, tail = self.find_head_package(parent, name)
        m = self.load_tail(q, tail)
        if not fromlist:
            return
        # "import ... from ...", and this is a package
        if m.__path__:
            self.ensure_fromlist(m, caller, fromlist)
        

    # used when relative import, return an added module
    def determine_parent(self, caller, level=0):
        
        if not caller or level == 0:
           
            return None
        # pname: parent's name
        pname = caller.__name__
        if level >= 1: # relative import
            if caller.__path__:
                # caller is a package
                level -= 1
            if level == 0:
                # when caller is a package, and module is inside the pacakge
                parent = self.modules[pname]
                assert parent is caller

                return parent
            if pname.count(".") < level:
                raise ImportError("relative importpath too deep")
            pname = ".".join(pname.split(".")[:-level])
            parent = self.modules[pname]

            return parent
        if caller.__path__:
            parent = self.modules[pname]
            assert caller is parent

            return parent
        if '.' in pname:
            i = pname.rfind('.')
            pname = pname[:i]
            parent = self.modules[pname]
            assert parent.__name__ == pname

            return parent

        return None

    # determine the head and import it
    def find_head_package(self, caller, parent, name):

        if '.' in name:
            i = name.find('.')
            head = name[:i]
            tail = name[i+1:]
        else:
            head = name
            tail = ""
        if parent and name:
            qname = "%s.%s" % (parent.__name__, head)
        elif parent:
            qname = parent.__name__
        else:
            qname = head
            
        q = self.import_module(caller, head, qname, parent)
        if q:

            return q, tail
        if parent:
            qname = head
            parent = None
            q = self.import_module(caller, head, qname, parent)
            if q:

                return q, tail

        raise ImportError("No module named " + qname)

    # when the head is imported, import the rest, return the last module
    # TODO: add globalNames here
    def load_tail(self, caller, q, tail):

        m = q
        while tail:
            i = tail.find('.')
            if i < 0: i = len(tail)
            head, tail = tail[:i], tail[i+1:]
            mname = "%s.%s" % (m.__name__, head)
            m = self.import_module(caller, head, mname, m)
            if not m:

                raise ImportError("No module named " + mname)

        return m

    # import submodules in fromlist, m should be a pacakge
    def ensure_fromlist(self, m, caller, fromlist):

        if("*" in fromlist):
            all = self.find_all_submodules(m)
            self.ensure_fromlist(m, caller, all)
            fromlist = [sub for sub in fromlist if sub != "*"]

        for sub in fromlist:
            if not hasattr(m, sub):
                subname = "%s.%s" % (m.__name__, sub)
                submod = self.import_module(sub, subname, m)
                if not submod:

                    self._add_badmodule(subname, caller)
                    

    # used when m is a package, return all submodules' name
    def find_all_submodules(self, m):
        if not m.__path__:
            return
        modules = {}
        # 'suffixes' used to be a list hardcoded to [".py", ".pyc"].
        # But we must also collect Python extension modules - although
        # we cannot separate normal dlls from Python extensions.
        suffixes = []
        suffixes += importlib.machinery.EXTENSION_SUFFIXES[:]
        suffixes += importlib.machinery.SOURCE_SUFFIXES[:]
        suffixes += importlib.machinery.BYTECODE_SUFFIXES[:]
        for dir in m.__path__:
            try:
                names = os.listdir(dir)
            except OSError:

                continue
            for name in names:
                mod = None
                for suff in suffixes:
                    n = len(suff)
                    if name[-n:] == suff:
                        mod = name[:-n]
                        break
                if mod and mod != "__init__":
                    modules[mod] = mod
        return modules.keys()

    # import = find + load, import specific module
    def import_module(self, partname, fqname, parent):
        if(self.verbose):
            print(f"Importing {fqname}                        \r", end="")
        try:
            m = self.modules[fqname]
        except KeyError:
            pass
        else:
            return m
        
        if fqname in self.badmodules:

            return None
        if parent and parent.__path__ is None:

            return None
        try:
            fp, pathname, stuff, isExternal = self.find_module(partname,
                                                   parent and parent.__path__, parent)
        except ImportError:
            return None

        if()

        try:
            m = self.load_module(fqname, fp, pathname, stuff)
            if(m and parent):
                tmp = parent.__generator__.newTmpVariable()
                NewModule(tmp, m.__codeBlock__, parent.__codeBlock__)
                SetAttr(parent.__codeBlock__.globalVariable, partname, tmp, parent.__codeBlock__)
        finally:
            if fp:
                fp.close()
        if parent:
            setattr(parent, partname, m)

        return m

    # load = process import statements and globalnames
    def load_module(self, fqname, fp, pathname, file_info):
        suffix, mode, type = file_info

        if type == _PKG_DIRECTORY:
            m = self.load_package(fqname, pathname)

            return m

        if type == _PY_SOURCE:
            m = self.add_module(fqname)
            m.__file__ = pathname
            tree = ast.parse(fp.read())
            m.__generator__ = ModuleCodeBlockGenerator(fqname, moduleManager=self)
            m.__codeBlock__ = m.__generator__.codeBlock
            m.__generator__.parse(tree)
            return m
        elif type == _PY_COMPILED:
            # try:
            #     data = fp.read()
            #     importlib._bootstrap_external._classify_pyc(data, fqname, {})
            # except ImportError as exc:

            #     raise
            # co = marshal.loads(memoryview(data)[16:])
            pass
            # m.__codeBlock__.done = True

        else:
            pass
            # m.__codeBlock__.done = True


    def _add_badmodule(self, name, caller):
        if name not in self.badmodules:
            self.badmodules[name] = {}
        if caller:
            self.badmodules[name][caller.__name__] = 1
        else:
            self.badmodules[name]["-"] = 1


    # name: from what module
    # caller: in which module
    # fromlist: import what names
    # no return
    def import_hook(self, name: str, caller: str, fromlist: list[str]=None, level: int=0) -> None:
        caller = caller and self.modules[caller]

        if name in self.badmodules:
            self._add_badmodule(name, caller)
            return
        try:
            self._import_hook(name, caller, fromlist, level=level)
        except ImportError as msg:

            self._add_badmodule(name, caller)
        except SyntaxError as msg:

            self._add_badmodule(name, caller)

    def load_package(self, fqname, pathname):

        m = self.add_module(fqname)
        m.__file__ = pathname
        m.__path__ = [pathname]

        fp, buf, stuff, _ = self.find_module("__init__", m.__path__)
        try:
            # the __init__ is treated as this package itself
            self.load_module(fqname, fp, buf, stuff)
            return m
        finally:
            if fp:
                fp.close()

    # add to self.modules: full quarlified name -> Module
    def add_module(self, fqname):
        if fqname in self.modules:
            return self.modules[fqname]
        self.modules[fqname] = m = Module(fqname)
        return m

    # parent is used when relative import
    # return file, module path, and other stuff
    def find_module(self, name, path, parent=None):
        if parent is not None:
            # assert path is not None
            fullname = parent.__name__+'.'+name
        else:
            fullname = name

        if path is None:
            if name in sys.builtin_module_names:
                return (None, None, ("", "", _C_BUILTIN))
            try:
                return *_find_module(name, self.cwd), False
                
            except ImportError:
                pass

            return *_find_module(name, self.externalPath), True
        else:
            return *_find_module(name, self.cwd), False
        

class ModuleNotFoundException(Exception):
    pass