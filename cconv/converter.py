from __future__ import annotations

import re
from typing import Dict, List, Tuple, Optional, Set


# Basic regex helpers
_include_stdio = re.compile(r"^\s*#\s*include\s*<stdio\.h>\s*$", re.MULTILINE)
_include_iostream = re.compile(r"^\s*#\s*include\s*<iostream>\s*$", re.MULTILINE)
_include_stdlib = re.compile(r"^\s*#\s*include\s*<stdlib\.h>\s*$", re.MULTILINE)


def _collect_typedefs(code: str) -> Dict[str, str]:
    """Collect simple typedefs and struct aliases.
    Examples:
      typedef struct Node Node;
      typedef struct Node { ... } Node;
      typedef int i32;
    Returns alias->base-type string (e.g., 'Node'->'struct Node', 'i32'->'int').
    """
    tdefs: Dict[str, str] = {}
    # typedef struct Name Alias;
    for m in re.finditer(r"typedef\s+struct\s+([A-Za-z_]\w*)\s+([A-Za-z_]\w*)\s*;", code):
        base, alias = m.group(1), m.group(2)
        tdefs[alias] = f"struct {base}"
    # typedef struct Name { ... } Alias;
    for m in re.finditer(r"typedef\s+struct\s+([A-Za-z_]\w*)\s*\{[^}]*\}\s*([A-Za-z_]\w*)\s*;", code, re.DOTALL):
        base, alias = m.group(1), m.group(2)
        tdefs[alias] = f"struct {base}"
    # typedef base Alias;
    for m in re.finditer(r"typedef\s+((?:struct\s+)?[A-Za-z_]\w*)\s+([A-Za-z_]\w*)\s*;", code):
        base, alias = m.group(1), m.group(2)
        tdefs.setdefault(alias, base)
    return tdefs


def _infer_decl_types(code: str) -> Dict[str, str]:
    """Infer simple variable types including primitives, struct types, and typedef aliases.
    Returns var->ctype; pointer stars included if declared as pointer.
    """
    types: Dict[str, str] = {}
    typedefs = _collect_typedefs(code)
    # discover declared struct names to accept 'struct Name'
    struct_names = set(re.findall(r"struct\s+([A-Za-z_]\w*)\s*\{", code))

    # Build a set of acceptable type tokens
    base_types = {"int", "long", "float", "double", "char", *{f"struct {s}" for s in struct_names}, *set(typedefs.keys())}

    # Match lines like: TYPE declarators;
    decl_re = re.compile(r"^(?P<type>(?:struct\s+)?[A-Za-z_]\w*)\s+(?P<rest>[^;]+);", re.MULTILINE)
    for m in decl_re.finditer(code):
        t = m.group("type")
        if t not in base_types:
            # also allow typedef that maps to struct/base
            if t in typedefs or t.startswith("struct "):
                pass
            else:
                continue
        rest = m.group("rest")
        parts = [p.strip() for p in rest.split(",")]
        for p in parts:
            # remove initial stars near name
            stars = 0
            q = p
            while q.startswith("*"):
                stars += 1
                q = q[1:].lstrip()
            name_match = re.match(r"([A-Za-z_][A-Za-z0-9_]*)", q)
            if not name_match:
                continue
            name = name_match.group(1)
            base = typedefs.get(t, t)
            ctype = base + ("*" * stars)
            types[name] = ctype
    return types


def _fmt_for_type(ctype: str) -> str:
    base = ctype.replace("*", "")
    return {
        "int": "%d",
        "long": "%ld",
        "float": "%f",
        "double": "%lf",
        "char": "%c",
        "char*": "%s",
    }.get(ctype, {
        "int": "%d",
        "long": "%ld",
        "float": "%f",
        "double": "%lf",
        "char": "%c",
    }.get(base, "%d"))


def _expr_ctype(expr: str, types: Dict[str, str]) -> Optional[str]:
    expr = expr.strip()
    # var
    m = re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", expr)
    if m:
        return types.get(expr)
    # *var or *(var)
    m = re.fullmatch(r"\*\s*\(?\s*([A-Za-z_][A-Za-z0-9_]*)\s*\)?", expr)
    if m:
        v = m.group(1)
        t = types.get(v)
        if t and t.endswith("*"):
            return t[:-1]
        return None
    # arr[i] or *(arr + i)
    m = re.fullmatch(r"([A-Za-z_][A-Za-z0-9_]*)\s*\[.+\]", expr)
    if m:
        v = m.group(1)
        t = types.get(v)
        if t and t.endswith("*"):
            return t[:-1]
        return None
    return None


def _split_printf_args(args: str) -> List[str]:
    # naive split by commas not inside quotes
    parts: List[str] = []
    buf = []
    q = None
    depth = 0
    for ch in args:
        if ch in ('"', "'"):
            if q is None:
                q = ch
            elif q == ch:
                q = None
            buf.append(ch)
        elif ch == '(' and q is None:
            depth += 1
            buf.append(ch)
        elif ch == ')' and q is None and depth > 0:
            depth -= 1
            buf.append(ch)
        elif ch == ',' and q is None and depth == 0:
            parts.append(''.join(buf).strip())
            buf = []
        else:
            buf.append(ch)
    if buf:
        parts.append(''.join(buf).strip())
    return parts


def _convert_printf_to_cout(call: str) -> str:
    # call like: printf("x=%d\n", x);
    m = re.match(r"printf\s*\((.*)\)\s*;\s*", call, re.DOTALL)
    if not m:
        return call
    args = _split_printf_args(m.group(1))
    if not args:
        return call
    fmt = args[0]
    if not (fmt.startswith('"') or fmt.startswith("'")):
        return call
    fmt_str = fmt.strip().strip('"')
    out = "std::cout"
    # replace format specifiers with stream insertions
    specs = re.findall(r"%[0-9]*\.?[0-9]*[dlfcsg]", fmt_str)
    # Split on specifiers to interleave literals and vars
    tokens = re.split(r"(%[0-9]*\.?[0-9]*[dlfcsg])", fmt_str)
    var_iter = iter(args[1:])
    newline = False
    for tok in tokens:
        if tok == '':
            continue
        if tok.startswith('%'):
            v = next(var_iter, None)
            if v is None:
                out += " << \"%s\"" % tok
            else:
                out += " << (" + v + ")"
        else:
            if tok.endswith("\\n"):
                tok = tok[:-2]
                newline = True
            if tok:
                out += " << \"" + tok.replace("\\", "\\\\").replace("\"", "\\\"") + "\""
    if newline:
        out += " << std::endl"
    return out + ";"


def _convert_scanf_to_cin(call: str, types: Dict[str, str]) -> str:
    # scanf("%d %f", &x, &y);
    m = re.match(r"scanf\s*\((.*)\)\s*;\s*", call, re.DOTALL)
    if not m:
        return call
    args = _split_printf_args(m.group(1))
    if not args:
        return call
    fmt = args[0]
    if not (fmt.startswith('"') or fmt.startswith("'")):
        return call
    fmt_str = fmt.strip().strip('"')
    specs = re.findall(r"%[0-9]*\.?[0-9]*[dlfcs]", fmt_str)
    vars = [a.lstrip('&').strip() for a in args[1:]]
    out = "std::cin"
    # pair vars up to specs
    for i, v in enumerate(vars):
        out += " >> (" + v + ")"
    out += ";"
    return out


def _convert_new_delete_to_malloc_free(code: str) -> str:
    # new T[n] -> (T*)malloc(sizeof(T) * n)
    code = re.sub(r"new\s+([A-Za-z_][A-Za-z0-9_]*)\s*\[\s*([^\]]+)\s*\]",
                  r"(\1*)malloc(sizeof(\1) * (\2))", code)
    # new T -> (T*)malloc(sizeof(T))
    code = re.sub(r"new\s+([A-Za-z_][A-Za-z0-9_]*)\b(?!\s*\[)",
                  r"(\1*)malloc(sizeof(\1))", code)
    # delete[] p -> free(p)
    code = re.sub(r"delete\s*\[\s*\]\s*([A-Za-z_][A-Za-z0-9_]*)\s*;", r"free(\1);", code)
    # delete p -> free(p)
    code = re.sub(r"delete\s+([A-Za-z_][A-Za-z0-9_]*)\s*;", r"free(\1);", code)
    return code


def _convert_malloc_free_to_new_delete(code: str, types: Dict[str, str] | None = None) -> str:
    # Track array allocations for delete[]
    allocs: Dict[str, str] = {}
    types = types or {}

    # Avoid converting allocations for variables that use realloc
    realloc_names: Set[str] = set(re.findall(r"realloc\s*\(\s*([A-Za-z_][A-Za-z0-9_]*)\s*,", code))

    def repl_array(m: re.Match) -> str:
        name, T, n = m.group(1), m.group(2), m.group(3)
        if name in realloc_names:
            return m.group(0)
        allocs[name] = 'array'
        return f"{name} = new {T}[{n}];"

    def repl_scalar(m: re.Match) -> str:
        name, T = m.group(1), m.group(2)
        if name in realloc_names:
            return m.group(0)
        allocs[name] = 'scalar'
        return f"{name} = new {T};"

    # p = (T*)malloc(sizeof(T) * n) with optional 'struct'
    code = re.sub(
        r"([A-Za-z_][A-Za-z0-9_]*)\s*=\s*\(\s*(?:struct\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*\*\s*\)\s*malloc\s*\(\s*sizeof\(\s*(?:struct\s+)?\2\s*\)\s*\*\s*([^\)]+)\)\s*;",
        repl_array,
        code,
    )
    # p = (T*)malloc(sizeof(T)) with optional 'struct'
    code = re.sub(
        r"([A-Za-z_][A-Za-z0-9_]*)\s*=\s*\(\s*(?:struct\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*\*\s*\)\s*malloc\s*\(\s*sizeof\(\s*(?:struct\s+)?\2\s*\)\s*\)\s*;",
        repl_scalar,
        code,
    )

    # With sizeof(*p) forms (cast optional)
    def repl_sizeof_ptr(m: re.Match) -> str:
        name, T, n = m.group(1), m.group(2), m.group(3)
        if name in realloc_names:
            return m.group(0)
        # If cast type T missing, try from declared type map
        if not T:
            decl = types.get(name)
            if decl:
                base = decl.replace('*', '').replace(' ', '')
                T = base
        if not T:
            T = "int"  # fallback
        if n:
            allocs[name] = 'array'
            return f"{name} = new {T}[{n}];"
        else:
            allocs[name] = 'scalar'
            return f"{name} = new {T};"

    code = re.sub(
        r"([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(?:\(\s*(?:struct\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*\*\s*\)\s*)?malloc\s*\(\s*sizeof\s*\(\s*\*\s*\1\s*\)\s*(?:\*\s*([^\)]+))?\)\s*;",
        repl_sizeof_ptr,
        code,
    )

    # No-cast forms with explicit type on LHS: T* p = malloc(sizeof(T) * n) / sizeof(T)
    def repl_lhs_type_array(m: re.Match) -> str:
        T, name, n = m.group(1), m.group(2), m.group(3)
        if name in realloc_names:
            return m.group(0)
        allocs[name] = 'array'
        return f"{T}* {name} = new {T}[{n}];"

    def repl_lhs_type_scalar(m: re.Match) -> str:
        T, name = m.group(1), m.group(2)
        if name in realloc_names:
            return m.group(0)
        allocs[name] = 'scalar'
        return f"{T}* {name} = new {T};"

    code = re.sub(
        r"(?:^|;)\s*(?:struct\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*\*\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*malloc\s*\(\s*sizeof\(\s*(?:struct\s+)?\1\s*\)\s*\*\s*([^\)]+)\)\s*;",
        repl_lhs_type_array,
        code,
    )
    code = re.sub(
        r"(?:^|;)\s*(?:struct\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*\*\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*malloc\s*\(\s*sizeof\(\s*(?:struct\s+)?\1\s*\)\s*\)\s*;",
        repl_lhs_type_scalar,
        code,
    )

    # calloc forms: (T*)calloc(n, sizeof(T)) or calloc(1, sizeof(T)) and sizeof(*p)
    def repl_calloc_cast(m: re.Match) -> str:
        name, T, n = m.group(1), m.group(2), m.group(3)
        if name in realloc_names:
            return m.group(0)
        if n.strip() == '1':
            allocs[name] = 'scalar'
            return f"{name} = new {T};"
        else:
            allocs[name] = 'array'
            return f"{name} = new {T}[{n}];"

    code = re.sub(
        r"([A-Za-z_][A-Za-z0-9_]*)\s*=\s*\(\s*(?:struct\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*\*\s*\)\s*calloc\s*\(\s*([^,]+)\s*,\s*sizeof\(\s*(?:struct\s+)?\2\s*\)\s*\)\s*;",
        repl_calloc_cast,
        code,
    )

    def repl_calloc_sizeof_ptr(m: re.Match) -> str:
        name, n = m.group(1), m.group(2)
        if name in realloc_names:
            return m.group(0)
        decl = types.get(name, 'int')
        T = decl.replace('*', '').replace(' ', '') or 'int'
        if n.strip() == '1':
            allocs[name] = 'scalar'
            return f"{name} = new {T};"
        else:
            allocs[name] = 'array'
            return f"{name} = new {T}[{n}];"

    code = re.sub(
        r"([A-Za-z_][A-Za-z0-9_]*)\s*=\s*calloc\s*\(\s*([^,]+)\s*,\s*sizeof\(\s*\*\s*\1\s*\)\s*\)\s*;",
        repl_calloc_sizeof_ptr,
        code,
    )

    # free(p) -> delete or delete[]
    def repl_free(m: re.Match) -> str:
        name = m.group(1)
        kind = allocs.get(name)
        if kind == 'array':
            return f"delete[] {name};"
        return f"delete {name};"

    code = re.sub(r"free\s*\(\s*([A-Za-z_][A-Za-z0-9_]*)\s*\)\s*;", repl_free, code)
    return code


def convert_c_to_cpp(code: str) -> str:
    # includes
    if _include_stdio.search(code):
        code = _include_stdio.sub("#include <iostream>", code)
    # don't remove stdlib.h by default; harmless in C++

    # printf / scanf
    # convert line-by-line to keep semi-colons intact
    types = _infer_decl_types(code)
    lines = code.splitlines()
    out_lines: List[str] = []
    for ln in lines:
        l = ln
        l = re.sub(r"printf\s*\(.*?\)\s*;", lambda m: _convert_printf_to_cout(m.group(0)), l)
        l = re.sub(r"scanf\s*\(.*?\)\s*;", lambda m: _convert_scanf_to_cin(m.group(0), types), l)
        out_lines.append(l)
    code = "\n".join(out_lines)

    # malloc/free -> new/delete
    code = _convert_malloc_free_to_new_delete(code, types)

    # idiomatic C++ tweaks: remove 'struct' in pointer declarations/usages and use nullptr
    code = re.sub(r"\bstruct\s+([A-Za-z_][A-Za-z0-9_]*)\s*\*", r"\1*", code)
    code = re.sub(r"\bNULL\b", "nullptr", code)

    # add using namespace std? avoid; we use std:: prefixes.
    return code


def convert_cpp_to_c(code: str) -> str:
    # includes
    if _include_iostream.search(code):
        code = _include_iostream.sub("#include <stdio.h>\n#include <stdlib.h>", code)

    # std::cout / std::cin
    # Convert simple cout chains ending with optional std::endl
    def cout_repl(m: re.Match) -> str:
        expr = m.group(1)
        # break by '<<'
        parts = [p.strip() for p in re.split(r"<<", expr)]
        fmt: List[str] = []
        vs: List[str] = []
        for p in parts:
            if p == "std::endl":
                fmt.append("\\n")
            elif p.startswith('"'):
                lit = p.strip().strip('"')
                fmt.append(lit)
            else:
                vs.append(p)
                # Try to infer format based on a simple type map
                # Build a quick type map for current code
                tmap = _infer_decl_types(code)
                ctp = _expr_ctype(p, tmap)
                fmt.append(_fmt_for_type(ctp or "int"))
        fmt_str = "".join(fmt)
        # build printf call
        args = (", " + ", ".join(vs)) if vs else ""
        return f'printf("{fmt_str}"{args});'

    code = re.sub(r"std::cout\s*<<(.*?);", cout_repl, code)

    # std::cin >> x >> y;
    def cin_repl(m: re.Match) -> str:
        expr = m.group(1)
        vars = [p.strip() for p in re.split(r">>", expr)]
        # naive types: default to %d
        fmts = ["%d" for _ in vars]
        fmt = " ".join(fmts)
        vaddrs = ["&" + v for v in vars]
        args = ", ".join(vaddrs)
        return f'scanf("{fmt}", {args});'

    code = re.sub(r"std::cin\s*>>(.*?);", cin_repl, code)

    # nullptr, bool, true/false -> C equivalents
    code = re.sub(r"\bnullptr\b", "NULL", code)
    # Replace bool declarations with int (simple cases)
    code = re.sub(r"\bbool\b", "int", code)
    code = re.sub(r"\btrue\b", "1", code)
    code = re.sub(r"\bfalse\b", "0", code)

    # new/delete -> malloc/free
    code = _convert_new_delete_to_malloc_free(code)

    return code
