# C <-> C++ Converter (heuristic)

A lightweight Python CLI that converts C code to C++ and C++ back to C using practical heuristics. It focuses on common patterns:

- printf/scanf ↔ std::cout/std::cin (basic format/stream conversions)
- malloc/free ↔ new/delete (tracks array vs scalar when detectable)
- Header swaps: stdio.h/stdlib.h ↔ iostream
- Simple type inference to pick printf/scanf format specifiers

Limitations: This is not a full compiler or parser. It won’t handle every corner case (templates, complex macros, custom i/o, advanced formatting, complex pointer arithmetic, etc.). It’s intended as a best-effort helper for straightforward code. Always review the output.

## Install

No dependencies beyond Python 3.8+.

## Usage

You can run the tool directly as a module:

```bash
python -m cconv --to cpp examples/example_c.c -o out.cpp
python -m cconv --to c   examples/example_cpp.cpp -o out.c
```

Options:
- --to {c,cpp}  Target language. If omitted, inferred from the output extension.
- -o / --output Output file path. If omitted, prints to stdout.
- -              Reads from stdin when input path is '-'.

## What it converts

- C → C++
  - `#include <stdio.h>` → `#include <iostream>`
  - `printf(...)` → `std::cout << ... << std::endl` (common specifiers: %d, %ld, %f, %lf, %c, %s)
  - `scanf(...)` → `std::cin >> ...` (common specifiers)
  - `malloc(sizeof(T) * n)` → `new T[n]`
  - `malloc(sizeof(T))` → `new T`
  - `free(p)` → `delete p` or `delete[] p` when previous allocation detected as array
  - SLL patterns: `(struct Node*)malloc(sizeof(struct Node))` → `new Node`; `struct Node*` → `Node*`; `NULL` → `nullptr`

- C++ → C
  - `#include <iostream>` → `#include <stdio.h>` (+ `#include <stdlib.h>` when needed)
  - `std::cout << ...` (+ `std::endl`) → `printf("...%d...\n", vars...)` when inferable
  - `std::cin >> x >> y` → `scanf("%d %d", &x, &y)` (basic types)
  - `new T[n]` → `(T*)malloc(sizeof(T) * n)`
  - `new T` → `(T*)malloc(sizeof(T))`
  - `delete p` / `delete[] p` → `free(p)`
  - `nullptr`/`bool`/`true`/`false` → `NULL`/`int`/`1`/`0`

## Caveats & tips

- Complex `printf`/`scanf` formats or chained `cout` with mixed types/expressions may need manual fixing.
- We do basic type tracking from simple declarations to choose `%d/%ld/%f/%lf/%c/%s`.
- We don’t convert C++ strings, iostream manipulators, templates, exceptions, or STL.
- Always compile and test after conversion.

## Examples

See `examples/` for minimal inputs and the expected flavor of outputs. Includes a singly linked list example (`examples/sll_c.c`).

## License

MIT

## Web app UI

You can also use a simple web UI (Flask) to convert code in the browser.

Run locally:

```bash
python3 -m pip install --user -r requirements.txt
python3 webapp/app.py
# then open http://localhost:8000
```

Features:
- Paste code, choose C → C++ or C++ → C, view output instantly
- Optional download of the result as a file
- Health check at `/healthz`

Files:
- `webapp/app.py` — Flask server
- `webapp/templates/index.html` — Minimal UI (responsive)

## GitHub Pages (no server)

This repo also includes a static site that runs the converter in your browser via Pyodide.

Live demo (after Pages is enabled):
- https://SiRex750.github.io/c-to-cpp-convertor/

Enable Pages:
1. Open your repo Settings → Pages
2. Under "Build and deployment":
  - Source: Deploy from a branch
  - Branch: `main`
  - Folder: `/docs`
3. Save and wait ~1–2 minutes for deployment

Static site files:
- `docs/index.html` — UI
- `docs/cconv_py/` — Python converter files used by Pyodide
- `docs/.nojekyll` — ensures GitHub Pages serves files as-is