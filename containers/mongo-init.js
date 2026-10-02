const fs = require('fs');
const credentials = JSON.parse(fs.readFileSync('/run/secrets/mongo_credentials', 'utf8'));
db = db.getSiblingDB('admin');
db.createUser({user: credentials.username, pwd: credentials.password,
  roles: [{role: 'readWrite', db: 'backend'}, {role: 'dbAdmin', db: 'backend'},
          {role: 'readWrite', db: 'auth'}, {role: 'dbAdmin', db: 'auth'}]});
