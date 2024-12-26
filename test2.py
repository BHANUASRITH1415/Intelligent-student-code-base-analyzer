import os
import sys
from pycparser import c_parser, c_ast, parse_file
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
        
#checking for lexical and syntax errors
def pycparser_analysis(file_path):
    """
    Check lexical and syntax errors using pycparser.
    """
    parser = c_parser.CParser()
    try:
        with open(file_path, 'r') as f:
            code = f.read()
        parser.parse(code)
        print(" Lexical and Syntax Check: No errors found.")
    except Exception as e:
        print(f" Lexical/Syntax Error: {e}")


#checking for semantic errors
def clang_analysis(file_path):
    """
    Check semantic errors using clang.
    """
    clang_command = (
        f'clang -I "C:\\MinGW\\include" '
        f'-I "C:\\MinGW\\lib\\gcc\\x86_64-w64-mingw32\\6.3.0" '
        f'-fsyntax-only "{file_path}"'
    )
    try:
        result = os.popen(clang_command).read()
        if result:
            print(" Semantic Check Errors:")
            print(result)
        else:
            print(" Semantic Check: No errors found.")
    except Exception as e:
        print(f"Error running clang: {e}")
def analyze_code(c_file):
    print(f"Analyzing: {c_file}\n")
    
    print(f"Checking for lexical and syntax errors using pycparser:")
    pycparser_analysis(c_file)

    print("\nChecking for semantic errors using clang:")
    clang_analysis(c_file)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python test.py <file_path>")
        sys.exit(1)
    else:
        analyze_code(sys.argv[1])
    # file_path = r"undefvar.c"

    # if os.path.exists(file_path):
    #     print(f"Checking file: {file_path}\n")
    #     check_lexical_syntax_errors(file_path)
    #     check_semantic_errors(file_path)
    # else:
    #     print(f"File not found: {file_path}")
