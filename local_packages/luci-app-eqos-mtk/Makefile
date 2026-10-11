include $(TOPDIR)/rules.mk

LUCI_TITLE:=LuCI support for Easy QoS
LUCI_DEPENDS:=+bash +ip-full +iptables-legacy +ip6tables-legacy +iptables-mod-ipopt +iptables-mod-conntrack-extra +iptables-mod-iprange +tc-full +kmod-sched-core +kmod-ifb +kmod-mediatek_hnat +ebtables-legacy-utils +ebtables-legacy @!PACKAGE_luci-app-eqos

PKG_MAINTAINER:=Jianhui Zhao <jianhuizhao329@gmail.com>
PKG_NAME:=luci-app-eqos-mtk

include $(TOPDIR)/feeds/luci/luci.mk

# call BuildPackage - OpenWrt buildroot signature
