import unittest

from backend.parser import parse_code


class ParserRestrictionsTests(unittest.TestCase):
    def test_allows_basic_code(self):
        code = """int x;
int y = 3;
x = y + 4;
return x;"""
        ast = parse_code(code)
        self.assertEqual(ast[0][0], 'declare')
        self.assertEqual(ast[-1][0], 'return')

    def test_rejects_loops(self):
        with self.assertRaisesRegex(SyntaxError, 'Control-flow keywords are not supported'):
            parse_code("""int x;
while (x) {
    x = x - 1;
}""")

    def test_rejects_includes(self):
        with self.assertRaisesRegex(SyntaxError, 'Libraries and preprocessor directives are not supported'):
            parse_code("""#include <stdio.h>
int x;
x = 1;""")

    def test_rejects_function_calls(self):
        with self.assertRaisesRegex(SyntaxError, 'Function definitions and function calls are not supported'):
            parse_code("""int x;
print(x);""")


if __name__ == '__main__':
    unittest.main()
