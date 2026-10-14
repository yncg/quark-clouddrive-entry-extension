#!/usr/bin/env python3
"""夸克网盘入口扩展 v5 —— 生成扩展文件 + 重打包 resources.pak。

  slot_tpl/background.v5.js.tpl -> slot_ext/background.js   (rid 45596)
  slot_tpl/popup.v5.html.tpl    -> slot_ext/popup.html      (rid 45623)
  slot_ext/manifest.json        -> 重建，保留原 `key`（扩展 ID 不变）(rid 45622)

另外确保 quarkRoutePrivate 的 api_features 白名单里有我们的扩展 ID (rid 21000)。

pak 里的槽位来自 App 资源表（按 .grd 声明顺序推出并已逐一核对内容类型）：
    45590..45630 = 本机 "sniffing" 组件扩展的全部文件，其中
    45596 background.js / 45603 content_script.js / 45622 manifest.json
    45623 popup.html    / 45624 popup.js         / 45625 sniff.png
    45626 sniffDark.png / 45627 sniffer.js

换夸克版本后，这些 ID 需要重新核对（见 README「风险与注意事项」）。

usage: python3 build_v5.py
"""
import glob
import hashlib
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.join(HERE, "tools")
sys.path.insert(0, TOOLS)
from pak import read_pak, decompress  # noqa: E402

APP = "/Applications/Quark.app"
APP_PAK = os.path.join(HERE, "out", "resources.pak.src")
OUT = os.path.join(HERE, "out", "resources.final.pak")
OUT_DIR = os.path.join(HERE, "slot_ext")
TPL = os.path.join(HERE, "slot_tpl")
EXT_ID = "ihcocgihcaabbilifelfcdihidfmklgm"
RID_API_FEATURES = 21000
RID_MANIFEST, RID_BACKGROUND, RID_POPUP = 45622, 45596, 45623


def find_app_pak():
    """定位 App 内的 resources.pak（版本目录是变的，用 glob 兜住；
    `Versions/Current` 是指向真实版本目录的软链，排除掉免得看起来像两个版本）。"""
    pat = os.path.join(APP, "Contents", "Frameworks", "Quark Framework.framework",
                       "Versions", "*", "Resources", "resources.pak")
    hits = [h for h in sorted(glob.glob(pat)) if "/Versions/Current/" not in h]
    if not hits:
        sys.exit("找不到 %s\n（夸克没装在这里？或者 frameworks 结构变了）" % pat)
    if len(hits) > 1:
        print("警告：有多个版本目录，用最后一个：%s" % hits[-1])
    return hits[-1]


# ---------------------------------------------------------------- 1) 生成扩展
MPATH = os.path.join(OUT_DIR, "manifest.json")
KEY = json.load(open(MPATH, encoding="utf-8"))["key"]

MANIFEST = {
    "name": "夸克网盘",
    "short_name": "夸克网盘",
    "version": "5.0.0",
    "description": "点一下云朵图标直接打开夸克网盘首页。",
    "manifest_version": 3,
    "key": KEY,
    "incognito": "not_allowed",
    "permissions": ["storage", "tabs", "quarkRoutePrivate"],
    "background": {"service_worker": "background.js"},
    "action": {
        "default_title": "夸克网盘",
        "default_icon": {"16": "sniff.png", "24": "sniff.png", "32": "sniff.png"},
    },
    "options_ui": {"page": "popup.html", "open_in_tab": True},
    "icons": {"48": "sniff.png", "128": "sniff.png"},
    "commands": {},
}


def w(name, text):
    p = os.path.join(OUT_DIR, name)
    open(p, "w", encoding="utf-8").write(text)
    return p


w("background.js", open(os.path.join(TPL, "background.v5.js.tpl"), encoding="utf-8").read())
w("popup.html", open(os.path.join(TPL, "popup.v5.html.tpl"), encoding="utf-8").read())
json.dump(MANIFEST, open(MPATH, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
open(MPATH, "a", encoding="utf-8").write("\n")
print("扩展 v%s 已生成：" % MANIFEST["version"])
for n in ("manifest.json", "background.js", "popup.html"):
    print("   %-16s %6d 字节" % (n, os.path.getsize(os.path.join(OUT_DIR, n))))

# 语法自检（有 node 就查，没有就跳过）
node = shutil.which("node")
if node:
    subprocess.check_call([node, "--check", os.path.join(OUT_DIR, "background.js")])
    print("   background.js 语法 OK")
else:
    print("   （没找到 node，跳过语法自检）")

app_pak = find_app_pak()
print("App pak:", app_pak)

# ------------------------------------------- 2) 确保白名单（quarkRoutePrivate）
d = dict(read_pak(app_pak)["entries"])
src = decompress(d[RID_API_FEATURES]).decode("utf-8")
needle = '"quarkRoutePrivate": ['
assert src.count(needle) == 1, "quarkRoutePrivate 块不唯一"
i = src.find(needle)
seg_end = src.find("\n  ],", i)
seg = src[i:seg_end]

our_hash = hashlib.sha1(EXT_ID.encode()).hexdigest().upper()
if EXT_ID in seg:
    patched = src
    print("白名单：已有本扩展，跳过")
else:
    anchor = '        "6FB091FE811DD266F69445DFD0B7175DDE227F98"\n'
    assert seg.count(anchor) == 1, "找不到插入锚点"
    add = ('        // QuarkCloudEntry (by id)\n        "%s",\n'
           '        // QuarkCloudEntry (by hash)\n        "%s"\n' % (EXT_ID, our_hash))
    # 注意：这个锚点字符串在文件别处也出现（quarkNativeUiHelperPrivate 的
    # allowlist 里有同一个 quark ai 哈希），所以必须按 seg 内的绝对位置替换，
    # 不能用 src.replace(..., 1)，那样会改错地方。
    k = i + seg.index(anchor)
    patched = src[:k] + anchor.rstrip("\n") + ",\n" + add + src[k + len(anchor):]
    print("白名单：已加入 %s（位置 %d）" % (EXT_ID, k))
    assert patched.count(EXT_ID) >= 1

tmp = "/tmp/api_features_v5.json"
open(tmp, "w", encoding="utf-8").write(patched)

# ---------------------------------------------------------------- 3) 重打包
os.makedirs(os.path.dirname(OUT), exist_ok=True)
subprocess.check_call([
    sys.executable, os.path.join(TOOLS, "pak_patch2.py"), app_pak, OUT,
    "%d:%s/manifest.json" % (RID_MANIFEST, OUT_DIR),
    "%d:%s/background.js" % (RID_BACKGROUND, OUT_DIR),
    "%d:%s/popup.html" % (RID_POPUP, OUT_DIR),
    "%d:%s" % (RID_API_FEATURES, tmp),
])
print("产物:", OUT)
print("下一步：sh install.sh（或手动把产物拷进 App 并重签名）")
