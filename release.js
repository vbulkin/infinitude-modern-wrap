const { execSync } = require('child_process');
const fs = require('fs');

// Read current version from manifest.json
const manifest = JSON.parse(fs.readFileSync('custom_components/infinitude_direct/manifest.json', 'utf8'));
const current = manifest.version;
const parts = current.split('.');
parts[2] = String(Number(parts[2]) + 1);
const next = parts.join('.');

// Bump version in all files
function sed(file, pattern, replacement) {
  const content = fs.readFileSync(file, 'utf8');
  const updated = content.replace(pattern, replacement);
  if (content === updated) console.warn(`  WARNING: no change in ${file}`);
  fs.writeFileSync(file, updated);
}

console.log(`Bumping ${current} → ${next}`);
sed('infinitude/config.yaml', `version: "${current}"`, `version: "${next}"`);
sed('infinitude/infinitude-ui.html', `const APP_VERSION = '${current}'`, `const APP_VERSION = '${next}'`);
sed('custom_components/infinitude_direct/manifest.json', `"version": "${current}"`, `"version": "${next}"`);
sed('src/infinitude-hvac-card.js', `const CARD_VERSION = '${current}'`, `const CARD_VERSION = '${next}'`);

// Build
execSync('npm run build --silent', { stdio: 'inherit' });

// Commit, tag, push
const tag = `v${next}`;
execSync('git add -A', { stdio: 'inherit' });
execSync(`git commit -m "Release ${tag}"`, { stdio: 'inherit' });
execSync(`git tag -a ${tag} -m "Release ${tag}"`, { stdio: 'inherit' });
execSync('git push', { stdio: 'inherit' });
execSync('git push origin --tags', { stdio: 'inherit' });
console.log(`Released ${tag}. To create a GitHub release, run: npm run gh-release`);
