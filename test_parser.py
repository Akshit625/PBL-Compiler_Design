from backend.parser import parse_code


code = """int x;
int y;
x = 5;
y = x + 10;
x = y * 2;"""

try:
    ast = parse_code(code)
    print("Parsed AST:", ast)
except Exception as e:
    print("Parse error:", e)
