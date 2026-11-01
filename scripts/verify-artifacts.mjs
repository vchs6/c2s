import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
const root = process.cwd();
const manifest = JSON.parse(fs.readFileSync('docs/session/artifact-manifest.json', 'utf8'));
for (const file of manifest.files) {
  const target = path.resolve(root, file.path);
  if (!target.startsWith(root + path.sep)) throw new Error('Artifact escapes repository');
  const actual = crypto.createHash('sha256').update(fs.readFileSync(target)).digest('hex');
  if (actual !== file.sha256) throw new Error(`SHA-256 mismatch: ${file.path}`);
}
for (const required of ['AGENTS.md', 'openspec/config.yaml', '.agents/skills/openspec-propose/SKILL.md', '.agents/plugins/marketplace.json', 'tools/superpowers/skills/using-superpowers/SKILL.md', 'docs/decisions/0001-five-semantic-layers.md']) {
  if (!fs.existsSync(required)) throw new Error(`Missing: ${required}`);
}
const plugin = JSON.parse(fs.readFileSync('tools/superpowers/.codex-plugin/plugin.json', 'utf8'));
if (plugin.version !== '7.0.1') throw new Error('Unexpected Superpowers version');
console.log(`PASS: ${manifest.files.length} original artifact hashes; workflow files; Superpowers ${plugin.version}.`);
