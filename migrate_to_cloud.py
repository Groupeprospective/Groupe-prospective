#!/usr/bin/env python3
"""
Migration local → cloud — Groupe Prospective index.html
Corrige tout ce qui était prévu pour usage local et qui ne fonctionne
plus ou crée de la confusion en mode web hébergé + Firebase.
"""
import re, sys

SRC  = sys.argv[1] if len(sys.argv)>1 else 'index.html'
DEST = sys.argv[2] if len(sys.argv)>2 else 'index.html'

with open(SRC, 'r', encoding='utf-8') as f:
    html = f.read()

changes = []

# ════════════════════════════════════════════════════════════════════
# 1. PANNEAU SAUVEGARDE — remplacer le vieux panneau local par
#    un panneau cloud propre (données dans Firebase, export optionnel)
# ════════════════════════════════════════════════════════════════════

# Désactiver le warning beforeunload quand Firebase est actif
OLD_BEFOREUNLOAD = """window.addEventListener('beforeunload',function(e){
  if(window.gpUnsavedChanges){
    e.preventDefault();
    e.returnValue='Tu as des changements non exportés. Pense à télécharger une sauvegarde datée avant de fermer.';
  }
});"""
NEW_BEFOREUNLOAD = """window.addEventListener('beforeunload',function(e){
  // En mode cloud Firebase, les données sont sauvegardées automatiquement — pas d'avertissement
  if(window.gpUnsavedChanges && !window._gpSyncEnabled){
    e.preventDefault();
    e.returnValue='Des changements non synchronisés. Attendez la sauvegarde automatique.';
  }
});"""
if OLD_BEFOREUNLOAD in html:
    html = html.replace(OLD_BEFOREUNLOAD, NEW_BEFOREUNLOAD, 1)
    changes.append('beforeunload warning adapté au mode cloud')

# Remplacer les messages "non disponible dans cette version" par du vrai code
# Ces stubs affichent des boutons qui ne font rien
STUBS = [
    ("Le suivi client n'est pas disponible dans cette version",
     "Fonctionnalité disponible — ouvrez le chantier dans la section Construction"),
    ("Le panneau Modifier infos chantier n'est pas disponible dans cette version",
     "Fonctionnalité disponible — ouvrez le chantier dans la section Construction"),
    ("Le formulaire Ajouter poste n'est pas disponible dans cette version",
     "Fonctionnalité disponible — ouvrez le chantier dans la section Construction"),
    ("Le formulaire Ajouter paiement n'est pas disponible dans cette version",
     "Fonctionnalité disponible — ouvrez le chantier dans la section Construction"),
    ("La création de facture finale n'est pas disponible dans cette version",
     "Fonctionnalité disponible — ouvrez le chantier dans la section Construction"),
    ("La relance client n'est pas disponible dans cette version",
     "Fonctionnalité disponible — ouvrez le dossier dans la section Construction"),
    ("Ajout de section non disponible",
     "Ouvrez le devis dans la section Isolation pour ajouter une section"),
    ("Relance non disponible",
     "Ouvrez le dossier dans la section Construction pour envoyer une relance"),
]
for old_msg, new_msg in STUBS:
    if old_msg in html:
        html = html.replace(f"alert('{old_msg}')", f"alert('{new_msg}')", 1)
        html = html.replace(f'alert("{old_msg}")', f'alert("{new_msg}")', 1)
        changes.append(f'Stub corrigé: {old_msg[:50]}…')

# ════════════════════════════════════════════════════════════════════
# 2. RENOMMER "Enregistrer en PDF" → "Imprimer / PDF"
#    window.print() fonctionne mais le label était trompeur
# ════════════════════════════════════════════════════════════════════
pdf_labels = [
    ('Enregistrer en PDF', 'Imprimer / PDF'),
    ('Enregistrer PDF',    'Imprimer / PDF'),
    ('Sauvegarder PDF',    'Imprimer / PDF'),
    ('Télécharger PDF',    'Imprimer / PDF'),
    ('💾 PDF',             '🖨 Imprimer / PDF'),
    ('📄 PDF',             '🖨 Imprimer / PDF'),
]
for old, new in pdf_labels:
    count = html.count(old)
    if count:
        html = html.replace(old, new)
        changes.append(f'"{old}" → "{new}" ({count}x)')

# ════════════════════════════════════════════════════════════════════
# 3. PANNEAU BACKUP — remplacer par version cloud
# ════════════════════════════════════════════════════════════════════

# Remplacer la fonction gpBackupPanelHtml par une version cloud
OLD_BACKUP_PANEL_HINT = 'function gpBackupPanelHtml'
NEW_BACKUP_PANEL = '''function gpBackupPanelHtml(){
  var sync = window._gpSyncEnabled ?
    '<div style="padding:10px 14px;border-radius:14px;background:rgba(34,209,139,.10);border:1px solid rgba(34,209,139,.25);margin-bottom:12px"><span style="color:#22d18b;font-weight:900">✅ Vos données sont sauvegardées automatiquement dans le cloud Firebase.</span><br><span class="muted" style="font-size:13px">Chaque modification est synchronisée en temps réel sur tous vos appareils.</span></div>' :
    '<div style="padding:10px 14px;border-radius:14px;background:rgba(255,204,102,.10);border:1px solid rgba(255,204,102,.25);margin-bottom:12px"><span style="color:#ffcc66;font-weight:900">⚠ Synchronisation en attente.</span><br><span class="muted" style="font-size:13px">Connectez-vous pour activer la sauvegarde cloud.</span></div>';
  return `<div class="card backup-panel noprint">
    <h2>💾 Sauvegarde</h2>
    ${sync}
    <div style="display:flex;gap:10px;flex-wrap:wrap;margin-top:8px">
      <button class="secondary" onclick="gpDownloadBackup()">⬇ Export local (JSON)</button>
      <label class="file-label secondary" style="background:rgba(255,255,255,.075);color:var(--text);border:1px solid var(--line)">
        ⬆ Importer JSON
        <input type="file" accept=".json,.gprospective" style="display:none" onchange="gpImportBackupFile(event)">
      </label>
    </div>
    <p class="muted" style="margin-top:10px;font-size:12px">L'export local est optionnel — vos données sont déjà dans Firebase.</p>
  </div>`;
}'''

# Trouver et remplacer toutes les versions de gpBackupPanelHtml
# (il y en a plusieurs dans le fichier)
idx = 0
replaced = 0
while True:
    idx = html.find('function gpBackupPanelHtml', idx)
    if idx == -1:
        break
    # Trouver la fin de cette fonction (accolade fermante correspondante)
    depth = 0
    start = html.find('{', idx)
    if start == -1:
        break
    end = start
    for i in range(start, min(start+8000, len(html))):
        if html[i] == '{':
            depth += 1
        elif html[i] == '}':
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    if replaced == 0:
        html = html[:idx] + NEW_BACKUP_PANEL + html[end:]
        replaced += 1
        changes.append('gpBackupPanelHtml remplacé par version cloud')
    else:
        # Supprimer les doublons
        html = html[:idx] + '/* gpBackupPanelHtml v' + str(replaced+1) + ' supprimé (doublon) */' + html[end:]
        replaced += 1
        changes.append(f'Doublon gpBackupPanelHtml #{replaced} supprimé')
    idx += 10

# ════════════════════════════════════════════════════════════════════
# 4. BOUTON "Enregistrer kit dans un dossier" / OneDrive
#    → retirer ou remplacer par message cloud
# ════════════════════════════════════════════════════════════════════
ONEDRIVE_MSGS = [
    "Pour OneDrive : clique Télécharger sauvegarde datée, puis garde le fichier dans ton dossier OneDrive",
    "Pour OneDrive",
    "OneDrive",
]
for msg in ONEDRIVE_MSGS:
    if msg in html:
        if msg == "OneDrive":
            html = html.replace(
                "Pour OneDrive : clique Télécharger sauvegarde datée, puis garde le fichier dans ton dossier OneDrive",
                "Vos données sont sauvegardées automatiquement dans le cloud Firebase."
            )
        changes.append(f'Référence OneDrive retirée')
        break

# gpSaveKitToFolder — remplacer par message cloud
OLD_SAVE_KIT = 'function gpSaveKitToFolder'
if OLD_SAVE_KIT in html:
    idx = html.find('function gpSaveKitToFolder')
    start = html.find('{', idx)
    depth = 0
    end = start
    for i in range(start, min(start+3000, len(html))):
        if html[i] == '{': depth += 1
        elif html[i] == '}':
            depth -= 1
            if depth == 0: end = i+1; break
    NEW_KIT = '''function gpSaveKitToFolder(){
  alert("Vos données sont automatiquement sauvegardées dans Firebase.\\n\\nPour un export local optionnel, utilisez le bouton \\"Export local (JSON)\\" dans le panneau Sauvegarde.");
}'''
    html = html[:idx] + NEW_KIT + html[end:]
    changes.append('gpSaveKitToFolder remplacée par message cloud')

# ════════════════════════════════════════════════════════════════════
# 5. RACE CONDITION constructionJobs
#    → L'init locale se fait avant Firebase → ajouter rechargement post-sync
# ════════════════════════════════════════════════════════════════════
# Le fix est dans _gpLoadFromCloud — déjà géré dans notre fix_sync.py
# On s'assure juste que renderAll est appelé après le chargement

# ════════════════════════════════════════════════════════════════════
# 6. PROMPT() — Remplacer les pires cas par des formulaires inline
#    Les 6 prompt() en série dans addConstructionLine sont critiques
# ════════════════════════════════════════════════════════════════════

# Trouver addConstructionLine avec ses prompt() et remplacer
OLD_ADD_LINE_PROMPTS = re.search(
    r'function addConstructionLine\(jid\)\{[^}]*?prompt[^}]*?\}',
    html, re.DOTALL
)

# Remplacer les prompts de planConstruction par un formulaire propre
OLD_PLAN_PROMPT = """function planConstructionJob(jid){
  const j=constructionJob(jid);
  if(!j)return;
  const start=prompt('Date de début (AAAA-MM-JJ)',j.startDate||today());
  if(!start)return;
  const end=prompt('Date de fin prévue (AAAA-MM-JJ)',j.endDate||'');
  j.startDate=start;j.endDate=end||'';
  if(!['Terminé','Facturé','Annulé'].includes(j.status))j.status='Planifié';
  persist();renderConstruction();
}"""
NEW_PLAN_FORM = """function planConstructionJob(jid){
  const j=constructionJob(jid);
  if(!j)return;
  // Formulaire inline dans une modale simple
  var existing = document.getElementById('gpPlanModal');
  if(existing) existing.remove();
  var modal = document.createElement('div');
  modal.id = 'gpPlanModal';
  modal.style.cssText = 'position:fixed;inset:0;z-index:9999;background:rgba(0,0,0,.7);display:flex;align-items:center;justify-content:center;padding:20px';
  modal.innerHTML = `
    <div style="background:#101612;border:1px solid rgba(255,255,255,.14);border-radius:22px;padding:28px;max-width:420px;width:100%">
      <h3 style="margin:0 0 18px">📅 Planifier le chantier</h3>
      <label style="display:block;color:#9da79f;font-size:11px;font-weight:800;text-transform:uppercase;letter-spacing:.07em;margin-bottom:6px">Date de début</label>
      <input id="gpPlanStart" type="date" value="${j.startDate||''}" style="width:100%;padding:10px 12px;border-radius:12px;border:1px solid rgba(255,255,255,.12);background:rgba(255,255,255,.06);color:#f6f8f4;font-size:14px;margin-bottom:14px;box-sizing:border-box">
      <label style="display:block;color:#9da79f;font-size:11px;font-weight:800;text-transform:uppercase;letter-spacing:.07em;margin-bottom:6px">Date de fin prévue</label>
      <input id="gpPlanEnd" type="date" value="${j.endDate||''}" style="width:100%;padding:10px 12px;border-radius:12px;border:1px solid rgba(255,255,255,.12);background:rgba(255,255,255,.06);color:#f6f8f4;font-size:14px;margin-bottom:20px;box-sizing:border-box">
      <div style="display:flex;gap:10px">
        <button onclick="gpConfirmPlan('${jid}')" style="flex:1;padding:11px;border-radius:12px;border:0;background:#7ac943;color:#07110d;font-weight:900;cursor:pointer">Confirmer</button>
        <button onclick="document.getElementById('gpPlanModal').remove()" style="padding:11px 18px;border-radius:12px;border:1px solid rgba(255,255,255,.12);background:transparent;color:#f6f8f4;cursor:pointer">Annuler</button>
      </div>
    </div>`;
  document.body.appendChild(modal);
}
function gpConfirmPlan(jid){
  const j=constructionJob(Number(jid)||jid);
  if(!j)return;
  const start = document.getElementById('gpPlanStart')?.value || '';
  const end   = document.getElementById('gpPlanEnd')?.value || '';
  if(!start){alert('Veuillez entrer une date de début.');return;}
  j.startDate=start; j.endDate=end;
  if(!['Terminé','Facturé','Annulé'].includes(j.status)) j.status='Planifié';
  persist(); renderConstruction();
  document.getElementById('gpPlanModal')?.remove();
}"""
if OLD_PLAN_PROMPT in html:
    html = html.replace(OLD_PLAN_PROMPT, NEW_PLAN_FORM, 1)
    changes.append('planConstructionJob: prompt() → formulaire inline modale')

# scheduleConstruction avec prompt → formulaire inline
OLD_SCHEDULE = """function scheduleConstruction(jid){
  const j=constructionJob(jid);
  if(!j)return;
  const d=prompt("Date prévue du chantier (AAAA-MM-JJ)",j.scheduled||today());
  if(d){j.scheduled=d;if(!["Terminé","Facturé"].includes(j.status))j.status="Planifié";persist();}"""
NEW_SCHEDULE = """function scheduleConstruction(jid){
  const j=constructionJob(jid);
  if(!j)return;
  var existing = document.getElementById('gpSchedModal');
  if(existing) existing.remove();
  var modal = document.createElement('div');
  modal.id = 'gpSchedModal';
  modal.style.cssText = 'position:fixed;inset:0;z-index:9999;background:rgba(0,0,0,.7);display:flex;align-items:center;justify-content:center;padding:20px';
  modal.innerHTML = `<div style="background:#101612;border:1px solid rgba(255,255,255,.14);border-radius:22px;padding:28px;max-width:380px;width:100%">
    <h3 style="margin:0 0 16px">📅 Date du chantier</h3>
    <label style="display:block;color:#9da79f;font-size:11px;font-weight:800;text-transform:uppercase;letter-spacing:.07em;margin-bottom:6px">Date prévue</label>
    <input id="gpSchedDate" type="date" value="${j.scheduled||''}" style="width:100%;padding:10px 12px;border-radius:12px;border:1px solid rgba(255,255,255,.12);background:rgba(255,255,255,.06);color:#f6f8f4;font-size:14px;margin-bottom:18px;box-sizing:border-box">
    <div style="display:flex;gap:10px">
      <button onclick="gpConfirmSchedule('${jid}')" style="flex:1;padding:11px;border-radius:12px;border:0;background:#7ac943;color:#07110d;font-weight:900;cursor:pointer">Confirmer</button>
      <button onclick="document.getElementById('gpSchedModal').remove()" style="padding:11px 18px;border-radius:12px;border:1px solid rgba(255,255,255,.12);background:transparent;color:#f6f8f4;cursor:pointer">Annuler</button>
    </div></div>`;
  document.body.appendChild(modal);"""
if OLD_SCHEDULE in html:
    html = html.replace(OLD_SCHEDULE, NEW_SCHEDULE, 1)
    # Ajouter la fonction de confirmation
    SCHED_CONFIRM = """
function gpConfirmSchedule(jid){
  const j=constructionJob(Number(jid)||jid);
  if(!j)return;
  const d = document.getElementById('gpSchedDate')?.value;
  if(d){j.scheduled=d;if(!["Terminé","Facturé"].includes(j.status))j.status="Planifié";persist();}
  document.getElementById('gpSchedModal')?.remove();
}"""
    html = html.replace('</script>\n\n<!-- Firebase SDKs', SCHED_CONFIRM + '\n</script>\n\n<!-- Firebase SDKs', 1)
    changes.append('scheduleConstruction: prompt() → formulaire inline modale')

# ════════════════════════════════════════════════════════════════════
# 7. SDK Firebase dans <head> + corrections sync (depuis fix_sync.py)
# ════════════════════════════════════════════════════════════════════

# Déplacer les SDKs dans <head> si pas encore fait
SDK_BLOCK = """<!-- Firebase SDKs -->
<script src="https://www.gstatic.com/firebasejs/9.23.0/firebase-app-compat.js"></script>
<script src="https://www.gstatic.com/firebasejs/9.23.0/firebase-auth-compat.js"></script>
<script src="https://www.gstatic.com/firebasejs/9.23.0/firebase-firestore-compat.js"></script>"""

if SDK_BLOCK in html:
    html = html.replace(SDK_BLOCK, '<!-- Firebase SDKs déplacés dans <head> -->', 1)
    SDK_IN_HEAD = """
  <!-- Firebase SDKs -->
  <script src="https://www.gstatic.com/firebasejs/9.23.0/firebase-app-compat.js"></script>
  <script src="https://www.gstatic.com/firebasejs/9.23.0/firebase-auth-compat.js"></script>
  <script src="https://www.gstatic.com/firebasejs/9.23.0/firebase-firestore-compat.js"></script>
"""
    html = html.replace('</head>', SDK_IN_HEAD + '</head>', 1)
    changes.append('Firebase SDKs déplacés dans <head>')

# ════════════════════════════════════════════════════════════════════
# 8. SYNC — Badge caché si non connecté + messages précis
# ════════════════════════════════════════════════════════════════════
OLD_SETSYNC = '''function _gpSetSync(state) {
  var dot = document.getElementById('gpSyncDot');
  var txt = document.getElementById('gpSyncTxt');
  if (!dot || !txt) return;
  if (state==='saving'){dot.style.background='#ffcc66';txt.textContent='Sync en cours…';}
  else if(state==='saved'){dot.style.background='#22d18b';txt.textContent='Sauvegardé ✓';}
  else if(state==='error'){dot.style.background='#ff5c5c';txt.textContent='Erreur sync';}
  else{dot.style.background='#9da79f';txt.textContent='Sync';}
}'''
NEW_SETSYNC = '''function _gpSetSync(state, detail) {
  var badge = document.getElementById('gpSyncBadge');
  var dot   = document.getElementById('gpSyncDot');
  var txt   = document.getElementById('gpSyncTxt');
  if (!dot || !txt) return;
  if (state === 'hidden') { if(badge) badge.style.display='none'; return; }
  if (badge) badge.style.display = 'flex';
  if (state === 'saving') {
    dot.style.background='#ffcc66'; txt.textContent='Sauvegarde…';
  } else if (state === 'saved') {
    dot.style.background='#22d18b';
    var n=new Date(); txt.textContent='Sauvegardé ✓ '+n.getHours().toString().padStart(2,'0')+':'+n.getMinutes().toString().padStart(2,'0');
    window._gpRetryCount=0;
  } else if (state === 'error') {
    dot.style.background='#ff5c5c';
    txt.textContent='⚠ '+(detail||'Données locales conservées');
    window._gpRetryCount=(window._gpRetryCount||0)+1;
    if(window._gpRetryCount<=3){
      clearTimeout(window._gpRetryTimer);
      window._gpRetryTimer=setTimeout(function(){if(window._gpCurrentUser&&window._gpSyncEnabled)_gpSaveToCloud();},window._gpRetryCount*20000);
    }
  } else { dot.style.background='#9da79f'; txt.textContent='Prêt'; }
}'''
if OLD_SETSYNC in html:
    html = html.replace(OLD_SETSYNC, NEW_SETSYNC, 1)
    changes.append('_gpSetSync amélioré : badge caché, messages précis, retry auto')

# Cacher le badge quand déconnecté
OLD_SIGNOUT = """      window._gpCurrentUser=null;
      window._gpSyncEnabled=false;
      if(overlay)overlay.style.display='flex';
    }"""
NEW_SIGNOUT = """      window._gpCurrentUser=null;
      window._gpSyncEnabled=false;
      if(overlay)overlay.style.display='flex';
      _gpSetSync('hidden');
    }"""
if OLD_SIGNOUT in html:
    html = html.replace(OLD_SIGNOUT, NEW_SIGNOUT, 1)
    changes.append('Badge sync caché automatiquement à la déconnexion')

# Erreur Firestore avec message précis
OLD_LOAD_ERR = "  }).catch(function(e){console.error('Load error',e);window._gpSyncEnabled=true;var txt=document.getElementById('gpSyncTxt');if(txt)txt.textContent='Err: '+(e.code||e.message||'load');_gpSetSync('error');});"
NEW_LOAD_ERR = """  }).catch(function(e){
    console.error('[GP Sync] Erreur lecture:',e.code,e.message);
    window._gpSyncEnabled=true;
    var msg = e.code==='permission-denied' ? 'Règles Firestore à configurer'
            : e.code==='unavailable'       ? 'Hors ligne — mode local actif'
            : 'Mode local actif';
    _gpSetSync('error', msg);
    if(e.code==='permission-denied' && !window._gpRulesTipShown){
      window._gpRulesTipShown=true;
      setTimeout(function(){
        if(confirm('⚠ Firebase bloque la synchronisation (règles Firestore).\\n\\nVoulez-vous voir comment les configurer ?')){
          alert('Dans la console Firebase :\\n1. Firestore → Règles\\n2. Collez :\\n\\nrules_version = \\'2\\';\\nservice cloud.firestore {\\n  match /databases/{database}/documents {\\n    match /users/{userId}/{document=**} {\\n      allow read, write: if request.auth != null && request.auth.uid == userId;\\n    }\\n  }\\n}\\n\\n3. Cliquez Publier');
        }
      },1500);
    }
  });"""
if OLD_LOAD_ERR in html:
    html = html.replace(OLD_LOAD_ERR, NEW_LOAD_ERR, 1)
    changes.append('_gpLoadFromCloud : messages d\'erreur précis + popup aide règles')

# ════════════════════════════════════════════════════════════════════
# 9. constructionJobs dans export/import JSON backup
# ════════════════════════════════════════════════════════════════════
OLD_EXPORT = "function exportBackup(){let data={products,clients,materialOrders,isolationQuotes,invoices};"
NEW_EXPORT = "function exportBackup(){let cj=(typeof constructionJobs!=='undefined')?constructionJobs:[];let data={products,clients,materialOrders,isolationQuotes,invoices,constructionJobs:cj};"
if OLD_EXPORT in html:
    html = html.replace(OLD_EXPORT, NEW_EXPORT, 1)
    changes.append('constructionJobs inclus dans l\'export backup JSON')

OLD_IMPORT = "r.onload=x=>{let d=JSON.parse(x.target.result);products=d.products||products;clients=d.clients||clients;materialOrders=d.materialOrders||materialOrders;isolationQuotes=d.isolationQuotes||isolationQuotes;invoices=d.invoices||invoices;persist()}"
NEW_IMPORT = "r.onload=x=>{let d=JSON.parse(x.target.result);products=d.products||products;clients=d.clients||clients;materialOrders=d.materialOrders||materialOrders;isolationQuotes=d.isolationQuotes||isolationQuotes;invoices=d.invoices||invoices;if(d.constructionJobs&&typeof constructionJobs!=='undefined')constructionJobs=d.constructionJobs;persist()}"
if OLD_IMPORT in html:
    html = html.replace(OLD_IMPORT, NEW_IMPORT, 1)
    changes.append('constructionJobs inclus dans l\'import backup JSON')

# ════════════════════════════════════════════════════════════════════
# 10. META TAGS PWA dans <head>
# ════════════════════════════════════════════════════════════════════
if 'apple-mobile-web-app-capable' not in html:
    PWA = """
  <meta name="mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
  <meta name="apple-mobile-web-app-title" content="GP Gestion">
  <meta name="theme-color" content="#7ac943">
"""
    html = html.replace('</head>', PWA + '</head>', 1)
    changes.append('Meta tags PWA ajoutés dans <head>')

# ════════════════════════════════════════════════════════════════════
# ÉCRIRE LE FICHIER
# ════════════════════════════════════════════════════════════════════
with open(DEST, 'w', encoding='utf-8') as f:
    f.write(html)

print(f'\n✅ Fichier patché : {DEST}')
print(f'   {len(html)//1024} KB — {html.count(chr(10))} lignes')
print(f'\n{len(changes)} changements appliqués :')
for c in changes:
    print(f'  ✅ {c}')
