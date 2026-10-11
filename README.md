# CMCC RAX3000M NAND 固件编译

独立构建工程，使用官方 OpenWrt `openwrt-24.10`，移植 `padavanonly/immortalwrt-mt798x-6.6` 的 `openwrt-24.10-6.6` 平台及 WiFi 驱动。仅适用于 CMCC RAX3000M NAND 版本。

WiFi 源码固定为 `ec9ef10efc65da1e6d1de4e2c043c0e13d08eed8`；官方 OpenWrt 分支在每次构建时拉取最新提交，实际源码版本记录在发布附件中。Linux 6.6 平台补丁、HNAT、WARP、conninfra 与厂商 WiFi 配置一起移植。

包含 LuCI、厂商 WiFi 管理页面、NPS 客户端及 LuCI 页面、zram。内核警告处理与原驱动工程一致，关闭 `CONFIG_KERNEL_WERROR`，保留日志警告与已有代码修复。

在 GitHub Actions 中打开 **Build CMCC RAX3000M OpenWrt MTK WiFi**，点击 **Run workflow**。编译成功并通过固件检查后自动创建 Release。失败时上传构建日志和配置，格式参数扫描仅提供候选问题，不替代实际编译。

构建检查包括驱动依赖、WiFi 固件、datconf 源码校验，以及生成镜像的设备标识、校验和、包清单与升级兼容元数据。镜像适用于 NAND，刷写前仍需在设备上执行 `sysupgrade -T` 并备份配置；编译检查不证明实际 WiFi、WAN 或硬件加速已通过运行测试。不会自动刷写设备。
