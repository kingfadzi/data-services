import importlib.util
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('render', ROOT / 'tools/render.py')
render = importlib.util.module_from_spec(spec)
spec.loader.exec_module(render)


class RenderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.env = render.env_file(ROOT / '.env.example')
        self.env['DATA_HOST'] = 'data-host'  # placeholder in the example is CHANGE_ME

    def tearDown(self):
        self.temp.cleanup()

    def test_credentials_stable_and_exported(self):
        render.render(self.root, self.env, self.root)
        first = (self.root / 'generated/credentials.json').read_bytes()
        render.render(self.root, self.env, self.root)
        self.assertEqual(first, (self.root / 'generated/credentials.json').read_bytes())
        connection = render.env_file(self.root / 'generated/clearml.env')
        self.assertIn('/backend?authSource=admin', connection['MONGO_BACKEND_URI'])
        self.assertEqual(connection['REDIS_TLS'], 'false')
        compose_env = render.env_file(self.root / 'generated/compose.env')
        self.assertEqual(compose_env['ES_TLS_DIR'], str(self.root / 'generated/no-tls'))
        self.assertEqual(compose_env['MONGO_TLS_ARGS'], '')
        self.assertTrue((self.root / 'generated/no-tls').is_dir())
        self.assertEqual((self.root / 'generated/mongo_root_username').read_text(), 'admin')
        self.assertTrue((self.root / 'generated/mongo_root_password').stat().st_size)
        self.assertEqual((self.root / 'generated/credentials.json').stat().st_mode & 0o777, 0o600)
        self.assertEqual((self.root / 'generated/redis.conf').stat().st_mode & 0o777, 0o644)
        self.assertEqual((self.root / 'generated/mssql.conf').stat().st_mode & 0o777, 0o644)
        self.assertEqual((self.root / 'generated/sqlserver_sa_password').stat().st_mode & 0o777, 0o600)
        self.assertIn('memorylimitmb = 2048', (self.root / 'generated/mssql.conf').read_text())
        self.assertNotIn('[network]', (self.root / 'generated/mssql.conf').read_text())
        sqlserver = render.env_file(self.root / 'generated/sqlserver.env')
        self.assertEqual(sqlserver['SQLSERVER_HOST'], 'data-host')
        self.assertIn('databaseName=appdb;encrypt=false', sqlserver['SQLSERVER_JDBC_URL'])
        self.assertEqual((self.root / 'generated/mongo_credentials').stat().st_mode & 0o777, 0o600)
        self.assertEqual((self.root / 'generated').stat().st_mode & 0o777, 0o700)

    def test_sqlserver_passwords_satisfy_the_policy(self):
        # token_hex is lower case and digits only, which SQL Server refuses; see render.COMPLEX.
        render.render(self.root, self.env, self.root)
        import json
        credentials = json.loads((self.root / 'generated/credentials.json').read_text())
        for key in ('SQLSERVER_SA_PASSWORD', 'SQLSERVER_PASSWORD'):
            self.assertRegex(credentials[key], render.COMPLEX)
            self.assertEqual(credentials[key], (self.root / f'generated/{key.lower()}').read_text())

    def test_sqlserver_password_without_complexity_fails(self):
        self.env['SQLSERVER_SA_PASSWORD'] = 'alllowercaseandnodigits'
        with self.assertRaises(render.Error):
            render.render(self.root, self.env, self.root)

    def test_sqlserver_login_cannot_silently_change(self):
        render.render(self.root, self.env, self.root)
        self.env['SQLSERVER_USERNAME'] = 'someone-else'
        with self.assertRaises(render.Error):
            render.render(self.root, self.env, self.root)

    def test_low_max_map_count_disables_mmap(self):
        import json
        render.render(self.root, self.env, self.root, map_count=65530)
        self.assertFalse(json.loads((self.root / 'generated/elasticsearch.yml').read_text())['node.store.allow_mmap'])
        render.render(self.root, self.env, self.root, map_count=262144)
        self.assertNotIn('node.store.allow_mmap', json.loads((self.root / 'generated/elasticsearch.yml').read_text()))
    def test_credentials_cannot_silently_rotate(self):
        render.render(self.root, self.env, self.root)
        self.env['REDIS_PASSWORD'] = 'a-different-password'
        with self.assertRaises(render.Error):
            render.render(self.root, self.env, self.root)

    def test_tls_missing_certificates_fails(self):
        self.env['TLS_ENABLED'] = 'true'
        with self.assertRaises(render.Error):
            render.render(self.root, self.env, self.root)

    def test_tls_mount_uses_host_path(self):
        self.env['TLS_ENABLED'] = 'true'
        tls = self.root / 'config/tls'
        tls.mkdir(parents=True)
        for name in ('ca.pem', 'server.crt', 'server.key', 'mongo.pem'):
            (tls / name).write_text('x')
        render.render(self.root, self.env, '/srv/data-services', tls)
        compose_env = render.env_file(self.root / 'generated/compose.env')
        self.assertEqual(compose_env['MONGO_TLS_DIR'], '/srv/data-services/generated/private/mongo/tls')
        self.assertIn('--tlsMode requireTLS', compose_env['MONGO_TLS_ARGS'])
        self.assertEqual(compose_env['ES_SCHEME'], 'https')
        self.assertIn('tls-port 6379', (self.root / 'generated/redis.conf').read_text())
        self.assertEqual(render.env_file(self.root / 'generated/clearml.env')['REDIS_TLS'], 'true')
        self.assertEqual(compose_env['SQLSERVER_TLS_DIR'], '/srv/data-services/generated/private/sqlserver/tls')
        self.assertIn('forceencryption = 1', (self.root / 'generated/mssql.conf').read_text())
        self.assertIn('encrypt=true', render.env_file(self.root / 'generated/sqlserver.env')['SQLSERVER_JDBC_URL'])

    def test_datactl_rejects_bad_env_and_honours_blank_allowlist(self):
        env=self.root/'bad.env'; env.write_text('A=1\nA=2\n')
        self.assertNotEqual(subprocess.run(['bash',str(ROOT/'datactl'),'--env',str(env),'status'],capture_output=True).returncode,0)
        text=(ROOT/'datactl').read_text()
        self.assertNotIn('YUM_REPO_FILE',text); self.assertIn('BASE_IMAGE',text); self.assertIn('mongo-restore',text); self.assertNotIn('TOOLBOX_IMAGE',text); self.assertNotIn('REDIS_BASE_IMAGE',text); self.assertIn('pull_policy', (ROOT/'compose.yaml').read_text()); self.assertIn('SQLSERVER_FTS_IMAGE', text); self.assertIn('stage sqlserver', text)
    def test_datactl_is_bash_and_parses(self):
        subprocess.run(['bash', '-n', str(ROOT / 'datactl')], check=True)
        subprocess.run(['bash', '-n', str(ROOT / 'containers/sqlserver/entrypoint.sh')], check=True)
        text = (ROOT / 'datactl').read_text()
        self.assertTrue(text.startswith('#!/usr/bin/env bash'))
        # python3 may appear only inside the container invocation.
        self.assertEqual([l for l in text.splitlines() if 'python' in l and 'docker run' not in l], [])

    @unittest.skipUnless(shutil.which('docker'), 'Docker CLI required (daemon not needed)')
    def test_compose_model_valid(self):
        render.render(self.root, self.env, self.root)
        subprocess.run(['docker', 'compose', '--project-directory', str(ROOT), '--env-file', str(ROOT / '.env.example'),
                        '--env-file', str(self.root / 'generated/compose.env'), '-f', str(ROOT / 'compose.yaml'),
                        'config', '--quiet'], check=True)


if __name__ == '__main__':
    unittest.main()
