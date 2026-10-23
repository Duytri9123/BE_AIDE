"""Inventory API declarations without importing the app or issuing mutations."""
import ast
import collections
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def inventory():
    base = ROOT / 'app/api/v1'
    prefixes = {}
    for n in ast.walk(ast.parse((base/'api_router.py').read_text(encoding='utf-8-sig'))):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == 'include_router' and n.args:
            arg = n.args[0]
            if isinstance(arg, ast.Attribute) and isinstance(arg.value, ast.Name):
                prefixes[arg.value.id] = next((ast.literal_eval(k.value) for k in n.keywords if k.arg == 'prefix'), '')
    prefixes['workspace_library'] = prefixes['analyze']
    routes = []
    for path in [*sorted((base/'endpoints').glob('*.py')), base/'api_router.py']:
        src = path.read_text(encoding='utf-8-sig'); tree = ast.parse(src)
        own_prefix = ''
        for n in tree.body:
            if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'router' for t in n.targets) and isinstance(n.value, ast.Call):
                own_prefix = next((ast.literal_eval(k.value) for k in n.value.keywords if k.arg == 'prefix'), '')
        for fn in tree.body:
            if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)): continue
            for dec in fn.decorator_list:
                if not (isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute) and dec.func.attr in ('get','post','put','patch','delete') and dec.args): continue
                text = ast.get_source_segment(src, fn)
                flags = []
                if '.all()' in text and '.limit(' not in text and '[skip:' not in text: flags.append('materializes_all_review')
                if any(isinstance(n, ast.Await) for loop in ast.walk(fn) if isinstance(loop, (ast.For, ast.AsyncFor)) for n in ast.walk(loop)): flags.append('await_in_loop_review')
                if isinstance(fn, ast.AsyncFunctionDef) and any(x in text for x in ('.read_text(', '.read_bytes(', '.rglob(', 'requests.', 'time.sleep(')): flags.append('sync_work_in_async_review')
                routes.append(dict(method=dec.func.attr.upper(), path='/api/v1'+prefixes.get(path.stem, '')+own_prefix+ast.literal_eval(dec.args[0]),
                    file=path.relative_to(ROOT).as_posix(), line=fn.lineno, function=fn.name,
                    pagination=[a.arg for a in fn.args.args if a.arg in ('skip','limit','page','page_size','cursor')],
                    flags=flags, runtime_measured=False))
    keys = collections.Counter((r['method'], r['path']) for r in routes)
    return {'scope': 'source inventory, heuristic flags require manual review; no production requests executed',
            'route_count': len(routes), 'duplicate_method_paths': [dict(method=k[0],path=k[1],count=v) for k,v in keys.items() if v>1],
            'routes': routes}


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(); parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(); result = inventory()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'routes':result['route_count'],'duplicates':result['duplicate_method_paths']}))
