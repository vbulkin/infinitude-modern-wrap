const { version } = require('./custom_components/infinitude_direct/manifest.json');
const { execSync } = require('child_process');
const tag = `v${version}`;
console.log(`Pushing ${tag}...`);
execSync('git push', { stdio: 'inherit' });
execSync('git push origin --tags', { stdio: 'inherit' });
console.log(`Pushed. To create a GitHub release, run: npm run gh-release`);
