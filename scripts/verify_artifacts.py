"""Verify immutable session imports and pinned workflow dependencies."""
import hashlib
import json
from pathlib import Path


def main():
    root = Path.cwd().resolve()
    manifest = json.loads((root / 'docs/session/artifact-manifest.json').read_text())
    for item in manifest['files']:
        target = (root / item['path']).resolve()
        if not target.is_relative_to(root):
            raise ValueError('Artifact escapes repository')
        if hashlib.sha256(target.read_bytes()).hexdigest() != item['sha256']:
            raise ValueError('SHA-256 mismatch: ' + item['path'])
    required = ['AGENTS.md', 'openspec/config.yaml', '.agents/skills/openspec-propose/SKILL.md',
                '.agents/plugins/marketplace.json', 'tools/superpowers/skills/using-superpowers/SKILL.md',
                'docs/decisions/0001-five-semantic-layers.md']
    for name in required:
        if not (root / name).is_file():
            raise ValueError('Missing: ' + name)
    plugin = json.loads((root / 'tools/superpowers/.codex-plugin/plugin.json').read_text())
    if plugin['version'] != '7.0.1':
        raise ValueError('Unexpected Superpowers version')
    print(f"PASS: {len(manifest['files'])} artifact hashes; workflow files; Superpowers {plugin['version']}.")


if __name__ == '__main__':
    main()
