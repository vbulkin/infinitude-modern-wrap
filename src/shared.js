/**
 * Shared utilities, constants, and base class for Infinitude cards.
 */
import { LitElement, html, css, nothing } from 'lit';

export { html, css, nothing };

export const CARD_VERSION = '1.0.79';
export const DAYS = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday'];
export const JS_DAY_MAP = [6,0,1,2,3,4,5];
export const ACTIVITIES = ['home','away','sleep','wake'];
export const HOLD_ACTIVITIES = ['home','away','sleep','wake','manual'];
export const FAN_OPTIONS = ['off','low','med','high'];
export const DURATION_OPTIONS = [
  { v: '60', l: '1 hour' },
  { v: '120', l: '2 hours' },
  { v: '240', l: '4 hours' },
  { v: 'forever', l: 'Indefinite' },
  { v: 'custom', l: 'Custom time…' },
];
export const CIRCLED = ['①','②','③','④','⑤','⑥','⑦','⑧'];
export const TIME_OPTIONS = (() => {
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

/**
 * Base class providing registry/entity discovery, state helpers, and service calls.
 * Every Infinitude card extends this.
 */
export class InfinitudeBase extends LitElement {

  static get baseProperties() {
    return {
      hass: { attribute: false },
      _config: { state: true },
      _registryLoaded: { state: true },
    };
  }

  constructor() {
    super();
    this._config = {};
    this._registryEntities = null;
    this._registryLoaded = false;
  }

  setConfig(c) { this._config = c; }

  /* Only re-render when OUR entities change. */
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
      this._registryEntities = Array.isArray(all)
        ? all.filter(e => e.platform === 'infinitude_direct')
        : [];
    } catch (e) {
      console.warn('Failed to load entity registry', e);
      this._registryEntities = [];
    }
    this._registryLoaded = true;
  }

  // ── Entity discovery ───────────────────────────────────────────────────
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
    try { return JSON.parse(this._at(system.info, 'schedule') || '{}'); } catch (e) { console.warn('Failed to parse schedule data', e); return {}; }
  }

  _getProfilesData() {
    const { system } = this._findEntities();
    if (!system.info) return [];
    try { return JSON.parse(this._at(system.info, 'profiles') || '[]'); } catch (e) { console.warn('Failed to parse profiles data', e); return []; }
  }

  async _svc(domain, service, data) {
    try { await this.hass.callService(domain, service, data); }
    catch (e) { console.error(`${domain}.${service} failed`, e); }
  }

  _setHvacMode(eid, mode) { this._svc('climate', 'set_hvac_mode', { entity_id: eid, hvac_mode: mode }); }
  _setPreset(eid, preset) { this._svc('climate', 'set_preset_mode', { entity_id: eid, preset_mode: preset }); }

  _resolveUntil(duration, custom) {
    if (duration === 'forever') return 'forever';
    if (duration === 'custom') {
      if (!custom) return null;
      return custom;
    }
    const now = new Date();
    now.setMinutes(now.getMinutes() + parseInt(duration));
    const m = Math.round(now.getMinutes() / 15) * 15;
    now.setMinutes(m, 0, 0);
    if (m === 60) { now.setMinutes(0); now.setHours(now.getHours() + 1); }
    return `${String(now.getHours()).padStart(2,'0')}:${String(now.getMinutes()).padStart(2,'0')}`;
  }

  _otmrRelative(otmr) {
    if (!otmr) return '';
    const [h, m] = otmr.split(':').map(Number);
    const d = new Date();
    d.setHours(h, m, 0, 0);
    return 'until ' + d.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
  }

  _zoneId(eid) {
    const reg = (this._registryEntities || []).find(e => e.entity_id === eid);
    return reg ? (reg.unique_id || '').replace(/^infinitude_/, '') : '';
  }

  _renderLoading() {
    return html`<ha-card>
      <div style="padding:24px;text-align:center;color:var(--secondary-text-color)">Loading…</div>
    </ha-card>`;
  }
}

// ── Shared CSS tokens ────────────────────────────────────────────────────
export const sharedStyles = css`
  :host { display: block; }
  ha-card { overflow: hidden; }
  .conn-dot { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; }
  .conn-dot.ok { background: var(--label-badge-green, #34d399); animation: pulse-dot 2.5s ease infinite; }
  .conn-dot.err { background: #ef4444; }
  .conn-dot.unk { background: var(--secondary-text-color); opacity: 0.4; }
  @keyframes pulse-dot { 0%,100% { opacity: 1; } 50% { opacity: 0.4; } }
  .summary-stats {
    display: flex; align-items: center; gap: 0; margin-bottom: 14px;
    border: 1px solid var(--divider-color); border-radius: 8px; overflow: hidden;
  }
  .summary-stat {
    display: flex; flex-direction: column; align-items: center; gap: 2px;
    padding: 8px 14px; flex: 1; min-width: 0;
  }
  .summary-stat-label { font-size: 10px; color: var(--secondary-text-color); text-transform: uppercase; letter-spacing: 0.5px; }
  .summary-stat-val { font-size: 14px; font-weight: 700; color: var(--primary-text-color); }
  .summary-stat-val.heat { color: var(--label-badge-red, #f97316); }
  .summary-stat-val.cool { color: var(--label-badge-blue, #38bdf8); }
  .summary-divider { width: 1px; align-self: stretch; background: var(--divider-color); }
  .wh-hold {
    display: flex; align-items: center; gap: 6px; width: 100%;
    padding: 8px 12px; margin-bottom: 14px;
    background: rgba(251,191,36,0.08); border: 1px solid rgba(251,191,36,0.2);
    border-radius: 8px; font-size: 12px; color: var(--warning-color, #fbbf24); cursor: pointer;
  }
  .wh-hold:hover { background: rgba(251,191,36,0.14); }
  .wh-set {
    display: flex; align-items: center; gap: 8px; width: 100%; margin-bottom: 14px;
    padding: 10px 12px; background: var(--secondary-background-color);
    border: 1px solid var(--divider-color); border-radius: 8px; flex-wrap: wrap;
  }
  .wh-set-label { font-size: 11px; font-weight: 600; color: var(--secondary-text-color); text-transform: uppercase; letter-spacing: 0.5px; }
  .wh-pills { display: flex; gap: 0; border-radius: 6px; overflow: hidden; border: 1px solid var(--divider-color); }
  .wh-pill {
    font-size: 11px; font-weight: 600; padding: 5px 12px; border: none;
    border-right: 1px solid var(--divider-color);
    background: var(--card-background-color, var(--ha-card-background)); color: var(--secondary-text-color);
    cursor: pointer; transition: all 0.12s; text-transform: capitalize;
  }
  .wh-pill:last-child { border-right: none; }
  .wh-pill:hover { color: var(--primary-text-color); }
  .wh-pill.active { background: var(--primary-color); color: var(--text-primary-color, #fff); }
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
  .sp-pending { animation: sp-pulse 0.8s ease-in-out infinite; color: var(--warning-color, #fbbf24) !important; }
  @keyframes sp-pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.4; } }
  .hold-dur-select {
    background: var(--card-background-color); border: 1px solid var(--divider-color);
    border-radius: 4px; color: var(--primary-text-color); font-size: 11px; padding: 4px 6px; outline: none;
  }
  .hold-dur-select:focus { border-color: var(--primary-color); }
  .hold-time-input {
    background: var(--card-background-color); border: 1px solid var(--divider-color);
    border-radius: 4px; color: var(--primary-text-color); font-size: 11px; padding: 4px 6px; outline: none;
  }
  .hold-time-input:focus { border-color: var(--primary-color); }
  .btn {
    padding: 6px 14px; border-radius: 8px; font-size: 12px; font-weight: 500;
    border: 1px solid var(--divider-color); cursor: pointer; transition: all 0.12s;
    background: var(--secondary-background-color); color: var(--secondary-text-color);
  }
  .btn:hover { color: var(--primary-text-color); border-color: var(--primary-color); }
  .btn-primary { background: var(--primary-color); color: var(--text-primary-color, #fff); border-color: var(--primary-color); }
  .btn-primary:hover { opacity: 0.9; }
  .action-bar {
    display: flex; align-items: center; gap: 8px; padding: 10px 0;
    border-top: 1px solid var(--divider-color); margin-top: 8px;
  }
  .action-bar-label { font-size: 12px; color: var(--warning-color, #fbbf24); margin-right: auto; }
  .section-title { font-size: 11px; font-weight: 600; color: var(--secondary-text-color); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 10px; }
  .zone-legend { display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 10px; font-size: 12px; color: var(--secondary-text-color); }
  .legend-item { display: flex; align-items: center; gap: 4px; }
  .legend-num { font-weight: 700; color: var(--primary-text-color); font-size: 14px; }
  .sched-select {
    background: var(--card-background-color); border: 1px solid var(--divider-color);
    border-radius: 4px; color: var(--primary-text-color); font-size: 11px; padding: 3px 6px; outline: none;
  }
  .sched-select:focus { border-color: var(--primary-color); }
`;
