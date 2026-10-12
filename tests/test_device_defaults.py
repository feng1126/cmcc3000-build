"""Run the real first-boot script with isolated UCI and filesystem commands."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]

class DeviceDefaults(unittest.TestCase):
    def apply(self, board, address='192.168.1.1'):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state = root / 'uci.json'
            state.write_text(json.dumps({'network.lan.ipaddr': address,
                                        'dhcp.lan.dhcpv4': 'server',
                                        'network.wan.proto': 'dhcp'}))
            (root / 'uci').write_text('#!' + sys.executable + '\n' + '''import json, os, sys
from pathlib import Path
p=Path(os.environ['TEST_UCI_STATE']); v=json.loads(p.read_text())
a=[x for x in sys.argv[1:] if x!='-q']
if a[0]=='get':
 if a[1] not in v: sys.exit(1)
 print(v[a[1]])
elif a[0]=='set':
 k,x=a[1].split('=',1);v[k]=x;p.write_text(json.dumps(v))
''')
            (root / 'cat').write_text('#!/bin/sh\nprintf "%s\\n" "$TEST_BOARD"\n')
            (root / 'ln').write_text('#!/bin/sh\nexit 0\n')
            for name in ('uci', 'cat', 'ln'):
                (root / name).chmod(0o755)
            env = dict(os.environ, PATH=str(root) + ':' + os.environ['PATH'],
                       TEST_UCI_STATE=str(state), TEST_BOARD=board)
            subprocess.run(['/bin/sh', str(REPO / 'local_packages/default-settings/files/99-default-settings')],
                           env=env, check=True, capture_output=True)
            return json.loads(state.read_text())

    def test_cmcc_ap(self):
        config = self.apply('cmcc,rax3000m')
        self.assertEqual(config['network.lan.ipaddr'], '10.10.10.100')
        self.assertEqual(config['network.lan.gateway'], '10.10.10.10')
        for key in ('dhcpv4', 'dhcpv6', 'ra', 'ndp'):
            self.assertEqual(config['dhcp.lan.' + key], 'disabled')
        self.assertEqual(config['dhcp.lan.ignore'], '1')

    def test_nokia_router(self):
        config = self.apply('nokia,ea0326gmp')
        self.assertEqual(config['network.lan.ipaddr'], '10.10.10.10')
        self.assertEqual(config['dhcp.lan.dhcpv4'], 'server')
        self.assertEqual(config['network.wan.proto'], 'dhcp')
        self.assertNotIn('dhcp.lan.ignore', config)
        self.assertNotIn('network.lan.gateway', config)

    def test_custom_lan_is_preserved(self):
        for board in ('cmcc,rax3000m', 'nokia,ea0326gmp'):
            config = self.apply(board, '172.16.10.1')
            self.assertEqual(config['network.lan.ipaddr'], '172.16.10.1')
            self.assertNotIn('dhcp.lan.ignore', config)

    def test_unknown_board_is_not_reconfigured(self):
        config = self.apply('unknown,board')
        self.assertEqual(config['network.lan.ipaddr'], '192.168.1.1')
        self.assertNotIn('dhcp.lan.ignore', config)

if __name__ == '__main__':
    unittest.main()
