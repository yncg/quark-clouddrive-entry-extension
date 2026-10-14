# 夸克网盘入口扩展（Quark CloudDrive Entry）

给夸克 PC 浏览器（macOS 版）加一个**点一下就打开夸克网盘首页**的入口按钮，并且**可以自定义跳转链接**。

改的是 App 内自带的那个「组件扩展」——把它的资源槽位换成我们自己的扩展，走夸克自己的原生导航通道打开网盘。

> ⚠️ 本项目需要修改并重签名 `/Applications/Quark.app`。属于对本机 App 的魔改，务必先看最后的**风险与注意事项**。

---

## 基于哪个安装包

本项目全部的改动，都是在这个安装包（夸克 Mac 版）上做的：

```
QuarkMac_V2.0.7.222_mac_pf30004_no-update_cloudentry_Build2073740.dmg
```

| 项 | 值 |
|---|---|
| 夸克版本 | **2.0.7.222**（App 内目录：`Contents/Frameworks/Quark Framework.framework/Versions/2.0.7.222`） |
| `pf30004` | 渠道包标识 |
| `no-update` | **已去掉自动更新** —— 这点很关键，否则夸克自己升级一次，改过的东西全被覆盖 |
| `cloudentry` | 这个「云盘入口」改造版的标记 |
| `Build2073740` | 构建号 |
| 改动对象 | 该安装包装出来的 `/Applications/Quark.app`：只动它 `Resources/resources.pak` 里的扩展资源槽位（45596 / 45622 / 45623）和白名单（21000），然后重签名 |
| 成品安装包 | 同目录下的 DMG，见「六、打包成安装包（DMG）」 |

> 换用别的版本/渠道的安装包时，`Versions/<版本号>` 目录名会变，
> `resources.pak` 里的资源 ID 也可能变，需要重新核对（见「五、风险与注意事项」）。

---

## 一、最终效果

**图标在哪**：夸克窗口**工具栏最右侧**、「AI总结」左边，有一个**云朵图标**，
它就紧挨着「插件」（拼图）图标 —— 点这个云朵图标，就直接跳转到夸克网盘。

![图标位置](docs/toolbar-icon.png)

放大看这三个图标：`翻译` → **`☁️ 云朵（本项目加的，点它打开夸克网盘）`** → `🧩 插件分组` → `|` → `AI总结`

![图标放大](docs/toolbar-icon-zoom.png)

- 工具栏「插件」分组里能看到这个云朵图标（已写进 `pinned_extensions`，默认就是固定显示状态）。
- **单击 = 直接打开夸克网盘首页**（一次就开，不需要点好几下）。
- 图标右键 → 选项，可以改跳转链接、切换打开方式、测试打开、恢复默认。
- 默认链接：`uccd://cloud.quark/renderer/index.html`

---

## 二、怎么做的（改了什么）

### 1. 定位到"入口按钮"其实是 App 自带的组件扩展

夸克把一批组件扩展打进 `Quark Framework.framework/.../Resources/resources.pak`。本机是 `sniffing` 这个组件扩展，
它在 pak 里的资源槽位是**连续编号**的（从 `.grd` 声明顺序推出，已逐一核对内容类型验证）：

| 资源 ID | 文件名 | 用途 |
|---|---|---|
| 45596 | `background.js` | service worker |
| 45603 | `content_script.js` | 内容脚本（未用） |
| 45622 | `manifest.json` | 扩展清单 |
| 45623 | `popup.html` | 设置页 |
| 45624 | `popup.js` | 设置页脚本（未用） |
| 45625 | `sniff.png` | 图标 |
| 45626 | `sniffDark.png` | 深色图标 |

所以我们只替换 **45596 / 45622 / 45623** 三个槽位即可，图标沿用夸克自己的云朵图
（`sniff.png` / `sniffDark.png`），扩展 ID 由 `manifest.json` 里的 `key` 决定，保持不变。

### 2. 打开网盘：必须走夸克自己的原生通道

这是整件事最关键的一点，也是一路踩坑的核心：

| | 是什么 | 直接用它打开会怎样 |
|---|---|---|
| `uccd://cloud.quark/renderer/index.html` | 网盘窗口**真正加载的那个页面**（App 里叫 `CLOUD_BROWSER_URL.MAIN`） | 在**地址栏**里敲它能正常打开完整界面；但**扩展用 `chrome.tabs` 去导航它 = 白页** |
| `electron://cloud/` | 夸克自己的**路由**（`windowRegister["main"].fusionOptions.routeURL`） | 能开出网盘窗口，但那个窗口在等宿主发 `browser:init` 数据，只显示一个空壳 |
| `/cloud_disk/home` | 原生路由模块（`quark_native_route.cc` 里注册的） | 调用返回 `code:0`，但界面上没反应 |

**结论**：把**原始链接**交给夸克的**原生导航通道**去打开，也就是

```js
// 和你在地址栏里敲链接是同一件事
chrome.quarkRoutePrivate.submit({
  qk_tech: "pc",
  qk_biz: "native",
  qk_module: "/browser/navigator",
  qk_params: {
    url: "uccd://cloud.quark/renderer/index.html",
    type: "new_tab",
    page_transition: "typed"     // 就是"地址栏输入"那种导航类型
  }
}, function (res) { /* res = {code, data, msg} */ });
```

不要再做 `uccd://` → `electron://cloud/` 的换算（那是上一版的做法，只会得到空壳）。

### 3. 一路上修掉的 5 个坑

| # | 现象 | 根因 | 修法 |
|---|---|---|---|
| 1 | 点图标没反应，要点好几下才偶尔生效 | MV3 的 service worker 空闲约 30s 就被回收，而私有的 `onToolbarButtonClicked` 事件**唤不醒**它，点击事件直接丢 | 弃用私有工具栏按钮 API，改用标准扩展 `action.onClicked`（标准事件**必定先唤醒后台再派发**） |
| 2 | 改了代码"完全没效果" | 浏览器把后台脚本缓存在 `~/Library/Application Support/Quark/Default/Service Worker/ScriptCache/`，一直跑缓存里的旧副本 | 装完**必须清掉这个缓存**（夸克退出状态下移走该目录），否则改多少遍 pak 都白改 |
| 3 | 调私有 API 被拒 | `quarkRoutePrivate` 有 allowlist（`_api_features.json`，pak 资源 21000），我们的扩展不在里面 | 把扩展 ID + 它的 SHA1 哈希插进 `quarkRoutePrivate` 的 allowlist |
| 4 | 设置页输入框空白、按钮全都没反应 | 扩展页面的 CSP 是 `script-src 'self'`，**行内 `<script>` 被拦掉**，页面里的脚本一行都没执行 | 脚本改成**独立文件**（`popup.html` → `<script src="background.js">`） |
| 5 | 点开只有"一个搜索框"的壳 | 把链接换算成了 `electron://cloud/` 路由，那是给宿主窗口用的，缺 `browser:init` 就只有壳 | 改成提交**原始链接**走原生导航通道（见上） |

> 顺带一个坑：资源槽位 21000 的 allowlist 里，锚点字符串在文件**别处也出现过**
> （`quarkNativeUiHelperPrivate` 的 allowlist 里有同一个哈希），用 `str.replace(..., 1)`
> 会改错地方。必须按**段内绝对位置**替换 —— 见 `build_v5.py`。

### 4. 打包 / 安装 / 重签名

```
生成扩展       slot_tpl/*.tpl        -> slot_ext/{manifest.json,background.js,popup.html}
重打包 pak     pak_patch2.py         -> out/resources.final.pak（只换 45596/45622/45623 + 白名单 21000）
装入 App       cp -> Quark Framework.framework/.../Resources/resources.pak
重签名         codesign --force --deep --options runtime --entitlements sign/ent.plist -s -
清缓存         夸克退出后移走 Service Worker 缓存，确保加载新代码
```

`pak_patch2.py` 只替换资源体内的字节，并**保持原有的 gzip/plain 存储形式**、刷新索引末尾的
sentinel（`{id:0, offset:文件末尾}`），这样 Chromium 读起来和原来完全一致。

---

## 三、目录结构

```
.
├── README.md
├── LICENSE
├── .gitignore
├── install.sh              # 一键：生成扩展 → 打包 → 安装 → 签名 → 挂清缓存守护
├── build_v5.py             # 生成 slot_ext/* 并重打包 resources.pak（含白名单补丁）
├── slot_tpl/
│   ├── background.v5.js.tpl   # service worker + 设置页逻辑（同一份代码，按有无 DOM 分流）
│   └── popup.v5.html.tpl      # 设置页（只引外部脚本，不能用行内 script）
├── slot_ext/               # 构建产物（拷进 pak 的就是这三个）
│   ├── manifest.json
│   ├── background.js
│   └── popup.html
├── sign/                   # 重签名用的 entitlements
│   ├── ent.plist           # 给整个 App 用（`codesign --deep`）
│   ├── ent_app.plist       # 给主可执行文件用
│   └── ent_fw.plist        # 给 framework 用
└── tools/
    ├── pak.py              # 读 resources.pak（解压单条资源）
    ├── pak_patch2.py       # 重打包：替换指定资源 ID，保持存储形式
    ├── patch_asar.py       # 读 Electron asar（本项目里用来还原 asar 改动）
    └── watch-and-clear-cache.sh   # 等夸克退出后清 Service Worker 缓存 + 固定图标到插件分组
```

> `sign/*.plist` 是从本机 Quark.app **原有的签名里导出来的**（就是标准的 Electron
> entitlements：JIT、相机/麦克风、USB 之类），重签时原样用一份，保证不丢权限。

---

## 四、安装 / 使用

```bash
# 1) 先退出夸克
# 2) 一键安装（会挂一个守护脚本，等夸克退出后自动清缓存）
sh install.sh
# 3) 重新打开夸克 -> 工具栏「插件」分组 -> 点云朵图标
```

设置页：**插件分组里右键云朵图标 → 选项**（或者扩展详情页 → 扩展程序选项）。

可配置项：

| 选项 | 说明 |
|---|---|
| 跳转链接 | 默认 `uccd://cloud.quark/renderer/index.html`，可改成带 `#/list` 之类的具体页面 |
| 打开方式 | `auto`（默认，按地址栏输入的方式）/ `reuse`（复用已有网盘标签页）/ `home`（原生 `/cloud_disk/home`）/ `electron`（`electron://cloud/` 路由）/ `tab`（扩展标签页 API，仅测试） |
| 保存 / 测试打开 / 恢复默认 | 都会立即写入 `chrome.storage.local` 并生效 |

排障：扩展会把自己的每一步写进 `chrome.storage.local` 的 `qce_trace`（最近 40 条），
内容形如：

```
22:1x:0x V5 sw start
22:1x:0x V5 route api OK
22:1x:0x V5 CLICK
22:1x:0x V5 open mode=auto win=false url=uccd://cloud.quark/renderer/index.html
22:1x:0x V5 nav url=uccd://cloud.quark/renderer/index.html type=new_tab {"page_transition":"typed"}
22:1x:0x V5 auto ret {"code":0,"data":{},"msg":"success"}
```

存在 `~/Library/Application Support/Quark/Default/Local Extension Settings/<扩展ID>/000003.log`，
能直接看出卡在哪一步、原生返回了什么。

---

## 五、风险与注意事项

- **会破坏 App 签名**：改完 pak 必须重签名（`codesign --force --deep ... -s -`），否则夸克起不来。
  本项目用自签名（`-s -`），只在本机有效。
- **App 自动更新会覆盖**：夸克自带 Quattro 更新器，一旦升级到新版本，
  `Quark Framework.framework/Versions/<新版本>` 路径和 pak 都会变，
  改过的东西全部失效，需要按新路径重跑 `build_v5.py` + `install.sh`。升级前记得先备份。
- **资源槽位是按当前版本（`2.0.7.222`）核对的**：换版本后 `45596/45622/45623/21000` 这些 ID
  需要重新核对（方法：解析 `resources.pak` 索引 + 按内容类型/文件名顺序比对）。
- **改这份代码前先备份**：`/tmp/resources.pak.before-*`、`/tmp/app-arm64.before-*.asar` 之类，
  建议自己另存一份到仓库外。
- 本项目**不包含**夸克任何二进制内容，只操作本机已安装 App 的资源文件。

---

## 六、打包成安装包（DMG）

改完之后可以直接把 `/Applications/Quark.app` 重新打成一个 DMG，丢给别人（或换机器）装：

```bash
# usage: sh make_dmg.sh [输出.dmg]
sh make_dmg.sh "/path/to/QuarkMac_V2.0.7.222_mac_pf30004_no-update_cloudentry-v5_Build2073740.dmg"
```

脚本做的事（`make_dmg.sh`）：

1. `cp -Rc`（clonefile，秒级，不占额外空间）把 `/Applications/Quark.app` 复制到暂存目录；
2. 放一个 `/Applications` 软链（方便拖拽安装）；
3. **校验**：比对暂存里的 `resources.pak` 与源一致 + `codesign --verify --deep --strict` 签名有效；
4. `hdiutil create -format UDZO` 压成 DMG。

产物和原始安装包放在同一个目录（用户环境里是 `~/Downloads`），命名规则保持一致：

```
QuarkMac_V2.0.7.222_mac_pf30004_no-update_cloudentry_Build2073740.dmg      ← 原始基础安装包
QuarkMac_V2.0.7.222_mac_pf30004_no-update_cloudentry-v5_Build2073740.dmg   ← 本次改动后的成品
```

> 安装到别的机器时：因为是自签名（`-s -`）且未公证，Gatekeeper 会拦。
> 拖进 `/Applications` 后执行一次 `xattr -cr /Applications/Quark.app` 即可（或右键 → 打开）。

---

## 七、License

MIT，见 [LICENSE](LICENSE)。
