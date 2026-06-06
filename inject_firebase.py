#!/usr/bin/env python3
"""
Injecte Firebase (Auth + Firestore) dans le HTML Groupe Prospective.
Usage: python3 inject_firebase.py <input.html> <output.html>
"""
import sys, re

SRC  = sys.argv[1] if len(sys.argv) > 1 else "input.html"
DEST = sys.argv[2] if len(sys.argv) > 2 else "index.html"

with open(SRC, "r", encoding="utf-8") as f:
    html = f.read()

# ── 1. Scripts Firebase dans <head> ─────────────────────────────────────────
FIREBASE_SCRIPTS = """
  <!-- ===== FIREBASE SDK ===== -->
  <script src="https://www.gstatic.com/firebasejs/10.12.0/firebase-app-compat.js"></script>
  <script src="https://www.gstatic.com/firebasejs/10.12.0/firebase-auth-compat.js"></script>
  <script src="https://www.gstatic.com/firebasejs/10.12.0/firebase-firestore-compat.js"></script>
"""
html = html.replace("</head>", FIREBASE_SCRIPTS + "</head>", 1)

# ── 2. Overlay d'authentification (injecté après <body>) ────────────────────
AUTH_OVERLAY = """
<!-- ===== OVERLAY AUTH FIREBASE ===== -->
<style>
#gpAuthOverlay{position:fixed;inset:0;z-index:99999;background:radial-gradient(circle at 10% 0%,rgba(122,201,67,.22),transparent 34%),linear-gradient(135deg,#070a08,#0d120f 58%,#07110d);display:flex;align-items:center;justify-content:center;padding:24px}
#gpAuthOverlay.hidden{display:none!important}
.gp-auth-box{width:100%;max-width:400px;background:rgba(16,22,18,.95);border:1px solid rgba(122,201,67,.28);border-radius:28px;padding:36px;box-shadow:0 30px 80px rgba(0,0,0,.55)}
.gp-auth-logo{width:220px;display:block;margin:0 auto 22px;background:#050705;border-radius:16px;padding:5px}
.gp-auth-title{text-align:center;font-size:22px;font-weight:950;color:#f6f8f4;margin:0 0 6px}
.gp-auth-sub{text-align:center;color:#9da79f;font-size:14px;margin:0 0 26px}
.gp-auth-label{display:block;color:#9da79f;font-size:11px;font-weight:800;text-transform:uppercase;letter-spacing:.07em;margin:0 0 6px}
.gp-auth-input{width:100%;padding:11px 14px;border-radius:14px;border:1px solid rgba(255,255,255,.12);background:rgba(255,255,255,.055);color:#f6f8f4;outline:none;font-size:14px;margin-bottom:16px}
.gp-auth-input:focus{border-color:rgba(122,201,67,.5)}
.gp-auth-btn{width:100%;padding:13px;border-radius:14px;border:0;background:#7ac943;color:#07110d;font-weight:950;font-size:15px;cursor:pointer;margin-top:4px}
.gp-auth-btn:hover{filter:brightness(1.08)}
.gp-auth-err{color:#ffb3b3;font-size:13px;text-align:center;margin-top:10px;min-height:20px}
.gp-sync-bar{position:fixed;bottom:18px;right:18px;z-index:9000;display:flex;align-items:center;gap:8px;padding:9px 14px;border-radius:999px;background:rgba(16,22,18,.92);border:1px solid rgba(255,255,255,.12);font-size:12px;font-weight:900;color:#9da79f;box-shadow:0 8px 24px rgba(0,0,0,.35);transition:.3s}
.gp-sync-bar.syncing{border-color:rgba(255,204,102,.4);color:#ffcc66}
.gp-sync-bar.ok{border-color:rgba(34,209,139,.35);color:#22d18b}
.gp-sync-bar.err{border-color:rgba(255,92,92,.35);color:#ffb3b3}
.gp-sync-dot{width:8px;height:8px;border-radius:50%;background:currentColor}
.gp-user-chip{display:inline-flex;align-items:center;gap:7px;padding:7px 12px;border-radius:999px;background:rgba(122,201,67,.12);border:1px solid rgba(122,201,67,.28);color:#7ac943;font-size:12px;font-weight:900;cursor:pointer}
.gp-user-chip:hover{background:rgba(122,201,67,.2)}
</style>

<div id="gpAuthOverlay">
  <div class="gp-auth-box">
    <img id="gpAuthLogo" class="gp-auth-logo" src="" alt="Groupe Prospective">
    <h2 class="gp-auth-title">Groupe Prospective</h2>
    <p class="gp-auth-sub">Centre de gestion — Connexion sécurisée</p>
    <label class="gp-auth-label" for="gpAuthEmail">Courriel</label>
    <input class="gp-auth-input" id="gpAuthEmail" type="email" placeholder="votre@email.com" autocomplete="email">
    <label class="gp-auth-label" for="gpAuthPass">Mot de passe</label>
    <input class="gp-auth-input" id="gpAuthPass" type="password" placeholder="••••••••" autocomplete="current-password"
           onkeydown="if(event.key==='Enter')gpDoLogin()">
    <button class="gp-auth-btn" onclick="gpDoLogin()">Se connecter</button>
    <div class="gp-auth-err" id="gpAuthErr"></div>
  </div>
</div>

<!-- Barre de sync + chip utilisateur -->
<div class="gp-sync-bar" id="gpSyncBar">
  <div class="gp-sync-dot"></div>
  <span id="gpSyncTxt">En attente…</span>
</div>
"""
html = html.replace("<body>", "<body>\n" + AUTH_OVERLAY, 1)

# ── 3. Bloc Firebase JS — injecté AVANT </body> ─────────────────────────────
FIREBASE_JS = """
<script>
/* ================================================================
   GROUPE PROSPECTIVE — FIREBASE AUTH + FIRESTORE SYNC
   ================================================================
   CONFIGURATION : Remplacez les valeurs ci-dessous par celles de
   votre projet Firebase (console.firebase.google.com).
   ================================================================ */

const GP_FIREBASE_CONFIG = {
  apiKey:            "VOTRE_API_KEY",
  authDomain:        "VOTRE_PROJECT_ID.firebaseapp.com",
  projectId:         "VOTRE_PROJECT_ID",
  storageBucket:     "VOTRE_PROJECT_ID.appspot.com",
  messagingSenderId: "VOTRE_MESSAGING_SENDER_ID",
  appId:             "VOTRE_APP_ID"
};

/* ── Init Firebase ────────────────────────────────────────────── */
let _gpApp, _gpAuth, _gpDb, _gpUid = null;
try {
  _gpApp  = firebase.initializeApp(GP_FIREBASE_CONFIG);
  _gpAuth = firebase.auth();
  _gpDb   = firebase.firestore();
} catch(e) {
  console.warn("[GP Firebase] Init impossible — mode local uniquement.", e.message);
}

/* ── Helpers UI ──────────────────────────────────────────────── */
function gpSyncStatus(state, txt) {
  const bar = document.getElementById('gpSyncBar');
  const msg = document.getElementById('gpSyncTxt');
  if (!bar || !msg) return;
  bar.className = 'gp-sync-bar ' + (state || '');
  msg.textContent = txt || '';
}

function gpShowAuthOverlay(show) {
  const el = document.getElementById('gpAuthOverlay');
  if (el) el.classList.toggle('hidden', !show);
}

function gpSetLogo() {
  const img = document.getElementById('gpAuthLogo');
  if (img && typeof LOGO !== 'undefined') img.src = LOGO;
}

/* ── Login / Logout ──────────────────────────────────────────── */
async function gpDoLogin() {
  const email = (document.getElementById('gpAuthEmail')?.value || '').trim();
  const pass  =  document.getElementById('gpAuthPass')?.value  || '';
  const errEl =  document.getElementById('gpAuthErr');
  if (errEl) errEl.textContent = '';
  if (!email || !pass) {
    if (errEl) errEl.textContent = 'Veuillez entrer votre courriel et mot de passe.';
    return;
  }
  try {
    gpSyncStatus('syncing', 'Connexion…');
    await _gpAuth.signInWithEmailAndPassword(email, pass);
  } catch(e) {
    gpSyncStatus('err', 'Erreur connexion');
    const msgs = {
      'auth/user-not-found':   'Compte introuvable.',
      'auth/wrong-password':   'Mot de passe incorrect.',
      'auth/invalid-email':    'Courriel invalide.',
      'auth/too-many-requests':'Trop de tentatives — réessayez plus tard.',
      'auth/network-request-failed':'Pas de connexion réseau.',
      'auth/invalid-credential':'Courriel ou mot de passe incorrect.'
    };
    if (errEl) errEl.textContent = msgs[e.code] || ('Erreur : ' + e.message);
  }
}

function gpLogout() {
  if (_gpAuth) _gpAuth.signOut();
}

/* ── Charger les données depuis Firestore ────────────────────── */
async function gpLoadFromFirestore(uid) {
  try {
    gpSyncStatus('syncing', 'Chargement des données…');
    const ref  = _gpDb.collection('users').doc(uid).collection('gp').doc('data');
    const snap = await ref.get();
    if (snap.exists) {
      const d = snap.data();
      /* Écrase localStorage avec les données cloud */
      const keys = ['products','clients','materialOrders','isolationQuotes','constructionJobs','invoices'];
      keys.forEach(k => {
        if (d[k] !== undefined) {
          localStorage.setItem('gp_' + k, JSON.stringify(d[k]));
        }
      });
      gpSyncStatus('ok', 'Données chargées ✓');
      return true;
    } else {
      gpSyncStatus('ok', 'Nouveau compte — données locales conservées');
      return false;
    }
  } catch(e) {
    console.warn('[GP Firebase] Chargement échoué:', e.message);
    gpSyncStatus('err', 'Hors ligne — données locales');
    return false;
  }
}

/* ── Sauvegarder vers Firestore ──────────────────────────────── */
let _gpSyncTimer = null;
async function gpSyncToFirestore() {
  if (!_gpUid || !_gpDb) return;
  try {
    gpSyncStatus('syncing', 'Sauvegarde…');
    const ref = _gpDb.collection('users').doc(_gpUid).collection('gp').doc('data');
    await ref.set({
      products:         JSON.parse(localStorage.getItem('gp_products')         || '[]'),
      clients:          JSON.parse(localStorage.getItem('gp_clients')          || '[]'),
      materialOrders:   JSON.parse(localStorage.getItem('gp_materialOrders')   || '[]'),
      isolationQuotes:  JSON.parse(localStorage.getItem('gp_isolationQuotes')  || '[]'),
      constructionJobs: JSON.parse(localStorage.getItem('gp_constructionJobs') || '[]'),
      invoices:         JSON.parse(localStorage.getItem('gp_invoices')         || '[]'),
      updatedAt:        firebase.firestore.FieldValue.serverTimestamp()
    });
    gpSyncStatus('ok', 'Sauvegardé ✓ ' + new Date().toLocaleTimeString('fr-CA',{hour:'2-digit',minute:'2-digit'}));
  } catch(e) {
    console.warn('[GP Firebase] Sync échoué:', e.message);
    gpSyncStatus('err', 'Sync échoué — données locales OK');
  }
}

/* Sync avec délai (évite spam sur saisie rapide) */
function gpDebouncedSync() {
  if (_gpSyncTimer) clearTimeout(_gpSyncTimer);
  _gpSyncTimer = setTimeout(gpSyncToFirestore, 1500);
}

/* ── Surcharge de persist() pour ajouter le sync cloud ──────── */
(function patchPersist() {
  /* Attend que l'app soit initialisée avant de patcher */
  const _wait = setInterval(() => {
    if (typeof persist === 'function') {
      clearInterval(_wait);
      const _origPersist = persist;
      persist = function() {
        _origPersist.apply(this, arguments);
        gpDebouncedSync();
      };
    }
  }, 100);
})();

/* ── Chip utilisateur dans l'entête ─────────────────────────── */
function gpInjectUserChip(email) {
  /* Cherche la zone .actions dans le header */
  const actions = document.querySelector('header .actions');
  if (!actions) return;
  let chip = document.getElementById('gpUserChip');
  if (!chip) {
    chip = document.createElement('div');
    chip.id = 'gpUserChip';
    chip.className = 'gp-user-chip noprint';
    chip.title = 'Se déconnecter';
    chip.onclick = () => { if (confirm('Se déconnecter ?')) gpLogout(); };
    actions.prepend(chip);
  }
  const short = email.split('@')[0];
  chip.innerHTML = '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="8" r="4"/><path d="M4 20c0-4 3.6-7 8-7s8 3 8 7"/></svg>' + short;
}

/* ── Observateur d'authentification (point d'entrée) ─────────── */
if (_gpAuth) {
  _gpAuth.onAuthStateChanged(async (user) => {
    if (user) {
      _gpUid = user.uid;
      gpShowAuthOverlay(false);
      gpInjectUserChip(user.email);

      /* Charge les données Firestore puis réinitialise l'UI */
      const loaded = await gpLoadFromFirestore(user.uid);
      if (loaded) {
        /* Recharge les variables JS depuis localStorage mis à jour */
        try {
          if (typeof products          !== 'undefined') { const d = JSON.parse(localStorage.getItem('gp_products')         || 'null'); if(d) { products         = d; } }
          if (typeof clients           !== 'undefined') { const d = JSON.parse(localStorage.getItem('gp_clients')          || 'null'); if(d) { clients          = d; } }
          if (typeof materialOrders    !== 'undefined') { const d = JSON.parse(localStorage.getItem('gp_materialOrders')   || 'null'); if(d) { materialOrders   = d; } }
          if (typeof isolationQuotes   !== 'undefined') { const d = JSON.parse(localStorage.getItem('gp_isolationQuotes')  || 'null'); if(d) { isolationQuotes  = d; selectedQuoteId = isolationQuotes[0]?.id || null; } }
          if (typeof constructionJobs  !== 'undefined') { const d = JSON.parse(localStorage.getItem('gp_constructionJobs') || 'null'); if(d) { constructionJobs = d; selectedConstructionId = constructionJobs[0]?.id || null; } }
          if (typeof invoices          !== 'undefined') { const d = JSON.parse(localStorage.getItem('gp_invoices')         || 'null'); if(d) { invoices         = d; selectedInvoiceId = invoices[0]?.id || null; } }
          if (typeof renderAll === 'function') renderAll();
        } catch(e) {
          console.warn('[GP Firebase] Rechargement variables:', e);
        }
      }
    } else {
      _gpUid = null;
      gpShowAuthOverlay(true);
      gpSyncStatus('', 'Non connecté');
      const chip = document.getElementById('gpUserChip');
      if (chip) chip.remove();
    }
  });
} else {
  /* Firebase non configuré — mode local seulement */
  gpShowAuthOverlay(false);
  gpSyncStatus('err', '⚠ Firebase non configuré');
}

/* Injecte le logo dans l'overlay après chargement */
window.addEventListener('load', gpSetLogo);
</script>
"""
html = html.replace("</body>", FIREBASE_JS + "\n</body>", 1)

# ── 4. Écrire le fichier de sortie ───────────────────────────────────────────
with open(DEST, "w", encoding="utf-8") as f:
    f.write(html)

print(f"✅ Généré : {DEST}  ({len(html)//1024} KB)")
