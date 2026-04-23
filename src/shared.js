/**
 * Shared utilities, constants, and base class for Infinitude cards.
 */
import { LitElement, html, css, nothing } from 'lit';

export { LitElement, html, css, nothing };

export const CARD_VERSION = '2.0.0-alpha.6';
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

// Temperature bounds (must match Python const.py)
export const MIN_HEAT_TEMP = 50;
export const MAX_HEAT_TEMP = 90;
export const MIN_COOL_TEMP = 60;
export const MAX_COOL_TEMP = 99;
export const DEFAULT_HEAT_SP = 68;
export const DEFAULT_COOL_SP = 76;

// Debounce / cleanup timers (ms)
export const TEMP_DEBOUNCE_MS = 800;
export const TEMP_RETRY_MS = 400;
export const TEMP_CLEANUP_MS = 2000;
export const SAVE_CLEANUP_MS = 500;

/**
 * Base class providing registry/entity discovery, state helpers, service calls,
 * and shared logic methods used by multiple cards.
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
    this._cachedEntities = null;
    this._cachedEntitiesHass = null;
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
    if (changed.has('hass')) {
      this._cachedEntities = null;
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
    this._cachedEntities = null;
  }

  // ── Entity discovery (cached per hass update) ──────────────────────────
  _findEntities() {
    if (this._cachedEntities && this._cachedEntitiesHass === this.hass) return this._cachedEntities;
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
    const zidOf = eid => {
      const r = reg.find(e => e.entity_id === eid);
      return parseInt((r?.unique_id || '').replace(/^infinitude_/, '')) || 0;
    };
    climates.sort((a, b) => zidOf(a) - zidOf(b));
    const result = { climates, sensors, selects, system };
    this._cachedEntities = result;
    this._cachedEntitiesHass = this.hass;
    return result;
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

  // ── Temperature adjustment with debounce ────────────────────────────────
  _adjustTemp(eid, delta, sp) {
    const s = this._st(eid); if (!s) return;
    const a = s.attributes || {};
    if (!this._tempAdj) this._tempAdj = {};
    const adj = this._tempAdj[eid] || (this._tempAdj[eid] = {});
    const curHeat = adj.heat ?? a.target_temp_low ?? a.temperature ?? DEFAULT_HEAT_SP;
    const curCool = adj.cool ?? a.target_temp_high ?? (s.state === 'cool' ? a.temperature : null) ?? DEFAULT_COOL_SP;
    if (sp === 'heat') adj.heat = Math.max(MIN_HEAT_TEMP, Math.min(MAX_HEAT_TEMP, Math.round(curHeat) + delta));
    else               adj.cool = Math.max(MIN_COOL_TEMP, Math.min(MAX_COOL_TEMP, Math.round(curCool) + delta));
    this._pendingTemps = { ...this._pendingTemps, [eid]: { heat: adj.heat, cool: adj.cool } };
    if (!adj.committing) {
      clearTimeout(adj.timer);
      adj.timer = setTimeout(() => this._commitAdj(eid), TEMP_DEBOUNCE_MS);
    }
  }

  async _commitAdj(eid) {
    if (!this._tempAdj) return;
    const adj = this._tempAdj[eid];
    if (!adj || adj.committing) return;
    adj.committing = true;
    const s = this._st(eid);
    const a = s?.attributes || {};
    const snapH = adj.heat, snapC = adj.cool;
    const htsp = snapH ?? Math.round(a.target_temp_low ?? a.temperature ?? DEFAULT_HEAT_SP);
    const clsp = snapC ?? Math.round(a.target_temp_high ?? (s?.state === 'cool' ? a.temperature : null) ?? DEFAULT_COOL_SP);
    const mode = s?.state || 'off';
    const d = { entity_id: eid };
    if (mode === 'heat_cool') { d.target_temp_low = htsp; d.target_temp_high = clsp; }
    else if (mode === 'heat') { d.temperature = htsp; }
    else if (mode === 'cool') { d.temperature = clsp; }
    else { d.target_temp_low = htsp; d.target_temp_high = clsp; }
    try { await this.hass.callService('climate', 'set_temperature', d); }
    catch (e) { console.error('set_temperature failed', e); }
    adj.committing = false;
    if (adj.heat !== snapH || adj.cool !== snapC) {
      adj.timer = setTimeout(() => this._commitAdj(eid), TEMP_RETRY_MS);
      return;
    }
    adj.heat = null; adj.cool = null; adj.timer = null;
    setTimeout(() => {
      if (!this._tempAdj[eid]?.heat && !this._tempAdj[eid]?.cool) {
        const { [eid]: _, ...rest } = this._pendingTemps;
        this._pendingTemps = rest;
      }
    }, TEMP_CLEANUP_MS);
  }

  _hasPending(eid) {
    const adj = this._tempAdj?.[eid];
    return adj && (adj.heat != null || adj.cool != null || adj.committing);
  }

  // ── Hold controls ──────────────────────────────────────────────────────
  _cancelHold(eid) {
    const zoneId = this._zoneId(eid);
    if (!zoneId) return;
    this._svc('infinitude_direct', 'cancel_hold', { zone_id: zoneId });
  }

  _setZoneHold(eid) {
    const zoneId = this._zoneId(eid);
    if (!zoneId) return;
    const until = this._resolveUntil(this._holdDuration, this._holdCustom);
    if (until === null) return;
    if (this._holdActivity === 'manual') {
      this._svc('infinitude_direct', 'set_profile', {
        zone_id: zoneId, activity: 'manual',
        htsp: this._holdHtsp, clsp: this._holdClsp, fan: this._holdFan,
      });
    }
    this._svc('infinitude_direct', 'set_hold', {
      zone_id: zoneId, activity: this._holdActivity,
      ...(until !== undefined && { until }),
    });
    this._holdOpen = null;
  }

  _initHoldManual(eid) {
    const zid = this._zoneId(eid);
    const act = (this._getProfilesData().find(z => z.id === zid)?.activities?.manual) || {};
    this._holdHtsp = act.htsp ? Math.round(Number(act.htsp) || DEFAULT_HEAT_SP) : DEFAULT_HEAT_SP;
    this._holdClsp = act.clsp ? Math.round(Number(act.clsp) || DEFAULT_COOL_SP) : DEFAULT_COOL_SP;
    this._holdFan  = act.fan || 'auto';
  }

  _setWholeHouseHold() {
    const until = this._resolveUntil(this._whHoldDuration, this._whHoldCustom);
    if (until === null) return;
    this._svc('infinitude_direct', 'set_whole_house_hold', {
      activity: this._whHoldActivity,
      ...(until !== undefined && { until }),
    });
    this._whHoldOpen = false;
  }

  _cancelWholeHouseHold() {
    this._svc('infinitude_direct', 'cancel_whole_house_hold', {});
  }

  // ── Schedule logic ─────────────────────────────────────────────────────
  _periodCard(pi, zids, schedule, profiles, zn, zi) {
    const multiZone = zids.length > 1;
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
          const htsp = ap?.htsp ? Math.round(Number(ap.htsp) || 0) : '–';
          const clsp = ap?.clsp ? Math.round(Number(ap.clsp) || 0) : '–';
          const label = multiZone ? (CIRCLED[zi[zid]] ?? zid) : (zn[zid] || `Zone ${zid}`);
          return html`
            <div class="sched-line ${enabled ? '' : 'disabled'}">
              <span class="sched-name ${multiZone ? 'sched-name-compact' : ''}">${label}</span>
              <select class="sched-select" .value=${act} @change=${(e) => this._schedEdit(zid, pi, 'act', e.target.value)}>
                ${ACTIVITIES.map(a => html`<option value=${a} ?selected=${a === act}>${a}</option>`)}
              </select>
              <select class="sched-select" .value=${time} @change=${(e) => this._schedEdit(zid, pi, 'time', e.target.value)}>
                ${TIME_OPTIONS.map(o => html`<option value=${o.v} ?selected=${o.v === time}>${o.l}</option>`)}
              </select>
              <label class="sched-toggle">
                <input type="checkbox" .checked=${enabled}
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
    if (this._saving) return;
    this._saving = true;
    const edits = { ...this._schedEdits };
    try {
      const sch = this._getScheduleData();
      for (const zid of Object.keys(sch)) {
        const prog = DAYS.map(day => ({
          id: day,
          period: (sch[zid]?.[day] || []).map((p, pi) => {
            const ed = edits[`${zid}_${day}_${pi}`];
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
    } finally {
      setTimeout(() => {
        const cur = this._schedEdits;
        const kept = {};
        for (const k of Object.keys(cur)) {
          if (!(k in edits) || cur[k] !== edits[k]) kept[k] = cur[k];
        }
        this._schedEdits = kept;
        this._saving = false;
      }, SAVE_CLEANUP_MS);
    }
  }

  // ── Profile logic ──────────────────────────────────────────────────────
  _profAdj(zid, actId, field, delta) {
    const ek = `${zid}_${actId}`;
    const act = (this._getProfilesData().find(z => z.id === zid)?.activities?.[actId]) || {};
    const prev = this._profileEdits[ek] || {};
    const curH = prev.htsp ?? (act.htsp ? Math.round(Number(act.htsp) || DEFAULT_HEAT_SP) : DEFAULT_HEAT_SP);
    const curC = prev.clsp ?? (act.clsp ? Math.round(Number(act.clsp) || DEFAULT_COOL_SP) : DEFAULT_COOL_SP);
    const min = field === 'htsp' ? MIN_HEAT_TEMP : MIN_COOL_TEMP;
    const max = field === 'htsp' ? MAX_HEAT_TEMP : MAX_COOL_TEMP;
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
      htsp: prev.htsp ?? (act.htsp ? Math.round(Number(act.htsp) || DEFAULT_HEAT_SP) : DEFAULT_HEAT_SP),
      clsp: prev.clsp ?? (act.clsp ? Math.round(Number(act.clsp) || DEFAULT_COOL_SP) : DEFAULT_COOL_SP),
      fan,
    }};
  }

  async _saveProfs() {
    if (this._savingProfs) return;
    this._savingProfs = true;
    const edits = { ...this._profileEdits };
    try {
      for (const ed of Object.values(edits)) {
        const d = { zone_id: ed.zone_id, activity: ed.activity, htsp: ed.htsp, clsp: ed.clsp };
        if (ed.fan) d.fan = ed.fan;
        await this._svc('infinitude_direct', 'set_profile', d);
      }
    } finally {
      setTimeout(() => {
        const cur = this._profileEdits;
        const kept = {};
        for (const k of Object.keys(cur)) {
          if (!(k in edits) || cur[k] !== edits[k]) kept[k] = cur[k];
        }
        this._profileEdits = kept;
        this._savingProfs = false;
      }, SAVE_CLEANUP_MS);
    }
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
    display: flex; align-items: center; gap: 20px; flex-wrap: wrap; margin-bottom: 14px;
  }
  .summary-stat { display: flex; align-items: baseline; gap: 6px; }
  .summary-stat-label { font-size: 10px; color: var(--secondary-text-color); text-transform: uppercase; letter-spacing: 0.5px; }
  .summary-stat-val { font-size: 16px; font-weight: 500; color: var(--primary-text-color); }
  .summary-stat-val.heat { color: var(--label-badge-red, #f97316); }
  .summary-stat-val.cool { color: var(--label-badge-blue, #38bdf8); }
  .summary-divider { width: 1px; height: 18px; background: var(--divider-color); flex-shrink: 0; }
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

  @media (max-width: 520px) {
    .sched-line { padding: 6px 8px !important; gap: 4px !important; }
    .sched-name { width: 68px !important; min-width: 52px !important; font-size: 11px !important; }
    .sched-name-compact { width: 24px !important; min-width: 24px !important; font-size: 13px !important; }
    .sched-select { padding: 2px 4px; font-size: 10px; }
    .sched-toggle span { display: none; }
    .sched-temps { gap: 4px !important; font-size: 11px !important; }
    .prof-line { padding: 8px 8px !important; gap: 6px !important; }
    .prof-name { width: 68px !important; min-width: 52px !important; font-size: 11px !important; }
    .prof-name-compact { width: 24px !important; min-width: 24px !important; font-size: 13px !important; }
    .prof-fan-label { display: none; }
    .btn-adj { width: 22px; height: 22px; font-size: 13px; border-radius: 6px; }
    .sp-val { min-width: 22px; }
    .sp-row { gap: 2px; }
  }
`;
