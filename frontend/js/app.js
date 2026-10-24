/* PrepaCours frontend: vanilla JS, no frameworks. */
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
  const PARAM_FIELDS = ['discipline', 'classe', 'serie', 'duree', 'theme', 'competence', 'fiche_numero', 'semaine', 'annee_scolaire'];
  const TEACHER_FIELDS = ['nom', 'prenom', 'dre', 'iesg', 'etablissement', 'telephone'];

  /* The 6 canonical APC Togo didactic moments, in order (must match the backend enum). */
  const MOMENTS = [
    { key: 'prerequis', label: '1. Mobilisation des prérequis' },
    { key: 'situation_probleme', label: '2. Situation-problème' },
    { key: 'recherche_resolution', label: '3. Recherche / Résolution' },
    { key: 'mise_en_commun', label: '4. Mise en commun' },
    { key: 'institutionnalisation', label: '5. Institutionnalisation / Trace écrite' },
    { key: 'reinvestissement', label: '6. Réinvestissement / Évaluation' },
  ];
  const MOMENT_LABELS = Object.fromEntries(MOMENTS.map((m) => [m.key, m.label]));

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

  function restoreFields(fields, saved) {
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
    const ficheRaw = $('#fiche_numero').value.trim();
    return {
      discipline: $('#discipline').value,
      classe: $('#classe').value,
      serie: $('#serie').value,
      duree: Number($('#duree').value),
      theme: $('#theme').value.trim(),
      competence: $('#competence').value.trim(),
      fiche_numero: ficheRaw ? Number(ficheRaw) : null,
      semaine: $('#semaine').value.trim(),
      annee_scolaire: $('#annee_scolaire').value.trim(),
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

  /* The API returns a LessonPlan (title, timing, activities, capacites_contenus, consolidation). */
  async function requestFiche(payload) {
    const response = await fetchWithTimeout(`${API_BASE}/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!response.ok) {
      let detail = '';
      try {
        const body = await response.json();
        detail = (body && body.error && body.error.message) || '';
      } catch (err) {
        detail = '';
      }
      throw new Error(`HTTP ${response.status}${detail ? ' : ' + detail : ''}`);
    }
    const data = await response.json();
    if (!data || !Array.isArray(data.activities) || !Array.isArray(data.timing)) {
      throw new Error('Réponse invalide : plan de cours absent');
    }
    return data;
  }

  /* The fiche view model is the LessonPlan itself. Only the display-only fields are added here. */
  function planToFiche(plan, teacher, params) {
    return Object.assign({}, plan, {
      teacher: teacher || plan.teacher || null,
      dre: plan.dre || (teacher ? teacher.dre : ''),
      etablissement: plan.etablissement || (teacher ? teacher.etablissement : ''),
      classe: params ? params.classe : plan.level,
      serie: params ? params.serie : '',
      fiche_numero: params && params.fiche_numero != null ? params.fiche_numero : (plan.fiche_numero || null),
      semaine: params && params.semaine ? params.semaine : (plan.semaine || ''),
      annee_scolaire: params && params.annee_scolaire ? params.annee_scolaire : (plan.annee_scolaire || ''),
    });
  }

  /* Fallback fiche in the same 6-moment shape as the backend LessonPlan. */
  function buildDemoFiche(teacher, params) {
    const d = params.duree;
    const share = { prerequis: 10, situation_probleme: 15, recherche_resolution: 30, mise_en_commun: 20, institutionnalisation: 10, reinvestissement: 15 };
    const part = (key) => Math.max(5, Math.round((d * share[key]) / 100));
    const text = {
      prerequis: ['Poser des questions de rappel sur les notions utiles au thème.', 'Répondre aux questions et rappeler ses acquis.', 'Rappel des prérequis'],
      situation_probleme: ['Présenter une situation contextualisée et poser la question-problème.', 'Observer la situation, reformuler la consigne et formuler des hypothèses.', 'Situation d’apprentissage'],
      recherche_resolution: ['Organiser les groupes, distribuer le matériel et guider sans donner la réponse.', 'Expérimenter ou calculer en groupe, échanger avec ses pairs et prendre note.', 'Matériel de laboratoire, fiche d’activité'],
      mise_en_commun: ['Animer la mise en commun, faire comparer les résultats et valider ou corriger.', 'Présenter ses résultats et argumenter.', 'Tableau, schémas'],
      institutionnalisation: ['Institutionnaliser les notions clés et dicter la trace écrite.', 'Prendre note de la synthèse dans le cahier.', 'Trace écrite'],
      reinvestissement: ['Proposer des exercices d’application et l’évaluation formative.', 'Résoudre les exercices individuellement.', 'Exercices d’évaluation'],
    };
    return {
      title: `Fiche APC – ${params.theme}`,
      teacher: teacher,
      dre: teacher ? teacher.dre : '',
      etablissement: teacher ? teacher.etablissement : '',
      fiche_numero: params.fiche_numero != null ? params.fiche_numero : 1,
      semaine: params.semaine || '',
      annee_scolaire: params.annee_scolaire || '',
      subject: params.discipline,
      level: params.classe,
      classe: params.classe,
      serie: params.serie,
      theme: params.theme,
      competence: params.competence,
      duration_minutes: d,
      objectives: [{ description: params.competence, domain: 'cognitif', bloom_level: null }],
      prerequisites: [],
      materials: [],
      capacites_contenus: [{ capacite: params.competence, contenus: [] }],
      timing: MOMENTS.map((m) => ({ phase: m.key, duration_minutes: part(m.key), description: m.label })),
      activities: MOMENTS.map((m) => ({
        phase: m.key,
        professor_activity: text[m.key][0],
        student_activity: text[m.key][1],
        duration_minutes: part(m.key),
        materials: [text[m.key][2]],
      })),
      evaluation: [],
      essentiel_a_retenir: '',
      exercices_application: [],
      devoir_maison: '',
      notes: null,
      demo: true,
    };
  }

  async function handleGenerate() {
    const btn = $('#generate-btn');
    btn.disabled = true;
    setNotice('gen-notice', '');
    const teacher = {
      ...state.teacher,
      classe: (state.params && state.params.classe) ? state.params.classe : "",
      serie: (state.params && state.params.serie) ? state.params.serie : null,
    };
    const payload = {
      teacher: teacher,
      subject: state.params.discipline,
      level: state.params.classe,
      theme: state.params.theme,
      duration_minutes: Number(state.params ? state.params.duree : 55),
      competence: state.params.competence,
    };
    const animation = runPipelineStatus();
    let fiche;
    let source = 'api';
    try {
      const plan = await requestFiche(payload);
      fiche = planToFiche(plan, state.teacher, state.params);
    } catch (err) {
      source = 'demo';
      fiche = buildDemoFiche(state.teacher, state.params);
      const reason = err && err.message ? err.message : 'erreur inconnue';
      setNotice('gen-notice', `Le service de génération n’est pas disponible (${reason}). Une fiche de démonstration a été créée localement ; elle ne remplace pas une fiche générée par PrepaCours.`);
      toast('Génération IA en échec : ' + reason, true);
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

  function ensureExtraContainer() {
    let el = $('#fiche-extra');
    if (!el) {
      el = document.createElement('div');
      el.id = 'fiche-extra';
      const table = $('#fiche-table');
      table.parentNode.parentNode.insertBefore(el, table.parentNode.nextSibling);
    }
    return el;
  }

  function renderHeaderBlock(f) {
    const t = f.teacher || {};
    const rows = [
      ['DRE', f.dre || t.dre],
      ['IESG', t.iesg],
      ['Établissement', f.etablissement || t.etablissement],
      ['Professeur', [t.prenom, t.nom].filter(Boolean).join(' ')],
      ['Année scolaire', f.annee_scolaire],
      ['Classe', [f.classe || t.classe, f.serie].filter(Boolean).join(' ')],
      ['Discipline', f.subject],
      ['Fiche N°', f.fiche_numero],
      ['Semaine', f.semaine],
      ['Durée', f.duration_minutes ? `${f.duration_minutes} min` : ''],
      ['Thème', f.theme],
      ['Leçon', f.sub_theme],
      ['Compétence terminale', f.competence],
      ['Supports / matériels', (f.materials || []).join(', ')],
      ['Prérequis', (f.prerequisites || []).join(', ')],
    ];
    return '<h3>En-tête</h3><table class="apc-table"><tbody>' +
      rows.filter((r) => r[1]).map((r) => `<tr><th>${escapeHtml(r[0])}</th><td>${escapeHtml(r[1])}</td></tr>`).join('') +
      '</tbody></table>';
  }

  function renderMatrix(f) {
    const rows = (f.capacites_contenus || []).map((row) =>
      `<tr><td>${escapeHtml(row.capacite)}</td><td>${escapeHtml((row.contenus || []).join(' ; '))}</td></tr>`
    ).join('');
    return '<h3>Matrice Capacités / Contenus</h3><table class="apc-table"><thead><tr><th>Capacité opérationnelle</th><th>Contenus notionnels</th></tr></thead><tbody>' +
      (rows || '<tr><td colspan="2">Non renseignée</td></tr>') + '</tbody></table>';
  }

  function renderConsolidation(f) {
    const exos = (f.exercices_application || []).map((ex, i) => {
      const enonce = ex.enonce || ex.énoncé || ex.question || '';
      const correction = ex.correction || '';
      return `<li><p><strong>Exercice ${i + 1}.</strong> ${escapeHtml(enonce)}</p>` +
        (correction ? `<p><em>Correction :</em> ${escapeHtml(correction)}</p>` : '') + '</li>';
    }).join('');
    return '<h3>Consolidation</h3>' +
      `<p><strong>Essentiel à retenir :</strong></p><p>${escapeHtml(f.essentiel_a_retenir || 'Non renseigné')}</p>` +
      `<p><strong>Exercices d’application corrigés :</strong></p><ol>${exos || '<li>Non renseignés</li>'}</ol>` +
      `<p><strong>Devoir de maison :</strong></p><p>${escapeHtml(f.devoir_maison || 'Non renseigné')}</p>`;
  }

  function renderFiche() {
    const f = state.fiche;
    if (!f) return;
    const meta = [
      f.subject && `<span class="badge-pill yellow">${escapeHtml(f.subject)}</span>`,
      f.classe && `<span class="badge-pill">${escapeHtml(f.classe)} ${escapeHtml(f.serie || '')}</span>`,
      f.duration_minutes && `<span class="badge-pill">${escapeHtml(f.duration_minutes)} min</span>`,
      f.teacher && `<span class="badge-pill">${escapeHtml(f.teacher.prenom)} ${escapeHtml(f.teacher.nom)}</span>`,
      state.source === 'demo'
        ? '<span class="badge-pill red">Démonstration</span>'
        : '<span class="badge-pill green">Généré</span>',
    ].filter(Boolean).join('');
    $('#fiche-meta').innerHTML = meta;
    $('#h-fiche').textContent = f.title || 'Fiche APC';

    /* Grille didactique: the 6 moments, labelled in French, in canonical order. */
    const timingByMoment = Object.fromEntries((f.timing || []).map((t) => [t.phase, t]));
    const activityByMoment = Object.fromEntries((f.activities || []).map((a) => [a.phase, a]));
    $('#fiche-body').innerHTML = MOMENTS.map((m) => {
      const a = activityByMoment[m.key] || {};
      const t = timingByMoment[m.key] || {};
      const duree = a.duration_minutes || t.duration_minutes || '';
      return `<tr><td>${escapeHtml(m.label)}</td><td>${escapeHtml(duree)} min</td>` +
        `<td>${escapeHtml(a.professor_activity)}</td><td>${escapeHtml(a.student_activity)}</td>` +
        `<td>${escapeHtml((a.materials || []).join(', '))}</td></tr>`;
    }).join('');

    ensureExtraContainer().innerHTML = renderHeaderBlock(f) + renderMatrix(f) + renderConsolidation(f);
    setNotice('fiche-notice', state.source === 'demo'
      ? 'Fiche de démonstration : la génération IA n’est pas disponible.' : '');
  }

  /* Convert the fiche into the backend LessonPlan shape for POST /api/v1/export/docx.
     The fiche is already a LessonPlan, so only the teacher block is refreshed. */
  function toLessonPlan(fiche, teacher) {
    const { demo, classe, ...plan } = fiche;
    return { ...plan, teacher: teacher };
  }

  async function handleExport() {
    if (!state.fiche) return;
    const btn = $('#export-btn');
    btn.disabled = true;
    try {
      const teacher = {
        ...state.teacher,
        classe: (state.params && state.params.classe) ? state.params.classe : "",
        serie: (state.params && state.params.serie) ? state.params.serie : null,
      };
      const body = toLessonPlan(state.fiche, teacher);
      const response = await fetchWithTimeout(`${API_BASE}/export/docx`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
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
