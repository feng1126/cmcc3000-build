#!/usr/bin/env python3
"""Install vendored Full Cone support into a fresh OpenWrt source tree."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

REPO = Path(__file__).resolve().parents[1]
PATCHES = REPO / 'patches/fullcone'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    source = parser.parse_args().source.resolve()
    manifest = json.loads((PATCHES / 'sources.json').read_text())
    for name, expected in manifest['sha256'].items():
        if hashlib.sha256((REPO / name).read_bytes()).hexdigest() != expected:
            raise SystemExit(f'Full Cone source checksum mismatch: {name}')
    for component, relative in {
        'libnftnl': 'package/libs/libnftnl',
        'nftables': 'package/network/utils/nftables',
        'firewall4': 'package/network/config/firewall4',
    }.items():
        target = source / relative
        if not (target / 'Makefile').is_file():
            raise SystemExit(f'Required package missing: {relative}')
        (target / 'patches').mkdir(exist_ok=True)
        for patch in sorted((PATCHES / component).glob('*.patch')):
            output = target / 'patches' / patch.name
            if output.exists() and output.read_bytes() != patch.read_bytes():
                raise SystemExit(f'Conflicting patch: {output}')
            shutil.copyfile(patch, output)
            print(f'Installed {relative}/patches/{patch.name}', flush=True)
    # The libnftnl patch changes Makefile.am; regenerate with OpenWrt host tools.
    makefile = source / 'package/libs/libnftnl/Makefile'
    text = makefile.read_text()
    if 'PKG_FIXUP:=autoreconf' not in text:
        marker = 'include $(INCLUDE_DIR)/package.mk'
        if text.count(marker) != 1 or 'PKG_FIXUP' in text:
            raise SystemExit('Review changed libnftnl build system')
        makefile.write_text(text.replace(marker, 'PKG_FIXUP:=autoreconf\n\n' + marker))
    target = source / 'package/custom/fullconenat-nft'
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(REPO / 'local_packages/fullconenat-nft', target)
    luci = source / 'feeds/luci/applications/luci-app-firewall'
    subprocess.run(['patch', '--batch', '--forward', '--fuzz=0', '-p1',
                    '-i', str(PATCHES / 'luci/001-fullcone-switch.patch')],
                   cwd=luci, check=True)
    po = luci / 'po/zh_Hans/firewall.po'
    if 'msgid "Full Cone NAT"' in po.read_text():
        raise SystemExit('Full Cone translations already exist; review feed changes')
    with po.open('a') as f:
        f.write('\n' + (PATCHES / 'luci/zh_Hans.po').read_text())
    print('Full Cone support installed; fw4 controls IPv4 / IPv6 activation.')
    print('Source: ' + manifest['upstream'] + ' @ ' + manifest['commit'])


if __name__ == '__main__':
    main()
