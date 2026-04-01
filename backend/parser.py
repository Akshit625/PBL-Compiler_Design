import re

import ply.lex as lex
import ply.yacc as yacc


SUPPORTED_SYNTAX = (
    "Use only basic code: int declarations, assignments, an optional return, "
    "integer literals, variables, parentheses, and + - * / expressions."
)

UNSUPPORTED_PATTERNS = [
    (r'^\s*#', 'Libraries and preprocessor directives are not supported.'),
    (r'\b(?:if|else|for|while|do|switch|case|break|continue)\b', 'Control-flow keywords are not supported.'),
    (r'\b(?:float|double|char|void|bool|long|short|signed|unsigned)\b', 'Only int declarations are supported.'),
    (r'\b(?:struct|typedef|enum|union|class)\b', 'Custom types are not supported.'),
    (r'\b(?:true|false)\b', 'Boolean keywords are not supported.'),
    (r'"([^"\\]|\\.)*"', 'Strings are not supported.'),
    (r"'([^'\\]|\\.)*'", 'Character literals are not supported.'),
    (r'\b(?:printf|scanf|cin|cout)\b', 'Input/output functions are not supported.'),
    (r'\b[A-Za-z_][A-Za-z0-9_]*\s*\(', 'Function definitions and function calls are not supported.')
]


tokens = (
    'ID', 'NUMBER',
    'PLUS', 'MINUS', 'TIMES', 'DIVIDE',
    'LPAREN', 'RPAREN',
    'SEMICOLON', 'COMMA', 'ASSIGN',
    'INT', 'RETURN'
)


reserved = {
    'int': 'INT',
    'return': 'RETURN'
}


t_PLUS = r'\+'
t_MINUS = r'-'
t_TIMES = r'\*'
t_DIVIDE = r'/'
t_LPAREN = r'\('
t_RPAREN = r'\)'
t_SEMICOLON = r';'
t_COMMA = r','
t_ASSIGN = r'='


def t_BLOCK_COMMENT(t):
    r'/\*(.|\n)*?\*/'
    t.lexer.lineno += t.value.count('\n')


def t_LINE_COMMENT(t):
    r'//[^\n]*'
    pass


def t_ID(t):
    r'[a-zA-Z_][a-zA-Z0-9_]*'
    t.type = reserved.get(t.value, 'ID')
    return t


def t_NUMBER(t):
    r'\d+'
    t.value = int(t.value)
    return t


t_ignore = ' \t'


def t_newline(t):
    r'\n+'
    t.lexer.lineno += len(t.value)


def t_error(t):
    raise SyntaxError(f"Illegal character '{t.value[0]}'. {SUPPORTED_SYNTAX}")


lexer = lex.lex()

precedence = (
    ('left', 'PLUS', 'MINUS'),
    ('left', 'TIMES', 'DIVIDE'),
)


def p_program(p):
    'program : statements'
    p[0] = p[1]


def p_statements_single(p):
    'statements : statement'
    p[0] = p[1]


def p_statements_multiple(p):
    'statements : statements statement'
    p[0] = p[1] + p[2]


def p_statement(p):
    '''statement : declaration
                 | assignment
                 | return_stmt'''
    p[0] = p[1]


def p_declaration(p):
    'declaration : INT declarator_list SEMICOLON'
    p[0] = [('declare', p[2])]


def p_declarator_list_single(p):
    'declarator_list : declarator'
    p[0] = p[1]


def p_declarator_list_multiple(p):
    'declarator_list : declarator_list COMMA declarator'
    p[0] = p[1] + p[3]


def p_declarator(p):
    '''declarator : ID
                  | ID ASSIGN expression'''
    if len(p) == 2:
        p[0] = [(p[1], None)]
    else:
        p[0] = [(p[1], p[3])]


def p_assignment(p):
    'assignment : ID ASSIGN expression SEMICOLON'
    p[0] = [('assign', p[1], p[3])]


def p_return_stmt(p):
    'return_stmt : RETURN expression SEMICOLON'
    p[0] = [('return', p[2])]


def p_expression_binop(p):
    '''expression : expression PLUS term
                  | expression MINUS term'''
    p[0] = (p[1], p[2], p[3])


def p_expression_term(p):
    'expression : term'
    p[0] = p[1]


def p_term_binop(p):
    '''term : term TIMES factor
            | term DIVIDE factor'''
    p[0] = (p[1], p[2], p[3])


def p_term_factor(p):
    'term : factor'
    p[0] = p[1]


def p_factor(p):
    '''factor : NUMBER
              | ID
              | LPAREN expression RPAREN'''
    if len(p) == 2:
        p[0] = p[1]
    else:
        p[0] = p[2]


def p_error(p):
    if p is None:
        raise SyntaxError(f'Syntax error at end of input. {SUPPORTED_SYNTAX}')
    raise SyntaxError(f"Syntax error at '{p.value}'. {SUPPORTED_SYNTAX}")


parser = yacc.yacc()


def strip_comments(code):
    without_block_comments = re.sub(r'/\*(.|\n)*?\*/', '', code)
    return re.sub(r'//[^\n]*', '', without_block_comments)


def validate_supported_code(code):
    sanitized = strip_comments(code)

    if not sanitized.strip():
        raise SyntaxError('Please enter some code to optimize.')

    for pattern, message in UNSUPPORTED_PATTERNS:
        if re.search(pattern, sanitized, flags=re.MULTILINE):
            raise SyntaxError(f'{message} {SUPPORTED_SYNTAX}')


def preprocess_code(code):
    validate_supported_code(code)
    return strip_comments(code).strip()


def get_source_context(code):
    return {
        'includes': [],
        'wrap_main': False
    }


def parse_code(code):
    cleaned = preprocess_code(code)
    lexer.lineno = 1
    result = parser.parse(cleaned, lexer=lexer)
    if result is None:
        raise SyntaxError('Unable to parse input code.')
    return result
