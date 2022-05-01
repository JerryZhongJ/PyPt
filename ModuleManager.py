"""This file is based on python3.9/modulefinder.py"""

import dis
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

# Note this is a mapping is lists of paths.
packagePathMap = {}

# A Public interface
def AddPackagePath(packagename, path):
    packagePathMap.setdefault(packagename, []).append(path)

replacePackageMap = {}

# This ReplacePackage mechanism allows modulefinder to work around
# situations in which a package injects itself under the name
# of another package into sys.modules at runtime by calling
# ReplacePackage("real_package_name", "faked_package_name")
# before running ModuleFinder.

def ReplacePackage(oldname, newname):
    replacePackageMap[oldname] = newname


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

    def __init__(self, verbose=False):
        self.path = sys.path
        self.modules = {}
        self.badmodules = {}
        self.indent = 0
        self.excludes = []
        self.verbose = verbose
        # self.replace_paths = replace_paths if replace_paths is not None else []
        self.processed_paths = []   # Used in debugging only
        self.entry = None

    def start(self, target, mode="script") -> None:
        
        if(mode == "script"):
            self.path[0] = os.path.dirname(target)
            try:
                with io.open_code(target) as fp:
                    stuff = ("", "rb", _PY_SOURCE)
                    # __main__ is a fully quarlified name
                    self.load_module('__main__', fp, target, stuff)
                    self.entry = "__main__"
            except(IOError):
                raise Exception(f"Can't open file {target}. Please check if the file exists.")

        elif(mode == "module"):
            try:
                self._import_hook(target, None)
                self.entry = target
            except(ImportError):
                raise Exception(f"Can't import {target}. Please check if this module exists.")
                return
            
            if(self.modules[target].__path__):
                try:
                    self._import_hook(target + ".__main__", None)
                    self.entry = target + ".__main__"
                except(ImportError):
                    raise Exception(f"{target} is a package, but {target}.__main__ can't be imported. Please check if it exists.")
           
    def getEntry(self):
        if(self.entry):
            return self.entry
        else:
            raise Exception("Please call start() first.")
            

    def getCodeBlock(self, name: str, callerName: str=None, level: int=0) -> CodeBlock:
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
            return ModuleCodeBlock(fqname)
        


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
    def find_head_package(self, parent, name):

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
            
        q = self.import_module(head, qname, parent)
        if q:

            return q, tail
        if parent:
            qname = head
            parent = None
            q = self.import_module(head, qname, parent)
            if q:

                return q, tail

        raise ImportError("No module named " + qname)

    # when the head is imported, import the rest, return the last module
    # TODO: add globalNames here
    def load_tail(self, q, tail):

        m = q
        while tail:
            i = tail.find('.')
            if i < 0: i = len(tail)
            head, tail = tail[:i], tail[i+1:]
            mname = "%s.%s" % (m.__name__, head)
            m = self.import_module(head, mname, m)
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
            print(f"\rImporting {fqname}                    ", end="")
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
            fp, pathname, stuff = self.find_module(partname,
                                                   parent and parent.__path__, parent)
        except ImportError:

            return None

        try:
            m = self.load_module(fqname, fp, pathname, stuff)
            if(parent):
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

        m = self.add_module(fqname)
        m.__file__ = pathname
        
        if type == _PY_SOURCE:
            
            tree = ast.parse(fp.read())
            m.__generator__ = ModuleCodeBlockGenerator(fqname, moduleManager=self)
            m.__codeBlock__ = m.__generator__.codeBlock
            m.__generator__.parse(tree)
        elif type == _PY_COMPILED:
            # try:
            #     data = fp.read()
            #     importlib._bootstrap_external._classify_pyc(data, fqname, {})
            # except ImportError as exc:

            #     raise
            # co = marshal.loads(memoryview(data)[16:])
            m.__codeBlock__ = ModuleCodeBlock(fqname)
            # m.__codeBlock__.done = True

        else:
            m.__codeBlock__ = ModuleCodeBlock(fqname)
            # m.__codeBlock__.done = True


        

        return m

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
        # else:
        #     if fromlist:
        #         for sub in fromlist:
        #             fullname = name + "." + sub
        #             if fullname in self.badmodules:
        #                 self._add_badmodule(fullname, caller)
        #                 continue
        #             try:
        #                 self._import_hook(name, caller, [sub], level=level)
        #             except ImportError as msg:

        #                 self._add_badmodule(fullname, caller)

    # def scan_opcodes(self, co):
    #     # Scan the code, and yield 'interesting' opcode combinations
    #     code = co.co_code
    #     names = co.co_names
    #     consts = co.co_consts
    #     # opargs = (op, arg)
    #     opargs = [(op, arg) for _, op, arg in dis._unpack_opargs(code)
    #               if op != EXTENDED_ARG]
    #     for i, (op, oparg) in enumerate(opargs):
    #         if op in STORE_OPS:
    #             yield "store", (names[oparg],)
    #             continue
    #         if (op == IMPORT_NAME and i >= 2
    #                 and opargs[i-1][0] == opargs[i-2][0] == LOAD_CONST):
    #             level = consts[opargs[i-2][1]]
    #             fromlist = consts[opargs[i-1][1]]
    #             if level == 0: # absolute import
    #                 yield "absolute_import", (fromlist, names[oparg])
    #             else: # relative import
    #                 yield "relative_import", (level, fromlist, names[oparg])
    #             continue

    # def scan_code(self, co, m):
        # code = co.co_code
        # scanner = self.scan_opcodes
        # for what, args in scanner(co):
        #     if what == "store":
        #         name, = args
        #         m.globalnames[name] = 1
        #     elif what == "absolute_import":
        #         fromlist, name = args
        #         have_star = 0
        #         if fromlist is not None:
        #             if "*" in fromlist:
        #                 have_star = 1
        #             fromlist = [f for f in fromlist if f != "*"]
        #         self.import_hook(name, m, fromlist, level=0)
        #         if have_star:
        #             # We've encountered an "import *". If it is a Python module,
        #             # the code has already been parsed and we can suck out the
        #             # global names.
        #             mm = None
        #             if m.__path__:
        #                 # At this point we don't know whether 'name' is a
        #                 # submodule of 'm' or a global module. Let's just try
        #                 # the full name first.
        #                 mm = self.modules.get(m.__name__ + "." + name)
        #             if mm is None:
        #                 mm = self.modules.get(name)
        #             if mm is not None:
        #                 m.globalnames.update(mm.globalnames)
        #                 m.starimports.update(mm.starimports)
        #                 if mm.__code__ is None:
        #                     m.starimports[name] = 1
        #             else:
        #                 m.starimports[name] = 1
        #     elif what == "relative_import":
        #         level, fromlist, name = args
        #         if name:
        #             self.import_hook(name, m, fromlist, level=level)
        #         else:
        #             parent = self.determine_parent(m, level=level)
        #             self.import_hook(parent.__name__, None, fromlist, level=0)
        #     else:
        #         # We don't expect anything else from the generator.
        #         raise RuntimeError(what)

        # for c in co.co_consts:
        #     if isinstance(c, type(co)):
        #         self.scan_code(c, m)

    def load_package(self, fqname, pathname):

        newname = replacePackageMap.get(fqname)
        if newname:
            fqname = newname
        m = self.add_module(fqname)
        m.__file__ = pathname
        m.__path__ = [pathname]

        # As per comment at top of file, simulate runtime __path__ additions.
        m.__path__ = m.__path__ + packagePathMap.get(fqname, [])

        fp, buf, stuff = self.find_module("__init__", m.__path__)
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
        if fullname in self.excludes:

            raise ImportError(name)

        if path is None:
            if name in sys.builtin_module_names:
                return (None, None, ("", "", _C_BUILTIN))

            path = self.path

        return _find_module(name, path)
