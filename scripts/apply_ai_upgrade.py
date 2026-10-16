"""Apply the v0.4 source patch without replacing user data or credentials.

Uses only Python's standard library. Distributed with manifest.json and payload/.
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack, contextmanager
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import tempfile
import uuid

DEFAULT_PROJECT = r"D:\AI-News-Setup\AI-News-Windows\AI-News"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def set_limit(data):
    """Preserve all other bytes (including BOM, CRLF and API keys)."""
    text = data.decode('utf-8-sig')
    pattern = re.compile(r'^(\s*(?:export\s+)?MAX_PER_SECTION\s*=)[^\r\n]*', re.M)
    if pattern.search(text):
        text = pattern.sub(lambda m: m.group(1) + '10', text)
    else:
        newline = '\r\n' if '\r\n' in text else '\n'
        if text and not text.endswith(('\n', '\r')):
            text += newline
        text += 'MAX_PER_SECTION=10' + newline
    return (b'\xef\xbb\xbf' if data.startswith(b'\xef\xbb\xbf') else b'') + text.encode('utf-8')


def configured_path(root, name, default):
    value = os.environ.get(name)
    if value is None and (root / '.env').is_file():
        text = (root / '.env').read_text(encoding='utf-8-sig')
        matches = re.findall(r'^[ \t]*(?:export[ \t]+)?' + name + r'[ \t]*=[ \t]*(.*?)[ \t\r]*$', text, re.M)
        if matches:
            value = re.split(r'\s+#', matches[-1], maxsplit=1)[0].strip().strip('\"\'')
    if not value:
        return root / default
    if '$' in value:
        raise RuntimeError(f'{name} uses variable expansion. Set an absolute path before upgrading.')
    path = Path(value)
    return path if path.is_absolute() else root / path


def merge_sources(data, additions):
    sources = json.loads(data.decode('utf-8-sig'))
    if not isinstance(sources, list) or any(not isinstance(s, dict) or 'id' not in s for s in sources):
        raise RuntimeError('The sources file is not a valid source list. No files changed.')
    ids = {s['id'] for s in sources}
    if len(ids) != len(sources):
        raise RuntimeError('Duplicate source IDs. No files changed.')
    added = [s for s in additions if s['id'] not in ids]
    if not added:
        return data
    return (json.dumps(sources + added, ensure_ascii=False, indent=2) + '\n').encode('utf-8')


@contextmanager
def exclusive(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a+b') as handle:
        handle.seek(0, 2)
        if handle.tell() == 0:
            handle.write(b'0')
            handle.flush()
        handle.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise RuntimeError('News is running. Press Ctrl+C in its launch window, wait for it to stop, then retry.') from exc
        yield


def atomic_write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix='.ai-upgrade-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as out:
            out.write(data)
            out.flush()
            os.fsync(out.fileno())
        os.replace(temp, path)
    finally:
        Path(temp).unlink(missing_ok=True)


def validate_path(relative):
    path = PurePosixPath(relative)
    if (not relative or path.is_absolute() or '..' in path.parts or '\\' in relative
            or ':' in relative or str(path) != relative):
        raise RuntimeError('Invalid path in upgrade manifest.')
    if path.parts[0] in ('.venv', 'output', 'node_modules') or relative == '.env' or relative.startswith('database/data/'):
        raise RuntimeError('Upgrade manifest must not contain runtime data.')
    return path


def upgrade(project, bundle):
    project, bundle = Path(project).resolve(), Path(bundle).resolve()
    if not all((project / p).is_file() for p in ('manage.py', 'backend/app/config.py', 'frontend/package.json')):
        raise RuntimeError(f'Project not found at {project}. Use --project-root with the existing AI-News folder.')
    manifest = json.loads((bundle / 'manifest.json').read_text(encoding='utf-8'))
    if manifest.get('version') != '0.4.0':
        raise RuntimeError('Unexpected upgrade version.')
    with ExitStack() as stack:
        stack.enter_context(exclusive(project / 'output/local-run/launcher.lock'))
        stack.enter_context(exclusive(configured_path(project, 'DATA_DIR', 'database/data') / '.worker.lock'))
        changes = []
        seen = set()
        for record in manifest['files']:
            relative = record['path']
            path = validate_path(relative)
            if relative in seen or relative == 'backend/sources.json':
                raise RuntimeError('Duplicate or reserved source path in manifest.')
            seen.add(relative)
            target = project / path
            payload = bundle / 'payload' / path
            if not target.resolve().is_relative_to(project) or not payload.resolve().is_relative_to(bundle / 'payload'):
                raise RuntimeError('Symlink outside project or payload is not supported.')
            content = payload.read_bytes()
            if sha(content) != record['sha256']:
                raise RuntimeError(f'Upgrade file checksum failed: {relative}. Download the ZIP again.')
            old = target.read_bytes() if target.exists() else None
            if old == content:
                continue
            if (sha(old) if old is not None else None) not in record['previous_sha256']:
                raise RuntimeError(f'Locally modified file: {relative}. No code was overwritten; retain your changes and merge this file manually.')
            changes.append((target, old, content))
        env = project / '.env'
        old_env = env.read_bytes() if env.is_file() else None
        new_env = set_limit(old_env or (bundle / 'payload/.env.example').read_bytes())
        if old_env != new_env:
            changes.append((env, old_env, new_env))
        sources = configured_path(project, 'SOURCES_FILE', 'backend/sources.json')
        if not sources.is_file():
            raise RuntimeError(f'Source configuration is missing: {sources}. No code was changed.')
        old_sources = sources.read_bytes()
        new_sources = merge_sources(old_sources, manifest['add_sources'])
        if old_sources != new_sources:
            changes.append((sources, old_sources, new_sources))
        if not changes:
            print('Already upgraded: four categories, up to 10 items per region/category.', flush=True)
            return None
        backup = project / 'output' / ('ai-upgrade-backup-' + datetime.now().strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:6])
        backup.mkdir(parents=True, mode=0o700)
        # Back up every original before replacing any file. Keys are never logged.
        restore = []
        for i, (target, old, new) in enumerate(changes):
            name = f'{i:03}.original'
            if old is not None:
                (backup / name).write_bytes(old)
            restore.append({'target': str(target), 'original': name if old is not None else None,
                            'original_sha256': sha(old) if old is not None else None, 'updated_sha256': sha(new)})
        (backup / 'restore.json').write_text(json.dumps(restore, ensure_ascii=False, indent=2), encoding='utf-8')
        written = []
        try:
            for target, old, new in changes:
                written.append((target, old))
                atomic_write(target, new)
        except BaseException:
            failed = []
            for target, old in reversed(written):
                try:
                    if old is None:
                        target.unlink(missing_ok=True)
                    else:
                        atomic_write(target, old)
                except BaseException:
                    failed.append(str(target))
            if failed:
                raise RuntimeError(f'Rollback needs manual recovery. Backup: {backup}; files: {failed}')
            raise
        print(f'Upgrade complete. Backup: {backup}', flush=True)
        print('Accounts, saved news, reports and model credentials were preserved.', flush=True)
        return backup


def main():
    parser = argparse.ArgumentParser(description='Upgrade AI News to four categories, 10 items per section.')
    parser.add_argument('--project-root', default=DEFAULT_PROJECT)
    parser.add_argument('--no-start', action='store_true')
    args = parser.parse_args()
    try:
        project = Path(args.project_root).resolve()
        upgrade(project, Path(__file__).resolve().parent)
    except (OSError, ValueError, RuntimeError) as exc:
        print(f'ERROR: {exc}', file=sys.stderr, flush=True)
        return 1
    print('After startup, sign in and click Update briefing to regenerate today. Older reports remain unchanged.', flush=True)
    if not args.no_start:
        wrapper = project.parent / 'scripts/start-on-d.ps1'
        if os.name == 'nt' and wrapper.is_file():
            return subprocess.call(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(wrapper)])
        print('Start the project with its usual launcher.', flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
