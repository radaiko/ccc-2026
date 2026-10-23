"""Minimal pure-SAT interface to the Z3 dylib via ctypes (DIMACS in, model out)."""
import ctypes, re
LIB = '/Users/laurenzwurdinger/Library/Android/sdk/emulator/lib64/vulkan/libz3.4.15.dylib'
z = ctypes.CDLL(LIB)
P = ctypes.c_void_p
for name, res, args in [
    ('Z3_mk_config', P, []), ('Z3_mk_context', P, [P]), ('Z3_del_config', None, [P]),
    ('Z3_mk_solver', P, [P]), ('Z3_mk_simple_solver', P, [P]), ('Z3_solver_inc_ref', None, [P, P]),
    ('Z3_solver_dec_ref', None, [P, P]), ('Z3_solver_from_string', None, [P, P, ctypes.c_char_p]),
    ('Z3_solver_check', ctypes.c_int, [P, P]), ('Z3_solver_get_model', P, [P, P]),
    ('Z3_model_inc_ref', None, [P, P]), ('Z3_model_to_string', ctypes.c_char_p, [P, P]),
    ('Z3_del_context', None, [P]), ('Z3_set_param_value', None, [P, ctypes.c_char_p, ctypes.c_char_p]),
    ('Z3_global_param_set', None, [ctypes.c_char_p, ctypes.c_char_p]),
    ('Z3_mk_params', P, [P]), ('Z3_params_inc_ref', None, [P, P]),
    ('Z3_params_set_uint', None, [P, P, P, ctypes.c_uint]), ('Z3_mk_string_symbol', P, [P, ctypes.c_char_p]),
    ('Z3_solver_set_params', None, [P, P, P]),
    ('Z3_model_get_num_consts', ctypes.c_uint, [P, P]), ('Z3_model_get_const_decl', P, [P, P, ctypes.c_uint]),
    ('Z3_get_decl_name', P, [P, P]), ('Z3_get_symbol_string', ctypes.c_char_p, [P, P]),
    ('Z3_get_symbol_int', ctypes.c_int, [P, P]), ('Z3_get_symbol_kind', ctypes.c_int, [P, P]),
    ('Z3_model_get_const_interp', P, [P, P, P]), ('Z3_get_bool_value', ctypes.c_int, [P, P]),
]:
    f = getattr(z, name); f.restype = res; f.argtypes = args


def solve(nvars, clauses, timeout_ms=0):
    """Returns None (unsat), 'unknown', or a set of true variables (1-based)."""
    cfg = z.Z3_mk_config()
    if timeout_ms:
        z.Z3_set_param_value(cfg, b'timeout', str(timeout_ms).encode())
    ctx = z.Z3_mk_context(cfg)
    z.Z3_del_config(cfg)
    s = z.Z3_mk_solver(ctx)
    z.Z3_solver_inc_ref(ctx, s)
    txt = 'p cnf %d %d\n' % (nvars, len(clauses)) + ''.join(' '.join(map(str, c)) + ' 0\n' for c in clauses)
    z.Z3_solver_from_string(ctx, s, txt.encode())
    r = z.Z3_solver_check(ctx, s)
    out = None
    if r == 1:
        m = z.Z3_solver_get_model(ctx, s)
        z.Z3_model_inc_ref(ctx, m)
        out = set()
        for i in range(z.Z3_model_get_num_consts(ctx, m)):
            d = z.Z3_model_get_const_decl(ctx, m, i)
            sym = z.Z3_get_decl_name(ctx, d)
            if z.Z3_get_symbol_kind(ctx, sym) == 0:
                v = z.Z3_get_symbol_int(ctx, sym)
            else:
                v = int(re.sub(r'\D', '', z.Z3_get_symbol_string(ctx, sym).decode()))
            val = z.Z3_get_bool_value(ctx, z.Z3_model_get_const_interp(ctx, m, d))
            if val == 1:
                out.add(v)
    elif r == 0:
        out = 'unknown'
    z.Z3_del_context(ctx)
    return out

if __name__ == '__main__':
    print(solve(3, [[1, 2], [-1], [-2, 3]]))
    print(solve(2, [[1], [-1, 2], [-2]]))
