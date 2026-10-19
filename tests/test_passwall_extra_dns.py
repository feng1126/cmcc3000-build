"""Execute the real UDP resolver setup with controlled UCI responses."""
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / 'local_packages/luci-app-passwall'
APP = (PACKAGE / 'root/usr/share/passwall/app.sh').read_text()
BLOCK = APP.split('case "$direct_dns_mode" in', 1)[1].split('udp)', 1)[1].split(';;', 1)[0]
UTILS = PACKAGE / 'root/usr/share/passwall/utils.sh'

class ResolverTests(unittest.TestCase):
    def resolve(self, shunt, primary, extras):
        normalize = 'normalize_dns() {' + UTILS.read_text().split('normalize_dns() {', 1)[1].split('\n}', 1)[0] + '\n}\n'
        script = normalize + '''
DNS_SHUNT="$2"
primary="$3"
extras="$4"
config_n_get() {
    case "$2" in
        direct_dns) printf '%s' "$primary";;
        direct_dns_extra) printf '%s' "$extras";;
    esac
}
setup() {
''' + BLOCK + '''
printf '%s\\n%s\\n' "$china_ng_local_dns" "$v2ray_local_dns"
}
setup
'''
        return subprocess.check_output(
            ['sh', '-c', script, 'test', str(UTILS), shunt, primary, extras],
            text=True).splitlines()

    def test_multiple_resolvers_keep_xray_primary(self):
        self.assertEqual(self.resolve('chinadns-ng', '211.137.58.20',
                                     '211.137.64.163 119.29.29.29'),
                         ['211.137.58.20,211.137.64.163,119.29.29.29',
                          'direct_dns_udp_server=211.137.58.20'])

    def test_empty_list_preserves_primary(self):
        self.assertEqual(self.resolve('chinadns-ng', '119.29.29.29', ''),
                         ['119.29.29.29', 'direct_dns_udp_server=119.29.29.29'])

    def test_other_shunt_ignores_extras(self):
        self.assertEqual(self.resolve('dnsmasq', '119.29.29.29', '211.137.58.20'),
                         ['119.29.29.29', 'direct_dns_udp_server=119.29.29.29'])

if __name__ == '__main__':
    unittest.main()
