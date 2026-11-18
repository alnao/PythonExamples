/* Manager: tendina Project nella seconda barra.
 *
 * Le opzioni sono quelle del Panoramic e del Tag Manager (tag_match.js): valori suggeriti,
 * sottovoci trovate nelle risorse, "Altri valori"; il confronto e' di uguaglianza stretta.
 * I valori presenti in ogni servizio arrivano da /api/manager/projects (cache della Tagging
 * API, region scelta): scegliendo un Project i servizi senza risorse con quel valore
 * diventano grigi nella barra e nelle schede della pagina iniziale, ma restano cliccabili;
 * nell'elenco di un servizio diventano grigie le risorse con un altro Project (projectOut).
 * La scelta resta valida passando da un servizio all'altro (localStorage del browser).
 * Nella pagina di un servizio la tendina si ricarica dopo ogni lettura dell'elenco (manager.js).
 */

const PROJECT_KEY = 'manager.project';
const projectState = { services: null };

function savedProject() {
    try { return localStorage.getItem(PROJECT_KEY) || ''; } catch (e) { return ''; }
}

function saveProject(value) {
    try {
        if (value) localStorage.setItem(PROJECT_KEY, value); else localStorage.removeItem(PROJECT_KEY);
    } catch (e) { /* storage non disponibile: la scelta vale solo per questa pagina */ }
}

/* Legge i Project per servizio e rigenera le opzioni, tenendo la voce scelta se c'e' ancora. */
async function loadProjects() {
    const select = $('projectFilter');
    if (!select) return;
    try {
        const d = await apiGet(`/api/manager/projects?${query({ region: APP.region })}`);
        projectState.services = d.services;
        select.title = 'Project: in grigio i servizi senza risorse con quel valore nella region scelta'
            + ((d.warnings || []).length ? `\nRegion non lette: ${d.warnings.join('; ')}` : '');
    } catch (e) {
        projectState.services = null;
        select.title = 'Project non leggibili: ' + e.message;
    }
    const values = [...new Set(Object.values(projectState.services || {}).flat())];
    const current = select.value || savedProject();
    select.innerHTML = suggestedFilterOptions('Project', values.map(v => ({ tags: { Project: v } })), 'Tutti i Project');
    select.value = current;
    if (select.value !== current) select.value = '';
    markServices();
    if (typeof renderList === 'function') renderList();  // pagina di un servizio: grigio sulle risorse
}

function projectMatches(value, project) {
    if (value === undefined || value === null) return false;
    if (project === '__other__') return !isSuggestedValue('Project', value);
    return value === project;
}

/* Vero se la risorsa va in grigio: c'e' un Project scelto, i tag sono noti e il suo Project
 * e' diverso (o manca). Con i tag sconosciuti (null) la risorsa resta normale. */
function projectOut(tags) {
    const select = $('projectFilter');
    const project = select ? select.value : '';
    return Boolean(project && tags && !projectMatches(tags.Project, project));
}

/* Grigio sui servizi senza risorse del Project scelto (nessun grigio se i valori non si conoscono). */
function markServices() {
    const project = $('projectFilter').value;
    document.querySelectorAll('[data-service]').forEach(el => {
        const values = projectState.services && projectState.services[el.dataset.service];
        const empty = Boolean(project && values && !values.some(v => projectMatches(v, project)));
        el.classList.toggle('svc-empty', empty);
        const label = project === '__other__' ? 'Altri valori' : project;
        const note = empty ? `Nessuna risorsa con Project = ${label}` : '';
        el.title = [el.dataset.desc, note].filter(Boolean).join('\n');
    });
}

document.addEventListener('DOMContentLoaded', () => {
    const select = $('projectFilter');
    if (!select) return;
    select.addEventListener('change', () => {
        saveProject(select.value);
        markServices();
        if (typeof renderList === 'function') renderList();
    });
    // nella pagina di un servizio la lettura parte da manager.js, dopo l'elenco
    if (!APP.service) loadProjects();
});
