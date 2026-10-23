/* Pedago-AI frontend: vanilla JS, no frameworks. */
(() => {
  'use strict';

  const TEACHER_KEY = 'pedago.teacher.v1';
  const PARAMS_KEY = 'pedago.params.v1';
  const LAST_FICHE_KEY = 'pedago.lastFiche.v1';
  const API_BASE = '/api/v1';
  const REQUEST_TIMEOUT_MS = 60000;
  const DRES = ['Maritime', 'Golfe-Lomé', 'Plateaux-Est', 'Plateaux-Ouest', 'Centrale', 'Kara', 'Savanes'];
  const PERIOD_MINUTES = 55;
  const VALID_DUREES = [1, 2, 3, 4, 5, 6].map((n) => n * PERIOD_MINUTES);
  const PIPELINE = [
    { key: 'planning', label: 'Planning' },
    { key: 'ingestion', label: 'Ingestion Search' },
    { key: 'gold', label: 'Gold-standard Match' },
    { key: 'drafting', label: 'Drafting' },
    { key: 'iesg', label: 'IESG Validation' },
  ];
  const PARAM_FIELDS = ['discipline', 'classe', 'serie', 'duree', 'theme', 'competence'];
  const TEACHER_FIELDS = ['nom', 'prenom', 'dre', 'iesg', 'etablissement', 'telephone'];

  const state = { step: 1, teacher: null, params: null, fiche: null, source: null };

  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => Array.from(document.querySelectorAll(sel));

  function escapeHtml(value) {
    return String(value == null ? '' : value)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  function toast(message, isError) {
    const el = $('#toast');
    el.textContent = message;
    el.classList.toggle('error-toast', Boolean(isError));
    el.hidden = false;
    clearTimeout(toast.timer);
    toast.timer = setTimeout(() => { el.hidden = true; }, 3500);
  }

  function readJson(key) {
    try {
      const raw = localStorage.getItem(key);
      return raw ? JSON.parse(raw) : null;
    } catch (err) {
      return null;
    }
  }

  function writeJson(key, value) {
    try {
      localStorage.setItem(key, JSON.stringify(value));
      return true;
    } catch (err) {
      return false;
    }
  }

  function fetchWithTimeout(url, options) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
    return fetch(url, Object.assign({}, options, { signal: controller.signal }))
      .finally(() => clearTimeout(timer));
  }

  /* ---------- Step 1: Teacher profile ---------- */

  function populateDres() {
    $('#dre').innerHTML = '<option value="">Choisir une DRE</option>' +
      DRES.map((d) => `<option value="${escapeHtml(d)}">${escapeHtml(d)}</option>`).join('');
  }

  function restoreFields(fields, saved, prefix) {
    if (!saved) return;
    fields.forEach((id) => {
      const field = $('#' + id);
      if (field && saved[id] != null) field.value = saved[id];
    });
  }

  function readTeacherForm() {
    return {
      nom: $('#nom').value.trim(),
      prenom: $('#prenom').value.trim(),
      dre: $('#dre').value,
      iesg: $('#iesg').value.trim(),
      etablissement: $('#etablissement').value.trim(),
      telephone: $('#telephone').value.trim(),
    };
  }

  function handleTeacherSubmit(event) {
    event.preventDefault();
    const data = readTeacherForm();
    const errorEl = $('#teacher-error');
    const missing = ['nom', 'prenom', 'dre', 'iesg', 'etablissement'].filter((k) => !data[k]);
    if (missing.length) {
      errorEl.textContent = 'Veuillez renseigner tous les champs obligatoires.';
      return;
    }
    if (data.telephone && !/^\+?[0-9 ()-]{6,20}$/.test(data.telephone)) {
      errorEl.textContent = 'Le numéro de téléphone semble invalide.';
      return;
    }
    errorEl.textContent = '';
    state.teacher = data;
    if (writeJson(TEACHER_KEY, data)) {
      toast('Profil enregistré sur cet appareil.');
    } else {
      toast('Impossible d’enregistrer le profil sur cet appareil.', true);
    }
    goToStep(2);
  }

  /* ---------- Step 2: Parameters ---------- */

  function readParamsForm() {
    return {
      discipline: $('#discipline').value,
      classe: $('#classe').value,
      serie: $('#serie').value,
      duree: Number($('#duree').value),
      theme: $('#theme').value.trim(),
      competence: $('#competence').value.trim(),
    };
  }

  function handleParamsSubmit(event) {
    event.preventDefault();
    const data = readParamsForm();
    const errorEl = $('#params-error');
    if (!data.theme || !data.competence) {
      errorEl.textContent = 'Le thème et la compétence sont obligatoires.';
      return;
    }
    if (!VALID_DUREES.includes(data.duree)) {
      errorEl.textContent = 'La durée doit être de 1 à 6 périodes de 55 minutes.';
      return;
    }
    errorEl.textContent = '';
    state.params = data;
    writeJson(PARAMS_KEY, data);
    renderGenerationSummary();
    goToStep(3);
  }

  /* ---------- Step 3: Generation ---------- */

  function renderGenerationSummary() {
    const p = state.params || {};
    $('#gen-summary').textContent = `${p.discipline} · ${p.classe} ${p.serie} · ${p.theme} · ${p.duree} min`;
  }

  function renderPipeline(statusMap) {
    const labels = { pending: 'En attente', running: 'En cours', done: 'Terminé', failed: 'Échec' };
    $('#pipeline').innerHTML = PIPELINE.map((step) => {
      const status = statusMap[step.key] || 'pending';
      return `<li class="${status}"><span class="dot" aria-hidden="true"></span>` +
        `<span>${escapeHtml(step.label)}</span><span class="badge">${labels[status]}</span></li>`;
    }).join('');
  }

  function setNotice(id, message) {
    const el = $('#' + id);
    el.textContent = message || '';
    el.hidden = !message;
  }

  async function runPipelineStatus(run) {
    const statusMap = {};
    for (const step of PIPELINE) {
      statusMap[step.key] = 'running';
      renderPipeline(statusMap);
      await new Promise((r) => setTimeout(r, 650));
      statusMap[step.key] = 'done';
      renderPipeline(statusMap);
    }
    return run;
  }

  async function requestFiche(payload) {
    const response = await fetchWithTimeout(`${API_BASE}/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    if (!data || !Array.isArray(data.phases)) throw new Error('Réponse invalide');
    return data;
  }

  function buildDemoFiche(teacher, params) {
    const d = params.duree;
    const part = (n) => Math.max(5, Math.round((d * n) / 100));
    return {
      titre: `Fiche APC – ${params.theme}`,
      enseignant: teacher ? `${teacher.prenom} ${teacher.nom}` : '',
      etablissement: teacher ? teacher.etablissement : '',
      discipline: params.discipline,
      classe: params.classe,
      serie: params.serie,
      theme: params.theme,
      competence: params.competence,
      duree: d,
      phases: [
        { nom: 'Situation de départ', duree: part(10), enseignant: 'Poser une question problème en lien avec le thème.', eleves: 'Formuler des hypothèses individuellement.', supports: 'Tableau, image contextuelle' },
        { nom: 'Présentation de la situation', duree: part(15), enseignant: 'Présenter la situation d’apprentissage.', eleves: 'Lire et reformuler la consigne.', supports: 'Fiche élève' },
        { nom: 'Activité 1 – Investigation', duree: part(30), enseignant: 'Guider les groupes et distribuer le matériel.', eleves: 'Réaliser l’expérience et noter les observations.', supports: 'Matériel de laboratoire, fiche d’activité' },
        { nom: 'Activité 2 – Exploitation', duree: part(25), enseignant: 'Animer la mise en commun des résultats.', eleves: 'Interpréter les résultats et argumenter.', supports: 'Tableau, schémas' },
        { nom: 'Synthèse', duree: part(10), enseignant: 'Institutionnaliser le savoir visé.', eleves: 'Recopier la synthèse dans le cahier.', supports: 'Trace écrite' },
        { nom: 'Évaluation', duree: part(10), enseignant: 'Proposer un exercice d’application.', eleves: 'Résoudre l’exercice individuellement.', supports: 'Exercice d’évaluation' },
      ],
    };
  }

  async function handleGenerate() {
    const btn = $('#generate-btn');
    btn.disabled = true;
    setNotice('gen-notice', '');
    const payload = { teacher: state.teacher, params: state.params };
    const animation = runPipelineStatus();
    let fiche;
    let source = 'api';
    try {
      fiche = await requestFiche(payload);
    } catch (err) {
      source = 'demo';
      fiche = buildDemoFiche(state.teacher, state.params);
      setNotice('gen-notice', 'Le service de génération n’est pas disponible pour le moment. Une fiche de démonstration a été créée localement ; elle ne remplace pas une fiche générée par Pedago-AI.');
    }
    await animation;
    btn.disabled = false;
    state.fiche = fiche;
    state.source = source;
    writeJson(LAST_FICHE_KEY, { fiche: fiche, source: source, savedAt: new Date().toISOString() });
    renderFiche();
    goToStep(4);
  }

  /* ---------- Step 4: Live view & export ---------- */

  function renderFiche() {
    const f = state.fiche;
    if (!f) return;
    const meta = [
      f.discipline && `<span class="badge-pill yellow">${escapeHtml(f.discipline)}</span>`,
      f.classe && `<span class="badge-pill">${escapeHtml(f.classe)} ${escapeHtml(f.serie || '')}</span>`,
      f.duree && `<span class="badge-pill">${escapeHtml(f.duree)} min</span>`,
      f.enseignant && `<span class="badge-pill">${escapeHtml(f.enseignant)}</span>`,
      state.source === 'demo'
        ? '<span class="badge-pill red">Démonstration</span>'
        : '<span class="badge-pill green">Généré</span>',
    ].filter(Boolean).join('');
    $('#fiche-meta').innerHTML = meta;
    $('#h-fiche').textContent = f.titre || 'Fiche APC';
    $('#fiche-body').innerHTML = (f.phases || []).map((ph) =>
      `<tr><td>${escapeHtml(ph.nom)}</td><td>${escapeHtml(ph.duree)} min</td>` +
      `<td>${escapeHtml(ph.enseignant)}</td><td>${escapeHtml(ph.eleves)}</td>` +
      `<td>${escapeHtml(ph.supports)}</td></tr>`
    ).join('');
    setNotice('fiche-notice', state.source === 'demo'
      ? 'Fiche de démonstration : la génération IA n’est pas disponible.' : '');
  }

  async function handleExport() {
    if (!state.fiche) return;
    const btn = $('#export-btn');
    btn.disabled = true;
    try {
      const response = await fetchWithTimeout(`${API_BASE}/export/docx`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ fiche: state.fiche, teacher: state.teacher }),
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const slug = ((state.params && state.params.theme) || 'fiche').toLowerCase().replace(/[^a-z0-9]+/g, '-');
      const a = document.createElement('a');
      a.href = url;
      a.download = `fiche-apc-${slug}.docx`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
      toast('Fiche téléchargée.');
    } catch (err) {
      toast('L’export DOCX n’est pas disponible. Vérifiez votre connexion.', true);
    } finally {
      btn.disabled = false;
    }
  }

  /* ---------- Navigation ---------- */

  function goToStep(step) {
    state.step = step;
    $$('.panel').forEach((p) => { p.hidden = Number(p.dataset.panel) !== step; });
    $$('.step-tab').forEach((t) => {
      const n = Number(t.dataset.step);
      t.setAttribute('aria-selected', String(n === step));
      t.disabled = (n === 2 && !state.teacher) || (n === 3 && !state.params) || (n === 4 && !state.fiche);
    });
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  /* ---------- Offline / PWA ---------- */

  function updateOnlineStatus() {
    $('#offline-banner').hidden = navigator.onLine;
  }

  function registerServiceWorker() {
    if (!('serviceWorker' in navigator)) return;
    window.addEventListener('load', () => {
      navigator.serviceWorker.register('sw.js').catch(() => {
        toast('Le mode hors ligne n’a pas pu être activé.', true);
      });
    });
  }

  /* ---------- Init ---------- */

  function init() {
    populateDres();
    state.teacher = readJson(TEACHER_KEY);
    restoreFields(TEACHER_FIELDS, state.teacher);
    state.params = readJson(PARAMS_KEY);
    restoreFields(PARAM_FIELDS, state.params);
    const lastFiche = readJson(LAST_FICHE_KEY);
    if (lastFiche && lastFiche.fiche) {
      state.fiche = lastFiche.fiche;
      state.source = lastFiche.source || 'api';
    }

    $('#teacher-form').addEventListener('submit', handleTeacherSubmit);
    $('#params-form').addEventListener('submit', handleParamsSubmit);
    $('#generate-btn').addEventListener('click', handleGenerate);
    $('#export-btn').addEventListener('click', handleExport);
    document.body.addEventListener('click', (event) => {
      const tab = event.target.closest('.step-tab');
      if (tab && !tab.disabled) { goToStep(Number(tab.dataset.step)); return; }
      const go = event.target.closest('[data-go]');
      if (go) goToStep(Number(go.dataset.go));
    });

    window.addEventListener('online', updateOnlineStatus);
    window.addEventListener('offline', updateOnlineStatus);
    updateOnlineStatus();

    if (state.fiche) renderFiche();
    if (state.params) renderGenerationSummary();
    goToStep(state.teacher ? 2 : 1);
    registerServiceWorker();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
