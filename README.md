# mt7981-openwrt-build

独立构建工程，使用官方 OpenWrt `openwrt-24.10`，移植 `padavanonly/immortalwrt-mt798x-6.6` 的 `openwrt-24.10-6.6` 平台及 WiFi 驱动。支持 CMCC RAX3000M NAND 和 Nokia EA0326GMP NAND。

WiFi 源码固定为 `ec9ef10efc65da1e6d1de4e2c043c0e13d08eed8`；官方 OpenWrt 分支在每次构建时拉取最新提交，实际源码版本记录在发布附件中。Linux 6.6 平台补丁、HNAT、WARP、conninfra 与厂商 WiFi 配置一起移植。

包含 LuCI、厂商 WiFi 管理页面、NPS 客户端及 LuCI 页面、zram。内核警告处理与原驱动工程一致，关闭 `CONFIG_KERNEL_WERROR`，保留日志警告与已有代码修复。

在 GitHub Actions 中打开 **mt7981-openwrt-build**，点击 **Run workflow**，通过 `device` 选择 `cmcc_rax3000m` 或 `nokia_ea0326gmp`。编译成功并通过固件检查后自动创建 Release。失败时上传构建日志和配置，格式参数扫描仅提供候选问题，不替代实际编译。

构建检查包括驱动依赖、WiFi 固件、datconf 源码校验，以及生成镜像的设备标识、校验和、包清单与升级兼容元数据。镜像适用于 NAND，刷写前仍需在设备上执行 `sysupgrade -T` 并备份配置；编译检查不证明实际 WiFi、WAN 或硬件加速已通过运行测试。不会自动刷写设备。

## 设备选择

两个设备共用 OpenWrt 分支、MTK WiFi/HNAT 驱动和软件清单，均不包含 ttyd。工作流每次只编译所选设备；设备树、镜像定义、升级元数据和容量检查按设备切换。

| device | 设备 | sysupgrade 格式 | UBI 分区容量 | 默认网络用途 |
|---|---|---|---|---|
| `cmcc_rax3000m` | CMCC RAX3000M NAND | `.itb` FIT | 114 MiB | AP，LAN 10.10.10.100，关闭 DHCP |
| `nokia_ea0326gmp` | Nokia EA0326GMP NAND | `.bin` sysupgrade TAR | 110 MiB | 路由器，LAN 10.10.10.10，WAN DHCP |

2026-10-12 检查的 EA0326GMP 正在运行 OpenWrt 24.10-SNAPSHOT / Linux 6.6.95，使用厂商 `mt_wifi`，256 MiB RAM。`192.168.10.100` 是其 ZeroTier 地址，不是默认 LAN 地址。新配置复用现有软件包并包含 zram，不代表所有服务应同时启动。不同设备的镜像不能互刷。

## MTK 加速插件

迁移自固定版本的原驱动仓库，作为本工程 `local_packages` 管理：

- `luci-app-turboacc-mtk`：网络 → TurboACC，支持有线 HNAT、IPv6 HNAT、绑定阈值、运行状态与各 PPE 表使用量进度条。WiFi 的 Wireless HWNAT 开关在无线管理页面。
- `luci-app-eqos-mtk`：EQoS 设备限速及硬件 QoS 页面，默认关闭。原后端依赖 64 个硬件队列；当前 MT7981 移植限定为 16 个队列，启动时拒绝不兼容的硬件接口，暂不能在本设备启用该后端。
- `mtkhqos_util`：16 队列硬件 QoS 命令行工具，默认不执行；需要明确设置 `/etc/config/mtkhqos` 的 `global.enabled=1` 后启动服务。它与 EQoS 不应同时管理队列。
- `mtk-smp`：原仓库的 MT7981 中断/RPS CPU 分配脚本，随系统启动，把 WiFi 中断分配到 CPU1，无线 RPS 使用两个核心。显式依赖 `ethtool`，确保脚本的 GRO 设置能执行。

TurboACC 已精简原仓库的无关依赖，移除 AP 网络重写与没有后端实现的 PPE 数量选项；保存 FullCone 设置由 LuCI 应用防火墙配置；HNAT 参数由 TurboACC 服务应用。实际 HNAT 状态和 PPE 统计来自驱动 debugfs。现有已绑定连接在关闭加速后是否立即清除取决于驱动行为，测试应使用新连接。

## 原 AP 软件配置

`configs/existing-software.config` 按 10.10.10.100 刷机前清单补齐主要软件和管理页面，包括 PassWall（Xray、Sing-box、HAProxy；Shadowsocks Rust 已禁用）、SmartDNS、ZeroTier、Cloudflared、DDNSTO、DDNS、微信推送、Socat、MQTT、流量统计、Argon 和诊断/存储工具。TTYD 和 LuCI 网页终端不再编译。基础库与内核模块由依赖解析选择，不复制旧内核模块或旧版本系统库。软件版本采用兼容 24.10 的包定义，可能与旧固件不同。

厂商 `mtwifi-cfg` 现在显式依赖 `wifi-scripts`、Lua 和 nixio；配置与镜像检查均验证这些运行组件。固件不包含 AP 的密码、令牌或其他私人配置。设备保留配置升级时沿用已有设置。

## AP 吞吐验证

2026-10-11，X200 Pro 通过 5GHz WiFi 从有线树莓派下载，四个并发连接、每轮 256MiB，四次速度为 99.1、92.1、102.3、101.2 MB/s，平均 98.7 MB/s。当前移植可以在此局域网测试中达到约千兆吞吐。CPU 分配脚本已在设备上恢复；单独恢复脚本没有改善此前的 vivo 下载测速，不能把正常速度完全归功于该修改。

同一 vivo 视频在树莓派有线网口的 64 并发公网测试平均 42.42 MB/s；手机公网测试连接已进入 HNAT 绑定流表，CPU 没有满载。公网测试与局域网测试的服务器和并发方式不同，结果不能证明单连接性能完全一致，也不能仅凭公网 40 MB/s 判断 WiFi 驱动回退。此次未回退驱动或内核，保留已有平台与安全修复。

## 首次启动默认设置

包含 `default-settings` 和 `default-settings-chn`：首次启动使用中文、Argon、上海时区和国内 NTP。只有 LAN 仍为出厂地址 `192.168.1.1` 时才应用设备默认设置：CMCC 使用 AP 地址 `10.10.10.100/24`、网关/DNS `10.10.10.10`，关闭 LAN DHCP、DHCPv6 和 RA；Nokia EA0326GMP 使用路由模式，LAN `10.10.10.10/24`、LAN DHCP 服务保持开启，WAN `eth1` 使用 DHCP。已有自定义 LAN 地址保持不变。公开仓库和公开固件不包含个人服务令牌或 ZeroTier 私钥。

## 个人配置构建

工作流输入 `personal_config=true` 时，按设备选择独立 GitHub Secrets：CMCC 使用 `CMCC_PRIVATE_CONFIG_B64` / `CMCC_PRIVATE_ARTIFACT_KEY`；Nokia 使用 `EA0326_PRIVATE_CONFIG_B64` / `EA0326_PRIVATE_ARTIFACT_KEY`，需要单独配置。注入该设备的 DDNSTO、ZeroTier UCI 配置，并加密生成的固件包。缺少对应设备的密钥或配置时构建失败，不会回退使用另一台设备的身份。此模式只上传加密附件，保留 7 天，不发布 Release、不上传明文固件或构建日志。公开仓库的构建附件可能被其他登录用户下载，因此加密不能省略。解密密钥保存在个人本地目录，不放进仓库。默认公开构建不注入私人配置。ZeroTier 身份随此个人配置恢复，不应同时刷到其他设备。

## nft_fullcone

FullCone 使用与 `openwrt-build` 相同的 nft_fullcone 内核模块和 libnftnl、nftables、fw4 集成，移除 BCM 全局补丁。TurboACC 加速页面只有一个“全锥形 NAT（IPv4 / IPv6）”开关，同时设置 `fullcone` / `fullcone6`；只有启用了对应地址伪装的区域生成规则，不自动开启 NAT66。TurboACC 读取实际 nftables 规则显示状态，并直接保存防火墙配置，防火墙页面不再添加重复开关。MTK HNAT/WED 保留，实际加速兼容性需新固件运行测试。
