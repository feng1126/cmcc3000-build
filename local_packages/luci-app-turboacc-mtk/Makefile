# SPDX-Identifier-License: GPL-3.0-only
#
# Copyright (C) 2018 Lean <coolsnowwolf@gmail.com>
# Copyright (C) 2019-2022 ImmortalWrt.org

include $(TOPDIR)/rules.mk

PKG_LICENSE:=GPL-3.0-only
PKG_RELEASE:=2

LUCI_TITLE:=LuCI support for MTK HNAT
LUCI_DEPENDS:=+kmod-nft-fullcone +nftables-json +luci-app-firewall +kmod-mediatek_hnat +kmod-tcp-bbr +luci-compat +rpcd @!PACKAGE_luci-app-turboacc
LUCI_PKGARCH:=all

include $(TOPDIR)/feeds/luci/luci.mk

# call BuildPackage - OpenWrt buildroot signature
