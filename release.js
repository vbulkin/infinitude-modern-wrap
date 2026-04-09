const { version } = require('./custom_components/infinitude_direct/manifest.json');
const { execSync } = require('child_process');
const tag = `v${version}`;
console.log(`Releasing ${tag}...`);
execSync('git push', { stdio: 'inherit' });
execSync('git push origin --tags', { stdio: 'inherit' });
try {
  execSync(`gh release create ${tag} --title ${tag} --generate-notes`, { stdio: 'inherit' });
} catch (e) {
  console.log(`Release ${tag} may already exist, skipping.`);
}
