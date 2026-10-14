#!/bin/bash
# 一键安装「夸克网盘入口」扩展：
#   生成扩展 -> 重打包 resources.pak（含 quarkRoutePrivate 白名单）-> 装入 App -> 重签名
#   最后挂一个守护脚本：等夸克退出后自动清掉 service worker 旧脚本缓存
#
# 用法:
#   sh install.sh              # 完整流程（会先退出夸克）
#   sh install.sh --no-kill    # 不主动关夸克，只装（装完自己重启）
set -e

HERE="$(cd "$(dirname "$0")" && pwd)"
cd "$HERE"

APP="/Applications/Quark.app"
PY="$(command -v python3)"
NO_KILL=0
[ "$1" = "--no-kill" ] && NO_KILL=1

echo "[0/5] 检查环境"
[ -n "$PY" ] || { echo "找不到 python3"; exit 1; }
[ -d "$APP" ] || { echo "找不到 $APP"; exit 1; }
PAK=$(ls "$APP/Contents/Frameworks/Quark Framework.framework/Versions/"*/Resources/resources.pak 2>/dev/null | tail -1)
[ -n "$PAK" ] || { echo "找不到 App 内的 resources.pak"; exit 1; }
echo "    App pak: $PAK"

if [ "$NO_KILL" = "0" ] && pgrep -f "Quark.app/Contents/MacOS/Quark" >/dev/null 2>&1; then
  echo "[1/5] 退出夸克"
  pkill -f "Quark.app/Contents/MacOS/Quark" >/dev/null 2>&1 || true
  pkill -f "Quark.app/Contents/Frameworks" >/dev/null 2>&1 || true
  sleep 3
else
  echo "[1/5] 跳过关闭夸克（--no-kill 或夸克本来没运行）"
fi

echo "[2/5] 生成扩展 + 重打包 pak"
"$PY" build_v5.py

echo "[3/5] 安装到 App（旧 pak 备份到 /tmp）"
cp "$PAK" "/tmp/resources.pak.$(date +%Y%m%d-%H%M%S).bak"
cp out/resources.final.pak "$PAK"

echo "[4/5] 重签名"
# 本项目用自签名（-s -）。改动资源后官方签名必然失效，只能自签。
if [ -f sign/ent.plist ]; then
  codesign --force --deep --options runtime --entitlements sign/ent.plist -s - "$APP"
else
  codesign --force --deep --options runtime -s - "$APP"
fi
codesign --verify --deep --strict "$APP" && echo "    签名 OK"

echo "[5/5] 挂守护脚本（夸克退出后清 service worker 缓存 + 固定图标到插件分组）"
nohup sh tools/watch-and-clear-cache.sh > /tmp/quark-entry-watch.out 2>&1 &

echo
echo "完成。请：退出夸克（若还开着）-> 等 5 秒 -> 重新打开 -> 点「插件」分组里的云朵图标。"
echo "清缓存守护脚本日志：/tmp/quark-entry-watch.out"
