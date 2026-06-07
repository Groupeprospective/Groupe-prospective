#!/usr/bin/env python3
"""
Patch complet — Groupe Prospective index.html
Corrections + améliorations toutes appliquées en une passe.
"""
import re, sys

SRC  = sys.argv[1] if len(sys.argv)>1 else 'index.html'
DEST = sys.argv[2] if len(sys.argv)>2 else 'index.html'

with open(SRC, 'r', encoding='utf-8') as f:
    html = f.read()

# ══════════════════════════════════════════════════════════════════
# 1. CORRECTION ERREUR SYNC
#    Problème : _gpLoadFromCloud affiche "Erreur sync" si Firestore
#    refuse la connexion (règles ou réseau). On améliore la gestion
#    d'erreur et on cache le badge quand non connecté.
# ══════════════════════════════════════════════════════════════════
OLD_SETYNC = '''function _gpSetSync(state) {
  var dot = document.getElementById('gpSyncDot');
  var txt = document.getElementById('gpSyncTxt');
  if (!dot || !txt) return;
  if (state==='saving'){dot.style.background='#ffcc66';txt.textContent='Sync en cours…';}
  else if(state==='saved'){dot.style.background='#22d18b';txt.textContent='Sauvegardé ✓';}
  else if(state==='error'){dot.style.background='#ff5c5c';txt.textContent='Erreur sync';}
  else{dot.style.background='#9da79f';txt.textContent='Sync';}
}'''

NEW_SETYNC = '''function _gpSetSync(state, detail) {
  var badge = document.getElementById('gpSyncBadge');
  var dot   = document.getElementById('gpSyncDot');
  var txt   = document.getElementById('gpSyncTxt');
  if (!dot || !txt) return;
  if (state==='hidden'){if(badge)badge.style.display='none';return;}
  if(badge)badge.style.display='flex';
  if (state==='saving'){
    dot.style.background='#ffcc66';
    txt.textContent='Sauvegarde…';
  } else if(state==='saved'){
    dot.style.background='#22d18b';
    txt.textContent='Sauvegardé ✓ '+_gpTimeNow();
  } else if(state==='error'){
    dot.style.background='#ff5c5c';
    txt.textContent = detail ? ('Sync: '+detail) : 'Hors ligne — données locales OK';
    // Retry automatique dans 30 secondes
    clearTimeout(window._gpRetryTimer);
    window._gpRetryTimer = setTimeout(function(){
      if(window._gpCurrentUser && window._gpSyncEnabled) _gpSaveToCloud();
    }, 30000);
  } else if(state==='offline'){
    dot.style.background='#9da79f';
    txt.textContent='Mode local';
  } else {
    dot.style.background='#9da79f';
    txt.textContent='Sync';
  }
}
function _gpTimeNow(){
  var d=new Date();
  return d.getHours().toString().padStart(2,'0')+':'+d.getMinutes().toString().padStart(2,'0');
}'''

html = html.replace(OLD_SETYNC, NEW_SETYNC, 1)

# Amélioration _gpLoadFromCloud — message d'erreur plus précis
OLD_LOAD_ERR = "  }).catch(function(e){console.error('Load error',e);_gpSetSync('error');});"
NEW_LOAD_ERR = """  }).catch(function(e){
    console.error('Load error',e);
    var msg = e.code==='permission-denied' ? 'Règles Firestore à configurer'
            : e.code==='unavailable'       ? 'Hors ligne'
            : 'Erreur réseau';
    _gpSetSync('error', msg);
    window._gpSyncEnabled = true; // Continue en mode local
  });"""
html = html.replace(OLD_LOAD_ERR, NEW_LOAD_ERR, 1)

# Cacher le badge quand l'utilisateur n'est pas connecté
OLD_AUTH_STATE = """    }else{
      window._gpCurrentUser=null;
      window._gpSyncEnabled=false;
      if(overlay)overlay.style.display='flex';
    }"""
NEW_AUTH_STATE = """    }else{
      window._gpCurrentUser=null;
      window._gpSyncEnabled=false;
      if(overlay)overlay.style.display='flex';
      _gpSetSync('hidden');
    }"""
html = html.replace(OLD_AUTH_STATE, NEW_AUTH_STATE, 1)

# ══════════════════════════════════════════════════════════════════
# 2. CORRIGER constructionJobs ABSENT DE L'EXPORT BACKUP JSON
# ══════════════════════════════════════════════════════════════════
OLD_EXPORT = "function exportBackup(){let data={products,clients,materialOrders,isolationQuotes,invoices};"
NEW_EXPORT = "function exportBackup(){let cj=(typeof constructionJobs!=='undefined')?constructionJobs:[];let data={products,clients,materialOrders,isolationQuotes,invoices,constructionJobs:cj};"
html = html.replace(OLD_EXPORT, NEW_EXPORT, 1)

OLD_IMPORT = "r.onload=x=>{let d=JSON.parse(x.target.result);products=d.products||products;clients=d.clients||clients;materialOrders=d.materialOrders||materialOrders;isolationQuotes=d.isolationQuotes||isolationQuotes;invoices=d.invoices||invoices;persist()}"
NEW_IMPORT = "r.onload=x=>{let d=JSON.parse(x.target.result);products=d.products||products;clients=d.clients||clients;materialOrders=d.materialOrders||materialOrders;isolationQuotes=d.isolationQuotes||isolationQuotes;invoices=d.invoices||invoices;if(d.constructionJobs&&typeof constructionJobs!=='undefined')constructionJobs=d.constructionJobs;persist()}"
html = html.replace(OLD_IMPORT, NEW_IMPORT, 1)

# ══════════════════════════════════════════════════════════════════
# 3. AJOUTER STATUT "En cours" DANS LE WORKFLOW ISOLATION
# ══════════════════════════════════════════════════════════════════
# Le statut "En cours" est absent de l'affichage workflow visuel
OLD_WORKFLOW_STEPS = "const statusOrder=['Brouillon','Envoyé','Accepté','Dépôt reçu','Planifié','Terminé','Facturé'];"
NEW_WORKFLOW_STEPS = "const statusOrder=['Brouillon','Envoyé','Accepté','Dépôt reçu','Planifié','En cours','Terminé','Facturé'];"
if OLD_WORKFLOW_STEPS in html:
    html = html.replace(OLD_WORKFLOW_STEPS, NEW_WORKFLOW_STEPS, 1)

# ══════════════════════════════════════════════════════════════════
# 4. BLOC JS FINAL — toutes les nouvelles fonctionnalités
# ══════════════════════════════════════════════════════════════════
IMPROVEMENTS_JS = """
<script>
/* ================================================================
   GROUPE PROSPECTIVE — AMÉLIORATIONS v2
   ================================================================ */

// ── Paramètres entreprise (stockés en localStorage) ─────────────
(function gpCompanySettings(){
  var LS = 'gp_center_v2_';
  var KEY = LS + 'companySettings';

  function getSettings(){
    try{ return JSON.parse(localStorage.getItem(KEY)) || {}; }catch(e){ return {}; }
  }
  function saveSettings(s){
    localStorage.setItem(KEY, JSON.stringify(s));
  }

  window.gpGetSettings = getSettings;
  window.gpSaveSettings = saveSettings;

  // Injecte les paramètres dans tous les documents PDF
  window.gpCompanyBlock = function(){
    var s = getSettings();
    var lines = [];
    if(s.rbq)   lines.push('RBQ : ' + s.rbq);
    if(s.neq)   lines.push('NEQ : ' + s.neq);
    if(s.tps)   lines.push('TPS : ' + s.tps);
    if(s.tvq)   lines.push('TVQ : ' + s.tvq);
    if(s.ccq)   lines.push('CCQ : ' + s.ccq);
    return lines.join(' &nbsp;·&nbsp; ');
  };
})();

// ── Validité des devis (30 jours par défaut) ─────────────────────
window.gpQuoteExpiry = function(dateStr, days){
  days = days || 30;
  var d = new Date(dateStr);
  d.setDate(d.getDate() + days);
  return d.toISOString().slice(0,10);
};
window.gpIsQuoteExpired = function(q){
  if(!q || !q.date) return false;
  if(['Accepté','Dépôt reçu','Planifié','En cours','Terminé','Facturé'].includes(q.status)) return false;
  var expiry = gpQuoteExpiry(q.date, q.validDays||30);
  return expiry < new Date().toISOString().slice(0,10);
};
window.gpDaysUntilExpiry = function(q){
  if(!q || !q.date) return null;
  var expiry = new Date(gpQuoteExpiry(q.date, q.validDays||30));
  var today  = new Date();
  return Math.ceil((expiry - today) / 86400000);
};

// ── Panneau Paramètres entreprise ───────────────────────────────
function gpInjectSettingsPanel(){
  if(document.getElementById('gpSettingsPanel')) return;

  // Ajouter onglet "Paramètres" dans la nav
  var nav = document.querySelector('nav.nav');
  if(nav){
    var btn = document.createElement('button');
    btn.id = 'gpSettingsNavBtn';
    btn.textContent = '⚙ Paramètres';
    btn.onclick = function(){ gpShowSettingsPanel(); };
    btn.style.cssText = 'background:transparent;color:var(--muted);border:1px solid transparent;';
    nav.appendChild(btn);
  }

  // Créer la section paramètres
  var main = document.querySelector('main.wrap');
  if(!main) return;

  var s = window.gpGetSettings();
  var section = document.createElement('section');
  section.id = 'gpSettingsPanel';
  section.className = 'page hidden';
  section.innerHTML = `
    <div class="card" style="max-width:780px;margin:0 auto">
      <h2>⚙ Paramètres de l'entreprise</h2>
      <p class="muted" style="margin-bottom:20px">Ces informations apparaissent sur vos devis et factures PDF.</p>

      <div style="display:grid;grid-template-columns:repeat(2,1fr);gap:14px">
        <div>
          <label>Nom de l'entreprise</label>
          <input id="gps_name" value="${s.name||'Groupe Prospective'}" placeholder="Groupe Prospective">
        </div>
        <div>
          <label>Adresse</label>
          <input id="gps_address" value="${s.address||'St-Cyrille-de-Wendover, QC'}" placeholder="Ville, QC">
        </div>
        <div>
          <label>Téléphone</label>
          <input id="gps_phone" value="${s.phone||''}" placeholder="819-XXX-XXXX">
        </div>
        <div>
          <label>Courriel</label>
          <input id="gps_email" value="${s.email||''}" placeholder="info@groupeprospective.com">
        </div>
        <div>
          <label>Numéro RBQ <span style="color:#ff5c5c">*</span></label>
          <input id="gps_rbq" value="${s.rbq||''}" placeholder="5821-XXXX-XX">
        </div>
        <div>
          <label>Numéro NEQ</label>
          <input id="gps_neq" value="${s.neq||''}" placeholder="XXXXXXXXX">
        </div>
        <div>
          <label>Numéro TPS</label>
          <input id="gps_tps" value="${s.tps||''}" placeholder="RT XXXXXXXXX">
        </div>
        <div>
          <label>Numéro TVQ</label>
          <input id="gps_tvq" value="${s.tvq||''}" placeholder="XXXXXXXXX TQ 0001">
        </div>
        <div>
          <label>Numéro CCQ (si applicable)</label>
          <input id="gps_ccq" value="${s.ccq||''}" placeholder="XXXXXXXXX">
        </div>
        <div>
          <label>Assurance responsabilité</label>
          <input id="gps_insurance" value="${s.insurance||''}" placeholder="Montant / Assureur">
        </div>
        <div>
          <label>Validité des devis (jours)</label>
          <input id="gps_validdays" type="number" value="${s.validDays||30}" min="1" max="365">
        </div>
        <div>
          <label>Site web</label>
          <input id="gps_website" value="${s.website||'groupeprospective.netlify.app'}" placeholder="www.votre-site.com">
        </div>
      </div>

      <div style="margin-top:22px;padding:14px;border-radius:16px;background:rgba(255,204,102,.08);border:1px solid rgba(255,204,102,.22)">
        <p style="color:var(--warning);font-weight:900;margin:0 0 8px">⚠ Obligations légales Québec</p>
        <p class="muted" style="margin:0;font-size:13px">Votre numéro RBQ est obligatoire sur tous les contrats de construction. Vos numéros TPS/TVQ sont requis sur toutes les factures si vos revenus dépassent 30 000 $/an.</p>
      </div>

      <div style="margin-top:18px;display:flex;gap:10px">
        <button onclick="gpSaveSettingsForm()">💾 Sauvegarder</button>
        <button class="secondary" onclick="gpCloseSettings()">Fermer</button>
      </div>
      <div id="gpSettingsSaved" style="margin-top:10px;color:#22d18b;font-weight:900;display:none">✅ Paramètres sauvegardés !</div>
    </div>
  `;
  main.appendChild(section);
}

window.gpShowSettingsPanel = function(){
  document.querySelectorAll('.page').forEach(p=>p.classList.add('hidden'));
  var panel = document.getElementById('gpSettingsPanel');
  if(panel){ panel.classList.remove('hidden'); }
  document.querySelectorAll('nav.nav button').forEach(b=>b.classList.remove('active'));
  var nb = document.getElementById('gpSettingsNavBtn');
  if(nb) nb.classList.add('active');
};

window.gpCloseSettings = function(){
  document.querySelectorAll('.page').forEach(p=>p.classList.add('hidden'));
  var dash = document.getElementById('dashboard');
  if(dash) dash.classList.remove('hidden');
  document.querySelectorAll('nav.nav button').forEach((b,i)=>{ if(i===0) b.classList.add('active'); else b.classList.remove('active'); });
};

window.gpSaveSettingsForm = function(){
  var s = {
    name:       document.getElementById('gps_name')?.value?.trim() || '',
    address:    document.getElementById('gps_address')?.value?.trim() || '',
    phone:      document.getElementById('gps_phone')?.value?.trim() || '',
    email:      document.getElementById('gps_email')?.value?.trim() || '',
    rbq:        document.getElementById('gps_rbq')?.value?.trim() || '',
    neq:        document.getElementById('gps_neq')?.value?.trim() || '',
    tps:        document.getElementById('gps_tps')?.value?.trim() || '',
    tvq:        document.getElementById('gps_tvq')?.value?.trim() || '',
    ccq:        document.getElementById('gps_ccq')?.value?.trim() || '',
    insurance:  document.getElementById('gps_insurance')?.value?.trim() || '',
    validDays:  parseInt(document.getElementById('gps_validdays')?.value) || 30,
    website:    document.getElementById('gps_website')?.value?.trim() || '',
  };
  window.gpSaveSettings(s);
  var ok = document.getElementById('gpSettingsSaved');
  if(ok){ ok.style.display='block'; setTimeout(()=>ok.style.display='none',3000); }
  // Déclenche un sync Firebase
  if(typeof _gpSaveToCloud === 'function') {
    clearTimeout(window._gpSyncTimer);
    window._gpSyncTimer = setTimeout(_gpSaveToCloud, 1000);
  }
};

// ── Alertes devis expirés dans le dashboard ──────────────────────
function gpInjectExpiryAlerts(){
  var alertBox = document.getElementById('gpExpiryAlerts');
  if(!alertBox) return;
  var quotes = (typeof isolationQuotes !== 'undefined' ? isolationQuotes : [])
    .concat(typeof constructionJobs !== 'undefined' ? constructionJobs : []);
  var expiring = [], expired = [];
  quotes.forEach(function(q){
    if(!['Brouillon','Envoyé'].includes(q.status||'')) return;
    var days = window.gpDaysUntilExpiry(q);
    if(days === null) return;
    if(days < 0) expired.push({q:q, days:days});
    else if(days <= 7) expiring.push({q:q, days:days});
  });
  var html = '';
  expired.forEach(function(x){
    html += '<div style="padding:10px 14px;border-radius:14px;background:rgba(255,92,92,.10);border:1px solid rgba(255,92,92,.25);margin-bottom:8px;font-size:13px">' +
      '<span style="color:#ffb3b3;font-weight:900">⚠ Devis expiré</span> — ' +
      (x.q.clientName||x.q.client||'Client') + ' · ' +
      'Expiré depuis ' + Math.abs(x.days) + ' jour(s)' +
      '</div>';
  });
  expiring.forEach(function(x){
    html += '<div style="padding:10px 14px;border-radius:14px;background:rgba(255,204,102,.10);border:1px solid rgba(255,204,102,.25);margin-bottom:8px;font-size:13px">' +
      '<span style="color:#ffcc66;font-weight:900">⏰ Expire bientôt</span> — ' +
      (x.q.clientName||x.q.client||'Client') + ' · ' +
      'Expire dans ' + x.days + ' jour(s)' +
      '</div>';
  });
  alertBox.innerHTML = html;
  alertBox.style.display = html ? 'block' : 'none';
}

// ── Bloc numéros légaux pour les pieds de page PDF ───────────────
window.gpLegalFooter = function(){
  var s = window.gpGetSettings ? window.gpGetSettings() : {};
  var parts = [];
  if(s.rbq) parts.push('RBQ : ' + s.rbq);
  if(s.tps) parts.push('TPS : ' + s.tps);
  if(s.tvq) parts.push('TVQ : ' + s.tvq);
  if(s.neq) parts.push('NEQ : ' + s.neq);
  return parts.length ? '<div style="margin-top:10px;font-size:11px;color:#888;border-top:1px solid #eee;padding-top:8px">' + parts.join(' &nbsp;·&nbsp; ') + '</div>' : '';
};

// ── Badge "Expiré" sur les devis ─────────────────────────────────
window.gpExpiryBadge = function(q){
  if(!q || !q.date) return '';
  if(!['Brouillon','Envoyé'].includes(q.status||'')) return '';
  var days = window.gpDaysUntilExpiry(q);
  if(days === null) return '';
  if(days < 0) return '<span style="background:rgba(255,92,92,.16);color:#ffb3b3;padding:3px 8px;border-radius:999px;font-size:11px;font-weight:900;margin-left:6px">EXPIRÉ</span>';
  if(days <= 7) return '<span style="background:rgba(255,204,102,.16);color:#ffcc66;padding:3px 8px;border-radius:999px;font-size:11px;font-weight:900;margin-left:6px">Expire dans '+days+'j</span>';
  return '';
};

// ── PWA — manifest dynamique ─────────────────────────────────────
(function gpInjectPWA(){
  if(document.querySelector('link[rel="manifest"]')) return;
  var manifest = {
    name: 'Groupe Prospective — Gestion',
    short_name: 'GP Gestion',
    description: 'Logiciel de gestion Groupe Prospective',
    start_url: '/',
    display: 'standalone',
    background_color: '#070a08',
    theme_color: '#7ac943',
    icons: [
      { src: 'logo.png', sizes: '192x192', type: 'image/png' },
      { src: 'logo.png', sizes: '512x512', type: 'image/png' }
    ]
  };
  var blob = new Blob([JSON.stringify(manifest)], {type:'application/json'});
  var url  = URL.createObjectURL(blob);
  var link = document.createElement('link');
  link.rel  = 'manifest';
  link.href = url;
  document.head.appendChild(link);

  var meta = document.createElement('meta');
  meta.name = 'theme-color';
  meta.content = '#7ac943';
  document.head.appendChild(meta);

  var metaApple = document.createElement('meta');
  metaApple.name = 'apple-mobile-web-app-capable';
  metaApple.content = 'yes';
  document.head.appendChild(metaApple);
})();

// ── Initialisation au démarrage ──────────────────────────────────
document.addEventListener('DOMContentLoaded', function(){
  setTimeout(function(){
    gpInjectSettingsPanel();

    // Injecter la zone d'alertes expiration dans le dashboard
    var dash = document.getElementById('dashboard');
    if(dash){
      var alertDiv = document.createElement('div');
      alertDiv.id = 'gpExpiryAlerts';
      alertDiv.style.marginBottom = '14px';
      dash.prepend(alertDiv);
    }

    // Vérifier les expirations à chaque rendu du dashboard
    var origRenderDash = window.renderDashboard;
    if(typeof origRenderDash === 'function'){
      window.renderDashboard = function(){
        origRenderDash.apply(this, arguments);
        gpInjectExpiryAlerts();
      };
    }

    gpInjectExpiryAlerts();
  }, 600);
});

</script>
"""

html = html.replace('</body>', IMPROVEMENTS_JS + '\n</body>', 1)

# ══════════════════════════════════════════════════════════════════
# 5. PWA — ajouter meta tags dans <head>
# ══════════════════════════════════════════════════════════════════
PWA_META = '''
  <meta name="mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
  <meta name="apple-mobile-web-app-title" content="GP Gestion">
  <meta name="theme-color" content="#7ac943">
'''
html = html.replace('</head>', PWA_META + '</head>', 1)

with open(DEST, 'w', encoding='utf-8') as f:
    f.write(html)

print(f'✅ Fichier patché : {DEST}  ({len(html)//1024} KB)')
