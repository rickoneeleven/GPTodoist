import module_call_counter
import ast
import astunparse


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

    # Remove all unnecessary spaces but keep newlines
    condensed_code = "\n".join(
        line.strip() for line in code_without_comments.split("\n")
    )

    return condensed_code


module_call_counter.apply_call_counter_to_all(globals(), __name__)
