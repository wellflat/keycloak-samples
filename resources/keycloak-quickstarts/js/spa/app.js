import express from 'express';
import url from 'node:url';

const app = express();
const port = 8000;

app.use('/', express.static('public'));
app.use('/vendor/keycloak.js', express.static(resolveDependency('keycloak-js')));

app.listen(port, '0.0.0.0', () => {
  console.log(`Listening on port ${port}.`);
});

function resolveDependency(module) {
  return url.fileURLToPath(import.meta.resolve(module));
}
