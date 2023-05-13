import module_call_counter
import ast
import astunparse
import python_minifier


def shrink_code(code):
    # Parse the code into an AST
    tree = ast.parse(code)

    # Remove docstrings
    for node in ast.walk(tree):
        if isinstance(
            node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Module)
        ):
            node.docstring = None

    # Remove comments and unnecessary whitespace by unparsing the AST back into code
    code_without_comments = astunparse.unparse(tree)

    # Minify the code
    minified_code = python_minifier.minify(code_without_comments)

    return minified_code


module_call_counter.apply_call_counter_to_all(globals(), __name__)
