/**
 * Infinitude HVAC Card — composite tabbed dashboard.
 * Registers all sub-cards and provides a single-card full dashboard experience.
 * type: custom:infinitude-hvac-card
 *
 * Individual cards are also available:
 *   custom:infinitude-status-card    — system mode, stats, connectivity, WH hold
 *   custom:infinitude-zone-card      — single zone (config: { entity: "climate.xxx" })
 *   custom:infinitude-schedule-card  — weekly schedule editing
 *   custom:infinitude-profiles-card  — comfort profile editing
 */

// Import sub-cards so they register their custom elements in this bundle
import './infinitude-status-card.js';
import './infinitude-zone-card.js';
import './infinitude-schedule-card.js';
import './infinitude-profiles-card.js';

import {
  InfinitudeBase, sharedStyles, html, css, nothing,
  CARD_VERSION, DAYS, JS_DAY_MAP, ACTIVITIES, HOLD_ACTIVITIES, FAN_OPTIONS,
  DURATION_OPTIONS, CIRCLED, TIME_OPTIONS,
  MIN_HEAT_TEMP, MAX_HEAT_TEMP, MIN_COOL_TEMP, MAX_COOL_TEMP,
  DEFAULT_HEAT_SP, DEFAULT_COOL_SP,
} from './shared.js';

class InfinitudeHVACCard extends InfinitudeBase {

  static properties = {
    ...InfinitudeBase.baseProperties,
    _tab:           { state: true },
    _schedDay:      { state: true },
    _schedEdits:    { state: true },
    _profileEdits:  { state: true },
    _pendingTemps:  { state: true },
    _whHoldOpen:    { state: true },
    _whHoldActivity:{ state: true },
    _whHoldDuration:{ state: true },
    _whHoldCustom:  { state: true },
    _holdOpen:      { state: true },
    _holdActivity:  { state: true },
    _holdDuration:  { state: true },
    _holdCustom:    { state: true },
    _holdHtsp:      { state: true },
    _holdClsp:      { state: true },
    _holdFan:       { state: true },
  };

  constructor() {
    super();
    this._tab = 'status';
    this._schedDay = DAYS[JS_DAY_MAP[new Date().getDay()]];
    this._schedEdits = {};
    this._profileEdits = {};
    this._tempAdj = {};
    this._pendingTemps = {};
    this._whHoldOpen = false;
    this._whHoldActivity = 'home';
    this._whHoldDuration = '120';
    this._whHoldCustom = '';
    this._holdOpen = null;
    this._holdActivity = 'home';
    this._holdDuration = '120';
    this._holdCustom = '';
    this._holdHtsp = DEFAULT_HEAT_SP;
    this._holdClsp = DEFAULT_COOL_SP;
    this._holdFan = 'auto';
    this._saving = false;
    this._savingProfs = false;
  }

  connectedCallback() {
    super.connectedCallback();
    this._staleTimer = setInterval(() => this.requestUpdate(), 30000);
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    clearInterval(this._staleTimer);
  }

  static getStubConfig() { return {}; }
  getCardSize() { return 8; }

  static styles = [sharedStyles, css`
    .card-header {
      display: flex; align-items: center;
      padding: 12px 16px 8px; gap: 8px;
    }
    .header-left { display: flex; align-items: center; gap: 8px; }
    .header-title { font-size: 18px; font-weight: 500; color: var(--primary-text-color); }
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
    .zone-meta { display: flex; gap: 10px; padding: 0 14px 10px; font-size: 11px; color: var(--secondary-text-color); flex-wrap: wrap; }
    .meta-item { display: flex; align-items: center; gap: 4px; }
    .meta-val { color: var(--primary-text-color); font-weight: 500; }
    .zone-hold {
      display: flex; align-items: center; gap: 6px; padding: 8px 14px;
      background: rgba(251,191,36,0.06); border-top: 1px solid rgba(251,191,36,0.15); font-size: 11px;
    }
    .hold-label { color: var(--warning-color, #fbbf24); font-weight: 500; flex: 1; }
    .zone-hold-picker {
      padding: 8px 14px; border-top: 1px solid var(--divider-color);
      display: flex; flex-direction: column; gap: 8px; font-size: 11px;
    }
    .hold-picker-row { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
    .zone-actions { padding: 0 14px 10px; display: flex; gap: 8px; }
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
    .sched-name-compact { width: 28px; min-width: 28px; font-size: 14px; text-align: center; }
    .sched-temps { display: flex; gap: 6px; align-items: center; font-size: 12px; font-variant-numeric: tabular-nums; }
    .sched-toggle { cursor: pointer; display: flex; align-items: center; gap: 3px; }
    .sched-toggle input { cursor: pointer; }
    .sched-toggle span { font-size: 10px; color: var(--secondary-text-color); }
    .copy-bar { display: flex; align-items: center; gap: 8px; margin-top: 10px; font-size: 12px; color: var(--secondary-text-color); }
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
    .prof-name-compact { width: 28px; min-width: 28px; font-size: 14px; text-align: center; }
    .prof-fan { display: flex; align-items: center; gap: 4px; }
    .prof-fan-label { font-size: 10px; color: var(--secondary-text-color); }
    .zone-cond-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
    .zone-cond-dot.heating { background: var(--label-badge-red, #f97316); }
    .zone-cond-dot.cooling { background: var(--label-badge-blue, #38bdf8); }
    .zone-cond-dot.drying  { background: var(--accent-color, #a78bfa); }
    .zone-cond-dot.idle    { background: var(--secondary-text-color); opacity: 0.4; }
    .zone-activity-pill {
      font-size: 11px; font-weight: 500; padding: 2px 8px; border-radius: 20px;
      background: var(--secondary-background-color); color: var(--secondary-text-color);
    }
    .stale-warn {
      margin-top: 8px; padding: 6px 12px; margin-bottom: 8px;
      background: rgba(251,191,36,0.10); border: 1px solid rgba(251,191,36,0.28);
      border-radius: 8px; font-size: 12px; color: var(--warning-color, #fbbf24);
    }
  `];

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
          ${this._tab === 'status'   ? this._status(ent) : nothing}
          ${this._tab === 'schedule' ? this._sched()      : nothing}
          ${this._tab === 'profiles' ? this._profs()      : nothing}
        </div>
      </ha-card>`;
  }

  // ── Header ─────────────────────────────────────────────────────────────
  _hdr(ent) {
    const { system } = ent;
    const infAvail = system.info ? this._st(system.info)?.state !== 'unavailable' : false;
    const sseConnected = system.info ? this._at(system.info, 'sse_connected') : null;
    const carrierStatus = system.info ? this._at(system.info, 'carrier_status') : null;
    const [infCls, infTitle] = this._infinitudeDot(infAvail, sseConnected);
    const [carCls, carTitle] = this._carrierDot(carrierStatus);

    return html`
      <div class="header-left">
        <span class="header-title">infinitude</span>
        <span class="conn-dot ${infCls}" title="${infTitle}"></span>
        <span class="conn-dot ${carCls}" title="${carTitle}"></span>
        <span style="font-size:10px;color:var(--secondary-text-color);opacity:0.5">v${CARD_VERSION}</span>
      </div>`;
  }

  // ── Tabs ───────────────────────────────────────────────────────────────
  _tabs() {
    const tabs = ['status','schedule','profiles'];
    return html`${tabs.map(t => html`
      <div class="tab ${this._tab === t ? 'active' : ''}"
           @click=${() => { this._tab = t; }}>${t.charAt(0).toUpperCase() + t.slice(1)}</div>`)}`;
  }

  // ── Status tab ─────────────────────────────────────────────────────────
  _status(ent) {
    const { climates } = ent;
    if (!climates.length) return html`<div style="padding:20px;text-align:center;color:var(--secondary-text-color)">No zone entities found</div>`;
    return html`
      ${this._summaryStrip(ent)}
      <div class="zone-grid">${climates.map(eid => this._zoneCard(eid))}</div>`;
  }

  _summaryStrip(ent) {
    const { system, selects, climates } = ent;
    const mode = climates.length ? (this._st(climates[0])?.state || 'off') : 'off';
    const modes = ['off','heat','cool','heat_cool','fan_only'];
    const lbl = { off:'Off', heat:'Heat', cool:'Cool', heat_cool:'Auto', fan_only:'Fan' };

    const os = this._st(system.oat);
    let oat = '–';
    if (os?.state && os.state !== 'unavailable') oat = `${Math.round(Number(os.state))}°`;
    else if (climates.length) { const v = this._at(climates[0], 'outdoor_temperature'); if (v != null) oat = `${Math.round(Number(v))}°`; }

    const opS = this._st(system.opStatus);
    const opStatus = opS?.state && opS.state !== 'unavailable' ? opS.state : '';
    const humid = this._st(system.humidifier)?.state === 'on';
    const whS = this._st(selects.wholeHouse);
    const whHold = whS && whS.state !== 'off';
    const whOtmr = climates.length ? this._at(climates[0], 'whole_house_hold_until') : null;
    const rh = climates.length ? this._at(climates[0], 'current_humidity') : null;

    const anyHeating = climates.some(eid => this._at(eid, 'hvac_action') === 'heating');
    const anyCooling = climates.some(eid => this._at(eid, 'hvac_action') === 'cooling');
    const anyDrying  = climates.some(eid => this._at(eid, 'hvac_action') === 'drying');
    const effectiveStatus = anyHeating ? 'Heating' : anyCooling ? 'Cooling' : anyDrying ? 'Dehumidifying' : (opStatus || 'Idle');
    const statusCls = anyHeating ? 'heat' : anyCooling ? 'cool' : '';

    const reg = this._registryEntities || [];
    let maxReport = 0;
    for (const e of reg) {
      const ts = this.hass.states[e.entity_id]?.last_reported;
      if (!ts) continue;
      const t = Date.parse(ts);
      if (t > maxReport) maxReport = t;
    }
    const stale = maxReport > 0 && (Date.now() - maxReport) > 90000;

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
      <div class="summary-stats">
        <div class="summary-stat">
          <span class="summary-stat-label">Status</span>
          <span class="summary-stat-val ${statusCls}">${effectiveStatus}</span>
        </div>
        <div class="summary-divider"></div>
        <div class="summary-stat">
          <span class="summary-stat-label">Outdoor</span>
          <span class="summary-stat-val">${oat}</span>
        </div>
        <div class="summary-divider"></div>
        <div class="summary-stat">
          <span class="summary-stat-label">Humidity</span>
          <span class="summary-stat-val">${rh != null ? `${rh}%` : '–'}</span>
        </div>
        ${humid ? html`
          <div class="summary-divider"></div>
          <div class="summary-stat">
            <span class="summary-stat-label">Humidifier</span>
            <span class="summary-stat-val" style="color:var(--label-badge-blue,#38bdf8)">💧 On</span>
          </div>` : nothing}
      </div>
      ${stale ? html`<div class="stale-warn">⚠ Thermostat data is stale — system may be offline</div>` : nothing}
      ${whHold ? html`
        <div class="wh-hold" @click=${() => this._cancelWholeHouseHold()}>
          <ha-icon icon="mdi:home-lock" style="--mdc-icon-size:16px"></ha-icon>
          <span>Whole house: <strong>${whS.state}</strong>${whOtmr ? html` · <span style="opacity:0.85">${this._otmrRelative(whOtmr)}</span>` : nothing}</span>
          <span style="margin-left:auto;opacity:0.7">Tap to cancel</span>
        </div>` : html`
        ${this._whHoldOpen ? html`
          <div class="wh-set">
            <span class="wh-set-label">WH Hold</span>
            <div class="wh-pills">
              ${ACTIVITIES.map(a => html`
                <div class="wh-pill ${this._whHoldActivity === a ? 'active' : ''}"
                     @click=${() => { this._whHoldActivity = a; }}>${a}</div>`)}
            </div>
            <select class="hold-dur-select" @change=${(e) => { this._whHoldDuration = e.target.value; }}>
              ${DURATION_OPTIONS.map(d => html`<option value=${d.v} ?selected=${d.v === this._whHoldDuration}>${d.l}</option>`)}
            </select>
            ${this._whHoldDuration === 'custom' ? html`
              <input type="time" class="hold-time-input" step="900" .value=${this._whHoldCustom}
                     @change=${(e) => { this._whHoldCustom = e.target.value; }}>` : nothing}
            <button class="btn btn-primary" style="font-size:11px;padding:4px 12px" @click=${() => this._setWholeHouseHold()}>Apply</button>
            <button class="btn" style="font-size:11px;padding:4px 10px" @click=${() => { this._whHoldOpen = false; }}>Cancel</button>
          </div>` : html`
          <div style="margin-bottom:12px">
            <button class="btn" style="font-size:11px;padding:4px 12px" @click=${() => { this._whHoldOpen = true; }}>
              <ha-icon icon="mdi:home-lock" style="--mdc-icon-size:14px;vertical-align:middle;margin-right:4px"></ha-icon>Set WH hold
            </button>
          </div>`}
      `}`;
  }

  // ── Zone card (inline) ─────────────────────────────────────────────────
  _zoneCard(eid) {
    const s = this._st(eid);
    if (!s) return nothing;
    const a = s.attributes || {};
    const zid = this._zoneId(eid);
    const prefix = CIRCLED[parseInt(zid) - 1] || zid;
    const rawName = (a.friendly_name || eid).replace(/^Infinitude\s+/i, '').replace(/^infinitude_direct\s+/i, '');
    const name = prefix ? `${prefix} ${rawName}` : rawName;
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
    const holdUntil = a.hold_until;
    const holdIsOpen = this._holdOpen === eid;

    const pending = this._pendingTemps[eid];
    const isPending = this._hasPending(eid);
    const htsp = pending?.heat ?? a.target_temp_low ?? a.temperature ?? null;
    const clsp = pending?.cool ?? a.target_temp_high ?? (mode === 'cool' ? a.temperature : null) ?? null;

    const dotCls = ac || 'idle';
    const badgeLabel = action === 'drying' ? 'Dehumidifying' : al;

    return html`
      <div class="zone-card ${ac}">
        <div class="zone-top">
          <div style="display:flex;align-items:center;gap:8px">
            <span class="zone-cond-dot ${dotCls}" title="${badgeLabel}"></span>
            <span class="zone-name">${name}</span>
          </div>
          <span class="zone-activity-pill">${preset}</span>
        </div>
        <div class="zone-body">
          <div>
            <span class="temp-hero">${temp}</span><span class="temp-unit">°F</span>
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
          ${rh != null ? html`<span class="meta-item">RH <span class="meta-val">${rh}%</span></span>` : nothing}
          ${a.fan_mode ? html`<span class="meta-item">Fan <span class="meta-val">${a.fan_mode}</span></span>` : nothing}
          ${a.damper_position != null ? html`<span class="meta-item">Damper <span class="meta-val">${a.damper_position}%</span></span>` : nothing}
        </div>
        ${hasHold ? html`
          <div class="zone-hold">
            <span class="hold-label">Hold: ${holdActivity}${holdUntil ? ` · ${this._otmrRelative(holdUntil)}` : ''}</span>
            <button class="btn" style="font-size:11px;padding:3px 10px;color:var(--error-color,#f87171)" @click=${() => this._cancelHold(eid)}>Cancel</button>
          </div>` : nothing}
        ${holdIsOpen ? html`
          <div class="zone-hold-picker">
            <div class="hold-picker-row">
              <div class="wh-pills">
                ${HOLD_ACTIVITIES.map(act => html`
                  <div class="wh-pill ${this._holdActivity === act ? 'active' : ''}"
                       @click=${() => { this._holdActivity = act; if (act === 'manual') this._initHoldManual(eid); }}>${act}</div>`)}
              </div>
            </div>
            ${this._holdActivity === 'manual' ? html`
              <div class="hold-picker-row" style="gap:10px;flex-wrap:wrap">
                <div class="sp-row">
                  <button class="btn-adj" @click=${() => { this._holdHtsp = Math.max(MIN_HEAT_TEMP, this._holdHtsp - 1); }}>−</button>
                  <span class="sp-val sp-heat">${this._holdHtsp}°</span>
                  <button class="btn-adj" @click=${() => { this._holdHtsp = Math.min(MAX_HEAT_TEMP, this._holdHtsp + 1); }}>+</button>
                </div>
                <div class="sp-row">
                  <button class="btn-adj" @click=${() => { this._holdClsp = Math.max(MIN_COOL_TEMP, this._holdClsp - 1); }}>−</button>
                  <span class="sp-val sp-cool">${this._holdClsp}°</span>
                  <button class="btn-adj" @click=${() => { this._holdClsp = Math.min(MAX_COOL_TEMP, this._holdClsp + 1); }}>+</button>
                </div>
                <div style="display:flex;align-items:center;gap:4px">
                  <span style="font-size:10px;color:var(--secondary-text-color)">Fan</span>
                  <select class="hold-dur-select" style="width:auto" .value=${this._holdFan} @change=${(e) => { this._holdFan = e.target.value; }}>
                    <option value="auto">Auto</option>
                    <option value="low">Low</option>
                    <option value="med">Med</option>
                    <option value="high">High</option>
                  </select>
                </div>
              </div>` : nothing}
            <div class="hold-picker-row">
              <select class="hold-dur-select" @change=${(e) => { this._holdDuration = e.target.value; }}>
                ${DURATION_OPTIONS.map(d => html`<option value=${d.v} ?selected=${d.v === this._holdDuration}>${d.l}</option>`)}
              </select>
              ${this._holdDuration === 'custom' ? html`
                <input type="time" class="hold-time-input" step="900" .value=${this._holdCustom}
                       @change=${(e) => { this._holdCustom = e.target.value; }}>` : nothing}
            </div>
            <div class="hold-picker-row">
              <button class="btn btn-primary" style="font-size:11px;padding:4px 12px" @click=${() => this._setZoneHold(eid)}>Apply</button>
              <button class="btn" style="font-size:11px;padding:4px 10px" @click=${() => { this._holdOpen = null; }}>Cancel</button>
            </div>
          </div>` : hasHold ? nothing : html`
          <div class="zone-actions">
            <button class="btn" style="font-size:11px;padding:4px 12px" @click=${() => { this._holdActivity = preset !== '–' ? preset : 'home'; this._holdDuration = '120'; this._holdCustom = ''; if (this._holdActivity === 'manual') this._initHoldManual(eid); this._holdOpen = eid; }}>Set hold</button>
          </div>`}
      </div>`;
  }

  // ── Schedule tab ───────────────────────────────────────────────────────
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
    const zn = {}; const zi = {}; for (let i = 0; i < profiles.length; i++) { zn[profiles[i].id] = profiles[i].name; zi[profiles[i].id] = i; }
    let maxP = 0;
    for (const zid of zids) maxP = Math.max(maxP, (schedule[zid]?.[this._schedDay] || []).length);
    if (!maxP) maxP = 5;
    const hasEdits = Object.keys(this._schedEdits).length > 0;

    return html`
      <div class="section-title">Schedule</div>
      ${zids.length > 1 ? html`<div class="zone-legend">${zids.map((zid, i) => html`<span class="legend-item"><span class="legend-num">${CIRCLED[i] || i+1}</span> ${zn[zid] || `Zone ${zid}`}</span>`)}</div>` : nothing}
      <div class="sched-day-tabs">
        ${DAYS.map(d => html`
          <div class="day-tab ${d === this._schedDay ? 'active' : ''} ${d === today && d !== this._schedDay ? 'today' : ''}"
               @click=${() => { this._schedDay = d; }}>${d.slice(0,3)}</div>`)}
      </div>
      ${Array.from({length: maxP}, (_, pi) => this._periodCard(pi, zids, schedule, profiles, zn, zi))}
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

  // ── Profiles tab ───────────────────────────────────────────────────────
  _profs() {
    const profiles = this._getProfilesData();
    if (!profiles.length) return html`
      <div style="padding:20px;text-align:center;color:var(--secondary-text-color)">
        <ha-icon icon="mdi:tune-vertical" style="--mdc-icon-size:48px;opacity:0.3;margin-bottom:12px;display:block"></ha-icon>
        No profile data available. Waiting for thermostat data…
      </div>`;

    const multiZone = profiles.length > 1;
    const hasEdits = Object.keys(this._profileEdits).length > 0;
    return html`
      <div class="section-title">Comfort Profiles</div>
      ${multiZone ? html`<div class="zone-legend">${profiles.map((z, i) => html`<span class="legend-item"><span class="legend-num">${CIRCLED[i] || i+1}</span> ${z.name}</span>`)}</div>` : nothing}
      ${ACTIVITIES.map(actId => html`
        <div class="prof-card">
          <div class="prof-header">${actId}</div>
          ${profiles.map((zone, idx) => {
            const act = zone.activities?.[actId] || {};
            const ek = `${zone.id}_${actId}`;
            const ed = this._profileEdits[ek];
            const htsp = ed?.htsp ?? (act.htsp ? Math.round(Number(act.htsp) || DEFAULT_HEAT_SP) : DEFAULT_HEAT_SP);
            const clsp = ed?.clsp ?? (act.clsp ? Math.round(Number(act.clsp) || DEFAULT_COOL_SP) : DEFAULT_COOL_SP);
            const fan  = ed?.fan  ?? act.fan ?? 'low';
            const label = multiZone ? (CIRCLED[idx] || idx+1) : zone.name;
            return html`
              <div class="prof-line">
                <span class="prof-name ${multiZone ? 'prof-name-compact' : ''}">${label}</span>
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
                  <select class="sched-select" .value=${fan} @change=${(e) => this._profFan(zone.id, actId, e.target.value)}>
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
