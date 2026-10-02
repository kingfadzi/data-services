const fs = require('fs');
const credentials = JSON.parse(fs.readFileSync('/run/secrets/mongo_credentials', 'utf8'));
db = db.getSiblingDB('admin');
db.createUser({user: credentials.username, pwd: credentials.password,
  // Runs once on first init as the root user. clusterMonitor lets the ClearML API server read featureCompatibilityVersion.
  roles: [{role: 'readWrite', db: 'backend'}, {role: 'dbAdmin', db: 'backend'},
          {role: 'readWrite', db: 'auth'}, {role: 'dbAdmin', db: 'auth'},
          {role: 'clusterMonitor', db: 'admin'}]});
