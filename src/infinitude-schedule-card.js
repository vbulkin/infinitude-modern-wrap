/**
 * Infinitude Schedule Card — weekly schedule editing.
 * type: custom:infinitude-schedule-card
 */
import {
  InfinitudeBase, sharedStyles, html, css, nothing,
  DAYS, JS_DAY_MAP, ACTIVITIES, CIRCLED, TIME_OPTIONS,
} from './shared.js';

class InfinitudeScheduleCard extends InfinitudeBase {

  static properties = {
    ...InfinitudeBase.baseProperties,
    _schedDay:   { state: true },
    _schedEdits: { state: true },
  };

  constructor() {
    super();
    this._schedDay = DAYS[JS_DAY_MAP[new Date().getDay()]];
    this._schedEdits = {};
  }

  static getConfigElement() { return document.createElement('div'); }
  static getStubConfig() { return {}; }
  getCardSize() { return 6; }

  static styles = [sharedStyles, css`
    .card-pad { padding: 16px; }
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
  `];

  render() {
    if (!this.hass) return nothing;
    if (!this._registryLoaded) return this._renderLoading();

    const schedule = this._getScheduleData();
    const profiles = this._getProfilesData();
    const zids = Object.keys(schedule);
    if (!zids.length) return html`<ha-card>
      <div class="card-pad" style="text-align:center;color:var(--secondary-text-color)">
        <ha-icon icon="mdi:calendar-clock" style="--mdc-icon-size:48px;opacity:0.3;margin-bottom:12px;display:block"></ha-icon>
        No schedule data available.
      </div></ha-card>`;

    const today = DAYS[JS_DAY_MAP[new Date().getDay()]];
    const zn = {}; const zi = {}; for (let i = 0; i < profiles.length; i++) { zn[profiles[i].id] = profiles[i].name; zi[profiles[i].id] = i; }
    let maxP = 0;
    for (const zid of zids) maxP = Math.max(maxP, (schedule[zid]?.[this._schedDay] || []).length);
    if (!maxP) maxP = 5;
    const hasEdits = Object.keys(this._schedEdits).length > 0;

    return html`
      <ha-card>
        <div class="card-pad">
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
            </div>` : nothing}
        </div>
      </ha-card>`;
  }

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
}

if (!customElements.get('infinitude-schedule-card')) {
  customElements.define('infinitude-schedule-card', InfinitudeScheduleCard);
}
window.customCards = window.customCards || [];
if (!window.customCards.some(c => c.type === 'infinitude-schedule-card')) {
  window.customCards.push({
    type: 'infinitude-schedule-card',
    name: 'Infinitude Schedule',
    description: 'Weekly schedule editing for Carrier/Bryant Infinity thermostat',
    preview: false,
  });
}
