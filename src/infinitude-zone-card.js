/**
 * Infinitude Zone Card — single zone: current temp, setpoints, hold, presets.
 * type: custom:infinitude-zone-card
 * config: { entity: "climate.infinitude_zone_1" }
 */
import {
  InfinitudeBase, sharedStyles, html, css, nothing,
  ACTIVITIES, HOLD_ACTIVITIES, DURATION_OPTIONS,
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
    this._holdHtsp = 68;
    this._holdClsp = 76;
    this._holdFan = 'auto';
  }

  static getConfigElement() { return document.createElement('div'); }
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
    .zone-preset-row {
      display: flex; gap: 0; border-radius: 6px; overflow: hidden;
      border: 1px solid var(--divider-color); margin-bottom: 10px;
    }
    .preset-btn {
      flex: 1; padding: 5px 0; font-size: 11px; font-weight: 600;
      text-align: center; border: none; border-right: 1px solid var(--divider-color);
      background: var(--secondary-background-color); color: var(--secondary-text-color);
      cursor: pointer; transition: all 0.12s; text-transform: capitalize;
    }
    .preset-btn:last-child { border-right: none; }
    .preset-btn:hover, .preset-btn.active { background: var(--primary-color); color: var(--text-primary-color, #fff); }
    ha-card.heating { border-left: 3px solid var(--label-badge-red, #f97316); }
    ha-card.cooling { border-left: 3px solid var(--label-badge-blue, #38bdf8); }
    ha-card.drying  { border-left: 3px solid var(--accent-color, #a78bfa); }
  `];

  render() {
    if (!this.hass) return nothing;
    if (!this._registryLoaded) return this._renderLoading();
    const eid = this._config.entity;
    if (!eid) return html`<ha-card><div class="card-pad" style="color:var(--secondary-text-color)">No entity configured</div></ha-card>`;
    const s = this._st(eid);
    if (!s) return html`<ha-card><div class="card-pad" style="color:var(--secondary-text-color)">Entity unavailable</div></ha-card>`;

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
    const holdUntil = a.hold_until;

    const pending = this._pendingTemps[eid];
    const isPending = this._hasPending(eid);
    const htsp = pending?.heat ?? a.target_temp_low ?? a.temperature ?? null;
    const clsp = pending?.cool ?? a.target_temp_high ?? (mode === 'cool' ? a.temperature : null) ?? null;

    return html`
      <ha-card class="${ac}">
        <div class="card-pad">
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
                    <button class="btn-adj" @click=${() => { this._holdHtsp = Math.max(50, this._holdHtsp - 1); }}>−</button>
                    <span class="sp-val sp-heat">${this._holdHtsp}°</span>
                    <button class="btn-adj" @click=${() => { this._holdHtsp = Math.min(90, this._holdHtsp + 1); }}>+</button>
                  </div>
                  <div class="sp-row">
                    <button class="btn-adj" @click=${() => { this._holdClsp = Math.max(60, this._holdClsp - 1); }}>−</button>
                    <span class="sp-val sp-cool">${this._holdClsp}°</span>
                    <button class="btn-adj" @click=${() => { this._holdClsp = Math.min(99, this._holdClsp + 1); }}>+</button>
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

  // ── Temperature adjustment with debounce ────────────────────────────
  _adjustTemp(eid, delta, sp) {
    const s = this._st(eid); if (!s) return;
    const a = s.attributes || {};
    const adj = this._tempAdj[eid] || (this._tempAdj[eid] = {});

    const curHeat = adj.heat ?? a.target_temp_low ?? a.temperature ?? 68;
    const curCool = adj.cool ?? a.target_temp_high ?? (s.state === 'cool' ? a.temperature : null) ?? 76;

    if (sp === 'heat') adj.heat = Math.max(50, Math.min(90, Math.round(curHeat) + delta));
    else               adj.cool = Math.max(60, Math.min(99, Math.round(curCool) + delta));

    this._pendingTemps = { ...this._pendingTemps, [eid]: { heat: adj.heat, cool: adj.cool } };

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

    if (adj.heat !== snapH || adj.cool !== snapC) {
      adj.timer = setTimeout(() => this._commitAdj(eid), 400);
      return;
    }

    adj.heat = null; adj.cool = null; adj.timer = null;
    adj.graceUntil = Date.now() + 30000;
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
    this._holdOpen = false;
  }

  _initHoldManual(eid) {
    const zid = this._zoneId(eid);
    const act = (this._getProfilesData().find(z => z.id === zid)?.activities?.manual) || {};
    this._holdHtsp = act.htsp ? Math.round(Number(act.htsp) || 68) : 68;
    this._holdClsp = act.clsp ? Math.round(Number(act.clsp) || 76) : 76;
    this._holdFan  = act.fan || 'auto';
  }
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
