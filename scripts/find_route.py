import os

for root, dirs, files in os.walk('BE_AIDE/app'):
    for f in files:
        if f.endswith('.py'):
            p = os.path.join(root, f)
            try:
                with open(p, 'r', encoding='utf-8', errors='ignore') as fp:
                    content = fp.read()
                    if 'device-catalog' in content:
                        print('Found in:', p)
            except Exception:
                pass
