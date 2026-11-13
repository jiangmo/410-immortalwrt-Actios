import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/package-selection.py'
PACKAGES = 'luci-theme-argon luci-app-openclash luci-app-ttyd luci-app-dockerman luci-app-istore'


class PackageSelectionTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.config = self.root / '.config'
        self.config.write_text('# CONFIG_PACKAGE_luci-app-ttyd is not set\nCONFIG_PACKAGE_luci-theme-argon=y\n', encoding='utf-8')

    def run_script(self, *args, ok=True):
        result = subprocess.run([sys.executable, '-X', 'utf8', str(SCRIPT), *args], cwd=self.root,
                                capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(result.returncode, 0 if ok else 1, result.stdout + result.stderr)
        return result

    def state(self):
        return json.loads((self.root / 'package-selection.json').read_text(encoding='utf-8'))

    def prepare(self):
        self.run_script('prepare', '--packages', PACKAGES)

    def test_alias_dedup_and_replacement(self):
        self.run_script('prepare', '--packages', PACKAGES + ',luci-app-store,luci-app-ttyd')
        names = [p['resolved'] for p in self.state()['packages']]
        self.assertEqual(len(names), 6)
        self.assertIn('luci-app-store', names)
        self.assertIn('luci-compat', names)
        config = self.config.read_text(encoding='utf-8')
        self.assertEqual(config.count('CONFIG_PACKAGE_luci-app-ttyd=y'), 1)
        self.assertNotIn('is not set', config)

    def test_invalid_input_is_atomic(self):
        before = self.config.read_bytes()
        self.run_script('prepare', '--packages', 'luci-app-ttyd $(bad)', ok=False)
        self.assertEqual(self.config.read_bytes(), before)

    def test_reproduce_original_missing_packages(self):
        self.prepare()
        # These were the only requested packages selected by run 43367019583.
        self.config.write_text('CONFIG_PACKAGE_luci-app-ttyd=y\nCONFIG_PACKAGE_luci-app-dockerman=y\n', encoding='utf-8')
        result = self.run_script('check-config', ok=False)
        for name in ['luci-theme-argon', 'luci-app-openclash', 'luci-app-store']:
            self.assertIn(name, result.stderr)
        self.run_script('release', ok=False)

    def test_module_is_not_builtin(self):
        self.prepare()
        self.config.write_text(self.config.read_text(encoding='utf-8').replace('luci-app-ttyd=y', 'luci-app-ttyd=m'), encoding='utf-8')
        self.run_script('check-config', ok=False)

    def manifest(self, filename='firmware.manifest', omit=None):
        path = self.root / filename
        path.write_text(''.join(f"{p['resolved']} - 1.2.3\n" for p in self.state()['packages'] if p['resolved'] != omit), encoding='utf-8')
        return str(path)

    def test_valid_release_uses_real_names_and_versions(self):
        self.prepare()
        self.run_script('check-config')
        self.run_script('check-manifest', '--manifest', self.manifest())
        result = self.run_script('release')
        self.assertIn('luci-app-istore | luci-app-store', result.stdout)
        self.assertIn('1.2.3', result.stdout)
        self.assertTrue(self.state()['manifest_verified'])

    def test_one_incomplete_manifest_blocks_release(self):
        self.prepare()
        self.run_script('check-config')
        self.run_script('check-manifest', '--manifest', self.manifest(), self.manifest('bad.manifest', 'luci-theme-argon'), ok=False)
        self.run_script('release', ok=False)

    def test_default_argon_is_audited(self):
        self.run_script('prepare')
        self.assertEqual(self.state()['packages'][0]['resolved'], 'luci-theme-argon')
        self.config.write_text('', encoding='utf-8')
        self.run_script('check-config', ok=False)

    def test_manifest_requires_config_verification(self):
        self.prepare()
        self.run_script('check-manifest', '--manifest', self.manifest(), ok=False)


if __name__ == '__main__':
    unittest.main()
