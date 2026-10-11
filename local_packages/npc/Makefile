include $(TOPDIR)/rules.mk

PKG_NAME:=npc
PKG_VERSION:=0.26.38
PKG_RELEASE:=1
PKG_SOURCE:=linux_arm64_client.tar.gz
PKG_SOURCE_URL:=https://github.com/yisier/nps/releases/download/v$(PKG_VERSION)/
PKG_HASH:=140cc423c3a926039d3c9b615b8dfeea3bc673a40d506ebea704835efa7be806
PKG_BUILD_DIR:=$(BUILD_DIR)/npc-$(PKG_VERSION)
PKG_LICENSE:=GPL-3.0

include $(INCLUDE_DIR)/package.mk

define Package/npc
  SECTION:=net
  CATEGORY:=Network
  TITLE:=NPS ARM64 client
  DEPENDS:=@aarch64
endef

define Package/npc/conffiles
/etc/config/npc
/etc/npc/
endef

define Build/Prepare
	mkdir -p $(PKG_BUILD_DIR)
	tar -xzf $(DL_DIR)/$(PKG_SOURCE) -C $(PKG_BUILD_DIR)
endef

define Build/Configure
endef

define Build/Compile
endef

define Package/npc/install
	$(INSTALL_DIR) $(1)/usr/bin $(1)/etc/config $(1)/etc/init.d
	$(INSTALL_BIN) $(PKG_BUILD_DIR)/npc $(1)/usr/bin/npc
	$(INSTALL_CONF) ./files/npc.config $(1)/etc/config/npc
	$(INSTALL_BIN) ./files/npc-codexweb $(1)/etc/init.d/npc-codexweb
endef

$(eval $(call BuildPackage,npc))
