import argparse
import sys
from .converter import convert_c_to_cpp, convert_cpp_to_c


def main(argv=None):
    p = argparse.ArgumentParser(description="C <-> C++ heuristic converter")
    p.add_argument("input", help="Input file path or '-' for stdin")
    p.add_argument("-o", "--output", help="Output file path; default stdout")
    p.add_argument("--to", choices=["c", "cpp"], help="Target language")
    args = p.parse_args(argv)

    # read input
    if args.input == "-":
        code = sys.stdin.read()
        in_ext = None
    else:
        with open(args.input, "r", encoding="utf-8") as f:
            code = f.read()
        in_ext = args.input.split(".")[-1].lower() if "." in args.input else None

    # decide direction
    target = args.to
    if target is None and args.output:
        out_ext = args.output.split(".")[-1].lower()
        if out_ext in ("c",):
            target = "c"
        elif out_ext in ("cc", "cpp", "cxx", "hpp", "hh", "hxx"):
            target = "cpp"
    if target is None:
        # fallback: infer from input ext
        if in_ext in ("c",):
            target = "cpp"
        else:
            target = "c"

    if target == "cpp":
        out_code = convert_c_to_cpp(code)
    else:
        out_code = convert_cpp_to_c(code)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(out_code)
    else:
        sys.stdout.write(out_code)


if __name__ == "__main__":
    main()
