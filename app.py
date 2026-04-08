from flask import Flask, request, jsonify, render_template
from backend.parser import get_source_context, parse_code
from backend.tac import generate_tac
from backend.cfg import build_cfg
from backend.analysis import analyze_code
from backend.ast_optimizer import optimize_ast
from backend.optimizer import optimize_code
from backend.generator import generate_code

app = Flask(__name__, template_folder='frontend', static_folder='frontend')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/optimize', methods=['POST'])
def optimize():
    data = request.get_json()
    code = data['code']
    source_context = get_source_context(code)
    print("Received code:", repr(code))
    try:
        # Parse
        ast = parse_code(code)
        print("Parsed AST:", ast)
        # TAC
        tac = generate_tac(ast)
        print("TAC:", tac)
        # CFG
        cfg = build_cfg(tac)
        print("CFG:", cfg)
        # Analysis
        analysis = analyze_code(tac, cfg)
        print("Analysis:", analysis)
        # Optimize
        optimized_tac = optimize_code(tac, analysis)
        print("Optimized TAC:", optimized_tac)
        optimized_ast = optimize_ast(ast)
        print("Optimized AST:", optimized_ast)
        # Generate code
        optimized_code = generate_code(optimized_ast, source_context)
        print("Optimized code:", repr(optimized_code))
        return jsonify({'success': True, 'optimized': optimized_code})
    except SyntaxError as e:
        print("Validation error:", e)
        return jsonify({'success': False, 'error': str(e)})
    except Exception as e:
        print("Error:", e)
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    app.run(debug=True)
