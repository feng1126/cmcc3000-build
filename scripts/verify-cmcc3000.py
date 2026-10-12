#!/usr/bin/env python3
"""Check selected MT7981 dependencies and verify the generated NAND image."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

base = Path(sys.argv[1]).resolve()
mode = sys.argv[2]
def require(condition, message):
    if not condition:
        raise SystemExit(message)

if mode == 'config':
    config = set((base / '.config').read_text().splitlines())
    require(not (base/'target/linux/generic/pending-6.6/682-add-bcm-fullconenat-support.patch').exists(), 'BCM FullCone patch must be removed')
    require('CONFIG_PACKAGE_rust=y' not in config, 'Unexpected Rust toolchain package')
    require(not any(line.startswith('CONFIG_PACKAGE_shadowsocks-rust-') and line.endswith('=y') for line in config),
            'Shadowsocks Rust must remain disabled')
    # Custom packages do not retain the feeds' relative directory layout.
    for package, language in [('xray-core', 'golang')]:
        helper = base / 'feeds/packages/lang' / language / (language + '-package.mk')
        require(helper.is_file(), 'Missing cross-compilation helper: ' + str(helper))
        recipe = (base / 'package/custom' / package / 'Makefile').read_text()
        require('include $(TOPDIR)/feeds/packages/lang/' + language + '/' + language + '-package.mk' in recipe,
                'Wrong cross-compilation helper path for ' + package)
    require('# CONFIG_KERNEL_WERROR is not set' in config,
            'Kernel warning policy differs from the donor tree')
    required = ['TARGET_mediatek_filogic_DEVICE_cmcc_rax3000m', 'LUCI_LANG_zh_Hans']
    required += ['PACKAGE_' + p for p in [
        'kmod-mt_wifi', 'kmod-warp', 'kmod-conninfra', 'kmod-mediatek_hnat',
        'kmod-ipt-nat', 'wifi-dats', 'mtwifi-cfg', 'datconf-lua', 'wireless-tools',
        'luci', 'luci-ssl-openssl', 'luci-app-mtwifi-cfg', 'npc', 'luci-app-nps',
        'rpcd-mod-file', 'zram-swap', 'luci-app-turboacc-mtk', 'luci-app-eqos-mtk',
        'mtkhqos_util', 'mtk-smp', 'lua', 'luci-lib-nixio', 'wifi-scripts',
        'luci-i18n-turboacc-mtk-zh-cn',
        'luci-i18n-eqos-mtk-zh-cn']]
    required += ['MTK_CHIP_MT7981', 'MTK_CONNINFRA_APSOC_MT7981', 'first_card']
    extra=(Path(__file__).resolve().parents[1]/'configs/existing-software.config').read_text().splitlines()
    required += [line.split('=')[0].removeprefix('CONFIG_') for line in extra
                 if line.startswith('CONFIG_PACKAGE_') and line.endswith('=y')]
    for symbol in required:
        require('CONFIG_' + symbol + '=y' in config, 'Missing CONFIG_' + symbol)
    for value in ['CONFIG_WARP_VERSION=2', 'CONFIG_WARP_CHIPSET="mt7981"',
                  'CONFIG_first_card_name="MT7981"']:
        require(value in config, 'Wrong driver setting: ' + value)
    for package in ['kmod-mt7915e', 'kmod-mt7981-firmware', 'mt7981-wo-firmware']:
        require('CONFIG_PACKAGE_' + package + '=y' not in config,
                'Conflicting mt76 package: ' + package)
    if 'CONFIG_MTK_MT7981_NEW_FW=y' in config:
        firmware = base / 'package/mtk/drivers/mt_wifi/files/mt7981-fw-20240613'
    else:
        firmware = base / 'package/mtk/drivers/mt_wifi/src/bin/mt7981/rebb'
    for name in ['WIFI_RAM_CODE_MT7981.bin', '7981_WACPU_RAM_CODE_release.bin',
                 'mt7981_patch_e1_hdr.bin']:
        require((firmware / name).is_file(), 'Missing WiFi firmware: ' + name)
    archive = base / 'dl/datconf-6bb733f7.tar.bz2'
    require(archive.is_file(), 'Missing bundled datconf source archive')
    require(hashlib.sha256(archive.read_bytes()).hexdigest() ==
            'c1632b1950407e731c8a36b14d50d6e04bed7e7218938283e06e16ac9050d20b',
            'Bundled datconf source archive checksum mismatch')
    print('MT7981 dependencies, firmware and bundled datconf sources verified')
elif mode == 'firmware':
    target = base / 'bin/targets/mediatek/filogic'
    profiles = json.loads((target / 'profiles.json').read_text())
    require(profiles.get('target') == 'mediatek/filogic', 'Wrong target')
    profile = profiles.get('profiles', {}).get('cmcc_rax3000m', {})
    require('cmcc,rax3000m' in profile.get('supported_devices', []), 'Wrong board')
    images = [i for i in profile.get('images', []) if i.get('type') == 'sysupgrade'
              and i.get('filesystem') == 'squashfs' and i['name'].endswith('.itb')]
    require(len(images) == 1, 'Expected exactly one NAND squashfs sysupgrade FIT')
    image = target / images[0]['name']
    require(0 < image.stat().st_size < 0x7200000, 'Image exceeds raw UBI partition')
    digest = hashlib.sha256(image.read_bytes()).hexdigest()
    require(digest == images[0]['sha256'], 'Image checksum mismatch')
    manifest = target / (profile['image_prefix'] + '.manifest')
    packages = {l.split()[0] for l in manifest.read_text().splitlines() if l.strip()}
    for package in ['kmod-mt_wifi', 'kmod-warp', 'kmod-conninfra', 'kmod-mediatek_hnat',
                    'mtwifi-cfg', 'luci-app-mtwifi-cfg', 'lua', 'luci-lib-nixio', 'wifi-scripts',
                    'luci-app-passwall', 'smartdns', 'zerotier', 'cloudflared', 'ddnsto',
                    'npc', 'luci-app-nps',
                    'luci-app-turboacc-mtk', 'luci-app-eqos-mtk', 'mtkhqos_util', 'mtk-smp', 'ethtool', 'luci-theme-argon',
                    'luci-i18n-base-zh-cn', 'zram-swap', 'default-settings', 'default-settings-chn', 'kmod-nft-fullcone']:
        require(package in packages, 'Missing package in image: ' + package)
    with tempfile.TemporaryDirectory() as tmp:
        metadata_file = Path(tmp) / 'metadata.json'
        subprocess.run([str(base / 'staging_dir/host/bin/fwtool'), '-i',
                        str(metadata_file), str(image)], check=True)
        metadata = json.loads(metadata_file.read_text())
        require('cmcc,rax3000m' in metadata.get('supported_devices', []),
                'Wrong sysupgrade compatibility metadata')
    print('Verified:', image.name, 'bytes:', image.stat().st_size, 'sha256:', digest)
else:
    raise SystemExit('Unknown verification mode: ' + mode)
