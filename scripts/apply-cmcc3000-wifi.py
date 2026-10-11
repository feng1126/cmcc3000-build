#!/usr/bin/env python3
"""Import the Linux 6.6 MTK wireless/platform stack into official OpenWrt."""
from pathlib import Path
import shutil,sys,json,subprocess,re,hashlib
base=Path(sys.argv[1]).resolve();src=Path(sys.argv[2]).resolve()
def tree(rel):
 s=src/rel;d=base/rel
 if not s.is_dir():raise RuntimeError('Missing source '+rel)
 if d.exists():shutil.rmtree(d)
 shutil.copytree(s,d,symlinks=True)
# Keep official target identity/default packages, but use matching vendor DTS,
# platform patches and generic kernel patch baseline for the MTK kernel ABI.
original=(base/'target/linux/mediatek/Makefile').read_text()
if 'KERNEL_PATCHVER:=6.6' not in original:raise RuntimeError('Expected OpenWrt 24.10 / Linux 6.6')
tree('target/linux/mediatek')
(base/'target/linux/mediatek/Makefile').write_text(original)
# The donor declares tagged structures without objects; static is invalid there.
p=base/'target/linux/mediatek/patches-6.6/999-2903-mtk-enhance.patch'
s=p.read_text()
if s.count('+static struct hnat_desc {') != 3:
 raise RuntimeError('Unexpected donor HNAT descriptor patch')
p.write_text(s.replace('+static struct hnat_desc {', '+struct hnat_desc {'))
# MT7981 shaper arrays have MTK_QDMA_NUM_QUEUES elements (16), not 64.
p=base/'target/linux/mediatek/patches-6.6/9999-01-hnat.patch'
s=p.read_text()
if s.count('+\tfor (i = 0; i < 64; i++)') != 3:
 raise RuntimeError('Unexpected donor QDMA queue loops')
p.write_text(s.replace('+\tfor (i = 0; i < 64; i++)',
                       '+\tfor (i = 0; i < MTK_QDMA_NUM_QUEUES; i++)'))
# Copy into the destination buffer using its size, not the source size.
p=base/'target/linux/mediatek/files-6.6/drivers/net/wireless/wifi_utility/pci_mediatek_rbus.c'
s=p.read_text()
old='strncpy(state, "state_epa", sizeof("state_epa"));'
if s.count(old) != 1: raise RuntimeError('Unexpected donor pinctrl state copy')
p.write_text(s.replace(old, 'strncpy(state, "state_epa", sizeof(state));'))
# Both shaper helpers must reject negative and one-past-the-end queue IDs.
p=base/'target/linux/mediatek/patches-6.6/999-2730-net-ethernet-mtk_eth_soc-record-PPPQ-status-in-the-mtk_qdma_shaper.patch'
s=p.read_text()
old='!mtk_is_netsys_v3_or_greater(eth) || idx > MTK_QDMA_NUM_QUEUES'
if s.count(old) != 1: raise RuntimeError('Unexpected donor shaper bounds')
s=s.replace(old, '!mtk_is_netsys_v3_or_greater(eth) || idx < 0 || idx >= MTK_QDMA_NUM_QUEUES')
old='+\tif (!mtk_is_netsys_v3_or_greater(eth))'
if s.count(old) != 1: raise RuntimeError('Unexpected donor shaper update guard')
p.write_text(s.replace(old, '+\tif (!mtk_is_netsys_v3_or_greater(eth) || idx < 0 || idx >= MTK_QDMA_NUM_QUEUES)'))


for part in ['backport-6.6','pending-6.6','hack-6.6','files','files-6.6']:
 rel='target/linux/generic/'+part
 if (src/rel).is_dir():tree(rel)
for rel in ['target/linux/generic/config-6.6','include/kernel-6.6']:
 shutil.copy2(src/rel,base/rel)
for rel in ['package/mtk/drivers','package/network/utils/iwinfo','package/network/config/wifi-scripts']:
 tree(rel)
# Correct WARP diagnostics rejected by the official compiler's format checks.
p=base/'package/mtk/drivers/warp/src/warp_main.c'
s=p.read_text()
old='"%s()======WO PC LR dump======\\n", __func__, heart_beat'
if s.count(old) != 4: raise RuntimeError('Unexpected WARP diagnostic calls')
s=s.replace(old, '"%s()======WO PC LR dump======\\n", __func__')
a=s.index('warp_isr_handler(void *priv_data)');b=s.index('EXPORT_SYMBOL(warp_isr_handler);',a)
body=s[a:b]
old='\tstruct wifi_entry *wifi = &warp->wifi;\n\tstruct wifi_hw *hw = &wifi->hw;\n'
if body.count(old) != 1: raise RuntimeError('Unexpected WARP ISR locals')
s=s[:a]+body.replace(old,'')+s[b:]
p.write_text(s)
# This token release callback is disabled in the donor. Preserve its return
# behavior without compiling leftover variables and an unreachable label.
p=base/'package/mtk/drivers/warp/src/wed.c'
s=p.read_text()
a=s.index('int wed_release_rx_token(');b=s.index('\n#endif\t/* WED_RX_D_SUPPORT */',a)
body=s[a:b]
if '#if 0' not in body or body.count('err:') != 1:
 raise RuntimeError('Unexpected WARP token release implementation')
s=s[:a]+"int wed_release_rx_token(struct wed_entry *wed, u32 token_id)\n{\n\treturn wed ? 0 : -1;\n}\n"+s[b:]
old='buf_free_task((unsigned long)wed);'
if s.count(old) != 1: raise RuntimeError('Unexpected WARP buffer free call')
p.write_text(s.replace(old, 'buf_free_task(wed);'))
# MT7981 uses the v2 register implementation; its reset diagnostics also
# passed a return code with no matching format conversion.
p=base/'package/mtk/drivers/warp/src/regs/reg_v2/warp_hw_v2.c'
s=p.read_text()
old='"%s(): check ser_busy_cnt: echo 18 > wed\\n", __func__, ret'
if s.count(old) != 3: raise RuntimeError('Unexpected WARP v2 reset logs')
p.write_text(s.replace(old, '"%s(): check ser_busy_cnt: echo 18 > wed\\n", __func__'))
for name in ['datconf','mtwifi-cfg','luci-app-mtwifi-cfg']:
 tree('package/mtk/applications/'+name)
# The donor vendors this source archive in dl/ instead of defining a download URL.
archive='datconf-6bb733f7.tar.bz2'
checksum='c1632b1950407e731c8a36b14d50d6e04bed7e7218938283e06e16ac9050d20b'
if hashlib.sha256((src/'dl'/archive).read_bytes()).hexdigest() != checksum:
 raise RuntimeError('Datconf source archive checksum mismatch')
(base/'dl').mkdir(exist_ok=True)
shutil.copy2(src/'dl'/archive,base/'dl'/archive)

# Declare the vendor HNAT kernel module required by mt_wifi and warp.
p=base/'package/kernel/linux/modules/netdevices.mk';s=p.read_text()
v=(src/'package/kernel/linux/modules/netdevices.mk').read_text()
block=v[v.index('define KernelPackage/mediatek_hnat\n'):]
block=block[:block.index('$(eval $(call KernelPackage,mediatek_hnat))')+len('$(eval $(call KernelPackage,mediatek_hnat))')]
# HNAT's kernel Kconfig depends on IP_NF_NAT. Official nftables-only defaults
# do not enable it, unlike the donor's full router configuration.
block=block.replace('+kmod-nf-conntrack', '+kmod-nf-conntrack +kmod-ipt-nat')
if 'define KernelPackage/mediatek_hnat\n' not in s:p.write_text(s+'\n'+block+'\n')
# The image must use the vendor stack, not the default mt76 driver.
p=base/'target/linux/mediatek/image/filogic.mk';s=p.read_text()
a=s.index('define Device/cmcc_rax3000m_common\n');b=s.index('\nendef',a)
block=s[a:b]
block=block.replace('kmod-mt7915e kmod-mt7981-firmware mt7981-wo-firmware','kmod-mt_wifi mtwifi-cfg luci-app-mtwifi-cfg').replace('automount f2fsck mkf2fs','block-mount f2fsck mkf2fs')
s=s[:a]+block+s[b:];p.write_text(s)
# Generate a small router profile, keeping the complete donor MT7981 driver flags.
seed=(src/'defconfig/mt7981-ax3000.config').read_text().splitlines()
flags=[l for l in seed if re.match(r'(?:# )?CONFIG_(MTK_|WARP_|WED_|FPGA_|CONNINFRA_|first_card|second_card|third_card|WIFI_|RT_FIRST_|RT_SECOND_)',l)]
config='''CONFIG_TARGET_mediatek=y
# CONFIG_KERNEL_WERROR is not set
CONFIG_TARGET_mediatek_filogic=y
CONFIG_TARGET_mediatek_filogic_DEVICE_cmcc_rax3000m=y
CONFIG_PACKAGE_kmod-mt_wifi=y
CONFIG_PACKAGE_kmod-conninfra=y
CONFIG_PACKAGE_kmod-warp=y
CONFIG_PACKAGE_kmod-mediatek_hnat=y
CONFIG_PACKAGE_wifi-dats=y
CONFIG_PACKAGE_mtwifi-cfg=y
CONFIG_PACKAGE_luci-app-mtwifi-cfg=y
CONFIG_PACKAGE_datconf-lua=y
CONFIG_PACKAGE_wireless-tools=y
CONFIG_PACKAGE_luci=y
CONFIG_PACKAGE_luci-ssl-openssl=y
CONFIG_PACKAGE_luci-i18n-base-zh-cn=y
CONFIG_PACKAGE_luci-i18n-mtwifi-cfg-zh-cn=y
CONFIG_PACKAGE_npc=y
CONFIG_PACKAGE_luci-app-nps=y
CONFIG_PACKAGE_openssh-sftp-server=y
CONFIG_PACKAGE_curl=y
CONFIG_PACKAGE_ca-bundle=y
CONFIG_PACKAGE_zram-swap=y
CONFIG_PACKAGE_kmod-zram=y
CONFIG_PACKAGE_block-mount=y
CONFIG_PACKAGE_f2fsck=y
CONFIG_PACKAGE_mkf2fs=y
CONFIG_TARGET_ROOTFS_PARTSIZE=64
# CONFIG_PACKAGE_kmod-mt7915e is not set
# CONFIG_PACKAGE_kmod-mt7981-firmware is not set
# CONFIG_PACKAGE_mt7981-wo-firmware is not set
'''
(base/'.config').write_text(config+'\n'.join(flags)+'\n')
meta={'base':'official OpenWrt openwrt-24.10','wifi_repository':'padavanonly/immortalwrt-mt798x-6.6','wifi_branch':'openwrt-24.10-6.6','wifi_commit':subprocess.check_output(['git','-C',str(src),'rev-parse','HEAD'],text=True).strip(),'profile':'cmcc_rax3000m','storage':'NAND','kernel':(src/'include/kernel-6.6').read_text().strip(),'overlay':'MTK platform, generic Linux 6.6 patches, wireless stack'}
(base/'cmcc3000-sources.json').write_text(json.dumps(meta,indent=2)+'\n')
print(json.dumps(meta,indent=2))
