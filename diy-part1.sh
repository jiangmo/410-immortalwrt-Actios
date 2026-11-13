#!/bin/bash
# DIY脚本
# https://github.com/P3TERX/Actions-OpenWrt
# 文件名: diy-part1.sh
# 功能说明: OpenWrt DIY脚本第1部分（更新feeds之前）
# 版权: (c) 2019-2024 P3TERX <https://p3terx.com>
# 基于 MIT 开源协议，详见 /LICENSE

set -euo pipefail
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
# Argon 仓库根目录就是一个 LuCI 包，必须保留 luci-theme-argon 目录名。
# 直接以 feeds/argon 名称克隆会改变 luci.mk 推导出的包名。
bash "$SCRIPT_DIR/scripts/fetch-custom-packages.sh" "$SCRIPT_DIR/custom-packages.lock"

# 取消注释一个源
# sed -i 's/^#\(.*helloworld\)/\1/' feeds.conf.default

# 第三方 feeds 已在 feeds.conf.default 中固定 OpenClash 和 iStore 的提交。
# 如另行引入 small-package，需重新处理包覆盖及依赖版本冲突。
# echo 'src-git smpackage https://github.com/kenzok8/small-package' >> feeds.conf.default
# 添加第三方源，下面 iStore 应用商店了，然后在编译时候包输入luci-app-store
# echo 'src-git store https://github.com/linkease/istore.git;main' >> feeds.conf.default


# OpenClash代理
# git clone --depth 1 https://github.com/vernesong/OpenClash.git OpenClash

# turboacc网络加速
# curl -sSL https://raw.githubusercontent.com/mufeng05/turboacc/main/add_turboacc.sh -o add_turboacc.sh && bash add_turboacc.sh

# 调试
# sed -i 's|src-git-full openstick https://github.com/lkiuyu/openstick-feeds.git|src-git-full openstick https://github.com/xuxin1955/openstick-feeds|g' feeds.conf.default



