"""Upgrade transactions must preserve local configuration and user data."""
import importlib.util
import json
from pathlib import Path
import pytest

spec = importlib.util.spec_from_file_location('ai_upgrade', Path(__file__).resolve().parents[2] / 'scripts/apply_ai_upgrade.py')
upgrade = importlib.util.module_from_spec(spec)
spec.loader.exec_module(upgrade)


@pytest.fixture
def patch_env(tmp_path):
    project, bundle = tmp_path / 'AI-News', tmp_path / 'upgrade'
    files = {'manage.py': b'old launch', 'backend/app/config.py': b'old config', 'frontend/package.json': b'{}'}
    for name, data in files.items():
        path = project / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    (project / '.env').write_bytes(b'\xef\xbb\xbfAI_API_KEY="keep-secret"\r\nMAX_PER_SECTION=3\r\nJPUSH_MASTER_SECRET=keep-push\r\n')
    (project / 'backend/sources.json').write_text('[{"id":"custom","enabled":false,"name":"My feed"}]')
    (project / 'database/data').mkdir(parents=True)
    (project / 'database/data/news.db').write_bytes(b'account-and-history-fixture')
    records = []
    updates = {'manage.py': b'new launch', 'backend/app/config.py': b'new config',
               '.env.example': b'MAX_PER_SECTION=10\n', 'ai-service/new.py': b'new feature'}
    for name, data in updates.items():
        path = bundle / 'payload' / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        records.append({'path': name, 'sha256': upgrade.sha(data),
                        'previous_sha256': [upgrade.sha(files[name]) if name in files else None]})
    manifest = {'version': '0.4.0', 'files': records, 'add_sources': [{'id': 'qbitai', 'enabled': True}]}
    (bundle / 'manifest.json').write_text(json.dumps(manifest))
    return project, bundle


def test_upgrade_preserves_credentials_data_custom_sources_and_is_repeatable(patch_env):
    project, bundle = patch_env
    old_env = (project / '.env').read_bytes()
    backup = upgrade.upgrade(project, bundle)
    assert (project / '.env').read_bytes() == old_env.replace(b'MAX_PER_SECTION=3', b'MAX_PER_SECTION=10')
    assert (project / 'database/data/news.db').read_bytes() == b'account-and-history-fixture'
    sources = json.loads((project / 'backend/sources.json').read_bytes())
    assert sources == [{'id': 'custom', 'enabled': False, 'name': 'My feed'}, {'id': 'qbitai', 'enabled': True}]
    assert old_env in [p.read_bytes() for p in backup.glob('*.original')]
    assert upgrade.upgrade(project, bundle) is None


def test_local_code_change_is_rejected_before_any_replacement(patch_env):
    project, bundle = patch_env
    (project / 'backend/app/config.py').write_bytes(b'local customization')
    with pytest.raises(RuntimeError, match='Locally modified'):
        upgrade.upgrade(project, bundle)
    assert (project / 'manage.py').read_bytes() == b'old launch'
    assert b'MAX_PER_SECTION=3' in (project / '.env').read_bytes()


def test_write_failure_rolls_back_all_files_and_env(patch_env, monkeypatch):
    project, bundle = patch_env
    originals = {p: p.read_bytes() for p in project.rglob('*') if p.is_file()}
    write = upgrade.atomic_write
    calls = []
    def fail_once(path, data):
        calls.append(path)
        if len(calls) == 6:
            raise OSError('simulated disk failure')
        write(path, data)
    monkeypatch.setattr(upgrade, 'atomic_write', fail_once)
    with pytest.raises(OSError, match='simulated'):
        upgrade.upgrade(project, bundle)
    assert all(p.read_bytes() == content for p, content in originals.items())
    assert not (project / 'ai-service/new.py').exists()
    assert not (project / '.env.example').exists()


def test_running_launcher_blocks_upgrade(patch_env):
    project, bundle = patch_env
    with upgrade.exclusive(project / 'output/local-run/launcher.lock'):
        with pytest.raises(RuntimeError, match='News is running'):
            upgrade.upgrade(project, bundle)
    assert (project / 'manage.py').read_bytes() == b'old launch'


def test_bad_checksum_is_rejected_before_any_write(patch_env):
    project, bundle = patch_env
    (bundle / 'payload/backend/app/config.py').write_bytes(b'damaged download')
    with pytest.raises(RuntimeError, match='checksum'):
        upgrade.upgrade(project, bundle)
    assert (project / 'manage.py').read_bytes() == b'old launch'


def test_custom_source_path_preserved_and_existing_ai_source_not_duplicated(patch_env):
    project, bundle = patch_env
    custom = project.parent / 'my feeds.json'
    custom.write_text('[{"id":"qbitai","enabled":false}]')
    with (project / '.env').open('ab') as out:
        out.write(f'SOURCES_FILE="{custom}"\r\n'.encode())
    upgrade.upgrade(project, bundle)
    assert custom.read_text() == '[{"id":"qbitai","enabled":false}]'
    assert json.loads((project / 'backend/sources.json').read_bytes())[0]['id'] == 'custom'


@pytest.mark.parametrize('data', [b'', b'AI_API_KEY=keep', b'export MAX_PER_SECTION = "3"\nMAX_PER_SECTION=4\n'])
def test_limit_update_handles_absent_or_duplicate_settings(data):
    result = upgrade.set_limit(data)
    assert b'MAX_PER_SECTION' in result
    assert upgrade.set_limit(result) == result


def test_empty_custom_path_does_not_consume_next_setting(patch_env):
    project, _ = patch_env
    (project / '.env').write_bytes(b'SOURCES_FILE=\r\nMAX_PER_SECTION=3\r\n')
    assert upgrade.configured_path(project, 'SOURCES_FILE', 'backend/sources.json') == project / 'backend/sources.json'
