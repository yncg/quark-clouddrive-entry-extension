#!/bin/bash
# 等夸克退出后：
#   1) 清掉 service worker 脚本缓存 —— 关键！
#      浏览器把扩展后台脚本缓存到 Profile/Service Worker/ScriptCache/，
#      不清掉的话它会一直跑缓存里的旧副本，改了 pak 也"完全没效果"。
#   2) 把云朵图标确保在「插件」分组里（写进 pinned_extensions）
#   3) 把上一轮的 qce_trace 埋点另存一份，方便对比新代码有没有跑起来
#
# usage: sh tools/watch-and-clear-cache.sh
PROF="$HOME/Library/Application Support/Quark/Default"
EXT="ihcocgihcaabbilifelfcdihidfmklgm"
MARK=/tmp/quark-entry-ready
PY="$(command -v python3)"
rm -f "$MARK"

echo "[watch] 等待夸克退出 ... $(date +%H:%M:%S)"
for i in $(seq 1 3600); do
  pgrep -f "Quark.app/Contents/MacOS/Quark" >/dev/null 2>&1 || break
  sleep 1
done
echo "[watch] 夸克已退出 $(date +%H:%M:%S)，开始清理"
sleep 3

# 0) 存档旧埋点
DB="$PROF/Local Extension Settings/$EXT/000003.log"
if [ -f "$DB" ]; then
  cp "$DB" "/tmp/qce_trace_prev.log" 2>/dev/null && echo "  旧埋点已存档 -> /tmp/qce_trace_prev.log"
fi

# 1) service worker 脚本缓存（只动这一个）
TS=$(date +%Y%m%d-%H%M%S)
if [ -d "$PROF/Service Worker" ]; then
  mv "$PROF/Service Worker" "/tmp/sw_cache_stale_$TS" && echo "  已移走 Service Worker 缓存 -> /tmp/sw_cache_stale_$TS"
fi

# 2) 把云朵图标放进「插件」分组
if [ -n "$PY" ]; then
"$PY" - "$EXT" <<'PYEOF'
import json, os, sys
ext_id = sys.argv[1]
p = os.path.expanduser('~/Library/Application Support/Quark/Default/Preferences')
try:
    d = json.load(open(p, encoding='utf-8'))
except Exception as e:
    print('  Preferences 读取失败:', e); raise SystemExit
ext = d.setdefault('extensions', {})
pin = ext.setdefault('pinned_extensions', [])
if ext_id not in pin:
    pin.append(ext_id)
    json.dump(d, open(p, 'w', encoding='utf-8'), ensure_ascii=False)
    print('  已把', ext_id, '加入插件分组 pinned_extensions')
else:
    print('  已在插件分组中')
PYEOF
fi

touch "$MARK"
echo "[done] $(date +%H:%M:%S)  现在可以重新打开夸克了"
