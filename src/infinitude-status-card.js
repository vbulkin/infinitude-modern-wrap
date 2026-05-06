/**
 * Infinitude Status Card — system mode, summary stats, connectivity, WH hold.
 * type: custom:infinitude-status-card
 */
import {
  InfinitudeBase, sharedStyles, html, css, nothing,
  CARD_VERSION, ACTIVITIES, DURATION_OPTIONS,
} from './shared.js';

class InfinitudeStatusCard extends InfinitudeBase {

  static properties = {
    ...InfinitudeBase.baseProperties,
    _whHoldOpen:     { state: true },
    _whHoldActivity: { state: true },
    _whHoldDuration: { state: true },
    _whHoldCustom:   { state: true },
  };

  constructor() {
    super();
    this._whHoldOpen = false;
    this._whHoldActivity = 'home';
    this._whHoldDuration = '120';
    this._whHoldCustom = '';
  }

  static getStubConfig() { return {}; }
  getCardSize() { return 3; }

  static styles = [sharedStyles, css`
    .card-pad { padding: 16px; }
    .header {
      display: flex; align-items: center; gap: 8px; margin-bottom: 14px;
    }
    .header-title { font-size: 18px; font-weight: 500; color: var(--primary-text-color); }
  `];

  render() {
    if (!this.hass) return nothing;
    if (!this._registryLoaded) return this._renderLoading();
    const ent = this._findEntities();
    const { system, selects, climates } = ent;
    const mode = climates.length ? (this._st(climates[0])?.state || 'off') : 'off';
    const modes = ['off','heat','cool','heat_cool'];
    const lbl = { off:'Off', heat:'Heat', cool:'Cool', heat_cool:'Auto' };

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

    const infAvail = system.info ? this._st(system.info)?.state !== 'unavailable' : false;
    const sseConnected = system.info ? this._at(system.info, 'sse_connected') : null;
    const carrierStatus = system.info ? this._at(system.info, 'carrier_status') : null;
    const [infCls, infTitle] = this._infinitudeDot(infAvail, sseConnected);
    const [carCls, carTitle] = this._carrierDot(carrierStatus);

    return html`
      <ha-card>
        <div class="card-pad">
          <div class="header">
            <span class="header-title">infinitude</span>
            <span class="conn-dot ${infCls}" title="${infTitle}"></span>
            <span class="conn-dot ${carCls}" title="${carTitle}"></span>
            <span style="font-size:10px;color:var(--secondary-text-color);opacity:0.5">v${CARD_VERSION}</span>
          </div>
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
              <span class="summary-stat-val ${opStatus.toLowerCase().includes('heat') ? 'heat' : opStatus.toLowerCase().includes('cool') ? 'cool' : ''}">${opStatus || 'Idle'}</span>
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
              <div>
                <button class="btn" style="font-size:11px;padding:4px 12px" @click=${() => { this._whHoldOpen = true; }}>
                  <ha-icon icon="mdi:home-lock" style="--mdc-icon-size:14px;vertical-align:middle;margin-right:4px"></ha-icon>Set WH hold
                </button>
              </div>`}
          `}
        </div>
      </ha-card>`;
  }

}

if (!customElements.get('infinitude-status-card')) {
  customElements.define('infinitude-status-card', InfinitudeStatusCard);
}
window.customCards = window.customCards || [];
if (!window.customCards.some(c => c.type === 'infinitude-status-card')) {
  window.customCards.push({
    type: 'infinitude-status-card',
    name: 'Infinitude Status',
    description: 'System mode, stats, and whole-house hold for Carrier/Bryant Infinity',
    preview: false,
  });
}
