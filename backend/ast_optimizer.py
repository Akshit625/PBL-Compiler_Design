def optimize_ast(statements):
    simplified = simplify_statements(statements)
    optimized, _, _ = eliminate_dead_code(simplified, set())
    return fold_declaration_initializers(optimized)


def simplify_statements(statements, assumptions=None):
    assumptions = assumptions or []
    simplified = []

    for stmt in statements:
        kind = stmt[0]

        if kind == 'declare':
            simplified.append(('declare', [(name, simplify_expression(init)) for name, init in stmt[1]]))
        elif kind == 'assign':
            simplified.append(('assign', stmt[1], simplify_expression(stmt[2])))
        elif kind == 'call':
            simplified.append(('call', stmt[1], [simplify_expression(arg) for arg in stmt[2]]))
        elif kind == 'return':
            simplified.append(('return', simplify_expression(stmt[1])))
            break
        elif kind == 'if':
            condition = simplify_expression(stmt[1])
            truth = evaluate_condition(condition, assumptions)
            body = simplify_statements(stmt[2], assumptions + [condition])

            if truth == 0:
                continue
            if truth == 1:
                simplified.extend(body)
                if block_returns(body):
                    break
                continue
            if body:
                simplified.append(('if', condition, body))
        elif kind == 'if-else':
            condition = simplify_expression(stmt[1])
            truth = evaluate_condition(condition, assumptions)
            then_body = simplify_statements(stmt[2], assumptions + [condition])
            else_body = simplify_statements(stmt[3], assumptions + [invert_condition(condition)])

            if truth == 1:
                simplified.extend(then_body)
                if block_returns(then_body):
                    break
                continue
            if truth == 0:
                simplified.extend(else_body)
                if block_returns(else_body):
                    break
                continue

            if then_body and else_body:
                simplified.append(('if-else', condition, then_body, else_body))
            elif then_body:
                simplified.append(('if', condition, then_body))
            elif else_body:
                simplified.append(('if', invert_condition(condition), else_body))
        elif kind == 'while':
            condition = simplify_expression(stmt[1])
            truth = evaluate_condition(condition, assumptions)
            body = simplify_statements(stmt[2], assumptions + [condition])

            if truth == 0:
                continue
            simplified.append(('while', condition, body))

    return simplified


def eliminate_dead_code(statements, live_after):
    optimized_reversed = []
    live = set(live_after)
    required_declarations = set(live_after)

    for stmt in reversed(statements):
        kind = stmt[0]

        if kind == 'return':
            optimized_reversed.append(stmt)
            live = expression_variables(stmt[1])
            required_declarations |= live
        elif kind == 'call':
            optimized_reversed.append(stmt)
            call_vars = expression_list_variables(stmt[2])
            live |= call_vars
            required_declarations |= call_vars
        elif kind == 'assign':
            if stmt[1] in live:
                optimized_reversed.append(stmt)
                required_declarations.add(stmt[1])
                live.discard(stmt[1])
                expr_vars = expression_variables(stmt[2])
                live |= expr_vars
                required_declarations |= expr_vars
        elif kind == 'declare':
            kept = []
            current_live = set(live)
            current_required = set(required_declarations)

            for name, initializer in reversed(stmt[1]):
                if name in current_required:
                    kept.append((name, initializer))
                    current_live.discard(name)
                    current_required.discard(name)
                    if initializer is not None:
                        init_vars = expression_variables(initializer)
                        current_live |= init_vars
                        current_required |= init_vars

            live = current_live
            required_declarations = current_required
            if kept:
                optimized_reversed.append(('declare', list(reversed(kept))))
        elif kind == 'if':
            body, body_live, body_required = eliminate_dead_code(stmt[2], live)
            if body:
                optimized_reversed.append(('if', stmt[1], body))
                cond_vars = expression_variables(stmt[1])
                live = live | body_live | cond_vars
                required_declarations |= body_required | cond_vars
        elif kind == 'if-else':
            then_body, then_live, then_required = eliminate_dead_code(stmt[2], live)
            else_body, else_live, else_required = eliminate_dead_code(stmt[3], live)

            if then_body and else_body:
                optimized_reversed.append(('if-else', stmt[1], then_body, else_body))
                cond_vars = expression_variables(stmt[1])
                live = then_live | else_live | cond_vars
                required_declarations |= then_required | else_required | cond_vars
            elif then_body:
                optimized_reversed.append(('if', stmt[1], then_body))
                cond_vars = expression_variables(stmt[1])
                live = then_live | live | cond_vars
                required_declarations |= then_required | cond_vars
            elif else_body:
                optimized_reversed.append(('if', invert_condition(stmt[1]), else_body))
                cond_vars = expression_variables(stmt[1])
                live = else_live | live | cond_vars
                required_declarations |= else_required | cond_vars
        elif kind == 'while':
            cond_vars = expression_variables(stmt[1])
            body, body_live, body_required = eliminate_dead_code(stmt[2], live | cond_vars)
            optimized_reversed.append(('while', stmt[1], body))
            live = live | body_live | cond_vars
            required_declarations |= body_required | cond_vars

    return list(reversed(optimized_reversed)), live, required_declarations


def fold_declaration_initializers(statements):
    folded = []
    index = 0

    while index < len(statements):
        stmt = statements[index]
        kind = stmt[0]

        if kind == 'declare':
            declarators = list(stmt[1])
            next_index = index + 1

            while next_index < len(statements):
                next_stmt = statements[next_index]
                if next_stmt[0] != 'assign':
                    break

                target = next_stmt[1]
                match_index = None

                for declarator_index, (name, initializer) in enumerate(declarators):
                    if name == target and initializer is None:
                        match_index = declarator_index
                        break

                if match_index is None:
                    break

                declarators[match_index] = (target, next_stmt[2])
                next_index += 1

            folded.append(('declare', declarators))
            index = next_index
            continue

        if kind == 'if':
            folded.append(('if', stmt[1], fold_declaration_initializers(stmt[2])))
        elif kind == 'if-else':
            folded.append((
                'if-else',
                stmt[1],
                fold_declaration_initializers(stmt[2]),
                fold_declaration_initializers(stmt[3])
            ))
        elif kind == 'while':
            folded.append(('while', stmt[1], fold_declaration_initializers(stmt[2])))
        else:
            folded.append(stmt)

        index += 1

    return folded


def block_returns(statements):
    return bool(statements) and statements[-1][0] == 'return'


def simplify_expression(expr):
    if isinstance(expr, tuple) and len(expr) == 3:
        left = simplify_expression(expr[0])
        op = expr[1]
        right = simplify_expression(expr[2])
        constant = evaluate_constant((left, op, right))
        if constant is not None:
            return constant
        return (left, op, right)
    return expr


def evaluate_constant(expr):
    if isinstance(expr, int):
        return expr

    if not (isinstance(expr, tuple) and len(expr) == 3):
        return None

    left = evaluate_constant(expr[0])
    right = evaluate_constant(expr[2])

    if left is None or right is None:
        return None

    op = expr[1]

    if op == '+':
        return left + right
    if op == '-':
        return left - right
    if op == '*':
        return left * right
    if op == '/':
        if right == 0:
            return None
        return left // right
    if op == '==':
        return int(left == right)
    if op == '!=':
        return int(left != right)
    if op == '<':
        return int(left < right)
    if op == '<=':
        return int(left <= right)
    if op == '>':
        return int(left > right)
    if op == '>=':
        return int(left >= right)

    return None


def evaluate_condition(expr, assumptions):
    constant = evaluate_constant(expr)
    if constant is not None:
        return int(bool(constant))

    if is_condition_impossible(expr, assumptions):
        return 0

    if is_condition_guaranteed(expr, assumptions):
        return 1

    return None


def is_condition_impossible(expr, assumptions):
    target = extract_constraint(expr)
    if target is None:
        return False

    for assumption in assumptions:
        constraint = extract_constraint(assumption)
        if constraint is None:
            continue
        if constraints_contradict(constraint, target):
            return True

    return False


def is_condition_guaranteed(expr, assumptions):
    target = extract_constraint(expr)
    if target is None:
        return False

    for assumption in assumptions:
        constraint = extract_constraint(assumption)
        if constraint is None:
            continue
        if constraint_implies(constraint, target):
            return True

    return False


def extract_constraint(expr):
    if not (isinstance(expr, tuple) and len(expr) == 3):
        return None

    left, op, right = expr
    if isinstance(left, str) and isinstance(right, int):
        return (left, op, right)
    if isinstance(left, int) and isinstance(right, str):
        flipped = {
            '<': '>',
            '<=': '>=',
            '>': '<',
            '>=': '<=',
            '==': '==',
            '!=': '!='
        }
        return (right, flipped.get(op, op), left)
    return None


def constraints_contradict(left, right):
    if left[0] != right[0]:
        return False
    return not ranges_overlap(constraint_range(left), constraint_range(right))


def constraint_implies(left, right):
    if left[0] != right[0]:
        return False
    left_range = constraint_range(left)
    right_range = constraint_range(right)
    return range_subset(left_range, right_range)


def constraint_range(constraint):
    _, op, value = constraint
    if op == '>':
        return (value + 1, None, True)
    if op == '>=':
        return (value, None, True)
    if op == '<':
        return (None, value - 1, True)
    if op == '<=':
        return (None, value, True)
    if op == '==':
        return (value, value, False)
    if op == '!=':
        return (None, None, False, value)
    return (None, None, True)


def ranges_overlap(left_range, right_range):
    left_forbidden = left_range[3] if len(left_range) > 3 else None
    right_forbidden = right_range[3] if len(right_range) > 3 else None

    if left_forbidden is not None:
        return not range_subset(right_range, (left_forbidden, left_forbidden, False))
    if right_forbidden is not None:
        return not range_subset(left_range, (right_forbidden, right_forbidden, False))

    lower = max_bound(left_range[0], right_range[0], minimum=True)
    upper = min_bound(left_range[1], right_range[1], minimum=False)

    if lower is None or upper is None:
        return True

    return lower <= upper


def range_subset(left_range, right_range):
    left_forbidden = left_range[3] if len(left_range) > 3 else None
    right_forbidden = right_range[3] if len(right_range) > 3 else None

    if left_forbidden is not None:
        return False
    if right_forbidden is not None:
        if left_range[0] == left_range[1] == right_forbidden:
            return False
        return True

    left_lower, left_upper = left_range[0], left_range[1]
    right_lower, right_upper = right_range[0], right_range[1]

    lower_ok = right_lower is None or (left_lower is not None and left_lower >= right_lower)
    upper_ok = right_upper is None or (left_upper is not None and left_upper <= right_upper)
    return lower_ok and upper_ok


def max_bound(left, right, minimum=True):
    bounds = [bound for bound in [left, right] if bound is not None]
    if not bounds:
        return None
    return max(bounds)


def min_bound(left, right, minimum=False):
    bounds = [bound for bound in [left, right] if bound is not None]
    if not bounds:
        return None
    return min(bounds)


def invert_condition(expr):
    if isinstance(expr, int):
        return 0 if expr else 1

    if isinstance(expr, tuple) and len(expr) == 3:
        inverse_ops = {
            '==': '!=',
            '!=': '==',
            '<': '>=',
            '<=': '>',
            '>': '<=',
            '>=': '<'
        }
        if expr[1] in inverse_ops:
            return (expr[0], inverse_ops[expr[1]], expr[2])

    return (expr, '==', 0)


def expression_variables(expr):
    if isinstance(expr, str):
        if expr.startswith('"') and expr.endswith('"'):
            return set()
        return {expr}
    if isinstance(expr, tuple) and len(expr) == 3:
        return expression_variables(expr[0]) | expression_variables(expr[2])
    return set()


def expression_list_variables(expressions):
    variables = set()
    for expr in expressions:
        variables |= expression_variables(expr)
    return variables
