/**
 * Infinitude Zone Card — single zone: current temp, setpoints, hold, presets.
 * type: custom:infinitude-zone-card
 * config: { entity: "climate.infinitude_zone_1" }
 */
import {
  LitElement, InfinitudeBase, sharedStyles, html, css, nothing,
  ACTIVITIES, HOLD_ACTIVITIES, DURATION_OPTIONS, CIRCLED,
  MIN_HEAT_TEMP, MAX_HEAT_TEMP, MIN_COOL_TEMP, MAX_COOL_TEMP,
  DEFAULT_HEAT_SP, DEFAULT_COOL_SP,
} from './shared.js';

class InfinitudeZoneCard extends InfinitudeBase {

  static properties = {
    ...InfinitudeBase.baseProperties,
    _pendingTemps:  { state: true },
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
    this._pendingTemps = {};
    this._tempAdj = {};
    this._holdOpen = false;
    this._holdActivity = 'home';
    this._holdDuration = '120';
    this._holdCustom = '';
    this._holdHtsp = DEFAULT_HEAT_SP;
    this._holdClsp = DEFAULT_COOL_SP;
    this._holdFan = 'auto';
  }

  static getConfigElement() { return document.createElement('infinitude-zone-card-editor'); }
  static getStubConfig() { return { entity: '' }; }
  getCardSize() { return 4; }

  static styles = [sharedStyles, css`
    .card-pad { padding: 14px; }
    .zone-top { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; }
    .zone-name { font-size: 14px; font-weight: 600; color: var(--primary-text-color); }
    .zone-badge {
      font-size: 10px; font-weight: 600; text-transform: uppercase;
      padding: 2px 8px; border-radius: 12px;
      background: var(--secondary-background-color); color: var(--secondary-text-color);
    }
    .zone-badge.heating { background: rgba(249,115,22,0.15); color: var(--label-badge-red, #f97316); }
    .zone-badge.cooling { background: rgba(56,189,248,0.15); color: var(--label-badge-blue, #38bdf8); }
    .zone-badge.drying  { background: rgba(167,139,250,0.15); color: var(--accent-color, #a78bfa); }
    .zone-body { display: flex; align-items: center; padding: 4px 0 12px; gap: 16px; }
    .temp-hero { font-size: 42px; font-weight: 300; line-height: 1; color: var(--primary-text-color); font-variant-numeric: tabular-nums; }
    .temp-unit { font-size: 14px; color: var(--secondary-text-color); }
    .zone-sp { display: flex; flex-direction: column; gap: 6px; }
    .zone-meta { display: flex; gap: 10px; padding-bottom: 10px; font-size: 11px; color: var(--secondary-text-color); flex-wrap: wrap; }
    .meta-item { display: flex; align-items: center; gap: 4px; }
    .meta-val { color: var(--primary-text-color); font-weight: 500; }
    .zone-hold {
      display: flex; align-items: center; gap: 6px; padding: 8px 0;
      border-top: 1px solid rgba(251,191,36,0.15); font-size: 11px;
    }
    .hold-label { color: var(--warning-color, #fbbf24); font-weight: 500; flex: 1; }
    .zone-hold-picker {
      padding: 8px 0; border-top: 1px solid var(--divider-color);
      display: flex; flex-direction: column; gap: 8px; font-size: 11px;
    }
    .hold-picker-row { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
    .zone-actions { padding: 0 0 4px; display: flex; gap: 8px; }
    ha-card.heating { border-left: 3px solid var(--label-badge-red, #f97316); }
    ha-card.cooling { border-left: 3px solid var(--label-badge-blue, #38bdf8); }
    ha-card.drying  { border-left: 3px solid var(--accent-color, #a78bfa); }
    .zone-cond-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
    .zone-cond-dot.heating { background: var(--label-badge-red, #f97316); }
    .zone-cond-dot.cooling { background: var(--label-badge-blue, #38bdf8); }
    .zone-cond-dot.drying  { background: var(--accent-color, #a78bfa); }
    .zone-cond-dot.idle    { background: var(--secondary-text-color); opacity: 0.4; }
    .zone-activity-pill {
      font-size: 11px; font-weight: 500; padding: 2px 8px; border-radius: 20px;
      background: var(--secondary-background-color); color: var(--secondary-text-color);
    }
  `];

  render() {
    if (!this.hass) return nothing;
    if (!this._registryLoaded) return this._renderLoading();
    const eid = this._config.entity;
    if (!eid) return html`<ha-card><div class="card-pad" style="color:var(--secondary-text-color)">No entity configured</div></ha-card>`;
    const s = this._st(eid);
    if (!s) return html`<ha-card><div class="card-pad" style="color:var(--secondary-text-color)">Entity unavailable</div></ha-card>`;

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

    const pending = this._pendingTemps[eid];
    const isPending = this._hasPending(eid);
    const htsp = pending?.heat ?? a.target_temp_low ?? a.temperature ?? null;
    const clsp = pending?.cool ?? a.target_temp_high ?? (mode === 'cool' ? a.temperature : null) ?? null;

    const dotCls = ac || 'idle';

    return html`
      <ha-card class="${ac}">
        <div class="card-pad">
          <div class="zone-top">
            <div style="display:flex;align-items:center;gap:8px">
              <span class="zone-cond-dot ${dotCls}" title="${action === 'drying' ? 'Dehumidifying' : al}"></span>
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
          ${this._holdOpen ? html`
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
                <button class="btn" style="font-size:11px;padding:4px 10px" @click=${() => { this._holdOpen = false; }}>Cancel</button>
              </div>
            </div>` : hasHold ? nothing : html`
            <div class="zone-actions">
              <button class="btn" style="font-size:11px;padding:4px 12px" @click=${() => { this._holdActivity = preset !== '–' ? preset : 'home'; this._holdDuration = '120'; this._holdCustom = ''; if (this._holdActivity === 'manual') this._initHoldManual(eid); this._holdOpen = true; }}>Set hold</button>
            </div>`}
        </div>
      </ha-card>`;
  }

}

class InfinitudeZoneCardEditor extends LitElement {
  static properties = {
    hass: { attribute: false },
    _config: { state: true },
    _infEntities: { state: true },
  };

  constructor() {
    super();
    this._infEntities = null;
  }

  setConfig(config) { this._config = config || {}; }

  async _loadRegistry() {
    if (this._infEntities || !this.hass) return;
    try {
      const all = await this.hass.callWS({ type: 'config/entity_registry/list' });
      this._infEntities = new Set(
        (all || [])
          .filter(e => e.platform === 'infinitude_direct' && e.entity_id.startsWith('climate.'))
          .map(e => e.entity_id)
      );
    } catch (e) {
      this._infEntities = new Set();
    }
  }

  updated(changed) {
    if (changed.has('hass') && !this._infEntities) this._loadRegistry();
  }

  _entityChanged(ev) {
    ev.stopPropagation();
    if (!this._config) return;
    const value = ev.target?.value ?? '';
    if (value === this._config.entity) return;
    const newConfig = { ...this._config, entity: value };
    this.dispatchEvent(new CustomEvent('config-changed', {
      detail: { config: newConfig },
      bubbles: true, composed: true,
    }));
  }

  _label(eid) {
    const st = this.hass.states[eid];
    const fn = st?.attributes?.friendly_name;
    return fn ? `${fn}  —  ${eid}` : eid;
  }

  render() {
    if (!this.hass) return html``;
    const entities = this._infEntities ? [...this._infEntities].sort() : [];
    const current = this._config?.entity || '';
    return html`
      <div style="padding:8px 0">
        <label style="display:block;font-size:12px;color:var(--secondary-text-color);margin-bottom:6px">Zone entity</label>
        <select
          style="width:100%;padding:8px 10px;background:var(--card-background-color);border:1px solid var(--divider-color);border-radius:4px;color:var(--primary-text-color);font-size:14px"
          .value=${current}
          @change=${this._entityChanged}>
          <option value="" ?selected=${!current}>— select a zone —</option>
          ${entities.map(e => html`<option value=${e} ?selected=${e === current}>${this._label(e)}</option>`)}
        </select>
        <div style="font-size:11px;color:var(--secondary-text-color);margin-top:6px">
          ${entities.length
            ? html`${entities.length} climate entit${entities.length === 1 ? 'y' : 'ies'} from the Infinitude Direct integration.`
            : html`No Infinitude Direct climate entities found.`}
        </div>
      </div>
    `;
  }
}

if (!customElements.get('infinitude-zone-card-editor')) {
  customElements.define('infinitude-zone-card-editor', InfinitudeZoneCardEditor);
}
if (!customElements.get('infinitude-zone-card')) {
  customElements.define('infinitude-zone-card', InfinitudeZoneCard);
}
window.customCards = window.customCards || [];
if (!window.customCards.some(c => c.type === 'infinitude-zone-card')) {
  window.customCards.push({
    type: 'infinitude-zone-card',
    name: 'Infinitude Zone',
    description: 'Single zone control for Carrier/Bryant Infinity thermostat',
    preview: false,
  });
}
