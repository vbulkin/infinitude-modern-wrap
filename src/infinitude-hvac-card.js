/**
 * Infinitude HVAC Card — LitElement Lovelace card for Carrier/Bryant Infinity thermostats.
 * Zones, schedule editing, and comfort profile management.
 */
import { LitElement, html, css, nothing } from 'lit';

const DAYS = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday'];
const JS_DAY_MAP = [6,0,1,2,3,4,5];
const ACTIVITIES = ['home','away','sleep','wake'];
const FAN_OPTIONS = ['off','low','med','high'];
const TIME_OPTIONS = (() => {
  const opts = [];
  for (let h = 0; h < 24; h++) {
    for (let m = 0; m < 60; m += 15) {
      const v = `${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}`;
      const l = h === 0 ? `12:${String(m).padStart(2,'0')} AM`
        : h < 12 ? `${h}:${String(m).padStart(2,'0')} AM`
        : h === 12 ? `12:${String(m).padStart(2,'0')} PM`
        : `${h-12}:${String(m).padStart(2,'0')} PM`;
      opts.push({ v, l });
    }
  }
  return opts;
})();

class InfinitudeHVACCard extends LitElement {

  static properties = {
    hass:           { attribute: false },
    _config:        { state: true },
    _tab:           { state: true },
    _schedDay:      { state: true },
    _schedEdits:    { state: true },
    _profileEdits:  { state: true },
    _registryLoaded:{ state: true },
    _pendingTemps:  { state: true },
  };

  constructor() {
    super();
    this._config = {};
    this._tab = 'zones';
    this._schedDay = DAYS[JS_DAY_MAP[new Date().getDay()]];
    this._schedEdits = {};
    this._profileEdits = {};
    this._registryEntities = null;
    this._registryLoaded = false;
    this._tempAdj = {};       // per-entity debounce/commit state
    this._pendingTemps = {};  // reactive: { [eid]: { heat, cool } } for optimistic display
  }

  static getConfigElement() { return document.createElement('div'); }
  static getStubConfig() { return {}; }
  setConfig(c) { this._config = c; }
  getCardSize() { return 8; }

  /* Only re-render when OUR entities change, not every HA state update. */
  shouldUpdate(changed) {
    if (!changed.has('hass')) return true;
    if (!this._registryLoaded) return true;
    const prev = changed.get('hass');
    if (!prev) return true;
    const reg = this._registryEntities || [];
    return reg.some(e => this.hass.states[e.entity_id] !== prev.states[e.entity_id]);
  }

  updated(changed) {
    if (changed.has('hass') && this.hass && !this._registryLoaded) {
      this._loadRegistry();
    }
  }

  async _loadRegistry() {
    try {
      const all = await this.hass.connection.sendMessagePromise({
        type: 'config/entity_registry/list',
      });
      this._registryEntities = all.filter(e => e.platform === 'infinitude_direct');
    } catch (e) {
      console.warn('Failed to load entity registry', e);
      this._registryEntities = [];
    }
    this._registryLoaded = true;
  }

  // ── Entity discovery (registry-based) ──────────────────────────────────
  _findEntities() {
    if (!this.hass) return { climates: [], sensors: {}, selects: {}, system: {} };
    const reg = this._registryEntities || [];
    const st = this.hass.states;
    const climates = [];
    const sensors = { damper: {}, fan: {} };
    const selects = {};
    const system = {};

    if (this._config.climate_entities) {
      for (const eid of this._config.climate_entities) if (st[eid]) climates.push(eid);
    }
    for (const entry of reg) {
      const eid = entry.entity_id;
      if (!st[eid]) continue;
      const dom = eid.split('.')[0];
      const uid = entry.unique_id || '';
      if (dom === 'climate') { if (!this._config.climate_entities) climates.push(eid); }
      else if (dom === 'select') { selects.wholeHouse = eid; }
      else if (dom === 'sensor') {
        if (uid.includes('damper'))       sensors.damper[eid] = st[eid];
        else if (uid.includes('fan'))     sensors.fan[eid] = st[eid];
        else if (uid.includes('humidifier'))  system.humidifier = eid;
        else if (uid.includes('oat'))         system.oat = eid;
        else if (uid.includes('op_status'))   system.opStatus = eid;
        else if (uid.includes('system_info')) system.info = eid;
      }
    }
    climates.sort();
    return { climates, sensors, selects, system };
  }

  _st(eid) { return eid ? this.hass?.states[eid] ?? null : null; }
  _at(eid, a) { return this._st(eid)?.attributes?.[a]; }

  _getScheduleData() {
    const { system } = this._findEntities();
    if (!system.info) return {};
    try { return JSON.parse(this._at(system.info, 'schedule') || '{}'); } catch { return {}; }
  }

  _getProfilesData() {
    const { system } = this._findEntities();
    if (!system.info) return [];
    try { return JSON.parse(this._at(system.info, 'profiles') || '[]'); } catch { return []; }
  }

  // ── Service calls ──────────────────────────────────────────────────────
  async _svc(domain, service, data) {
    try { await this.hass.callService(domain, service, data); }
    catch (e) { console.error(`${domain}.${service} failed`, e); }
  }

  _setHvacMode(eid, mode) { this._svc('climate', 'set_hvac_mode', { entity_id: eid, hvac_mode: mode }); }
  _setPreset(eid, preset) { this._svc('climate', 'set_preset_mode', { entity_id: eid, preset_mode: preset }); }

  // ── Optimistic temperature adjustment with debounce ────────────────────
  _adjustTemp(eid, delta, sp) {
    const s = this._st(eid); if (!s) return;
    const a = s.attributes;
    const adj = this._tempAdj[eid] || (this._tempAdj[eid] = {});

    // Read from pending value if active, else from entity state
    const curHeat = adj.heat ?? a.target_temp_low ?? a.temperature ?? 68;
    const curCool = adj.cool ?? a.target_temp_high ?? (s.state === 'cool' ? a.temperature : null) ?? 76;

    if (sp === 'heat') adj.heat = Math.max(50, Math.min(90, Math.round(curHeat) + delta));
    else               adj.cool = Math.max(60, Math.min(99, Math.round(curCool) + delta));

    // Optimistic UI — trigger reactive render
    this._pendingTemps = { ...this._pendingTemps, [eid]: { heat: adj.heat, cool: adj.cool } };

    // Debounce: only schedule commit when no API call is in-flight
    if (!adj.committing) {
      clearTimeout(adj.timer);
      adj.timer = setTimeout(() => this._commitAdj(eid), 800);
    }
  }

  async _commitAdj(eid) {
    const adj = this._tempAdj[eid];
    if (!adj || adj.committing) return;
    adj.committing = true;

    const s = this._st(eid);
    const a = s?.attributes || {};
    const snapH = adj.heat, snapC = adj.cool;
    const htsp = snapH ?? Math.round(a.target_temp_low ?? a.temperature ?? 68);
    const clsp = snapC ?? Math.round(a.target_temp_high ?? (s?.state === 'cool' ? a.temperature : null) ?? 76);

    const mode = s?.state || 'off';
    const d = { entity_id: eid };
    if (mode === 'heat_cool') { d.target_temp_low = htsp; d.target_temp_high = clsp; }
    else if (mode === 'heat') { d.temperature = htsp; }
    else if (mode === 'cool') { d.temperature = clsp; }
    else { d.target_temp_low = htsp; d.target_temp_high = clsp; }

    try { await this.hass.callService('climate', 'set_temperature', d); }
    catch (e) { console.error('set_temperature failed', e); }

    adj.committing = false;

    // Did the user adjust while we were committing?
    if (adj.heat !== snapH || adj.cool !== snapC) {
      adj.timer = setTimeout(() => this._commitAdj(eid), 400);
      return;
    }

    // Done — clear pending state, keep grace window so server state catches up
    adj.heat = null; adj.cool = null; adj.timer = null;
    adj.graceUntil = Date.now() + 30000;
    // Remove pending UI after a short delay so the next hass update takes over
    setTimeout(() => {
      if (!this._tempAdj[eid]?.heat && !this._tempAdj[eid]?.cool) {
        const { [eid]: _, ...rest } = this._pendingTemps;
        this._pendingTemps = rest;
      }
    }, 2000);
  }

  _hasPending(eid) {
    const adj = this._tempAdj[eid];
    return adj && (adj.heat != null || adj.cool != null || adj.committing);
  }

  // ── Hold controls ──────────────────────────────────────────────────────
  _cancelHold(eid) {
    // Extract zone_id from entity's unique_id ("infinitude_{zone_id}")
    const reg = (this._registryEntities || []).find(e => e.entity_id === eid);
    if (!reg) return;
    const zoneId = (reg.unique_id || '').replace(/^infinitude_/, '');
    if (!zoneId) return;
    this._svc('infinitude_direct', 'cancel_hold', { zone_id: zoneId });
  }

  _setWholeHouseHold(opt) {
    const { selects } = this._findEntities();
    if (selects.wholeHouse) this._svc('select', 'select_option', { entity_id: selects.wholeHouse, option: opt });
  }

  // ── Styles ─────────────────────────────────────────────────────────────
  static styles = css`
    :host { display: block; }
    ha-card { overflow: hidden; }
    .card-header {
      display: flex; align-items: center; justify-content: space-between;
      padding: 16px 16px 8px; flex-wrap: wrap; gap: 8px;
    }
    .header-left { display: flex; align-items: center; gap: 12px; }
    .header-title { font-size: 18px; font-weight: 500; color: var(--primary-text-color); }
    .header-mode {
      font-size: 11px; font-weight: 600; text-transform: uppercase;
      padding: 3px 8px; border-radius: 4px;
      background: var(--primary-color); color: var(--text-primary-color, #fff);
    }
    .header-mode.heat { background: var(--label-badge-red, #f97316); }
    .header-mode.cool { background: var(--label-badge-blue, #38bdf8); }
    .header-mode.auto { background: var(--label-badge-green, #34d399); }
    .header-stats { display: flex; gap: 16px; align-items: center; font-size: 12px; color: var(--secondary-text-color); }
    .stat-val { font-weight: 600; color: var(--primary-text-color); }
    .wh-hold {
      display: flex; align-items: center; gap: 6px; width: 100%;
      padding: 8px 12px; margin-top: 4px;
      background: rgba(251,191,36,0.08); border: 1px solid rgba(251,191,36,0.2);
      border-radius: 8px; font-size: 12px; color: var(--warning-color, #fbbf24); cursor: pointer;
    }
    .wh-hold:hover { background: rgba(251,191,36,0.14); }
    .card-tabs { display: flex; gap: 0; border-bottom: 1px solid var(--divider-color); padding: 0 16px; }
    .tab {
      padding: 10px 16px; font-size: 13px; font-weight: 500;
      color: var(--secondary-text-color); cursor: pointer;
      border-bottom: 2px solid transparent; margin-bottom: -1px;
      transition: all 0.15s; user-select: none;
    }
    .tab:hover { color: var(--primary-text-color); }
    .tab.active { color: var(--primary-color); border-bottom-color: var(--primary-color); }
    .card-content { padding: 12px 16px 16px; }
    .zone-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 12px; }
    .zone-card {
      background: var(--card-background-color, var(--ha-card-background));
      border: 1px solid var(--divider-color); border-radius: 12px;
      overflow: hidden; transition: border-color 0.2s;
    }
    .zone-card:hover { border-color: var(--primary-color); }
    .zone-card.heating { border-left: 3px solid var(--label-badge-red, #f97316); }
    .zone-card.cooling { border-left: 3px solid var(--label-badge-blue, #38bdf8); }
    .zone-card.drying  { border-left: 3px solid var(--accent-color, #a78bfa); }
    .zone-top { display: flex; align-items: center; justify-content: space-between; padding: 12px 14px 4px; }
    .zone-name { font-size: 14px; font-weight: 600; color: var(--primary-text-color); }
    .zone-badge {
      font-size: 10px; font-weight: 600; text-transform: uppercase;
      padding: 2px 8px; border-radius: 12px;
      background: var(--secondary-background-color); color: var(--secondary-text-color);
    }
    .zone-badge.heating { background: rgba(249,115,22,0.15); color: var(--label-badge-red, #f97316); }
    .zone-badge.cooling { background: rgba(56,189,248,0.15); color: var(--label-badge-blue, #38bdf8); }
    .zone-badge.drying  { background: rgba(167,139,250,0.15); color: var(--accent-color, #a78bfa); }
    .zone-body { display: flex; align-items: center; padding: 4px 14px 12px; gap: 16px; }
    .temp-hero { font-size: 42px; font-weight: 300; line-height: 1; color: var(--primary-text-color); font-variant-numeric: tabular-nums; }
    .temp-unit { font-size: 14px; color: var(--secondary-text-color); }
    .zone-sp { display: flex; flex-direction: column; gap: 6px; }
    .sp-row { display: flex; align-items: center; gap: 4px; font-size: 13px; font-variant-numeric: tabular-nums; }
    .sp-val { min-width: 32px; text-align: center; font-weight: 600; }
    .sp-heat { color: var(--label-badge-red, #f97316); }
    .sp-cool { color: var(--label-badge-blue, #38bdf8); }
    .btn-adj {
      width: 28px; height: 28px; border-radius: 8px; border: 1px solid var(--divider-color);
      background: var(--secondary-background-color); color: var(--secondary-text-color);
      font-size: 16px; font-weight: 600; cursor: pointer;
      display: inline-flex; align-items: center; justify-content: center;
      user-select: none; line-height: 1; transition: all 0.12s;
    }
    .btn-adj:hover { background: var(--primary-color); color: var(--text-primary-color, #fff); border-color: var(--primary-color); }
    .btn-adj:active { transform: scale(0.92); }
    .zone-meta { display: flex; gap: 10px; padding: 0 14px 10px; font-size: 11px; color: var(--secondary-text-color); flex-wrap: wrap; }
    .meta-item { display: flex; align-items: center; gap: 4px; }
    .meta-val { color: var(--primary-text-color); font-weight: 500; }
    .zone-hold {
      display: flex; align-items: center; gap: 6px; padding: 8px 14px;
      background: rgba(251,191,36,0.06); border-top: 1px solid rgba(251,191,36,0.15); font-size: 11px;
    }
    .hold-label { color: var(--warning-color, #fbbf24); font-weight: 500; flex: 1; }
    .sp-pending { animation: sp-pulse 0.8s ease-in-out infinite; color: var(--warning-color, #fbbf24) !important; }
    @keyframes sp-pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.4; } }
    .zone-actions { padding: 0 14px 10px; display: flex; gap: 8px; }
    .zone-preset-row {
      display: flex; gap: 0; border-radius: 6px; overflow: hidden;
      border: 1px solid var(--divider-color); margin: 0 14px 10px;
    }
    .preset-btn {
      flex: 1; padding: 5px 0; font-size: 11px; font-weight: 600;
      text-align: center; border: none; border-right: 1px solid var(--divider-color);
      background: var(--secondary-background-color); color: var(--secondary-text-color);
      cursor: pointer; transition: all 0.12s; text-transform: capitalize;
    }
    .preset-btn:last-child { border-right: none; }
    .preset-btn:hover, .preset-btn.active { background: var(--primary-color); color: var(--text-primary-color, #fff); }
    .mode-row { display: flex; align-items: center; gap: 8px; margin-bottom: 12px; width: 100%; }
    .mode-label { font-size: 10px; color: var(--secondary-text-color); text-transform: uppercase; letter-spacing: 0.5px; font-weight: 600; }
    .mode-pills { display: flex; gap: 0; border-radius: 8px; overflow: hidden; border: 1px solid var(--divider-color); }
    .mode-pill {
      font-size: 12px; font-weight: 600; padding: 6px 14px; border: none;
      border-right: 1px solid var(--divider-color);
      background: var(--secondary-background-color); color: var(--secondary-text-color);
      cursor: pointer; transition: all 0.15s;
    }
    .mode-pill:last-child { border-right: none; }
    .mode-pill:hover { color: var(--primary-text-color); }
    .mode-pill.active { background: var(--primary-color); color: var(--text-primary-color, #fff); }
    .mode-pill.active.heat { background: var(--label-badge-red, #f97316); }
    .mode-pill.active.cool { background: var(--label-badge-blue, #38bdf8); }
    .mode-pill.active.auto { background: var(--label-badge-green, #34d399); }
    .sched-day-tabs { display: flex; gap: 4px; margin-bottom: 12px; flex-wrap: wrap; }
    .day-tab {
      padding: 5px 12px; border-radius: 16px; font-size: 12px; font-weight: 600;
      cursor: pointer; background: var(--secondary-background-color);
      color: var(--secondary-text-color); border: 1px solid var(--divider-color);
      transition: all 0.15s; user-select: none;
    }
    .day-tab:hover { border-color: var(--primary-color); color: var(--primary-text-color); }
    .day-tab.active { background: var(--primary-color); color: var(--text-primary-color, #fff); border-color: var(--primary-color); }
    .day-tab.today { box-shadow: 0 0 0 2px var(--primary-color); }
    .period-card {
      background: var(--secondary-background-color); border: 1px solid var(--divider-color);
      border-radius: 10px; margin-bottom: 8px; overflow: hidden;
    }
    .period-header {
      padding: 6px 12px; font-size: 12px; font-weight: 600;
      color: var(--secondary-text-color); border-bottom: 1px solid var(--divider-color);
    }
    .sched-line {
      display: flex; align-items: center; gap: 8px; padding: 6px 12px;
      border-bottom: 1px solid var(--divider-color); font-size: 12px;
    }
    .sched-line:last-child { border-bottom: none; }
    .sched-line.disabled { opacity: 0.35; }
    .sched-name { width: 120px; min-width: 80px; flex-shrink: 0; font-weight: 600; color: var(--primary-text-color); white-space: nowrap; }
    .sched-select {
      background: var(--card-background-color); border: 1px solid var(--divider-color);
      border-radius: 4px; color: var(--primary-text-color); font-size: 11px; padding: 3px 6px; outline: none;
    }
    .sched-select:focus { border-color: var(--primary-color); }
    .sched-temps { display: flex; gap: 6px; align-items: center; font-size: 12px; font-variant-numeric: tabular-nums; }
    .sched-toggle { cursor: pointer; display: flex; align-items: center; gap: 3px; }
    .sched-toggle input { cursor: pointer; }
    .sched-toggle span { font-size: 10px; color: var(--secondary-text-color); }
    .action-bar {
      display: flex; align-items: center; gap: 8px; padding: 10px 0;
      border-top: 1px solid var(--divider-color); margin-top: 8px;
    }
    .action-bar-label { font-size: 12px; color: var(--warning-color, #fbbf24); margin-right: auto; }
    .btn {
      padding: 6px 14px; border-radius: 8px; font-size: 12px; font-weight: 500;
      border: 1px solid var(--divider-color); cursor: pointer; transition: all 0.12s;
      background: var(--secondary-background-color); color: var(--secondary-text-color);
    }
    .btn:hover { color: var(--primary-text-color); border-color: var(--primary-color); }
    .btn-primary { background: var(--primary-color); color: var(--text-primary-color, #fff); border-color: var(--primary-color); }
    .btn-primary:hover { opacity: 0.9; }
    .prof-card {
      background: var(--secondary-background-color); border: 1px solid var(--divider-color);
      border-radius: 10px; margin-bottom: 8px; overflow: hidden;
    }
    .prof-header {
      padding: 8px 12px; font-size: 13px; font-weight: 600;
      border-bottom: 1px solid var(--divider-color); text-transform: capitalize;
    }
    .prof-line {
      display: flex; align-items: center; gap: 10px; padding: 8px 12px;
      border-bottom: 1px solid var(--divider-color); font-size: 12px;
    }
    .prof-line:last-child { border-bottom: none; }
    .prof-name { width: 120px; min-width: 80px; flex-shrink: 0; font-weight: 600; color: var(--primary-text-color); white-space: nowrap; }
    .prof-fan { display: flex; align-items: center; gap: 4px; }
    .prof-fan-label { font-size: 10px; color: var(--secondary-text-color); }
    .copy-bar { display: flex; align-items: center; gap: 8px; margin-top: 10px; font-size: 12px; color: var(--secondary-text-color); }
    .section-title { font-size: 11px; font-weight: 600; color: var(--secondary-text-color); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 10px; }
  `;

  // ── Render ─────────────────────────────────────────────────────────────
  render() {
    if (!this.hass) return nothing;
    if (!this._registryLoaded) {
      return html`<ha-card>
        <div style="padding:24px;text-align:center;color:var(--secondary-text-color)">Loading…</div>
      </ha-card>`;
    }
    const ent = this._findEntities();
    if (!ent.climates.length && !this._config.show_empty) {
      return html`<ha-card>
        <div style="padding:24px;text-align:center;color:var(--secondary-text-color)">
          <ha-icon icon="mdi:thermostat" style="--mdc-icon-size:48px;opacity:0.3;margin-bottom:12px;display:block"></ha-icon>
          <div style="font-size:14px;font-weight:500">No Infinitude entities found</div>
          <div style="font-size:12px;margin-top:4px">Waiting for thermostat connection…</div>
        </div>
      </ha-card>`;
    }
    return html`
      <ha-card>
        <div class="card-header">${this._hdr(ent)}</div>
        <div class="card-tabs">${this._tabs()}</div>
        <div class="card-content">
          ${this._tab === 'zones'    ? this._zones(ent) : nothing}
          ${this._tab === 'schedule' ? this._sched(ent) : nothing}
          ${this._tab === 'profiles' ? this._profs()     : nothing}
        </div>
      </ha-card>`;
  }

  // ── Header ─────────────────────────────────────────────────────────────
  _hdr(ent) {
    const { system, selects, climates } = ent;
    const mode = climates.length ? (this._st(climates[0])?.state || 'off') : 'off';
    const mc = mode === 'heat' ? 'heat' : mode === 'cool' ? 'cool' : (mode === 'heat_cool' || mode === 'auto') ? 'auto' : '';
    const ml = mode === 'heat_cool' ? 'Auto' : mode.charAt(0).toUpperCase() + mode.slice(1);

    const os = this._st(system.oat);
    let oat = '–';
    if (os?.state && os.state !== 'unavailable') oat = `${Math.round(Number(os.state))}°`;
    else if (climates.length) { const v = this._at(climates[0], 'outdoor_temperature'); if (v != null) oat = `${Math.round(Number(v))}°`; }

    const opS = this._st(system.opStatus);
    const opStatus = opS?.state && opS.state !== 'unavailable' ? opS.state : '';
    const humid = this._st(system.humidifier)?.state === 'on';
    const whS = this._st(selects.wholeHouse);
    const whHold = whS && whS.state !== 'off';
    const rh = climates.length ? this._at(climates[0], 'current_humidity') : null;

    return html`
      <div class="header-left">
        <span class="header-title">HVAC</span>
        <span class="header-mode ${mc}">${ml}</span>
      </div>
      <div class="header-stats">
        <span>Outside <span class="stat-val">${oat}</span></span>
        ${rh != null ? html`<span>Indoor RH <span class="stat-val">${rh}%</span></span>` : nothing}
        ${humid ? html`<span style="color:var(--label-badge-blue,#38bdf8)">💧 Humidifier On</span>` : nothing}
        ${opStatus ? html`<span>${opStatus}</span>` : nothing}
      </div>
      ${whHold ? html`
        <div class="wh-hold" @click=${() => this._setWholeHouseHold('off')}>
          <ha-icon icon="mdi:home-lock" style="--mdc-icon-size:16px"></ha-icon>
          <span>Whole house: <strong>${whS.state}</strong></span>
          <span style="margin-left:auto;opacity:0.7">Tap to cancel</span>
        </div>` : nothing}`;
  }

  // ── Tabs ───────────────────────────────────────────────────────────────
  _tabs() {
    return html`${['zones','schedule','profiles'].map(t => html`
      <div class="tab ${this._tab === t ? 'active' : ''}"
           @click=${() => { this._tab = t; }}>${t.charAt(0).toUpperCase() + t.slice(1)}</div>`)}`;
  }

  // ── Zones ──────────────────────────────────────────────────────────────
  _zones(ent) {
    const { climates } = ent;
    if (!climates.length) return html`<div style="padding:20px;text-align:center;color:var(--secondary-text-color)">No zone entities found</div>`;
    const mode = this._st(climates[0])?.state || 'off';
    const modes = ['off','heat','cool','heat_cool'];
    const lbl = { off:'Off', heat:'Heat', cool:'Cool', heat_cool:'Auto' };

    return html`
      <div class="mode-row">
        <span class="mode-label">Mode</span>
        <div class="mode-pills">
          ${modes.map(m => {
            const mc = m === 'heat' ? 'heat' : m === 'cool' ? 'cool' : m === 'heat_cool' ? 'auto' : '';
            return html`<div class="mode-pill ${m === mode ? 'active' : ''} ${mc}"
              @click=${() => this._setHvacMode(climates[0], m)}>${lbl[m]}</div>`;
          })}
        </div>
      </div>
      <div class="zone-grid">${climates.map(eid => this._zoneCard(eid))}</div>`;
  }

  _zoneCard(eid) {
    const s = this._st(eid);
    if (!s) return nothing;
    const a = s.attributes || {};
    const name = (a.friendly_name || eid).replace(/^Infinitude\s+/i, '').replace(/^infinitude_direct\s+/i, '');
    const temp = a.current_temperature != null ? Math.round(a.current_temperature) : '–';
    const rh = a.current_humidity;
    const mode = s.state || 'off';
    const action = a.hvac_action || 'idle';
    const preset = a.preset_mode || '–';
    const ac = action === 'heating' ? 'heating' : action === 'cooling' ? 'cooling' : action === 'drying' ? 'drying' : '';
    const al = action === 'idle' ? 'Idle' : action.charAt(0).toUpperCase() + action.slice(1);
    const isRange = mode === 'heat_cool';
    const hasHold = !!a.hold_active;
    const holdActivity = a.hold_activity || preset;

    // Optimistic temps: use pending values if the user is adjusting
    const pending = this._pendingTemps[eid];
    const isPending = this._hasPending(eid);
    const htsp = pending?.heat ?? a.target_temp_low ?? a.temperature ?? null;
    const clsp = pending?.cool ?? a.target_temp_high ?? (mode === 'cool' ? a.temperature : null) ?? null;

    return html`
      <div class="zone-card ${ac}">
        <div class="zone-top">
          <span class="zone-name">${name}</span>
          <span class="zone-badge ${ac}">${al}</span>
        </div>
        <div class="zone-body">
          <div>
            <span class="temp-hero">${temp}</span><span class="temp-unit">°F</span>
            ${rh != null ? html`<div style="font-size:11px;color:var(--secondary-text-color);margin-top:2px">${rh}% RH</div>` : nothing}
          </div>
          <div class="zone-sp">
            ${htsp != null ? html`
              <div class="sp-row">
                <button class="btn-adj" @click=${() => this._adjustTemp(eid, -1, 'heat')}>−</button>
                <span class="sp-val sp-heat ${isPending ? 'sp-pending' : ''}">${Math.round(htsp)}°</span>
                <button class="btn-adj" @click=${() => this._adjustTemp(eid, 1, 'heat')}>+</button>
              </div>` : nothing}
            ${isRange && clsp != null ? html`
              <div class="sp-row">
                <button class="btn-adj" @click=${() => this._adjustTemp(eid, -1, 'cool')}>−</button>
                <span class="sp-val sp-cool ${isPending ? 'sp-pending' : ''}">${Math.round(clsp)}°</span>
                <button class="btn-adj" @click=${() => this._adjustTemp(eid, 1, 'cool')}>+</button>
              </div>` : nothing}
          </div>
        </div>
        <div class="zone-meta">
          <span class="meta-item">Activity <span class="meta-val">${preset}</span></span>
          ${a.fan_mode ? html`<span class="meta-item">Fan <span class="meta-val">${a.fan_mode}</span></span>` : nothing}
          ${a.damper_position != null ? html`<span class="meta-item">Damper <span class="meta-val">${a.damper_position}%</span></span>` : nothing}
        </div>
        <div class="zone-preset-row">
          ${ACTIVITIES.map(act => html`
            <div class="preset-btn ${preset === act ? 'active' : ''}"
                 @click=${() => this._setPreset(eid, act)}>${act}</div>`)}
        </div>
        ${hasHold ? html`
          <div class="zone-hold">
            <span class="hold-label">Hold: ${holdActivity}</span>
            <button class="btn" style="font-size:11px;padding:3px 10px;color:var(--error-color,#f87171)" @click=${() => this._cancelHold(eid)}>Cancel</button>
          </div>` : html`
          <div class="zone-actions">
            <button class="btn" style="font-size:11px;padding:4px 12px" @click=${() => this._setPreset(eid, preset !== '–' ? preset : 'home')}>Set hold</button>
          </div>`}
      </div>`;
  }

  // ── Schedule ───────────────────────────────────────────────────────────
  _sched() {
    const schedule = this._getScheduleData();
    const profiles = this._getProfilesData();
    const zids = Object.keys(schedule);
    if (!zids.length) return html`
      <div style="padding:20px;text-align:center;color:var(--secondary-text-color)">
        <ha-icon icon="mdi:calendar-clock" style="--mdc-icon-size:48px;opacity:0.3;margin-bottom:12px;display:block"></ha-icon>
        No schedule data available. Waiting for thermostat data…
      </div>`;

    const today = DAYS[JS_DAY_MAP[new Date().getDay()]];
    const zn = {}; for (const z of profiles) zn[z.id] = z.name;
    let maxP = 0;
    for (const zid of zids) maxP = Math.max(maxP, (schedule[zid]?.[this._schedDay] || []).length);
    if (!maxP) maxP = 5;
    const hasEdits = Object.keys(this._schedEdits).length > 0;

    return html`
      <div class="section-title">Schedule</div>
      <div class="sched-day-tabs">
        ${DAYS.map(d => html`
          <div class="day-tab ${d === this._schedDay ? 'active' : ''} ${d === today && d !== this._schedDay ? 'today' : ''}"
               @click=${() => { this._schedDay = d; }}>${d.slice(0,3)}</div>`)}
      </div>
      ${Array.from({length: maxP}, (_, pi) => this._periodCard(pi, zids, schedule, profiles, zn))}
      <div class="copy-bar">
        <span>Copy ${this._schedDay.slice(0,3)} →</span>
        <select class="sched-select" @change=${(e) => this._copySched(e)}>
          <option value="">select day…</option>
          ${DAYS.filter(d => d !== this._schedDay).map(d => html`<option value=${d}>${d.slice(0,3)}</option>`)}
          <option value="__all__">All other days</option>
        </select>
      </div>
      ${hasEdits ? html`
        <div class="action-bar">
          <span class="action-bar-label">● Unsaved changes</span>
          <button class="btn" @click=${() => { this._schedEdits = {}; }}>Discard</button>
          <button class="btn btn-primary" @click=${() => this._saveSched()}>Save schedule</button>
        </div>` : nothing}`;
  }

  _periodCard(pi, zids, schedule, profiles, zn) {
    return html`
      <div class="period-card">
        <div class="period-header">Period ${pi + 1}</div>
        ${zids.map(zid => {
          const period = (schedule[zid]?.[this._schedDay] || [])[pi];
          if (!period) return nothing;
          const ek = `${zid}_${this._schedDay}_${pi}`;
          const ed = this._schedEdits[ek];
          const act = ed?.act ?? period.activity;
          const time = ed?.time ?? period.time;
          const enabled = ed?.enabled ?? period.enabled;
          const zp = profiles.find(z => z.id === zid);
          const ap = zp?.activities?.[act];
          const htsp = ap?.htsp ? Math.round(parseFloat(ap.htsp)) : '–';
          const clsp = ap?.clsp ? Math.round(parseFloat(ap.clsp)) : '–';

          return html`
            <div class="sched-line ${enabled ? '' : 'disabled'}">
              <span class="sched-name">${zn[zid] || `Zone ${zid}`}</span>
              <select class="sched-select" @change=${(e) => this._schedEdit(zid, pi, 'act', e.target.value)}>
                ${ACTIVITIES.map(a => html`<option value=${a} ?selected=${a === act}>${a}</option>`)}
              </select>
              <select class="sched-select" @change=${(e) => this._schedEdit(zid, pi, 'time', e.target.value)}>
                ${TIME_OPTIONS.map(o => html`<option value=${o.v} ?selected=${o.v === time}>${o.l}</option>`)}
              </select>
              <label class="sched-toggle">
                <input type="checkbox" ?checked=${enabled}
                       @change=${(e) => this._schedEdit(zid, pi, 'enabled', e.target.checked)}>
                <span>on</span>
              </label>
              <div class="sched-temps">
                <span class="sp-heat">${htsp}°</span>
                <span class="sp-cool">${clsp}°</span>
              </div>
            </div>`;
        })}
      </div>`;
  }

  _schedEdit(zid, pi, field, val) {
    const ek = `${zid}_${this._schedDay}_${pi}`;
    const prev = this._schedEdits[ek] || {};
    const p = (this._getScheduleData()[zid]?.[this._schedDay] || [])[pi] || {};
    this._schedEdits = { ...this._schedEdits, [ek]: {
      act:     field === 'act'     ? val : (prev.act     ?? p.activity),
      time:    field === 'time'    ? val : (prev.time    ?? p.time),
      enabled: field === 'enabled' ? val : (prev.enabled ?? p.enabled),
    }};
  }

  _copySched(e) {
    const tgt = e.target.value; if (!tgt) return;
    e.target.value = '';
    const sch = this._getScheduleData();
    const targets = tgt === '__all__' ? DAYS.filter(d => d !== this._schedDay) : [tgt];
    const edits = { ...this._schedEdits };
    for (const zid of Object.keys(sch)) {
      const periods = sch[zid]?.[this._schedDay] || [];
      for (const day of targets) {
        periods.forEach((p, pi) => {
          const se = this._schedEdits[`${zid}_${this._schedDay}_${pi}`];
          edits[`${zid}_${day}_${pi}`] = {
            act: se?.act ?? p.activity, time: se?.time ?? p.time, enabled: se?.enabled ?? p.enabled,
          };
        });
      }
    }
    this._schedEdits = edits;
  }

  async _saveSched() {
    const sch = this._getScheduleData();
    for (const zid of Object.keys(sch)) {
      const prog = DAYS.map(day => ({
        id: day,
        period: (sch[zid]?.[day] || []).map((p, pi) => {
          const ed = this._schedEdits[`${zid}_${day}_${pi}`];
          return {
            id: p.id || String(pi + 1),
            activity: ed?.act ?? p.activity,
            time: ed?.time ?? p.time,
            enabled: (ed?.enabled ?? p.enabled) ? 'on' : 'off',
          };
        }),
      }));
      await this._svc('infinitude_direct', 'save_schedule', { zone_id: zid, schedule: JSON.stringify(prog) });
    }
    this._schedEdits = {};
  }

  // ── Profiles ───────────────────────────────────────────────────────────
  _profs() {
    const profiles = this._getProfilesData();
    if (!profiles.length) return html`
      <div style="padding:20px;text-align:center;color:var(--secondary-text-color)">
        <ha-icon icon="mdi:tune-vertical" style="--mdc-icon-size:48px;opacity:0.3;margin-bottom:12px;display:block"></ha-icon>
        No profile data available. Waiting for thermostat data…
      </div>`;

    const hasEdits = Object.keys(this._profileEdits).length > 0;
    return html`
      <div class="section-title">Comfort Profiles</div>
      ${ACTIVITIES.map(actId => html`
        <div class="prof-card">
          <div class="prof-header">${actId}</div>
          ${profiles.map(zone => {
            const act = zone.activities?.[actId] || {};
            const ek = `${zone.id}_${actId}`;
            const ed = this._profileEdits[ek];
            const htsp = ed?.htsp ?? (act.htsp ? Math.round(parseFloat(act.htsp)) : 68);
            const clsp = ed?.clsp ?? (act.clsp ? Math.round(parseFloat(act.clsp)) : 76);
            const fan  = ed?.fan  ?? act.fan ?? 'low';
            return html`
              <div class="prof-line">
                <span class="prof-name">${zone.name}</span>
                <div class="sp-row">
                  <button class="btn-adj" @click=${() => this._profAdj(zone.id, actId, 'htsp', -1)}>−</button>
                  <span class="sp-val sp-heat">${htsp}°</span>
                  <button class="btn-adj" @click=${() => this._profAdj(zone.id, actId, 'htsp', 1)}>+</button>
                </div>
                <div class="sp-row">
                  <button class="btn-adj" @click=${() => this._profAdj(zone.id, actId, 'clsp', -1)}>−</button>
                  <span class="sp-val sp-cool">${clsp}°</span>
                  <button class="btn-adj" @click=${() => this._profAdj(zone.id, actId, 'clsp', 1)}>+</button>
                </div>
                <div class="prof-fan">
                  <span class="prof-fan-label">Fan</span>
                  <select class="sched-select" @change=${(e) => this._profFan(zone.id, actId, e.target.value)}>
                    ${FAN_OPTIONS.map(f => html`<option value=${f} ?selected=${f === fan}>${f}</option>`)}
                  </select>
                </div>
              </div>`;
          })}
        </div>`)}
      ${hasEdits ? html`
        <div class="action-bar">
          <span class="action-bar-label">● Unsaved changes</span>
          <button class="btn" @click=${() => { this._profileEdits = {}; }}>Discard</button>
          <button class="btn btn-primary" @click=${() => this._saveProfs()}>Save profiles</button>
        </div>` : nothing}`;
  }

  _profAdj(zid, actId, field, delta) {
    const ek = `${zid}_${actId}`;
    const act = (this._getProfilesData().find(z => z.id === zid)?.activities?.[actId]) || {};
    const prev = this._profileEdits[ek] || {};
    const curH = prev.htsp ?? (act.htsp ? Math.round(parseFloat(act.htsp)) : 68);
    const curC = prev.clsp ?? (act.clsp ? Math.round(parseFloat(act.clsp)) : 76);
    const min = field === 'htsp' ? 50 : 60, max = field === 'htsp' ? 90 : 99;
    const cur = field === 'htsp' ? curH : curC;
    this._profileEdits = { ...this._profileEdits, [ek]: {
      zone_id: zid, activity: actId,
      htsp: field === 'htsp' ? Math.max(min, Math.min(max, cur + delta)) : curH,
      clsp: field === 'clsp' ? Math.max(min, Math.min(max, cur + delta)) : curC,
      fan: prev.fan ?? act.fan ?? 'low',
    }};
  }

  _profFan(zid, actId, fan) {
    const ek = `${zid}_${actId}`;
    const act = (this._getProfilesData().find(z => z.id === zid)?.activities?.[actId]) || {};
    const prev = this._profileEdits[ek] || {};
    this._profileEdits = { ...this._profileEdits, [ek]: {
      zone_id: zid, activity: actId,
      htsp: prev.htsp ?? (act.htsp ? Math.round(parseFloat(act.htsp)) : 68),
      clsp: prev.clsp ?? (act.clsp ? Math.round(parseFloat(act.clsp)) : 76),
      fan,
    }};
  }

  async _saveProfs() {
    for (const ed of Object.values(this._profileEdits)) {
      const d = { zone_id: ed.zone_id, activity: ed.activity, htsp: ed.htsp, clsp: ed.clsp };
      if (ed.fan) d.fan = ed.fan;
      await this._svc('infinitude_direct', 'set_profile', d);
    }
    this._profileEdits = {};
  }
}

if (!customElements.get('infinitude-hvac-card')) {
  customElements.define('infinitude-hvac-card', InfinitudeHVACCard);
}
window.customCards = window.customCards || [];
if (!window.customCards.some(c => c.type === 'infinitude-hvac-card')) {
  window.customCards.push({
    type: 'infinitude-hvac-card',
    name: 'Infinitude HVAC Card',
    description: 'Full HVAC dashboard for Carrier/Bryant Infinity thermostats',
    preview: false,
  });
}
