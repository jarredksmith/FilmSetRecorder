(() => {
  const $ = (id) => document.getElementById(id);
  const overlay = $('pairOverlay');
  const toast = $('toast');
  let paired = false;
  let busy = false;
  let lastState = null;
  let toastTimer = null;

  function showToast(message) {
    toast.textContent = message;
    toast.classList.add('show');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toast.classList.remove('show'), 1700);
  }

  function formatClock(seconds) {
    const ms = Math.max(0, Math.floor((Number(seconds) || 0) * 1000));
    const h = Math.floor(ms / 3600000);
    const m = Math.floor((ms % 3600000) / 60000);
    const s = Math.floor((ms % 60000) / 1000);
    const rem = ms % 1000;
    return `${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}.${String(rem).padStart(3,'0')}`;
  }

  function dbPercent(db) {
    const value = Math.max(-60, Math.min(0, Number(db) || -80));
    return ((value + 60) / 60) * 100;
  }

  function setConnection(mode, text) {
    const pill = $('connectionPill');
    pill.classList.remove('ready', 'offline');
    if (mode) pill.classList.add(mode);
    $('connectionText').textContent = text;
  }

  function buildMeters(state) {
    const wrap = $('meters');
    const names = state.tracks || [];
    const meters = state.meters || [];
    const armed = state.armed || [];
    const count = Math.max(names.length, meters.length, 4);
    if (wrap.children.length !== count) {
      wrap.innerHTML = '';
      for (let i = 0; i < count; i++) {
        const row = document.createElement('div');
        row.className = 'meter-row';
        row.innerHTML = `
          <div class="meter-name"><small>CH ${String(i+1).padStart(2,'0')}</small><b data-name></b></div>
          <div class="meter-track"><div class="meter-fill" data-fill></div></div>
          <div class="meter-db" data-db>−∞</div>`;
        wrap.appendChild(row);
      }
    }
    [...wrap.children].forEach((row, i) => {
      const db = Number(meters[i] ?? -80);
      row.querySelector('[data-name]').textContent = names[i] || `Track ${i+1}`;
      row.querySelector('[data-fill]').style.width = `${dbPercent(db)}%`;
      row.querySelector('[data-fill]').style.opacity = armed[i] === false ? '.25' : '1';
      row.querySelector('[data-db]').textContent = db <= -79 ? '−∞' : `${db.toFixed(1)}`;
    });
  }

  function render(state) {
    lastState = state;
    $('projectName').textContent = state.project || 'FilmSet Recorder';
    $('roll').textContent = state.roll || '—';
    $('scene').textContent = state.scene || '—';
    $('take').textContent = String(state.take ?? '—').padStart(3, '0');
    $('clock').textContent = formatClock(state.elapsed);
    $('xruns').textContent = state.xruns ?? 0;
    $('drops').textContent = state.dropped_blocks ?? 0;
    $('audioState').textContent = state.audio_ready ? 'READY' : 'OFFLINE';
    $('diskState').textContent = state.disk_display || '—';

    const circle = !!state.circle;
    $('circleButton').classList.toggle('active', circle);
    $('circleTop').classList.toggle('active', circle);

    const label = $('stateLabel');
    label.classList.remove('recording', 'playing');
    $('recordButton').classList.toggle('recording', !!state.recording);
    if (state.recording) {
      label.textContent = '● RECORDING';
      label.classList.add('recording');
    } else if (state.playing) {
      label.textContent = '▶ PLAYING';
      label.classList.add('playing');
    } else {
      label.textContent = state.audio_ready ? 'READY' : 'AUDIO OFFLINE';
    }
    buildMeters(state);
  }

  async function jsonFetch(url, options = {}) {
    const response = await fetch(url, {
      ...options,
      cache: 'no-store',
      credentials: 'same-origin',
      headers: {'Content-Type':'application/json', ...(options.headers || {})}
    });
    let body = {};
    try { body = await response.json(); } catch (_) {}
    if (!response.ok) {
      const error = new Error(body.error || `HTTP ${response.status}`);
      error.status = response.status;
      throw error;
    }
    return body;
  }

  async function pair() {
    const pin = $('pinInput').value.replace(/\D/g, '').slice(0, 6);
    $('pinInput').value = pin;
    if (pin.length !== 6) {
      $('pairError').textContent = 'Enter all six digits.';
      return;
    }
    $('pairError').textContent = '';
    try {
      await jsonFetch('/api/pair', {method:'POST', body:JSON.stringify({pin})});
      paired = true;
      overlay.classList.add('hidden');
      showToast('Remote paired');
      await poll();
    } catch (err) {
      $('pairError').textContent = err.message || 'Pairing failed.';
    }
  }

  async function command(command, extra = {}) {
    if (!paired) return;
    try {
      await jsonFetch('/api/command', {
        method:'POST',
        body:JSON.stringify({command, request_id: `${Date.now()}-${Math.random()}`, ...extra})
      });
    } catch (err) {
      if (err.status === 401) requirePairing();
      else showToast(err.message || 'Command failed');
    }
  }

  function requirePairing() {
    paired = false;
    overlay.classList.remove('hidden');
    setConnection('offline', 'PAIRING');
  }

  async function poll() {
    if (busy) return;
    busy = true;
    try {
      const state = await jsonFetch('/api/status');
      paired = true;
      overlay.classList.add('hidden');
      setConnection('ready', 'CONNECTED');
      render(state);
    } catch (err) {
      if (err.status === 401) requirePairing();
      else setConnection('offline', 'OFFLINE');
    } finally {
      busy = false;
    }
  }

  $('pairButton').addEventListener('click', pair);
  $('pinInput').addEventListener('keydown', e => { if (e.key === 'Enter') pair(); });
  $('pinInput').addEventListener('input', e => { e.target.value = e.target.value.replace(/\D/g,'').slice(0,6); });
  $('recordButton').addEventListener('click', () => command('record'));
  $('stopButton').addEventListener('click', () => command('stop'));
  $('playButton').addEventListener('click', () => command('play'));
  $('nextButton').addEventListener('click', () => command('next_take'));
  $('circleButton').addEventListener('click', () => command('toggle_circle'));
  $('circleTop').addEventListener('click', () => command('toggle_circle'));
  $('sceneBox').addEventListener('click', () => {
    if (!lastState || lastState.recording) return;
    const value = prompt('Scene', lastState.scene || '');
    if (value !== null && value.trim()) command('set_scene', {scene:value.trim()});
  });
  $('takeBox').addEventListener('click', () => {
    if (!lastState || lastState.recording) return;
    const value = prompt('Take number', lastState.take || 1);
    const n = Number.parseInt(value, 10);
    if (Number.isFinite(n) && n > 0) command('set_take', {take:n});
  });
  $('unpairButton').addEventListener('click', async () => {
    try { await jsonFetch('/api/unpair', {method:'POST', body:'{}'}); } catch (_) {}
    requirePairing();
  });

  // Initial probe. A QR code can provide the PIN in the URL fragment; fragments are
  // never sent to the server, and we remove it from browser history immediately.
  (async () => {
    const match = window.location.hash.match(/(?:^#|&)pin=(\d{6})(?:&|$)/);
    if (match) {
      $('pinInput').value = match[1];
      history.replaceState(null, '', window.location.pathname + window.location.search);
      await pair();
    }
    try {
      const info = await jsonFetch('/api/info');
      $('projectName').textContent = info.project || 'Remote Control';
    } catch (_) {}
    await poll();
  })();
  setInterval(poll, 150);
})();
