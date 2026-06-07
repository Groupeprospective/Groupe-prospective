#!/usr/bin/env python3
"""
Correction complète du système de sync Firebase.
Problèmes identifiés :
1. Badge "Erreur sync" reste affiché même quand non connecté
2. Pas de message précis (règles Firestore, trop gros, réseau)
3. Firebase SDKs chargés après les fonctions → risque de timing
4. Pas de retry automatique
5. Badge jamais caché quand on se déconnecte
"""
import sys

SRC  = sys.argv[1] if len(sys.argv)>1 else 'index.html'
DEST = sys.argv[2] if len(sys.argv)>2 else 'index.html'

with open(SRC, 'r', encoding='utf-8') as f:
    html = f.read()

# ─── 1. Déplacer les SDKs Firebase dans <head> ───────────────────
# Enlever les scripts à leur position actuelle
OLD_SDK_BLOCK = """<!-- Firebase SDKs -->
<script src="https://www.gstatic.com/firebasejs/9.23.0/firebase-app-compat.js"></script>
<script src="https://www.gstatic.com/firebasejs/9.23.0/firebase-auth-compat.js"></script>
<script src="https://www.gstatic.com/firebasejs/9.23.0/firebase-firestore-compat.js"></script>"""
html = html.replace(OLD_SDK_BLOCK, '<!-- Firebase SDKs déplacés dans <head> -->', 1)

# Les injecter dans <head>
SDK_IN_HEAD = """
  <!-- Firebase SDKs -->
  <script src="https://www.gstatic.com/firebasejs/9.23.0/firebase-app-compat.js"></script>
  <script src="https://www.gstatic.com/firebasejs/9.23.0/firebase-auth-compat.js"></script>
  <script src="https://www.gstatic.com/firebasejs/9.23.0/firebase-firestore-compat.js"></script>
"""
html = html.replace('</head>', SDK_IN_HEAD + '</head>', 1)

# ─── 2. Remplacer le bloc Firebase complet ───────────────────────
# Trouver et remplacer tout le bloc Firebase (de "// ===== FIREBASE" à la fin du fichier)
FIREBASE_START = '// ===== FIREBASE INTEGRATION ====='
idx = html.rfind(FIREBASE_START)
if idx == -1:
    print("❌ Bloc Firebase introuvable")
    sys.exit(1)

# Trouver le </script> qui ferme ce bloc
close_script = html.find('</script>', idx)
if close_script == -1:
    print("❌ Fermeture </script> introuvable")
    sys.exit(1)

FIREBASE_BLOCK = """// ===== FIREBASE SYNC — VERSION CORRIGÉE =====
window._gpCurrentUser  = null;
window._gpSyncEnabled  = false;
window._gpSyncTimer    = null;
window._gpRetryTimer   = null;
window._gpRetryCount   = 0;

/* ── Indicateur visuel ──────────────────────────────────────── */
function _gpSetSync(state, detail) {
  var badge = document.getElementById('gpSyncBadge');
  var dot   = document.getElementById('gpSyncDot');
  var txt   = document.getElementById('gpSyncTxt');
  if (!dot || !txt) return;

  // Cacher complètement si non connecté
  if (state === 'hidden') {
    if (badge) badge.style.display = 'none';
    return;
  }
  if (badge) badge.style.display = 'flex';

  if (state === 'saving') {
    dot.style.background = '#ffcc66';
    txt.textContent = 'Sauvegarde…';
  } else if (state === 'saved') {
    dot.style.background = '#22d18b';
    var now = new Date();
    var hh = now.getHours().toString().padStart(2,'0');
    var mm = now.getMinutes().toString().padStart(2,'0');
    txt.textContent = 'Sauvegardé ✓ ' + hh + ':' + mm;
    window._gpRetryCount = 0; // Reset compteur d'erreurs
  } else if (state === 'error') {
    dot.style.background = '#ff5c5c';
    var msg = detail || 'Données locales conservées';
    txt.textContent = '⚠ ' + msg;
    // Retry automatique (max 3 tentatives, délai croissant)
    if (window._gpRetryCount < 3) {
      window._gpRetryCount = (window._gpRetryCount || 0) + 1;
      var delay = window._gpRetryCount * 20000; // 20s, 40s, 60s
      clearTimeout(window._gpRetryTimer);
      window._gpRetryTimer = setTimeout(function() {
        if (window._gpCurrentUser && window._gpSyncEnabled) {
          _gpSaveToCloud();
        }
      }, delay);
    }
  } else if (state === 'offline') {
    dot.style.background = '#9da79f';
    txt.textContent = 'Mode local';
  } else {
    dot.style.background = '#9da79f';
    txt.textContent = 'Prêt';
  }
}

/* ── Retirer les photos base64 pour ne pas dépasser 1MB ────── */
function _gpStripBase64(str) {
  try {
    return str.replace(/"data:[^"]{50,}"/g, '"[photo]"');
  } catch(e) { return str; }
}

/* ── Sauvegarder vers Firestore ─────────────────────────────── */
function _gpSaveToCloud() {
  if (!window._gpCurrentUser || !window._gpSyncEnabled) return;
  _gpSetSync('saving');

  var LS2 = 'gp_center_v2_';
  var keys = ['products','clients','materialOrders','isolationQuotes','invoices','constructionJobs','lastBackupDate'];
  var data = {};

  keys.forEach(function(k) {
    var v = localStorage.getItem(LS2 + k);
    if (v) data[k] = _gpStripBase64(v);
  });

  // Vérifier la taille — Firestore limite à ~1 MB par document
  var dataStr = JSON.stringify(data);
  if (dataStr.length > 850000) {
    // Trop gros : retirer constructionJobs en dernier recours
    var withoutJobs = Object.assign({}, data);
    delete withoutJobs.constructionJobs;
    var withoutJobsStr = JSON.stringify(withoutJobs);
    if (withoutJobsStr.length <= 850000) {
      data = withoutJobs;
      console.warn('[GP Sync] constructionJobs retiré (document trop grand: ' + Math.round(dataStr.length/1024) + ' KB)');
    } else {
      // Même sans jobs c'est trop gros — retirer aussi les commandes
      delete withoutJobs.materialOrders;
      data = withoutJobs;
      console.warn('[GP Sync] materialOrders aussi retiré (document > 850 KB)');
    }
  }

  firebase.firestore()
    .collection('users')
    .doc(window._gpCurrentUser.uid)
    .set({ appData: data, updatedAt: new Date().toISOString() }, { merge: true })
    .then(function() {
      _gpSetSync('saved');
    })
    .catch(function(e) {
      console.error('[GP Sync] Erreur écriture:', e.code, e.message);
      var msg;
      switch(e.code) {
        case 'permission-denied':
          msg = 'Règles Firestore à configurer'; break;
        case 'unavailable':
        case 'deadline-exceeded':
          msg = 'Hors ligne — retry auto'; break;
        case 'resource-exhausted':
          msg = 'Quota Firebase atteint'; break;
        case 'invalid-argument':
          msg = 'Données trop volumineuses'; break;
        default:
          msg = e.code || 'Erreur réseau';
      }
      _gpSetSync('error', msg);
    });
}

/* ── Charger depuis Firestore ───────────────────────────────── */
function _gpLoadFromCloud(uid) {
  _gpSetSync('saving');

  firebase.firestore()
    .collection('users')
    .doc(uid)
    .get()
    .then(function(doc) {
      if (doc.exists && doc.data() && doc.data().appData) {
        var d   = doc.data().appData;
        var LS2 = 'gp_center_v2_';
        Object.keys(d).forEach(function(k) {
          if (d[k]) localStorage.setItem(LS2 + k, d[k]);
        });
        if (typeof renderAll === 'function') {
          try { renderAll(); } catch(e) { console.warn('[GP Sync] renderAll:', e); }
        }
      }
      _gpSetSync('saved');
      window._gpSyncEnabled = true;
    })
    .catch(function(e) {
      console.error('[GP Sync] Erreur lecture:', e.code, e.message);
      window._gpSyncEnabled = true; // Continuer en mode local

      var msg;
      switch(e.code) {
        case 'permission-denied':
          msg = 'Règles Firestore à configurer';
          // Afficher un popup d'aide une seule fois
          if (!window._gpRulesTipShown) {
            window._gpRulesTipShown = true;
            setTimeout(function() {
              if (confirm('⚠ Firestore bloque la synchronisation.\\n\\nVoulez-vous voir comment configurer les règles ?')) {
                alert('Dans la console Firebase :\\n1. Firestore → Règles\\n2. Remplacez par :\\n\\nrules_version = \\'2\\'\\nservice cloud.firestore {\\n  match /databases/{database}/documents {\\n    match /users/{userId}/{document=**} {\\n      allow read, write: if request.auth != null && request.auth.uid == userId;\\n    }\\n  }\\n}\\n\\n3. Cliquez Publier');
              }
            }, 1500);
          }
          break;
        case 'unavailable':
          msg = 'Hors ligne — mode local actif'; break;
        default:
          msg = 'Mode local actif';
      }
      _gpSetSync('error', msg);
    });
}

/* ── Intercepter persist() pour sync automatique ───────────── */
(function patchPersist() {
  var _orig = window.persist;
  window.persist = function() {
    if (_orig) _orig.apply(this, arguments);
    if (window._gpCurrentUser && window._gpSyncEnabled) {
      clearTimeout(window._gpSyncTimer);
      window._gpSyncTimer = setTimeout(_gpSaveToCloud, 1500);
    }
  };

  // Intercepter aussi localStorage.setItem (pour constructionJobs)
  var _origSet = localStorage.setItem.bind(localStorage);
  localStorage.setItem = function(key, val) {
    _origSet(key, val);
    if (typeof key === 'string' && key.indexOf('gp_center_v2_') === 0) {
      if (window._gpCurrentUser && window._gpSyncEnabled) {
        clearTimeout(window._gpSyncTimer);
        window._gpSyncTimer = setTimeout(_gpSaveToCloud, 1500);
      }
    }
  };
})();

/* ── Connexion ──────────────────────────────────────────────── */
window.fbLogin = function() {
  var email = (document.getElementById('gpFbEmail') || {}).value || '';
  var pass  = (document.getElementById('gpFbPass')  || {}).value || '';
  var err   =  document.getElementById('gpFbErr');
  email = email.trim();

  if (!email || !pass) {
    if (err) { err.textContent = 'Entrez votre courriel et mot de passe.'; err.style.color = '#ffb3b3'; }
    return;
  }

  if (err) { err.textContent = 'Connexion en cours…'; err.style.color = '#9da79f'; }

  firebase.auth().signInWithEmailAndPassword(email, pass)
    .catch(function(e) {
      var msgs = {
        'auth/user-not-found':        'Compte introuvable.',
        'auth/wrong-password':        'Mot de passe incorrect.',
        'auth/invalid-email':         'Courriel invalide.',
        'auth/invalid-credential':    'Courriel ou mot de passe incorrect.',
        'auth/too-many-requests':     'Trop de tentatives — réessayez dans quelques minutes.',
        'auth/network-request-failed':'Pas de connexion internet.'
      };
      if (err) {
        err.textContent = msgs[e.code] || e.message;
        err.style.color = '#ff5c5c';
      }
    });
};

window.fbLogout = function() {
  firebase.auth().signOut();
};

/* ── Touche Entrée dans le formulaire ───────────────────────── */
document.addEventListener('DOMContentLoaded', function() {
  var passEl  = document.getElementById('gpFbPass');
  var emailEl = document.getElementById('gpFbEmail');
  if (passEl)  passEl.addEventListener('keydown',  function(e) { if (e.key === 'Enter') window.fbLogin(); });
  if (emailEl) emailEl.addEventListener('keydown', function(e) { if (e.key === 'Enter' && passEl) passEl.focus(); });
});"""

# Remplacer l'ancien bloc
html = html[:idx] + FIREBASE_BLOCK + html[close_script:]

# ─── 3. Corriger onAuthStateChanged — cacher badge si déconnecté ──
OLD_AUTH = """  firebase.auth().onAuthStateChanged(function(user){
    var overlay=document.getElementById('gpLoginOverlay');
    if(user){
      window._gpCurrentUser=user;
      if(overlay)overlay.style.display='none';
      _gpLoadFromCloud(user.uid);
    }else{
      window._gpCurrentUser=null;
      window._gpSyncEnabled=false;
      if(overlay)overlay.style.display='flex';
    }
  });"""

NEW_AUTH = """  firebase.auth().onAuthStateChanged(function(user) {
    var overlay = document.getElementById('gpLoginOverlay');
    if (user) {
      window._gpCurrentUser = user;
      window._gpRetryCount  = 0;
      if (overlay) overlay.style.display = 'none';
      _gpLoadFromCloud(user.uid);
    } else {
      window._gpCurrentUser = null;
      window._gpSyncEnabled = false;
      if (overlay) overlay.style.display = 'flex';
      _gpSetSync('hidden'); // Cache le badge quand non connecté
    }
  });"""

html = html.replace(OLD_AUTH, NEW_AUTH, 1)

# ─── 4. Corriger constructionJobs dans export/import JSON ─────────
OLD_EXPORT = "function exportBackup(){let data={products,clients,materialOrders,isolationQuotes,invoices};"
NEW_EXPORT = "function exportBackup(){let cj=(typeof constructionJobs!=='undefined')?constructionJobs:[];let data={products,clients,materialOrders,isolationQuotes,invoices,constructionJobs:cj};"
if OLD_EXPORT in html:
    html = html.replace(OLD_EXPORT, NEW_EXPORT, 1)

OLD_IMPORT = "r.onload=x=>{let d=JSON.parse(x.target.result);products=d.products||products;clients=d.clients||clients;materialOrders=d.materialOrders||materialOrders;isolationQuotes=d.isolationQuotes||isolationQuotes;invoices=d.invoices||invoices;persist()}"
NEW_IMPORT = "r.onload=x=>{let d=JSON.parse(x.target.result);products=d.products||products;clients=d.clients||clients;materialOrders=d.materialOrders||materialOrders;isolationQuotes=d.isolationQuotes||isolationQuotes;invoices=d.invoices||invoices;if(d.constructionJobs&&typeof constructionJobs!=='undefined')constructionJobs=d.constructionJobs;persist()}"
if OLD_IMPORT in html:
    html = html.replace(OLD_IMPORT, NEW_IMPORT, 1)

# ─── 5. Meta tags PWA dans <head> ─────────────────────────────────
if 'apple-mobile-web-app-capable' not in html:
    PWA = """
  <meta name="mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
  <meta name="apple-mobile-web-app-title" content="GP Gestion">
  <meta name="theme-color" content="#7ac943">
"""
    html = html.replace('</head>', PWA + '</head>', 1)

with open(DEST, 'w', encoding='utf-8') as f:
    f.write(html)

print(f'✅ Sync corrigé : {DEST}  ({len(html)//1024} KB — {html.count(chr(10))} lignes)')
