<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>夸克网盘 - 设置</title>
<style>
  :root { color-scheme: light dark; }
  body { font: 14px/1.7 -apple-system, "PingFang SC", "Helvetica Neue", Arial, sans-serif;
         margin: 0; padding: 34px 38px; max-width: 760px; }
  h1 { font-size: 19px; margin: 0 0 4px; }
  .sub { opacity: .6; margin-bottom: 24px; }
  label { display: block; font-weight: 600; margin: 18px 0 8px; }
  input[type=text] { width: 100%; box-sizing: border-box; padding: 9px 11px; font: inherit;
         border-radius: 8px; border: 1px solid rgba(128,128,128,.45);
         background: transparent; color: inherit; }
  select { font: inherit; padding: 7px 10px; border-radius: 8px; width: 100%; box-sizing: border-box;
         border: 1px solid rgba(128,128,128,.45); background: transparent; color: inherit; }
  .row { display: flex; align-items: center; gap: 8px; margin-top: 14px; }
  button { font: inherit; padding: 8px 16px; border-radius: 8px; cursor: pointer;
         border: 1px solid rgba(128,128,128,.45); background: transparent; color: inherit; }
  button.primary { background: #2b6cff; border-color: #2b6cff; color: #fff; }
  .btns { margin-top: 24px; display: flex; gap: 10px; flex-wrap: wrap; }
  #qce-msg { margin-top: 14px; font-weight: 600; color: #1a9e4b; min-height: 22px; }
  #qce-preview { margin-top: 10px; font-size: 13px; opacity: .75; word-break: break-all; }
  .tip { margin-top: 26px; padding: 12px 14px; border-radius: 8px;
         background: rgba(128,128,128,.12); font-size: 13px; }
  code { word-break: break-all; }
</style>
</head>
<body>
  <h1>夸克网盘</h1>
  <div class="sub">单击「插件」分组里的云朵图标即可打开夸克网盘。</div>

  <label for="qce-url">跳转链接</label>
  <input id="qce-url" type="text" spellcheck="false" autocomplete="off"
         value="uccd://cloud.quark/renderer/index.html">

  <label for="qce-mode">打开方式</label>
  <select id="qce-mode">
    <option value="auto">自动（推荐）：按地址栏输入的方式打开填的链接</option>
    <option value="reuse">同样提交链接，但复用已有的网盘标签页</option>
    <option value="home">网盘首页模块（原生 /cloud_disk/home）</option>
    <option value="electron">夸克路由 electron://cloud/（只有壳，别用）</option>
    <option value="tab">扩展标签页 API 直接打开（uccd:// 会白页，仅测试用）</option>
  </select>

  <div class="row">
    <input id="qce-win" type="checkbox">
    <label for="qce-win" style="margin:0;font-weight:400">在新窗口中打开（仅「扩展标签页 API」方式有效）</label>
  </div>

  <div class="btns">
    <button class="primary" id="qce-save">保存</button>
    <button id="qce-test">测试打开</button>
    <button id="qce-reset">恢复默认</button>
  </div>
  <div id="qce-msg"></div>
  <div id="qce-preview"></div>

  <div class="tip">
    <b>默认链接</b>：<code>uccd://cloud.quark/renderer/index.html</code><br>
    点图标时，扩展会把这条链接交给夸克的<b>原生导航通道</b>去打开（相当于你在地址栏里敲它），
    而不是让扩展自己去导航 —— 扩展自己导航到 <code>uccd://</code> 只会白页。<br>
    想开某个具体文件夹，把完整链接（含 <code>#/list</code> 之类）贴到上面保存即可。
  </div>

  <!-- 扩展页面的 CSP 是 script-src 'self'，行内 <script> 会被拦掉，
       所以脚本必须是独立文件。 -->
  <script src="background.js"></script>
</body>
</html>
