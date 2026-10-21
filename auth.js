/* AURORA front-end auth (demo only — data lives in this browser, no server). */
(function () {
  var USERS_KEY = 'aurora_users', SESS_KEY = 'aurora_session';
  var DEMO = { name: 'Dr. Aris Vance', email: 'demo@aurora.com', role: 'Head Quant Arbitrage', demo: true };

  function read(k) { try { return JSON.parse(localStorage.getItem(k)); } catch (e) { return null; } }
  function write(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) {} }

  // window.name backup keeps the session across pages when file:// pages do not share storage.
  function getSession() {
    var s = read(SESS_KEY);
    if (s) return s;
    try {
      var m = (window.name || '').match(/^AURORA:(.*)$/);
      if (m) return JSON.parse(decodeURIComponent(m[1]));
    } catch (e) {}
    return null;
  }
  function setSession(s) {
    write(SESS_KEY, s);
    try { window.name = 'AURORA:' + encodeURIComponent(JSON.stringify(s)); } catch (e) {}
  }
  function clearSession() {
    try { localStorage.removeItem(SESS_KEY); } catch (e) {}
    window.name = '';
  }

  function hash(str) {
    if (window.crypto && crypto.subtle && window.TextEncoder) {
      return crypto.subtle.digest('SHA-256', new TextEncoder().encode(str)).then(function (b) {
        return Array.prototype.map.call(new Uint8Array(b), function (x) { return ('0' + x.toString(16)).slice(-2); }).join('');
      });
    }
    var h = 5381; for (var i = 0; i < str.length; i++) h = ((h << 5) + h + str.charCodeAt(i)) | 0;
    return Promise.resolve('x' + h);
  }

  var users = function () { return read(USERS_KEY) || []; };

  window.Aurora = {
    session: getSession,
    demoLogin: function () { setSession({ name: DEMO.name, email: DEMO.email, role: DEMO.role, demo: true }); },
    signup: function (name, email, password, role) {
      email = email.trim().toLowerCase();
      if (users().some(function (u) { return u.email === email; })) {
        return Promise.reject(new Error('An account with this email already exists. Log in instead.'));
      }
      return hash(password).then(function (h) {
        var list = users(); list.push({ name: name.trim(), email: email, role: role, pw: h }); write(USERS_KEY, list);
        setSession({ name: name.trim(), email: email, role: role, demo: false });
      });
    },
    login: function (email, password) {
      email = email.trim().toLowerCase();
      return hash(password).then(function (h) {
        var u = users().filter(function (x) { return x.email === email && x.pw === h; })[0];
        if (!u) throw new Error('Email or password is incorrect. Check both, or use Demo login.');
        setSession({ name: u.name, email: u.email, role: u.role, demo: false });
      });
    },
    logout: function () { clearSession(); location.href = 'login.html?signedout=1'; }
  };

  // Extract clean filename from pathname (supporting forward slashes and Windows backslashes)
  var rawPath = (location.pathname || '').replace(/\\/g, '/');
  var filename = (rawPath.split('/').pop() || 'index.html').split('?')[0].split('#')[0].toLowerCase();
  var baseName = filename.replace(/\.html$/, '');

  var isPublic = baseName === '' ||
                 baseName === 'index' ||
                 baseName === 'landing' ||
                 baseName === 'login' ||
                 baseName === 'signup';

  var isAuthPage = baseName === 'login' || baseName === 'signup';
  var sess = getSession();

  if (!isPublic && !sess) {
    location.replace('login.html?next=' + encodeURIComponent(filename || 'dashboard.html'));
    return;
  }
  // Public pages (landing, login, signup, index) are always accessible directly
  // without unexpected redirects or bypassing the login form.
  if (isPublic) return;

  // Load shared navigation and modal controller for app pages
  if (!window.AuroraNav && !document.querySelector('script[src*="aurora-nav.js"]')) {
    var navScript = document.createElement('script');
    navScript.src = 'aurora-nav.js';
    document.head.appendChild(navScript);
  }

  /* ---- App pages: show signed-in user, add Sign out to the sidebar ---- */
  document.addEventListener('DOMContentLoaded', function () {
    var footer = document.querySelector('.sidebar-footer') || document.querySelector('.sidebar-health');
    if (!sess.demo) {
      var n = document.querySelector('.user-name'); if (n) n.textContent = sess.name;
      var a = document.querySelector('.user-avatar');
      if (a) a.textContent = sess.name.split(/\s+/).map(function (w) { return w[0]; }).join('').slice(0, 2).toUpperCase();
      var r = document.querySelector('.user-role');
      if (r) { var ic = r.querySelector('i'); r.textContent = ' ' + sess.role; if (ic) r.insertBefore(ic, r.firstChild); }
    }
    if (!footer) return;
    var st = document.createElement('style');
    st.textContent = '.aurora-signout{display:flex;align-items:center;justify-content:center;gap:8px;width:100%;margin-top:10px;padding:9px 12px;border-radius:12px;border:1px solid rgba(240,185,11,.2);background:rgba(16,22,60,.5);color:#c9a227;font:600 12px Inter,sans-serif;cursor:pointer;transition:background .2s,color .2s,border-color .2s}.aurora-signout:hover,.aurora-signout:focus-visible{background:rgba(240,185,11,.12);color:#ffd700;border-color:rgba(240,185,11,.5);outline:none}.sidebar.collapsed .aurora-signout span{display:none}';
    document.head.appendChild(st);
    var b = document.createElement('button');
    b.type = 'button'; b.className = 'aurora-signout'; b.title = 'Sign out';
    b.innerHTML = '<i class="fa-solid fa-right-from-bracket"></i><span>Sign out</span>';
    b.addEventListener('click', window.Aurora.logout);
    footer.appendChild(b);
  });
})();
