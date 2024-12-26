import os
import clang.cindex
from pycparser import c_parser, c_ast
import subprocess

# Step 1: Define the pycparser-based analyzer
class SemanticErrorChecker(c_ast.NodeVisitor):
    def __init__(self):
        self.defined_vars = {}  # {var_name: used_status}
        self.function_signatures = {}  # {function_name: arg_count}
        self.errors = []

    def visit_Decl(self, node):
        if isinstance(node.type, c_ast.TypeDecl):
            self.defined_vars[node.name] = False  # False = not used
        elif isinstance(node.type, c_ast.FuncDecl):
            func_name = node.name
            arg_count = len(node.type.args.params) if node.type.args else 0
            self.function_signatures[func_name] = arg_count
        self.generic_visit(node)

    def visit_ID(self, node):
        var_name = node.name
        if var_name in self.defined_vars:
            self.defined_vars[var_name] = True
        else:
            self.errors.append(f"Error: Variable '{var_name}' used before declaration.")
        self.generic_visit(node)

    def visit_FuncCall(self, node):
        if isinstance(node.name, c_ast.ID):
            func_name = node.name.name
            if func_name in self.function_signatures:
                expected_args = self.function_signatures[func_name]
                actual_args = len(node.args.exprs) if node.args and node.args.exprs else 0
                if actual_args != expected_args:
                    self.errors.append(
                        f"Error: Function '{func_name}' called with {actual_args} arguments (expected {expected_args})."
                    )
        self.generic_visit(node)

    def check_unused_vars(self):
        unused_vars = [var for var, used in self.defined_vars.items() if not used]
        self.errors.extend([f"Warning: Variable '{var}' defined but never used." for var in unused_vars])

    def check_code(self, code):
        try:
            parser = c_parser.CParser()
            ast = parser.parse(code)
            self.visit(ast)
            self.check_unused_vars()
            return self.errors
        except Exception as e:
            return [f"Error in parsing code with pycparser: {e}"]

# Step 2: Define the Clang-based analyzer
def clang_analysis(file):
    # Set up Clang with the path to libclang
    clang.cindex.Config.set_library_file('C:/Program Files/LLVM/bin/libclang.dll')  # Update with your path
    index = clang.cindex.Index.create()

    # Parse the C file
    translation_unit = index.parse(file, args=["-Wall", "-fsyntax-only"])

    errors = []

    def traverse_ast(node):
        """Traverse the AST and look for undeclared identifiers."""
        if node.kind == clang.cindex.CursorKind.DECL_REF_EXPR:
            # Check if the referenced declaration exists
            decl = node.referenced
            if decl is None:
                errors.append(f"UNDEFINED_VARIABLE: Variable '{node.display_name}' used before declaration. Location: {node.location}")

        # Recursively check the children of the node
        for child in node.get_children():
            traverse_ast(child)

    # Traverse the AST from the root
    traverse_ast(translation_unit.cursor)

    return errors

# Step 3: Preprocess the C file for pycparser
def preprocess_code(file_path, include_dirs=None):
    try:
        clang_flags = [
             "-fms-extensions",  # Enable MSVC-specific extensions
            # "-fms-compatibility",  # Enable MSVC compatibility mode
            # "-fms-compatibility-version=19.33",  # MSVC compatibility version
            "-E",  # Only preprocess, don't compile
            file_path
        ]
        # Add -I flags if include directories are provided
        if include_dirs:
            for include_dir in include_dirs:
                clang_flags.append(f"-I{include_dir}")
        
        # Run GCC with the preprocessing command
        result = subprocess.run(
            ["clang"] + clang_flags,
            capture_output=True,
            text=True,
            check=True,
            bufsize=-1
        )

        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Preprocessing failed: {e.stderr}")
        return None

# Step 4: Unified entry point
def analyze_code(c_file):
    print(f"Analyzing: {c_file}\n")

    # Example of directories to include in the preprocessing
    include_dirs = [
        "C:/Program Files (x86)/Microsoft Visual Studio/VC/include",
        "C:/Program Files/LLVM/lib/clang/19/include",
        "C:/mingw/include",
        "C:\Program Files\LLVM\bin\clang-include-fixer.exe"
    ]

    # Preprocess the code for pycparser
    print("Preprocessing code for pycparser...")
    preprocessed_code = preprocess_code(c_file, include_dirs)
    if preprocessed_code is None:
        print("Failed to preprocess the code.")
        return

    # First-pass analysis using pycparser
    print("pycparser Analysis:")
    pycparser_checker = SemanticErrorChecker()
    pycparser_errors = pycparser_checker.check_code(preprocessed_code)
    if not pycparser_errors:
        print("No issues found by pycparser.")
    else:
        for error in pycparser_errors:
            print(error)

    # Second-pass analysis using Clang
    print("\nClang Analysis:")
    clang_errors = clang_analysis(c_file)
    if not clang_errors:
        print("No issues found by Clang.")
    else:
        for error in clang_errors:
            print(error)

    print("\nAnalysis Complete.\n")


# Main entry point
if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: python analyze.py <file.c>")
    else:
        analyze_code(sys.argv[1])
