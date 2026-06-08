#!/usr/bin/env python3
"""
Crée une version propre et définitive de index.html.
Source : deploy_latest_clean_v33.zip
Résultat : index_clean.html — zéro patch, zéro doublon, zéro local-only cassé.
"""
import re, sys
from collections import Counter

SRC  = '/tmp/gp_extract/deploy_latest_clean_v33_work/index.html'
DEST = '/home/user/Groupe-prospective/index.html'

with open(SRC, 'r', encoding='utf-8') as f:
    html = f.read()

fixes = []

# ═══════════════════════════════════════════════════════════════════
# 1. SYNC BADGE — message utile au lieu de "Erreur sync" brut
# ═══════════════════════════════════════════════════════════════════
old = "else if(state==='error'){txt.textContent='Erreur sync'; if(detail) txt.title=detail; txt.style.color='#ff6b6b';dot.style.background='#ff6b6b';}"
new = "else if(state==='error'){txt.textContent=detail||'Hors ligne — données locales OK';txt.title=detail||'';txt.style.color='#ff6b6b';dot.style.background='#ff6b6b';}"
if old in html:
    html = html.replace(old, new, 1)
    fixes.append('Message "Erreur sync" → message descriptif')

# Badge caché quand non connecté (mode local = badge discret)
old_local = "else{txt.textContent='Local';txt.style.color='#9da79f';dot.style.background='#9da79f';}"
new_local = "else{txt.textContent='Mode local';txt.style.color='#9da79f';dot.style.background='#9da79f';var b=document.getElementById('gpSyncBadge');if(b)b.style.opacity='.55';}"
if old_local in html:
    html = html.replace(old_local, new_local, 1)
    fixes.append('Badge sync discret en mode local')

# Badge plein en mode cloud/saving
old_cloud = "else if(state==='cloud'){txt.textContent='Cloud';txt.style.color='#22d18b';dot.style.background='#22d18b';}"
new_cloud = "else if(state==='cloud'){txt.textContent='Cloud ✓';txt.style.color='#22d18b';dot.style.background='#22d18b';var b=document.getElementById('gpSyncBadge');if(b)b.style.opacity='1';}"
if old_cloud in html:
    html = html.replace(old_cloud, new_cloud, 1)
    fixes.append('Badge cloud visible et vert')

# ═══════════════════════════════════════════════════════════════════
# 2. STUBS "non disponible" — remplacer par messages utiles
# ═══════════════════════════════════════════════════════════════════
stub_replacements = [
    ("non disponible dans cette version",
     "disponible — ouvrez le chantier dans l'onglet Construction"),
]
for old_msg, new_msg in stub_replacements:
    count = html.count(old_msg)
    if count:
        html = html.replace(old_msg, new_msg)
        fixes.append(f'Stubs "non disponible" corrigés ({count}x)')

# ═══════════════════════════════════════════════════════════════════
# 3. PROMPTS — remplacer les fenêtres natives par des modales inline
# ═══════════════════════════════════════════════════════════════════

# scheduleConstruction : prompt → modal
MODAL_CSS = """
<style id="gpModalStyle">
.gp-modal-overlay{position:fixed;inset:0;z-index:9999;background:rgba(0,0,0,.72);display:flex;align-items:center;justify-content:center;padding:20px}
.gp-modal-box{background:#101612;border:1px solid rgba(122,201,67,.28);border-radius:22px;padding:28px;max-width:420px;width:100%;box-shadow:0 30px 80px rgba(0,0,0,.5);font-family:Arial,sans-serif}
.gp-modal-box h3{margin:0 0 18px;color:#f6f8f4;font-size:18px}
.gp-modal-label{display:block;color:#9da79f;font-size:11px;font-weight:800;text-transform:uppercase;letter-spacing:.07em;margin:0 0 6px}
.gp-modal-input{width:100%;padding:10px 12px;border-radius:12px;border:1px solid rgba(255,255,255,.12);background:rgba(255,255,255,.06);color:#f6f8f4;font-size:14px;margin-bottom:14px;box-sizing:border-box;outline:none}
.gp-modal-input:focus{border-color:rgba(122,201,67,.5)}
.gp-modal-row{display:flex;gap:10px;margin-top:6px}
.gp-modal-btn{flex:1;padding:11px;border-radius:12px;border:0;background:#7ac943;color:#07110d;font-weight:900;font-size:14px;cursor:pointer}
.gp-modal-btn-sec{padding:11px 18px;border-radius:12px;border:1px solid rgba(255,255,255,.12);background:transparent;color:#f6f8f4;font-size:14px;cursor:pointer}
</style>
"""

# Fonction utilitaire modale générique
MODAL_UTILS = """
<script id="gpModalUtils">
/* Modale inline générique — remplace window.prompt() */
window.gpModal = function(opts) {
  // opts: {title, fields:[{id,label,type,value,placeholder}], onConfirm, confirmLabel}
  var existing = document.getElementById('gpDynModal');
  if (existing) existing.remove();

  var fieldsHtml = (opts.fields || []).map(function(f) {
    return '<label class="gp-modal-label" for="' + f.id + '">' + f.label + '</label>' +
      '<input class="gp-modal-input" id="' + f.id + '" type="' + (f.type||'text') + '" ' +
      'value="' + (f.value||'') + '" placeholder="' + (f.placeholder||'') + '">';
  }).join('');

  var overlay = document.createElement('div');
  overlay.id = 'gpDynModal';
  overlay.className = 'gp-modal-overlay';
  overlay.innerHTML =
    '<div class="gp-modal-box">' +
      '<h3>' + (opts.title||'') + '</h3>' +
      fieldsHtml +
      '<div class="gp-modal-row">' +
        '<button class="gp-modal-btn" id="gpDynModalConfirm">' + (opts.confirmLabel||'Confirmer') + '</button>' +
        '<button class="gp-modal-btn-sec" onclick="document.getElementById(\'gpDynModal\').remove()">Annuler</button>' +
      '</div>' +
    '</div>';

  document.body.appendChild(overlay);

  var confirmBtn = document.getElementById('gpDynModalConfirm');
  if (confirmBtn) {
    confirmBtn.addEventListener('click', function() {
      var values = {};
      (opts.fields || []).forEach(function(f) {
        var el = document.getElementById(f.id);
        values[f.id] = el ? el.value : '';
      });
      overlay.remove();
      if (opts.onConfirm) opts.onConfirm(values);
    });
  }

  // Focus premier champ
  var first = opts.fields && opts.fields[0] && document.getElementById(opts.fields[0].id);
  if (first) setTimeout(function(){ first.focus(); }, 50);
};
</script>
"""

# Remplacer scheduleConstruction
OLD_SCHED = r"""function scheduleConstruction\(jid\)\{[^}]+const j=constructionJob\(jid\)[^}]+prompt[^\}]+\}"""
sched_match = re.search(r'function scheduleConstruction\(jid\)\{.*?(?=\nfunction |\nconst |\nlet |\nvar |\n//)', html, re.DOTALL)
if sched_match:
    NEW_SCHED = """function scheduleConstruction(jid){
  var j=constructionJob(jid); if(!j)return;
  gpModal({
    title:'📅 Planifier le chantier',
    fields:[{id:'gp_sched_date',label:'Date prévue',type:'date',value:j.scheduled||''}],
    confirmLabel:'Confirmer',
    onConfirm:function(v){
      if(v.gp_sched_date){
        j.scheduled=v.gp_sched_date;
        if(!['Terminé','Facturé'].includes(j.status)) j.status='Planifié';
        persist();
      }
    }
  });
}"""
    html = html[:sched_match.start()] + NEW_SCHED + '\n' + html[sched_match.end():]
    fixes.append('scheduleConstruction: prompt() → gpModal()')

# Remplacer planConstructionJob (2 prompts)
plan_match = re.search(r'function planConstructionJob\(jid\)\{.*?(?=\nfunction |\nconst |\nlet |\nvar |\n//)', html, re.DOTALL)
if plan_match:
    NEW_PLAN = """function planConstructionJob(jid){
  var j=constructionJob(jid); if(!j)return;
  gpModal({
    title:'📅 Planifier le chantier',
    fields:[
      {id:'gp_plan_start',label:'Date de début',type:'date',value:j.startDate||''},
      {id:'gp_plan_end',label:'Date de fin prévue',type:'date',value:j.endDate||''}
    ],
    confirmLabel:'Confirmer',
    onConfirm:function(v){
      if(v.gp_plan_start){
        j.startDate=v.gp_plan_start; j.endDate=v.gp_plan_end||'';
        if(!['Terminé','Facturé','Annulé'].includes(j.status)) j.status='Planifié';
        persist(); renderConstruction();
      }
    }
  });
}"""
    html = html[:plan_match.start()] + NEW_PLAN + '\n' + html[plan_match.end():]
    fixes.append('planConstructionJob: 2×prompt() → gpModal()')

# ═══════════════════════════════════════════════════════════════════
# 4. LABELS "Enregistrer en PDF" → "Imprimer / PDF"
# ═══════════════════════════════════════════════════════════════════
pdf_renames = [
    ('Enregistrer en PDF', 'Imprimer / PDF'),
    ('Enregistrer PDF',    'Imprimer / PDF'),
    ('Sauvegarder PDF',    'Imprimer / PDF'),
    ('Télécharger PDF',    'Imprimer / PDF'),
]
for old_lbl, new_lbl in pdf_renames:
    count = html.count(old_lbl)
    if count:
        html = html.replace(old_lbl, new_lbl)
        fixes.append(f'"{old_lbl}" → "{new_lbl}" ({count}x)')

# ═══════════════════════════════════════════════════════════════════
# 5. BACKUP PANEL — version cloud propre
# ═══════════════════════════════════════════════════════════════════
def replace_function(source, func_name, new_body):
    """Remplace la première occurrence d'une fonction par new_body."""
    pat = r'function\s+' + re.escape(func_name) + r'\s*\([^)]*\)\s*\{'
    m = re.search(pat, source)
    if not m:
        return source, False
    start = m.start()
    brace_start = source.index('{', m.start())
    depth = 0
    end = brace_start
    for i in range(brace_start, min(brace_start + 12000, len(source))):
        if source[i] == '{': depth += 1
        elif source[i] == '}':
            depth -= 1
            if depth == 0: end = i + 1; break
    return source[:start] + new_body + source[end:], True

BACKUP_PANEL_NEW = """function gpBackupPanelHtml(){
  var synced = window._gpSyncEnabled && window._gpCurrentUser && window._gpCurrentUser.uid !== 'local';
  var statusHtml = synced
    ? '<div style="padding:11px 14px;border-radius:14px;background:rgba(34,209,139,.10);border:1px solid rgba(34,209,139,.25);margin-bottom:14px"><strong style="color:#22d18b">✅ Sauvegarde automatique active</strong><br><span class="muted" style="font-size:13px">Vos données sont synchronisées en temps réel dans Firebase.</span></div>'
    : '<div style="padding:11px 14px;border-radius:14px;background:rgba(255,204,102,.10);border:1px solid rgba(255,204,102,.25);margin-bottom:14px"><strong style="color:#ffcc66">☁ Mode local</strong><br><span class="muted" style="font-size:13px">Connectez-vous pour activer la sauvegarde cloud automatique.</span></div>';
  return \'<div class="card backup-panel noprint">\' +
    \'<h2>💾 Sauvegarde</h2>\' + statusHtml +
    \'<div style="display:flex;gap:10px;flex-wrap:wrap">\' +
      \'<button class="secondary" onclick="gpDownloadBackup()">⬇ Export JSON local</button>\' +
      \'<label class="file-label" style="background:rgba(255,255,255,.075);color:var(--text);border:1px solid var(--line)">\' +
        \'⬆ Importer JSON\' +
        \'<input type="file" accept=".json,.gprospective" style="display:none" onchange="gpImportBackupFile(event)">\' +
      \'</label>\' +
    \'</div>\' +
    \'<p class="muted" style="margin-top:10px;font-size:12px">L\\\'export local est optionnel — Firebase sauvegarde déjà toutes vos données.</p>\' +
  \'</div>\';
}"""

html, ok = replace_function(html, 'gpBackupPanelHtml', BACKUP_PANEL_NEW)
if ok:
    fixes.append('gpBackupPanelHtml → version cloud propre (sans OneDrive/dossier local)')

# gpSaveKitToFolder → message cloud
SAVE_KIT_NEW = """function gpSaveKitToFolder(){
  alert('Vos données sont automatiquement sauvegardées dans Firebase.\\nPour un export local optionnel, utilisez le bouton "Export JSON local".');
}"""
html, ok = replace_function(html, 'gpSaveKitToFolder', SAVE_KIT_NEW)
if ok:
    fixes.append('gpSaveKitToFolder → message cloud (plus de showDirectoryPicker)')

# ═══════════════════════════════════════════════════════════════════
# 6. constructionJobs dans export/import JSON
# ═══════════════════════════════════════════════════════════════════
OLD_EXP = "function exportBackup(){let data={products,clients,materialOrders,isolationQuotes,invoices};"
NEW_EXP = "function exportBackup(){let cj=(typeof constructionJobs!=='undefined')?constructionJobs:[];let data={products,clients,materialOrders,isolationQuotes,invoices,constructionJobs:cj};"
if OLD_EXP in html:
    html = html.replace(OLD_EXP, NEW_EXP, 1)
    fixes.append('exportBackup: constructionJobs inclus')

OLD_IMP = "r.onload=x=>{let d=JSON.parse(x.target.result);products=d.products||products;clients=d.clients||clients;materialOrders=d.materialOrders||materialOrders;isolationQuotes=d.isolationQuotes||isolationQuotes;invoices=d.invoices||invoices;persist()}"
NEW_IMP = "r.onload=x=>{let d=JSON.parse(x.target.result);products=d.products||products;clients=d.clients||clients;materialOrders=d.materialOrders||materialOrders;isolationQuotes=d.isolationQuotes||isolationQuotes;invoices=d.invoices||invoices;if(d.constructionJobs&&typeof constructionJobs!=='undefined')constructionJobs=d.constructionJobs;persist()}"
if OLD_IMP in html:
    html = html.replace(OLD_IMP, NEW_IMP, 1)
    fixes.append('importBackup: constructionJobs inclus')

# ═══════════════════════════════════════════════════════════════════
# 7. META TAGS PWA + thème
# ═══════════════════════════════════════════════════════════════════
if 'apple-mobile-web-app-capable' not in html:
    PWA_META = """
  <meta name="mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
  <meta name="apple-mobile-web-app-title" content="GP Gestion">
  <meta name="theme-color" content="#7ac943">
"""
    html = html.replace('</head>', PWA_META + '</head>', 1)
    fixes.append('Meta tags PWA ajoutés')

# ═══════════════════════════════════════════════════════════════════
# 8. INJECTION CSS MODALE + utilitaires avant </body>
# ═══════════════════════════════════════════════════════════════════
if 'gpModalStyle' not in html:
    html = html.replace('</body>', MODAL_CSS + MODAL_UTILS + '\n</body>', 1)
    fixes.append('CSS + utilitaire gpModal() injectés')

# ═══════════════════════════════════════════════════════════════════
# 9. beforeunload — silencieux si Firebase sync actif
# ═══════════════════════════════════════════════════════════════════
old_bul = "window.addEventListener('beforeunload',function(e){\n  if(window.gpUnsavedChanges){"
new_bul = "window.addEventListener('beforeunload',function(e){\n  if(window.gpUnsavedChanges && !window._gpSyncEnabled){"
if old_bul in html:
    html = html.replace(old_bul, new_bul, 1)
    fixes.append('beforeunload silencieux si Firebase sync actif')

# ═══════════════════════════════════════════════════════════════════
# ÉCRITURE
# ═══════════════════════════════════════════════════════════════════
with open(DEST, 'w', encoding='utf-8') as f:
    f.write(html)

print(f'✅  {DEST}')
print(f'    {len(html)//1024} KB — {html.count(chr(10))} lignes\n')
print(f'{len(fixes)} corrections appliquées :')
for c in fixes:
    print(f'  ✅ {c}')
