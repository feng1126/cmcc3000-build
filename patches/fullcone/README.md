# Full Cone NAT

The module package and libnftnl, nftables and firewall4 patches are vendored from
[ImmortalWrt](https://github.com/immortalwrt/immortalwrt/tree/bf156b68e3c9829f3e494e458caf97a40413c34c)
commit `bf156b68e3c9829f3e494e458caf97a40413c34c`.
The kernel module uses [nft-fullcone](https://github.com/fullcone-nat-nftables/nft-fullcone)
commit `07d93b626ce5ea885cd16f9ab07fac3213c355d9`, with ImmortalWrt's newer kernel
validation-callback adaptation. Original attribution and licenses are retained.
Module downloads are verified by PKG_MIRROR_HASH; sources.json verifies the
vendored integration files.

Local adaptations:

- Use the local first-boot defaults for FullCone; hardware offloading remains managed by MTK TurboACC.
- Probe Full Cone only when requested, falling back to regular NAT for both
  address families if the expression is unavailable.
- Renumber the nftables patch to 900, after OpenWrt build-system patches.
- Add one combined IPv4 / IPv6 Full Cone switch and Chinese text in the standard firewall UI.
- Enable libnftnl autoreconf after modifying Makefile.am.

The installer runs after feeds update and before defconfig. CI checks package
selection, patch preparation and then compiles the module with the target kernel.
No existing router configuration is modified by this integration.

After flashing, open **Network > Firewall > General Settings > Full Cone NAT**
and Save & Apply. This sets `firewall.@defaults[0].fullcone` for IPv4 masquerading
zones. IPv6 remains disabled. The module provides Full Cone behavior for UDP;
other protocols retain masquerading. It does not increase bandwidth or bypass
upstream NAT/CGNAT. The upstream Full Cone rules do not support masq_src/masq_dest
restrictions; use the default masquerading scope with this implementation.

Verify `lsmod | grep nft_fullcone` and `nft list ruleset | grep fullcone`, then
use new UDP connections from a LAN client to test end-to-end NAT behavior.
Rule generation alone does not prove the public NAT type. Airoha hardware
flow-offload compatibility requires testing on the device; disable offloading
when isolating NAT behavior. Turn off the Full Cone flag to restore normal NAT.

The single LuCI switch writes both `fullcone` and `fullcone6`. IPv6 rules still require zone `masq6`; the switch never enables NAT66 itself.
