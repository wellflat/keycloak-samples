const baseUrl = 'http://localhost:8080';

export default {
  baseUrl: baseUrl,
  token: {
    username: 'alice',
    password: 'alice',
    grant_type: 'password',
    client_id: 'test-cli',
    realmName: 'quickstart'
  },
  adminClient: {
    baseUrl: baseUrl,
    realmName: 'master',
    username: 'admin',
    password: 'admin',
    grantType: 'password',
    clientId: 'admin-cli'
  }
};
