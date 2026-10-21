#!/usr/bin/env python3
"""Check selected MT7981 dependencies and verify the generated NAND image."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import tarfile
from device_profiles import load_device

base = Path(sys.argv[1]).resolve()
mode = sys.argv[2]
profile_name = json.loads((base / 'cmcc3000-sources.json').read_text())['profile']
device = load_device(profile_name)
def require(condition, message):
    if not condition:
        raise SystemExit(message)

if mode == 'config':
    if profile_name == 'nokia_ea0326gmp':
        platform = (base / 'target/linux/mediatek/filogic/base-files/lib/upgrade/platform.sh').read_text()
        branch = platform.split('\tnokia,ea0326gmp)\n', 1)[-1].split('\n\t\t;;', 1)[0]
        require('\tnokia,ea0326gmp)\n' in platform and
                'CI_UBIPART="ubi"' in branch and 'CI_KERNPART="kernel"' in branch and
                'CI_ROOTPART="rootfs"' in branch and 'nand_do_upgrade "$1"' in branch,
                'EA0326GMP sysupgrade TAR requires the kernel/rootfs NAND handler')
    config = set((base / '.config').read_text().splitlines())
    require(not any(line.startswith(('CONFIG_PACKAGE_mosdns=',
                                     'CONFIG_PACKAGE_luci-app-mosdns=',
                                     'CONFIG_PACKAGE_luci-i18n-mosdns-zh-cn='))
                    for line in config), 'MosDNS must not be included in the firmware')
    selected = [line for line in config if line.startswith('CONFIG_TARGET_mediatek_filogic_DEVICE_') and line.endswith('=y')]
    require(selected == ['CONFIG_TARGET_mediatek_filogic_DEVICE_' + profile_name + '=y'],
            'Expected only the selected device profile')
    require(not any(line.startswith(('CONFIG_PACKAGE_ttyd=', 'CONFIG_PACKAGE_luci-app-ttyd=',
                                    'CONFIG_PACKAGE_luci-i18n-ttyd-')) and line.endswith(('=y', '=m'))
                    for line in config), 'TTYD and its LuCI terminal must remain disabled')
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
    required = ['TARGET_mediatek_filogic_DEVICE_' + profile_name, 'LUCI_LANG_zh_Hans']
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
    profile = profiles.get('profiles', {}).get(profile_name, {})
    require(device['board'] in profile.get('supported_devices', []), 'Wrong board')
    images = [i for i in profile.get('images', []) if i.get('type') == 'sysupgrade'
              and i.get('filesystem') == 'squashfs' and i['name'].endswith(device['sysupgrade_suffix'])]
    require(len(images) == 1, 'Expected exactly one squashfs sysupgrade image for ' + profile_name)
    image = target / images[0]['name']
    require(0 < image.stat().st_size < device['ubi_size'], 'Image exceeds raw UBI partition')
    if device['sysupgrade_suffix'] == '.bin':
        with tarfile.open(image) as archive:
            members = {m.name for m in archive.getmembers() if m.isfile()}
            prefix = 'sysupgrade-' + profile_name + '/'
            require(prefix + 'kernel' in members and prefix + 'root' in members,
                    'Wrong NAND sysupgrade TAR layout')
    digest = hashlib.sha256(image.read_bytes()).hexdigest()
    require(digest == images[0]['sha256'], 'Image checksum mismatch')
    manifest = target / (profile['image_prefix'] + '.manifest')
    packages = {l.split()[0] for l in manifest.read_text().splitlines() if l.strip()}
    require(not any(p in ('ttyd', 'luci-app-ttyd') or p.startswith('luci-i18n-ttyd-')
                    for p in packages), 'Unexpected TTYD terminal in image')
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
        require(device['board'] in metadata.get('supported_devices', []),
                'Wrong sysupgrade compatibility metadata')
    print('Verified:', image.name, 'bytes:', image.stat().st_size, 'sha256:', digest)
else:
    raise SystemExit('Unknown verification mode: ' + mode)
