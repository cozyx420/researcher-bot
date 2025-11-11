(function () {
  const $ = (s) => document.querySelector(s);
  const apiKeyInput = $('#apiKey');
  const intentInput = $('#intent');
  const taskInput = $('#task');
  const focusInput = $('#focus');
  const maxSourcesInput = $('#maxSources');
  const allowDomainsInput = $('#allowDomains');
  const runBtn = $('#runBtn');
  const statusEl = $('#status');
  const resultEl = $('#result');
  const jsonOut = $('#jsonOut');

  // API-Key in localStorage merken (optional)
  apiKeyInput.value = localStorage.getItem('manager_api_key') || '';
  apiKeyInput.addEventListener('change', () => {
    localStorage.setItem('manager_api_key', apiKeyInput.value);
  });

  runBtn.addEventListener('click', async () => {
    const task = taskInput.value.trim();
    if (!task) {
      statusEl.textContent = 'Bitte eine Aufgabe/Frage eingeben.';
      return;
    }
    runBtn.disabled = true;
    statusEl.textContent = 'Wird ausgeführt…';

    const allowDomains = (allowDomainsInput.value || '')
      .split(',')
      .map(s => s.trim())
      .filter(Boolean);

    const body = {
      task,
      intent: intentInput.value,
      params: {
        focus: focusInput.value || undefined,
        max_sources: Number(maxSourcesInput.value || 5),
        allow_domains: allowDomains.length ? allowDomains : undefined
      }
    };

    const headers = { 'Content-Type': 'application/json' };
    if (apiKeyInput.value) headers['X-API-Key'] = apiKeyInput.value;

    try {
      const res = await fetch('/task', {
        method: 'POST',
        headers,
        body: JSON.stringify(body)
      });
      const data = await res.json();
      jsonOut.textContent = JSON.stringify(data, null, 2);

      // Preferiere result_markdown, fallback: einfache Darstellung
      if (data.result_markdown) {
        // Minimal: Markdown nicht parsen, sondern anzeigen
        resultEl.textContent = data.result_markdown;
      } else if (Array.isArray(data.steps) && data.steps.length) {
        const s0 = data.steps[0];
        if (s0.ok && s0.data) {
          const parts = [];
          if (s0.data.summary) parts.push('Zusammenfassung:\n' + s0.data.summary);
          if (Array.isArray(s0.data.bullets) && s0.data.bullets.length) {
            parts.push('\nPunkte:\n- ' + s0.data.bullets.join('\n- '));
          }
          if (Array.isArray(s0.data.sources) && s0.data.sources.length) {
            const srcs = s0.data.sources.map(src => `- ${src.title} (${src.url}) · ${src.verdict}`).join('\n');
            parts.push('\nQuellen:\n' + srcs);
          }
          resultEl.textContent = parts.join('\n');
        } else {
          resultEl.textContent = s0.error ? ('Fehler: ' + s0.error) : 'Kein Ergebnis.';
        }
      } else {
        resultEl.textContent = 'Kein Ergebnis.';
      }

      statusEl.textContent = 'Fertig.';
    } catch (e) {
      statusEl.textContent = 'Fehler bei der Anfrage.';
      resultEl.textContent = String(e);
    } finally {
      runBtn.disabled = false;
    }
  });
})();
