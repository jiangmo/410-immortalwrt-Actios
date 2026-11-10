#!/usr/bin/env bash
# Ubuntu 24.04 构建环境；禁止推荐包拉入整套 TeX Live。
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive

# GitHub 镜像列表可能指向速度异常的 Azure 镜像，改用 Ubuntu 官方源。
for source_file in /etc/apt/sources.list /etc/apt/sources.list.d/ubuntu.sources; do
  if [ -f "$source_file" ]; then
    sudo sed -i \
      -e 's|mirror+file:/etc/apt/apt-mirrors.txt|https://archive.ubuntu.com/ubuntu|g' \
      -e 's|http://azure.archive.ubuntu.com/ubuntu|https://archive.ubuntu.com/ubuntu|g' \
      "$source_file"
  fi
done

apt_options=(-o Acquire::Retries=3 -o Acquire::http::Timeout=30 -o Acquire::https::Timeout=30)
sudo -E apt-get "${apt_options[@]}" update
sudo -E apt-get "${apt_options[@]}" -y --no-install-recommends install \
  ack android-sdk-libsparse-utils antlr3 asciidoc autoconf automake \
  autoconf-archive autopoint binutils bison build-essential bzip2 ccache \
  clang cmake cpio curl device-tree-compiler expect flex gawk gcc-multilib \
  g++-multilib gettext genisoimage git gperf haveged help2man intltool \
  libc6-dev-i386 libdeflate-tools libelf-dev libffi-dev libfuse-dev \
  libglib2.0-dev libgmp3-dev libjson-c-dev libltdl-dev liblz4-dev libmnl-dev \
  libmpc-dev libmpfr-dev libncurses-dev libpython3-dev libreadline-dev \
  libssl-dev libtool libusb-1.0-0-dev llvm lrzsz m4 msmtp ninja-build \
  p7zip p7zip-full patch pkgconf python3 python3-dev python3-pyelftools \
  python3-setuptools python3-socks qemu-utils quilt rsync scons \
  squashfs-tools subversion swig texinfo time uglifyjs unzip upx-ucl \
  vim wget xmlto xxd xz-utils zlib1g-dev zstd jq bc dwarves file kmod
