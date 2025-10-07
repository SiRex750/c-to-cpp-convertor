# Developer Guide: Understanding `cconv/converter.py`

This guide explains how the converter works so you can modify it or build a similar source-to-source transformer without relying on AI. It focuses on the design, the key regex patterns, and the Python techniques you’ll reuse.

## Big picture

- The converter is a stateless, text-to-text transformer focused on common DSA-style C/C++ code.
- Two public entry points:
  - `convert_c_to_cpp(code: str) -> str`
  - `convert_cpp_to_c(code: str) -> str`
- Each function runs a small pipeline of regex-based passes:
  1) Fix includes
  2) Translate I/O (printf/scanf ↔ std::cout/std::cin)
  3) Translate memory management (malloc/calloc/free ↔ new/delete[/[]])
  4) Apply small idiomatic tweaks (e.g., `NULL` ↔ `nullptr`, remove `struct` qualifiers)
- No full parser/AST. Heuristics + careful guardrails make it practical for typical contest/DSA code.

```
C code ──includes──▶ I/O ──▶ alloc ──▶ idioms ──▶ C++ code
C++ code ──includes──▶ I/O ──▶ alloc ──▶ idioms ──▶ C code
```

## Helper building blocks

### 1) Typedef and declaration inference
- `_collect_typedefs(code) -> Dict[str, str]`
  - Scans `typedef ... Alias;` forms.
  - Maps aliases to their base types, including `typedef struct Node Node;` and inline struct typedefs.
- `_infer_decl_types(code) -> Dict[str, str]`
  - Builds a map of `var -> ctype` by scanning simple declarations like `int *p, x;` or `struct Node* head;`.
  - Handles pointer asterisks near names (counts `*` prefixing each declarator).
  - Resolves typedef aliases to understand the base type.
- Why it matters: I/O and memory conversions sometimes need the type (e.g., choosing `%d` or `%lf`, converting `sizeof(*p)` to `new T[...]`).

### 2) Expression type guesses
- `_expr_ctype(expr, types) -> Optional[str]`
  - Given a small expression (e.g., `x`, `*p`, `arr[i]`), guess its C type from the inferred map.
  - Used when converting `std::cout` chains to `printf` to pick proper format specifiers.

### 3) Format helpers
- `_fmt_for_type(ctype) -> str` maps C types to printf formats (`int → %d`, `double → %lf`, `char* → %s`, etc.).

### 4) Utility: `_split_printf_args`
- Splits `printf("x=%d y=%f", x, y)` into top-level arguments without being confused by commas inside parentheses or quotes.

## I/O conversions

### `printf` → `std::cout`
- `_convert_printf_to_cout(call: str) -> str`
  - Extracts the format string and the value arguments.
  - Splits the format string at specifiers (e.g., `%d`, `%f`) and interleaves string literals with variables using `<<`.
  - Handles trailing `\n` as `<< std::endl`.
  - Example: `printf("x=%d\n", x);` → `std::cout << "x=" << (x) << std::endl;`

### `scanf` → `std::cin`
- `_convert_scanf_to_cin(call: str, types)`
  - Reads the format and variables, strips leading `&`, and connects them with `>>`.
  - Example: `scanf("%d %f", &i, &f);` → `std::cin >> (i) >> (f);`

### `std::cout` → `printf`
- In `convert_cpp_to_c`, a regex captures `std::cout << ...;` lines.
- Splits on `<<` into parts, constructs a format string (string literals are concatenated; expressions become type-driven specifiers), and emits one `printf`.
- Example: `std::cout << "x=" << x << std::endl;` → `printf("x=%d\n", x);`

### `std::cin` → `scanf`
- Similar approach: `std::cin >> a >> b;` → `scanf("%d %d", &a, &b);`

## Memory conversions

### C → C++ (`malloc/calloc/free` → `new/delete`)
- Implemented in `_convert_malloc_free_to_new_delete(code, types)`.
- Goals:
  - Support multiple forms: with/without casts, `sizeof(T)` vs `sizeof(*p)`, lhs typed declarations, `calloc`.
  - Track which variables were allocated as arrays vs scalars to choose `delete[]` vs `delete` later.
  - Never rewrite allocations for names that use `realloc` (guardrail).
- Strategy:
  - A series of `re.sub(pattern, repl_func, code)` passes. Each `repl_func` gets match groups and returns the transformed line.
  - Save `allocs[name] = 'array' | 'scalar'` during allocation passes; consult it when rewriting `free(name)`.
- Examples:
  - `p = (T*)malloc(sizeof(T) * n);` → `p = new T[n];`
  - `T* p = malloc(sizeof(T));` → `T* p = new T;`
  - `p = malloc(sizeof(*p));` (type inferred from declarations) → `p = new T;`
  - `p = calloc(n, sizeof(T));` → `p = new T[n];`
  - `free(p);` → `delete p;` or `delete[] p;` depending on how `p` was allocated.

### C++ → C (`new/delete` → `malloc/free`)
- `_convert_new_delete_to_malloc_free(code)` handles simple scalar/array `new` and `delete`.
- Examples:
  - `p = new T;` → `p = (T*)malloc(sizeof(T));`
  - `p = new T[n];` → `p = (T*)malloc(sizeof(T) * n);`
  - `delete p;` → `free(p);`, `delete[] p;` → `free(p);`

## Idiomatic tweaks

- C → C++: remove `struct` in pointer types (C++ doesn’t require it), replace `NULL` with `nullptr`.
- C++ → C: map `bool → int`, `true/false → 1/0`, `nullptr → NULL`.

## Python techniques you’ll reuse

- Regex basics used here:
  - Raw strings: `r"^\s*#include"` avoid escaping backslashes twice.
  - Flags: `re.MULTILINE` makes `^`/`$` match line starts/ends. `re.DOTALL` lets `.` span newlines.
  - Groups: `(`...`)` capture; `(?:...)` non-capturing; `?P<name>` named groups.
  - Backrefs in replacements: `\1`, `\2` refer to captured groups. When using a function as the replacement, access via `m.group(n)`.
- `re.sub` with a function:
  - Pattern matches → your function receives a `Match` → return the new string.
  - Lets you compute context-aware replacements (e.g., array vs scalar, looking up `types[name]`).
- String assembly patterns:
  - Build outputs incrementally (e.g., `out = "std::cout"; out += ...`).
  - Use `f"{var}"` for readability.
- Collections idioms:
  - Dicts/sets for fast lookups (`typedef` map, `allocs`, `realloc_names`).
  - List comprehensions and `split`/`join` to transform token lists.
- Defensive passes:
  - Work line-by-line when semicolons/newlines matter (I/O calls) to avoid over-greedy regex across multiple statements.

## How to extend it yourself

1) Decide the transformation stage it belongs to: includes, I/O, memory, or idioms.
2) Write 1–2 targeted regexes. Keep them narrow; prefer multiple simple passes over one giant pattern.
3) Add guardrails (like the `realloc` skip) to avoid unsafe rewrites.
4) Create 2–3 small examples and verify by compiling/running.

Examples you can try:
- Add `fprintf`/`fscanf` support for `stdout`/`stdin` cases.
- Handle `using namespace std;` by allowing `cout`/`cin` without the `std::` prefix.
- Improve `cout→printf` format detection (e.g., detect `double` via declarations more robustly).

## Common pitfalls (and how this code avoids them)

- Over-greedy matches across lines → use line-by-line for I/O and `re.DOTALL` only when needed.
- `realloc` semantics → skip converting names that use `realloc`.
- Pointer vs scalar delete → track allocations and choose `delete[]` accordingly.
- Struct-qualified typedefs → treat `typedef struct T T;` properly for type inference.

## Quick reference: patterns at a glance

- Includes: `^\s*#\s*include\s*<stdio\.h>` ↔ `^\s*#\s*include\s*<iostream>`
- `printf(...)` one-liner: `re.sub(r"printf\s*\(.*?\)\s*;", func, line)`
- `std::cout << ...;`: `re.sub(r"std::cout\s*<<(.*?);", func, code)`
- Malloc array (casted): `p = (T*)malloc(sizeof(T) * n);`
- Malloc scalar (casted): `p = (T*)malloc(sizeof(T));`
- Malloc with `sizeof(*p)`: `p = malloc(sizeof(*p) * n);`
- LHS typed forms: `T* p = malloc(sizeof(T) * n);`
- Calloc: `p = (T*)calloc(n, sizeof(T));`
- Free: `free(p);` → `delete p;` or `delete[] p;`

## Mental model to carry with you

- Think of your converter as a pipeline of small, deterministic text rewrites.
- Each pass should:
  - Match narrowly and predictably.
  - Do one job and leave the rest unchanged.
  - Be order-aware (I/O before memory, or vice versa, depending on needs) and idempotent if possible.
- Favor clarity over cleverness: several simple passes > one complex regex.
- Add tests early; compile the outputs when possible.

## Resources

- Python `re` docs: https://docs.python.org/3/library/re.html
- Quick regex testing: https://regex101.com
- C/C++ format specifiers cheat sheet (printf/scanf): `man 3 printf`, `man 3 scanf`
