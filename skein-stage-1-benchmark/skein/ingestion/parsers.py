from __future__ import annotations
import ast
import re
from abc import ABC, abstractmethod
from pathlib import Path
from .models import ParseResult, ParsedNode, ParsedEdge

class ParserPlugin(ABC):
    language: str
    extensions: tuple[str, ...]
    @abstractmethod
    def parse(self, path: Path, source: str) -> ParseResult: ...

class PythonTreeSitterParser(ParserPlugin):
    language = "python"; extensions = (".py",)
    def __init__(self) -> None:
        from tree_sitter import Parser
        import tree_sitter_python
        self._parser = Parser(tree_sitter_python.language())
    def parse(self, path: Path, source: str) -> ParseResult:
        tree=self._parser.parse(source.encode()); result=ParseResult([ParsedNode(f"file:{path.as_posix()}","File",{"path":path.as_posix(),"language":self.language})])
        functions={}; classes={}
        def text(n): return source.encode()[n.start_byte:n.end_byte].decode(errors="ignore")
        def walk(n, parent=None):
            if n.type in ("function_definition","async_function_definition"):
                nn=n.child_by_field_name("name")
                if nn:
                    name=text(nn); q=f"{parent}.{name}" if parent else name; fid=f"function:{path.as_posix()}:{q}"; functions[q]=fid
                    result.nodes.append(ParsedNode(fid,"Function",{"name":name,"qualified_name":q,"file":path.as_posix(),"line":n.start_point[0]+1}))
                    result.edges.append(ParsedEdge(fid,f"file:{path.as_posix()}","EXTRACTED","EXTRACTED",{"relationship":"CONTAINS"}))
            elif n.type=="class_definition":
                nn=n.child_by_field_name("name")
                if nn:
                    name=text(nn); cid=f"class:{path.as_posix()}:{name}"; classes[name]=cid
                    result.nodes.append(ParsedNode(cid,"Class",{"name":name,"file":path.as_posix(),"line":n.start_point[0]+1}))
                    result.edges.append(ParsedEdge(cid,f"file:{path.as_posix()}","EXTRACTED","EXTRACTED",{"relationship":"CONTAINS"}))
            for c in n.children: walk(c, text(n.child_by_field_name("name")) if n.type=="class_definition" and n.child_by_field_name("name") else parent)
        walk(tree.root_node)
        for q,fid in functions.items():
            node=next(n for n in result.nodes if n.id==fid); body="\n".join(source.splitlines()[node.attributes["line"]-1:node.attributes["line"]+120])
            for callee in re.findall(r"\b([A-Za-z_]\w*)\s*\(",body):
                target=next((x for name,x in functions.items() if name.split(".")[-1]==callee and x!=fid),None)
                if target:
                    result.edges.append(ParsedEdge(fid,target,"CALLS","EXTRACTED",{"symbol":callee}))
                else:
                    result.edges.append(ParsedEdge(fid,f"symbol:{callee}","CALLS","INFERRED",{"symbol":callee,"unresolved":True}))
        for n in tree.root_node.children:
            if n.type=="import_statement": result.edges.append(ParsedEdge(f"file:{path.as_posix()}",f"module:{text(n)}","IMPORTS","EXTRACTED",{"statement":text(n)}))
            elif n.type=="import_from_statement": result.edges.append(ParsedEdge(f"file:{path.as_posix()}",f"module:{text(n)}","IMPORTS","EXTRACTED",{"statement":text(n)}))
        return result

class JavaScriptTreeSitterParser(ParserPlugin):
    language="javascript"; extensions=(".js",".jsx")
    def __init__(self):
        from tree_sitter import Parser
        import tree_sitter_javascript
        self._parser=Parser(tree_sitter_javascript.language())
    def parse(self,path:Path,source:str)->ParseResult:
        tree=self._parser.parse(source.encode()); result=ParseResult([ParsedNode(f"file:{path.as_posix()}","File",{"path":path.as_posix(),"language":self.language})]); funcs={}
        def txt(n): return source.encode()[n.start_byte:n.end_byte].decode(errors="ignore")
        def walk(n):
            if n.type in ("function_declaration","method_definition"):
                nn=n.child_by_field_name("name")
                if nn:
                    name=txt(nn); fid=f"function:{path.as_posix()}:{name}"; funcs[name]=fid; result.nodes.append(ParsedNode(fid,"Function",{"name":name,"qualified_name":name,"file":path.as_posix(),"line":n.start_point[0]+1})); result.edges.append(ParsedEdge(fid,f"file:{path.as_posix()}","EXTRACTED","EXTRACTED",{"relationship":"CONTAINS"}))
            elif n.type=="class_declaration":
                nn=n.child_by_field_name("name")
                if nn:
                    name=txt(nn); cid=f"class:{path.as_posix()}:{name}"; result.nodes.append(ParsedNode(cid,"Class",{"name":name,"file":path.as_posix(),"line":n.start_point[0]+1})); result.edges.append(ParsedEdge(cid,f"file:{path.as_posix()}","EXTRACTED","EXTRACTED",{"relationship":"CONTAINS"}))
            elif n.type=="import_statement": result.edges.append(ParsedEdge(f"file:{path.as_posix()}",f"module:{txt(n)}","IMPORTS","EXTRACTED",{"statement":txt(n)}))
            for c in n.children: walk(c)
        walk(tree.root_node)
        for name,fid in funcs.items():
            for callee in re.findall(r"\b([A-Za-z_$][\w$]*)\s*\(",source):
                if callee in funcs and callee!=name:
                    result.edges.append(ParsedEdge(fid,funcs[callee],"CALLS","EXTRACTED",{"symbol":callee}))
                elif callee != name:
                    result.edges.append(ParsedEdge(fid,f"symbol:{callee}","CALLS","INFERRED",{"symbol":callee,"unresolved":True}))
        return result

class TypeScriptTreeSitterParser(JavaScriptTreeSitterParser):
    language="typescript"; extensions=(".ts",".tsx")
    def __init__(self):
        from tree_sitter import Parser
        import tree_sitter_typescript
        self._parser=Parser(tree_sitter_typescript.language_tsx())

class PythonAstFallbackParser(ParserPlugin):
    language="python"; extensions=(".py",)
    def parse(self,path:Path,source:str)->ParseResult:
        tree=ast.parse(source,filename=str(path)); result=ParseResult([ParsedNode(f"file:{path.as_posix()}","File",{"path":path.as_posix(),"language":self.language})]); funcs={}
        for node in ast.walk(tree):
            if isinstance(node,ast.ClassDef):
                cid=f"class:{path.as_posix()}:{node.name}"; result.nodes.append(ParsedNode(cid,"Class",{"name":node.name,"file":path.as_posix(),"line":node.lineno})); result.edges.append(ParsedEdge(cid,f"file:{path.as_posix()}","EXTRACTED","EXTRACTED",{"relationship":"CONTAINS"}))
            elif isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)):
                fid=f"function:{path.as_posix()}:{node.name}"; funcs[node.name]=fid; result.nodes.append(ParsedNode(fid,"Function",{"name":node.name,"qualified_name":node.name,"file":path.as_posix(),"line":node.lineno})); result.edges.append(ParsedEdge(fid,f"file:{path.as_posix()}","EXTRACTED","EXTRACTED",{"relationship":"CONTAINS"}))
        for node in ast.walk(tree):
            if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)) and node.name in funcs:
                for call in ast.walk(node):
                    if not isinstance(call, ast.Call):
                        continue
                    if isinstance(call.func, ast.Name):
                        callee = call.func.id
                    elif isinstance(call.func, ast.Attribute):
                        callee = call.func.attr
                    else:
                        continue
                    if callee == node.name:
                        continue
                    if callee in funcs:
                        result.edges.append(ParsedEdge(funcs[node.name],funcs[callee],"CALLS","EXTRACTED",{"symbol":callee}))
                    else:
                        result.edges.append(ParsedEdge(funcs[node.name],f"symbol:{callee}","CALLS","INFERRED",{"symbol":callee,"unresolved":True}))
            elif isinstance(node,ast.Import):
                for alias in node.names: result.edges.append(ParsedEdge(f"file:{path.as_posix()}",f"module:{alias.name}","IMPORTS","EXTRACTED",{"module":alias.name}))
            elif isinstance(node,ast.ImportFrom) and node.module: result.edges.append(ParsedEdge(f"file:{path.as_posix()}",f"module:{node.module}","IMPORTS","EXTRACTED",{"module":node.module}))
        return result

class HeuristicSourceParser(ParserPlugin):
    language="javascript"; extensions=(".js",".jsx",".ts",".tsx")
    def parse(self,path:Path,source:str)->ParseResult:
        result=ParseResult([ParsedNode(f"file:{path.as_posix()}","File",{"path":path.as_posix(),"language":self.language})]); funcs={}
        for m in re.finditer(r"(?:function|async function)\s+([A-Za-z_$][\w$]*)\s*\(|(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>",source):
            name=m.group(1) or m.group(2); fid=f"function:{path.as_posix()}:{name}"; funcs[name]=fid; result.nodes.append(ParsedNode(fid,"Function",{"name":name,"qualified_name":name,"file":path.as_posix(),"line":source.count("\n",0,m.start())+1})); result.edges.append(ParsedEdge(fid,f"file:{path.as_posix()}","EXTRACTED","EXTRACTED",{"relationship":"CONTAINS"}))
        for m in re.finditer(r"(?:import .*? from\s+|require\()\s*['\"]([^'\"]+)",source): result.edges.append(ParsedEdge(f"file:{path.as_posix()}",f"module:{m.group(1)}","IMPORTS","EXTRACTED",{"module":m.group(1)}))
        for name,fid in funcs.items():
            for callee in re.findall(r"\b([A-Za-z_$][\w$]*)\s*\(",source):
                if callee in funcs and callee!=name:
                    result.edges.append(ParsedEdge(fid,funcs[callee],"CALLS","EXTRACTED",{"symbol":callee}))
                elif callee != name:
                    result.edges.append(ParsedEdge(fid,f"symbol:{callee}","CALLS","INFERRED",{"symbol":callee,"unresolved":True}))
        return result

class ParserRegistry:
    def __init__(self):
        self.parsers=[]
        for cls,fallback in ((PythonTreeSitterParser,PythonAstFallbackParser),(JavaScriptTreeSitterParser,HeuristicSourceParser),(TypeScriptTreeSitterParser,HeuristicSourceParser)):
            try: self.parsers.append(cls())
            except ImportError: self.parsers.append(fallback())
    def for_path(self,path:Path)->ParserPlugin|None: return next((p for p in self.parsers if path.suffix.lower() in p.extensions),None)
