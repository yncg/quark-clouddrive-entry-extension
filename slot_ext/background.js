/* 夸克网盘 —— v5
 *
 * v4 的错：把 uccd://cloud.quark/renderer/index.html 「换算」成了 electron://cloud/。
 *   electron://cloud/ 是给「宿主窗口」用的路由 —— 开出来只有壳（一个搜索框），
 *   因为那个窗口在等宿主发 browser:init 数据。
 *   而直接在地址栏敲 uccd://cloud.quark/renderer/index.html，
 *   浏览器会把它当普通页面加载，网盘 web 应用自己就能跑起来 → 完整界面。
 *
 * v5：默认就照「地址栏敲链接」的方式做 ——
 *   用原生通道 /browser/navigator 提交**原始链接**，type=new_tab，
 *   并带上 page_transition="typed"（就是地址栏输入那种导航类型）。
 *   注意：不能用扩展的 chrome.tabs.update/create 去做这件事 —— 扩展发起的导航
 *   到 uccd:// 会白页（这正是 v2 白页的原因）。
 *
 * 其它备选方式（设置页里可切）：singleton_tab / 原生 /cloud_disk/home /
 *   electron://cloud/ 路由 / 扩展标签页 API。
 */
'use strict';

var DEFAULT_URL = 'uccd://cloud.quark/renderer/index.html';
var DEFAULT_MODE = 'auto';
var K_URL = 'qce_url';
var K_WIN = 'qce_in_window';
var K_MODE = 'qce_mode';
var V = 'V5';

/* ------------------------------------------------------------------ 埋点 */

var traceBuf = [];

function trace(msg) {
  try {
    traceBuf.push(new Date().toTimeString().slice(0, 8) + ' ' + msg);
    if (traceBuf.length > 40) traceBuf = traceBuf.slice(-40);
    chrome.storage.local.set({ qce_trace: traceBuf });
  } catch (e) {}
}

function lastErr() {
  try { return chrome.runtime.lastError; } catch (e) { return null; }
}

/* ------------------------------------------------- uccd:// 链接 → 路由（仅备选用） */

function toRoute(url) {
  var u = String(url || '').trim();
  if (!/^uccd:\/\/cloud\.quark\/renderer\//i.test(u)) return u;

  var hash = '';
  var hi = u.indexOf('#');
  if (hi >= 0) { hash = u.slice(hi + 1); u = u.slice(0, hi); }

  var qi = u.indexOf('?');
  var path = qi >= 0 ? u.slice(0, qi) : u;
  var query = qi >= 0 ? u.slice(qi + 1) : '';

  if (hash && query.indexOf('redirectHash=') < 0) {
    query = (query ? query + '&' : '') + 'redirectHash=' + encodeURIComponent(hash);
  }
  var base = /transport-window\.html$/i.test(path) ? 'electron://transfer/' : 'electron://cloud/';
  return base + (query ? '?' + query : '');
}

/* -------------------------------------------------------------- 配置读取 */

function cfg(cb) {
  try {
    chrome.storage.local.get([K_URL, K_WIN, K_MODE], function (v) {
      void lastErr();
      v = v || {};
      cb(String(v[K_URL] || '').trim() || DEFAULT_URL,
         String(v[K_MODE] || '').trim() || DEFAULT_MODE,
         !!v[K_WIN]);
    });
  } catch (e) { cb(DEFAULT_URL, DEFAULT_MODE, false); }
}

/* ---------------------------------------------------------------- 打开网盘 */

function apiReady() {
  try {
    return !!(chrome.quarkRoutePrivate && typeof chrome.quarkRoutePrivate.submit === 'function');
  } catch (e) { return false; }
}

function submit(module, params, cb) {
  try {
    chrome.quarkRoutePrivate.submit({
      qk_tech: 'pc',
      qk_biz: 'native',
      qk_module: module,
      qk_params: params || {}
    }, function (r) {
      var e = lastErr();
      cb(e ? ('err ' + e.message) : ('ret ' + JSON.stringify(r || {})));
    });
  } catch (e) { cb('err throw ' + e); }
}

/* 回调里 code 非 0 才算失败；没回调 / 没有 code 就不当失败（多半已经开了） */
function isFail(res) {
  if (!res) return false;
  if (res.indexOf('err ') === 0) return true;
  var m = /"code"\s*:\s*(-?\d+)/.exec(res);
  return !!(m && Number(m[1]) !== 0);
}

/* 原生通道打开一个 url —— 等价于「浏览器自己发起导航」 */
function viaNavigator(url, type, extra, cb) {
  var p = { url: url, type: type, active_window: true };
  if (extra) { for (var k in extra) { if (extra.hasOwnProperty(k)) p[k] = extra[k]; } }
  trace(V + ' nav url=' + url + ' type=' + type + (extra ? (' ' + JSON.stringify(extra)) : ''));
  submit('/browser/navigator', p, cb);
}

/* 兜底：扩展自己的标签页 API（对 uccd:// 会白页，只当最后手段） */
function viaTab(url, inWindow, tag) {
  try {
    if (inWindow) {
      chrome.windows.create({ url: url, focused: true, width: 1200, height: 768 }, function () {
        var e = lastErr();
        trace(V + ' window ' + (e ? ('err ' + e.message) : 'ok') + ' [' + tag + ']');
      });
      return;
    }
    chrome.tabs.create({ url: url, active: true }, function () {
      var e = lastErr();
      trace(V + ' tab.create ' + (e ? ('err ' + e.message) : 'ok') + ' [' + tag + ']');
    });
  } catch (e) { trace(V + ' tab throw ' + e); }
}

function openDrive() {
  cfg(function (url, mode, inWindow) {
    trace(V + ' open mode=' + mode + ' win=' + inWindow + ' url=' + url);

    function fallback(reason) {
      trace(V + ' fallback [' + reason + ']');
      viaTab(url, inWindow, reason);
    }

    if (mode === 'tab') { viaTab(url, inWindow, 'mode=tab'); return; }

    if (!apiReady()) { trace(V + ' route api 不可用'); fallback('no-api'); return; }

    if (mode === 'home') {
      submit('/cloud_disk/home', {}, function (res) {
        trace(V + ' home ' + res);
        if (isFail(res)) fallback('home-fail');
      });
      return;
    }

    if (mode === 'electron') {
      var route = toRoute(url);
      viaNavigator(route, 'singleton_tab', null, function (res) {
        trace(V + ' electron ' + res);
        if (isFail(res)) fallback('electron-fail');
      });
      return;
    }

    if (mode === 'reuse') {
      viaNavigator(url, 'singleton_tab', null, function (res) {
        trace(V + ' reuse ' + res);
        if (isFail(res)) fallback('reuse-fail');
      });
      return;
    }

    /* auto（默认）：照地址栏敲链接的方式 —— 原始链接 + new_tab + page_transition=typed */
    viaNavigator(url, 'new_tab', { page_transition: 'typed' }, function (res) {
      trace(V + ' auto ' + res);
      if (!isFail(res)) return;
      /* 失败才逐级退让，避免一次点开好几个窗口 */
      viaNavigator(url, 'singleton_tab', null, function (r2) {
        trace(V + ' reuse ' + r2);
        if (!isFail(r2)) return;
        submit('/cloud_disk/home', {}, function (r3) {
          trace(V + ' home ' + r3);
          if (isFail(r3)) fallback('all-fail');
        });
      });
    });
  });
}

/* ------------------------------------------------------------ 设置页逻辑 */

function flash($m, t) {
  if (!$m) return;
  $m.textContent = t;
  setTimeout(function () { $m.textContent = ''; }, 2500);
}

function describe(mode, url) {
  if (mode === 'auto') return '将提交原始链接（模拟地址栏输入）：' + url;
  if (mode === 'reuse') return '将提交原始链接（复用网盘标签页）：' + url;
  if (mode === 'home') return '将调用原生模块：/cloud_disk/home';
  if (mode === 'electron') return '将换算成夸克路由：' + toRoute(url);
  if (mode === 'tab') return '将用扩展标签页 API 直接打开：' + url + '（uccd:// 会白页，仅测试用）';
  return '';
}

function pageInit() {
  var $u = document.getElementById('qce-url');
  var $m = document.getElementById('qce-mode');
  var $w = document.getElementById('qce-win');
  var $msg = document.getElementById('qce-msg');
  var $pre = document.getElementById('qce-preview');
  if (!$u) return;
  window.__qcePageReady = true;

  function preview() {
    if ($pre) $pre.textContent = describe($m ? $m.value : DEFAULT_MODE, String($u.value || '').trim());
  }

  chrome.storage.local.get([K_URL, K_WIN, K_MODE], function (c) {
    void lastErr();
    c = c || {};
    $u.value = c[K_URL] || DEFAULT_URL;
    if ($m) $m.value = c[K_MODE] || DEFAULT_MODE;
    if ($w) $w.checked = !!c[K_WIN];
    preview();
  });

  $u.addEventListener('input', preview);
  if ($m) $m.addEventListener('change', preview);

  function save(cb) {
    var v = String($u.value || '').trim() || DEFAULT_URL;
    chrome.storage.local.set({
      qce_url: v,
      qce_mode: $m ? $m.value : DEFAULT_MODE,
      qce_in_window: !!(($w && $w.checked) || false)
    }, function () { void lastErr(); cb && cb(v); });
  }

  var $save = document.getElementById('qce-save');
  if ($save) $save.addEventListener('click', function () {
    save(function () { flash($msg, '已保存'); });
  });

  var $test = document.getElementById('qce-test');
  if ($test) $test.addEventListener('click', function () {
    save(function () {
      flash($msg, '正在打开…');
      try {
        chrome.runtime.sendMessage({ qce: 'open' }, function () { void lastErr(); });
      } catch (e) { flash($msg, '打开失败：' + e); }
    });
  });

  var $reset = document.getElementById('qce-reset');
  if ($reset) $reset.addEventListener('click', function () {
    $u.value = DEFAULT_URL;
    if ($m) $m.value = DEFAULT_MODE;
    if ($w) $w.checked = false;
    preview();
    chrome.storage.local.set({ qce_url: DEFAULT_URL, qce_mode: DEFAULT_MODE, qce_in_window: false },
      function () { void lastErr(); flash($msg, '已恢复默认'); });
  });
}

/* -------------------------------------------------------------------- 入口 */

if (typeof document !== 'undefined' && document.getElementById) {
  pageInit();
} else {
  trace(V + ' sw start');
  try { if (apiReady()) trace(V + ' route api OK'); } catch (e) {}

  try {
    chrome.action.onClicked.addListener(function () {
      trace(V + ' CLICK');
      openDrive();
    });
  } catch (e) { trace(V + ' action api unavailable'); }

  try {
    chrome.runtime.onMessage.addListener(function (msg, sender, sendResponse) {
      if (msg && msg.qce === 'open') {
        trace(V + ' MSG open');
        openDrive();
        try { sendResponse({ ok: true }); } catch (e) {}
      }
      return true;
    });
  } catch (e) {}

  try { chrome.runtime.onInstalled.addListener(function () { trace(V + ' installed'); }); } catch (e) {}
  try { chrome.runtime.onStartup.addListener(function () { trace(V + ' startup'); }); } catch (e) {}
}
