import importlib.util
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('render', ROOT / 'containers/tools/render.py')
render = importlib.util.module_from_spec(spec)
spec.loader.exec_module(render)


class RenderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.env = render.env_file(ROOT / '.env.example')

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
        self.assertEqual(compose_env['TLS_MOUNT_DIR'], str(self.root / 'generated/no-tls'))
        self.assertTrue((self.root / 'generated/no-tls').is_dir())
        self.assertEqual((self.root / 'generated/credentials.json').stat().st_mode & 0o777, 0o600)
        self.assertEqual((self.root / 'generated/redis.conf').stat().st_mode & 0o777, 0o644)

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
        self.assertEqual(compose_env['TLS_MOUNT_DIR'], '/srv/data-services/config/tls')
        self.assertIn('tls-port 6379', (self.root / 'generated/redis.conf').read_text())
        self.assertEqual(render.env_file(self.root / 'generated/clearml.env')['REDIS_TLS'], 'true')

    def test_datactl_rejects_bad_env_and_honours_blank_allowlist(self):
        env=self.root/'bad.env'; env.write_text('A=1\nA=2\n')
        self.assertNotEqual(subprocess.run(['bash',str(ROOT/'datactl'),'--env',str(env),'status'],capture_output=True).returncode,0)
        text=(ROOT/'datactl').read_text()
        self.assertNotIn('YUM_REPO_FILE',text); self.assertIn('proxy_args',text); self.assertIn('TLS_CA_BUNDLE_URL',text); self.assertNotIn('CA_BUNDLE=',text); self.assertIn('tls-ca-bundle.pem',text); self.assertIn('--cacert',text)
    def test_datactl_is_bash_and_parses(self):
        subprocess.run(['bash', '-n', str(ROOT / 'datactl')], check=True)
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
