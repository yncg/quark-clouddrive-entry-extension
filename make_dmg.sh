#!/bin/bash
# 把改好的 /Applications/Quark.app 打成一个可安装的 DMG。
#
# usage: sh make_dmg.sh [输出.dmg]
#   默认输出: ./out/QuarkMac_V2.0.7.222_mac_pf30004_no-update_cloudentry-v5_Build2073740.dmg
set -e

HERE="$(cd "$(dirname "$0")" && pwd)"
APP="${QUARK_APP:-/Applications/Quark.app}"
VER="${QUARK_VER:-2.0.7.222}"
DEFAULT_NAME="QuarkMac_V${VER}_mac_pf30004_no-update_cloudentry-v5_Build2073740.dmg"
DMG_OUT="${1:-$HERE/out/$DEFAULT_NAME}"

STAGE="/tmp/quark-dmg-stage"
PAK_REL="Contents/Frameworks/Quark Framework.framework/Versions/$VER/Resources/resources.pak"

echo "[0/4] 检查"
[ -d "$APP" ] || { echo "找不到 $APP"; exit 1; }
[ -f "$APP/$PAK_REL" ] || { echo "找不到 $APP/$PAK_REL（版本号对不对？）"; exit 1; }
mkdir -p "$(dirname "$DMG_OUT")"

echo "[1/4] 复制 app（clonefile，秒级）"
rm -rf "$STAGE"
mkdir -p "$STAGE"
cp -Rc "$APP" "$STAGE/Quark.app"
ln -s /Applications "$STAGE/Applications"

echo "[2/4] 校验 pak 一致性 + 签名"
cmp "$APP/$PAK_REL" "$STAGE/Quark.app/$PAK_REL" && echo "    pak 一致"
if codesign --verify --deep --strict "$STAGE/Quark.app" 2>/dev/null; then
  echo "    签名有效"
else
  echo "    !! 签名校验没过 —— 重新签一次（自签名）"
  codesign --force --deep --options runtime -s - "$STAGE/Quark.app"
  codesign --verify --deep --strict "$STAGE/Quark.app" && echo "    重签后 OK"
fi

echo "[3/4] 压缩成 DMG（1G 左右，要几分钟）"
rm -f "$DMG_OUT"
hdiutil create -volname "Quark" -srcfolder "$STAGE" -ov -format UDZO -quiet "$DMG_OUT"

echo "[4/4] 清理暂存目录"
rm -rf "$STAGE"

echo
echo "DONE $DMG_OUT"
ls -la "$DMG_OUT"
