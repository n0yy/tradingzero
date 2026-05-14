import json
from pathlib import Path


def test_web_scaffold_exists_with_required_scripts():
    package_json = Path('apps/web/package.json')
    assert package_json.exists()

    pkg = json.loads(package_json.read_text())
    scripts = pkg.get('scripts', {})

    assert 'dev' in scripts
    assert 'build' in scripts
    assert pkg.get('name') == 'web'
