/**
 * Infinitude Profiles Card — comfort profile editing (temps + fan per activity per zone).
 * type: custom:infinitude-profiles-card
 */
import {
  InfinitudeBase, sharedStyles, html, css, nothing,
  ACTIVITIES, FAN_OPTIONS, CIRCLED,
  DEFAULT_HEAT_SP, DEFAULT_COOL_SP,
} from './shared.js';

class InfinitudeProfilesCard extends InfinitudeBase {

  static properties = {
    ...InfinitudeBase.baseProperties,
    _profileEdits: { state: true },
  };

  constructor() {
    super();
    this._profileEdits = {};
    this._savingProfs = false;
  }

  static getConfigElement() { return document.createElement('div'); }
  static getStubConfig() { return {}; }
  getCardSize() { return 6; }

  static styles = [sharedStyles, css`
    .card-pad { padding: 16px; }
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
  `];

  render() {
    if (!this.hass) return nothing;
    if (!this._registryLoaded) return this._renderLoading();

    const profiles = this._getProfilesData();
    if (!profiles.length) return html`<ha-card>
      <div class="card-pad" style="text-align:center;color:var(--secondary-text-color)">
        <ha-icon icon="mdi:tune-vertical" style="--mdc-icon-size:48px;opacity:0.3;margin-bottom:12px;display:block"></ha-icon>
        No profile data available.
      </div></ha-card>`;

    const multiZone = profiles.length > 1;
    const hasEdits = Object.keys(this._profileEdits).length > 0;
    return html`
      <ha-card>
        <div class="card-pad">
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
            </div>` : nothing}
        </div>
      </ha-card>`;
  }

}

if (!customElements.get('infinitude-profiles-card')) {
  customElements.define('infinitude-profiles-card', InfinitudeProfilesCard);
}
window.customCards = window.customCards || [];
if (!window.customCards.some(c => c.type === 'infinitude-profiles-card')) {
  window.customCards.push({
    type: 'infinitude-profiles-card',
    name: 'Infinitude Profiles',
    description: 'Comfort profile editing for Carrier/Bryant Infinity thermostat',
    preview: false,
  });
}
