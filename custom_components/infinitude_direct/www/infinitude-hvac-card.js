/**
 * Infinitude HVAC Card — Custom Lovelace card for Carrier/Bryant Infinity thermostats.
 * Provides zone status, schedule editing, and comfort profile management.
 * Uses HA entity states + services for all data access.
 */

const DAYS = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday'];
const JS_DAY_MAP = [6,0,1,2,3,4,5];
const ACTIVITIES = ['home','away','sleep','wake'];
const ACT_COLORS = {
  home: 'var(--info-color, #4f8ef7)',
  away: 'var(--disabled-color, #6b7280)',
  sleep: 'var(--accent-color, #a78bfa)',
  wake: 'var(--warning-color, #fbbf24)',
  manual: 'var(--success-color, #34d399)',
};
const FAN_OPTIONS = ['off','low','med','high'];

class InfinitudeHVACCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this._config = {};
    this._hass = null;
    this._tab = 'zones';
    this._schedDay = DAYS[JS_DAY_MAP[new Date().getDay()]];
    this._schedEdits = {};
    this._profileEdits = {};
    this._rendered = false;
    this._stateHash = '';
  }

  static getConfigElement() { return document.createElement('div'); }

  static getStubConfig() {
    return {};
  }

  setConfig(config) {
    this._config = config;
  }

  set hass(hass) {
    this._hass = hass;
    const hash = this._computeStateHash();
    if (hash !== this._stateHash) {
      this._stateHash = hash;
      this._render();
    }
  }

  getCardSize() { return 8; }

  _computeStateHash() {
    if (!this._hass) return '';
    const entities = this._findEntities();
    const parts = [];
    for (const eid of entities.climates) {
      const s = this._hass.states[eid];
      if (s) parts.push(eid, s.state, s.last_changed);
    }
    for (const eid of Object.keys(this._hass.states)) {
      if (eid.includes('infinitude') || eid.includes('whole_house')) {
        const s = this._hass.states[eid];
        if (s) parts.push(eid, s.state, s.last_changed);
      }
    }
    return parts.join('|');
  }

  // ── Entity Discovery ────────────────────────────────────────────────────
  _findEntities() {
    if (!this._hass) return { climates: [], sensors: {}, selects: {}, system: {} };
    const states = this._hass.states;
    const climates = [];
    const sensors = { damper: {}, fan: {} };
    const selects = {};
    const system = {};

    // If user specified entities in config, use those
    if (this._config.climate_entities) {
      for (const eid of this._config.climate_entities) {
        if (states[eid]) climates.push(eid);
      }
    }

    // Auto-discover: climate entities with outdoor_temperature attribute
    // (unique fingerprint of Infinitude climate entities)
    if (!climates.length) {
      for (const eid of Object.keys(states)) {
        if (eid.startsWith('climate.') && states[eid].attributes?.outdoor_temperature !== undefined) {
          climates.push(eid);
        }
      }
    }

    // Find related entities by name patterns or explicit config
    for (const eid of Object.keys(states)) {
      if (eid.includes('infinitude') || eid.includes('whole_house')) {
        if (eid.includes('_damper')) sensors.damper[eid] = states[eid];
        else if (eid.includes('_fan') && eid.startsWith('sensor.')) sensors.fan[eid] = states[eid];
        else if (eid.includes('humidifier')) system.humidifier = eid;
        else if (eid.includes('oat') || eid.includes('outdoor_temperature')) system.oat = eid;
        else if (eid.includes('op_status') || eid.includes('operation_status')) system.opStatus = eid;
        else if (eid.includes('system_info')) system.info = eid;
        else if (eid.includes('whole_house') && eid.startsWith('select.')) selects.wholeHouse = eid;
      }
    }

    // Sort climates by entity_id for consistent ordering
    climates.sort();
    return { climates, sensors, selects, system };
  }

  _getState(entityId) {
    if (!this._hass || !entityId) return null;
    return this._hass.states[entityId] || null;
  }

  _getAttr(entityId, attr) {
    const s = this._getState(entityId);
    return s?.attributes?.[attr];
  }

  // ── Schedule/Profile Data ───────────────────────────────────────────────
  _getScheduleData() {
    const { system } = this._findEntities();
    if (!system.info) return {};
    const raw = this._getAttr(system.info, 'schedule');
    if (!raw) return {};
    try { return JSON.parse(raw); } catch { return {}; }
  }

  _getProfilesData() {
    const { system } = this._findEntities();
    if (!system.info) return [];
    const raw = this._getAttr(system.info, 'profiles');
    if (!raw) return [];
    try { return JSON.parse(raw); } catch { return []; }
  }

  // ── Service Calls ──────────────────────────────────────────────────────
  async _callService(domain, service, data) {
    if (!this._hass) return;
    try {
      await this._hass.callService(domain, service, data);
    } catch (e) {
      console.error(`Service call failed: ${domain}.${service}`, e);
    }
  }

  async _setHvacMode(entityId, mode) {
    await this._callService('climate', 'set_hvac_mode', {
      entity_id: entityId, hvac_mode: mode,
    });
  }

  async _setPreset(entityId, preset) {
    await this._callService('climate', 'set_preset_mode', {
      entity_id: entityId, preset_mode: preset,
    });
  }

  async _setTemp(entityId, temp, mode) {
    const data = { entity_id: entityId };
    if (mode === 'heat_cool') {
      data.target_temp_low = temp.low;
      data.target_temp_high = temp.high;
    } else {
      data.temperature = temp;
    }
    await this._callService('climate', 'set_temperature', data);
  }

  async _setWholeHouseHold(option) {
    const { selects } = this._findEntities();
    if (!selects.wholeHouse) return;
    await this._callService('select', 'select_option', {
      entity_id: selects.wholeHouse, option,
    });
  }

  async _saveSchedule(zoneId, dayProgram) {
    await this._callService('infinitude_direct', 'save_schedule', {
      zone_id: zoneId, schedule: dayProgram,
    });
  }

  async _saveProfile(zoneId, activity, htsp, clsp, fan) {
    const data = { zone_id: zoneId, activity, htsp, clsp };
    if (fan) data.fan = fan;
    await this._callService('infinitude_direct', 'set_profile', data);
  }

  // ── Render ─────────────────────────────────────────────────────────────
  _render() {
    if (!this._hass) return;
    const entities = this._findEntities();

    if (entities.climates.length === 0 && !this._config.show_empty) {
      this.shadowRoot.innerHTML = `
        <ha-card>
          <div style="padding: 24px; text-align: center; color: var(--secondary-text-color);">
            <ha-icon icon="mdi:thermostat" style="--mdc-icon-size: 48px; opacity: 0.3; margin-bottom: 12px; display: block;"></ha-icon>
            <div style="font-size: 14px; font-weight: 500;">No Infinitude entities found</div>
            <div style="font-size: 12px; margin-top: 4px;">Waiting for thermostat connection...</div>
          </div>
        </ha-card>`;
      return;
    }

    const html = `
      <ha-card>
        <style>${this._styles()}</style>
        <div class="card-header">
          ${this._renderHeader(entities)}
        </div>
        <div class="card-tabs">
          ${this._renderTabs()}
        </div>
        <div class="card-content">
          ${this._tab === 'zones' ? this._renderZones(entities) : ''}
          ${this._tab === 'schedule' ? this._renderSchedule(entities) : ''}
          ${this._tab === 'profiles' ? this._renderProfiles(entities) : ''}
        </div>
      </ha-card>`;

    this.shadowRoot.innerHTML = html;
    this._attachEvents();
  }

  // ── Styles ─────────────────────────────────────────────────────────────
  _styles() {
    return `
      :host { display: block; }
      ha-card { overflow: hidden; }

      .card-header {
        display: flex; align-items: center; justify-content: space-between;
        padding: 16px 16px 8px; flex-wrap: wrap; gap: 8px;
      }
      .header-left { display: flex; align-items: center; gap: 12px; }
      .header-title {
        font-size: 18px; font-weight: 500;
        color: var(--primary-text-color);
      }
      .header-mode {
        font-size: 11px; font-weight: 600; text-transform: uppercase;
        padding: 3px 8px; border-radius: 4px;
        background: var(--primary-color); color: var(--text-primary-color, #fff);
      }
      .header-mode.heat { background: var(--label-badge-red, #f97316); }
      .header-mode.cool { background: var(--label-badge-blue, #38bdf8); }
      .header-mode.auto { background: var(--label-badge-green, #34d399); }
      .header-stats {
        display: flex; gap: 16px; align-items: center; font-size: 12px;
        color: var(--secondary-text-color);
      }
      .stat-val { font-weight: 600; color: var(--primary-text-color); }
      .wh-hold {
        display: flex; align-items: center; gap: 6px; width: 100%;
        padding: 8px 12px; margin-top: 4px;
        background: rgba(251,191,36,0.08); border: 1px solid rgba(251,191,36,0.2);
        border-radius: 8px; font-size: 12px; color: var(--warning-color, #fbbf24);
        cursor: pointer;
      }
      .wh-hold:hover { background: rgba(251,191,36,0.14); }

      .card-tabs {
        display: flex; gap: 0; border-bottom: 1px solid var(--divider-color);
        padding: 0 16px;
      }
      .tab {
        padding: 10px 16px; font-size: 13px; font-weight: 500;
        color: var(--secondary-text-color); cursor: pointer;
        border-bottom: 2px solid transparent; margin-bottom: -1px;
        transition: all 0.15s; user-select: none;
      }
      .tab:hover { color: var(--primary-text-color); }
      .tab.active { color: var(--primary-color); border-bottom-color: var(--primary-color); }

      .card-content { padding: 12px 16px 16px; }

      /* Zone Cards */
      .zone-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 12px; }
      .zone-card {
        background: var(--card-background-color, var(--ha-card-background));
        border: 1px solid var(--divider-color); border-radius: 12px;
        overflow: hidden; transition: border-color 0.2s;
      }
      .zone-card:hover { border-color: var(--primary-color); }
      .zone-card.heating { border-left: 3px solid var(--label-badge-red, #f97316); }
      .zone-card.cooling { border-left: 3px solid var(--label-badge-blue, #38bdf8); }
      .zone-card.drying { border-left: 3px solid var(--accent-color, #a78bfa); }

      .zone-top { display: flex; align-items: center; justify-content: space-between; padding: 12px 14px 4px; }
      .zone-name { font-size: 14px; font-weight: 600; color: var(--primary-text-color); }
      .zone-badge {
        font-size: 10px; font-weight: 600; text-transform: uppercase;
        padding: 2px 8px; border-radius: 12px;
        background: var(--secondary-background-color); color: var(--secondary-text-color);
      }
      .zone-badge.heating { background: rgba(249,115,22,0.15); color: var(--label-badge-red, #f97316); }
      .zone-badge.cooling { background: rgba(56,189,248,0.15); color: var(--label-badge-blue, #38bdf8); }
      .zone-badge.drying { background: rgba(167,139,250,0.15); color: var(--accent-color, #a78bfa); }

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

      .zone-meta {
        display: flex; gap: 10px; padding: 0 14px 10px;
        font-size: 11px; color: var(--secondary-text-color); flex-wrap: wrap;
      }
      .meta-item { display: flex; align-items: center; gap: 4px; }
      .meta-val { color: var(--primary-text-color); font-weight: 500; }

      .zone-hold {
        display: flex; align-items: center; gap: 6px; padding: 8px 14px;
        background: rgba(251,191,36,0.06); border-top: 1px solid rgba(251,191,36,0.15);
        font-size: 11px;
      }
      .hold-label { color: var(--warning-color, #fbbf24); font-weight: 500; flex: 1; }
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
      .preset-btn:hover { background: var(--primary-color); color: var(--text-primary-color, #fff); }
      .preset-btn.active { background: var(--primary-color); color: var(--text-primary-color, #fff); }

      /* Mode pills */
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

      /* Schedule */
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
        border-radius: 4px; color: var(--primary-text-color);
        font-size: 11px; padding: 3px 6px; outline: none;
      }
      .sched-select:focus { border-color: var(--primary-color); }
      .sched-temps {
        display: flex; gap: 6px; align-items: center; font-size: 12px;
        font-variant-numeric: tabular-nums;
      }
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

      /* Profiles */
      .prof-card {
        background: var(--secondary-background-color); border: 1px solid var(--divider-color);
        border-radius: 10px; margin-bottom: 8px; overflow: hidden;
      }
      .prof-header {
        padding: 8px 12px; font-size: 13px; font-weight: 600;
        border-bottom: 1px solid var(--divider-color);
        text-transform: capitalize;
      }
      .prof-line {
        display: flex; align-items: center; gap: 10px; padding: 8px 12px;
        border-bottom: 1px solid var(--divider-color); font-size: 12px;
      }
      .prof-line:last-child { border-bottom: none; }
      .prof-name { width: 120px; min-width: 80px; flex-shrink: 0; font-weight: 600; color: var(--primary-text-color); white-space: nowrap; }
      .prof-fan { display: flex; align-items: center; gap: 4px; }
      .prof-fan-label { font-size: 10px; color: var(--secondary-text-color); }

      .copy-bar {
        display: flex; align-items: center; gap: 8px; margin-top: 10px;
        font-size: 12px; color: var(--secondary-text-color);
      }

      .section-title {
        font-size: 11px; font-weight: 600; color: var(--secondary-text-color);
        text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 10px;
      }
    `;
  }

  // ── Header ────────────────────────────────────────────────────────────
  _renderHeader(entities) {
    const { system, selects, climates } = entities;

    // Get mode from first climate entity
    let mode = 'off';
    if (climates.length > 0) {
      const s = this._getState(climates[0]);
      mode = s?.state || 'off';
    }
    const modeClass = mode === 'heat' ? 'heat' : mode === 'cool' ? 'cool' :
      (mode === 'heat_cool' || mode === 'auto') ? 'auto' : '';
    const modeLabel = mode === 'heat_cool' ? 'Auto' : mode.charAt(0).toUpperCase() + mode.slice(1);

    // OAT — from dedicated sensor or from climate attribute
    const oatState = system.oat ? this._getState(system.oat) : null;
    let oat = '–';
    if (oatState?.state && oatState.state !== 'unavailable') {
      oat = `${Math.round(Number(oatState.state))}°`;
    } else if (climates.length > 0) {
      const oatAttr = this._getAttr(climates[0], 'outdoor_temperature');
      if (oatAttr != null) oat = `${Math.round(Number(oatAttr))}°`;
    }

    // Operation status
    const opState = system.opStatus ? this._getState(system.opStatus) : null;
    const opStatus = opState?.state && opState.state !== 'unavailable' ? opState.state : '';

    // Humidifier
    const humState = system.humidifier ? this._getState(system.humidifier) : null;
    const humid = humState?.state || 'off';

    // Whole house hold
    const whState = selects.wholeHouse ? this._getState(selects.wholeHouse) : null;
    const whHold = whState && whState.state !== 'off';
    const whActivity = whState?.state || 'off';

    // Indoor humidity from first climate entity
    let indoorRh = '';
    if (climates.length > 0) {
      const rh = this._getAttr(climates[0], 'current_humidity');
      if (rh != null) indoorRh = `${rh}%`;
    }

    return `
      <div class="header-left">
        <span class="header-title">HVAC</span>
        <span class="header-mode ${modeClass}">${modeLabel}</span>
      </div>
      <div class="header-stats">
        <span>Outside <span class="stat-val">${oat}</span></span>
        ${indoorRh ? `<span>Indoor RH <span class="stat-val">${indoorRh}</span></span>` : ''}
        ${humid === 'on' ? `<span style="color: var(--label-badge-blue, #38bdf8)">💧 Humidifier On</span>` : ''}
        ${opStatus ? `<span>${opStatus}</span>` : ''}
      </div>
      ${whHold ? `
        <div class="wh-hold" data-action="cancel-wh-hold">
          <ha-icon icon="mdi:home-lock" style="--mdc-icon-size: 16px;"></ha-icon>
          <span>Whole house: <strong>${whActivity}</strong></span>
          <span style="margin-left: auto; opacity: 0.7;">Tap to cancel</span>
        </div>
      ` : ''}
    `;
  }

  // ── Tabs ───────────────────────────────────────────────────────────────
  _renderTabs() {
    return ['zones', 'schedule', 'profiles'].map(t =>
      `<div class="tab ${this._tab === t ? 'active' : ''}" data-tab="${t}">${t.charAt(0).toUpperCase() + t.slice(1)}</div>`
    ).join('');
  }

  // ── Zones Tab ──────────────────────────────────────────────────────────
  _renderZones(entities) {
    const { climates } = entities;
    if (!climates.length) return '<div style="padding: 20px; text-align: center; color: var(--secondary-text-color);">No zone entities found</div>';

    // Mode pills
    const firstClimate = this._getState(climates[0]);
    const currentMode = firstClimate?.state || 'off';
    const modes = ['off', 'heat', 'cool', 'heat_cool'];
    const modeLabels = { off: 'Off', heat: 'Heat', cool: 'Cool', heat_cool: 'Auto' };
    const modePills = `
      <div class="mode-row">
        <span class="mode-label">Mode</span>
        <div class="mode-pills">
          ${modes.map(m => {
            const cls = m === currentMode ? 'active' : '';
            const mcls = m === 'heat' ? 'heat' : m === 'cool' ? 'cool' : (m === 'heat_cool') ? 'auto' : '';
            return `<div class="mode-pill ${cls} ${mcls}" data-mode="${m}" data-entity="${climates[0]}">${modeLabels[m]}</div>`;
          }).join('')}
        </div>
      </div>
    `;

    const cards = climates.map(eid => this._renderZoneCard(eid)).join('');
    return modePills + `<div class="zone-grid">${cards}</div>`;
  }

  _renderZoneCard(entityId) {
    const s = this._getState(entityId);
    if (!s) return '';

    const attrs = s.attributes || {};
    const name = attrs.friendly_name || entityId;
    const temp = attrs.current_temperature != null ? Math.round(attrs.current_temperature) : '–';
    const rh = attrs.current_humidity;
    const mode = s.state || 'off';
    const action = attrs.hvac_action || 'idle';
    const preset = attrs.preset_mode || '–';

    const htsp = attrs.target_temp_low ?? attrs.temperature ?? null;
    const clsp = attrs.target_temp_high ?? (mode === 'cool' ? attrs.temperature : null) ?? null;

    const damper = attrs.damper_position;
    const fan = attrs.fan_mode;
    const holdActive = attrs.hold_active;

    const actionClass = action === 'heating' ? 'heating' : action === 'cooling' ? 'cooling' : action === 'drying' ? 'drying' : '';
    const actionLabel = action === 'idle' ? 'Idle' : action.charAt(0).toUpperCase() + action.slice(1);

    const isRange = mode === 'heat_cool';

    return `
      <div class="zone-card ${actionClass}">
        <div class="zone-top">
          <span class="zone-name">${name}</span>
          <span class="zone-badge ${actionClass}">${actionLabel}</span>
        </div>
        <div class="zone-body">
          <div>
            <span class="temp-hero">${temp}</span><span class="temp-unit">°F</span>
            ${rh != null ? `<div style="font-size: 11px; color: var(--secondary-text-color); margin-top: 2px;">${rh}% RH</div>` : ''}
          </div>
          <div class="zone-sp">
            ${htsp != null ? `
              <div class="sp-row">
                <button class="btn-adj" data-adj="-1" data-entity="${entityId}" data-sp="heat">−</button>
                <span class="sp-val sp-heat">${Math.round(htsp)}°</span>
                <button class="btn-adj" data-adj="1" data-entity="${entityId}" data-sp="heat">+</button>
              </div>
            ` : ''}
            ${(isRange && clsp != null) ? `
              <div class="sp-row">
                <button class="btn-adj" data-adj="-1" data-entity="${entityId}" data-sp="cool">−</button>
                <span class="sp-val sp-cool">${Math.round(clsp)}°</span>
                <button class="btn-adj" data-adj="1" data-entity="${entityId}" data-sp="cool">+</button>
              </div>
            ` : ''}
          </div>
        </div>
        <div class="zone-meta">
          <span class="meta-item">Activity <span class="meta-val">${preset}</span></span>
          ${fan ? `<span class="meta-item">Fan <span class="meta-val">${fan}</span></span>` : ''}
          ${damper != null ? `<span class="meta-item">Damper <span class="meta-val">${damper}%</span></span>` : ''}
        </div>
        <div class="zone-preset-row">
          ${ACTIVITIES.map(a =>
            `<div class="preset-btn ${preset === a ? 'active' : ''}" data-preset="${a}" data-entity="${entityId}">${a}</div>`
          ).join('')}
        </div>
        ${holdActive ? `
          <div class="zone-hold">
            <span class="hold-label">Hold: ${preset}</span>
          </div>
        ` : ''}
      </div>
    `;
  }

  // ── Schedule Tab ───────────────────────────────────────────────────────
  _renderSchedule(entities) {
    const schedule = this._getScheduleData();
    const profiles = this._getProfilesData();
    const zoneIds = Object.keys(schedule);

    if (!zoneIds.length) {
      return `<div style="padding: 20px; text-align: center; color: var(--secondary-text-color);">
        <ha-icon icon="mdi:calendar-clock" style="--mdc-icon-size: 48px; opacity: 0.3; margin-bottom: 12px; display: block;"></ha-icon>
        No schedule data available. Waiting for thermostat data...
      </div>`;
    }

    const todayName = DAYS[JS_DAY_MAP[new Date().getDay()]];

    // Day tabs
    const dayTabs = DAYS.map(d => {
      const isActive = d === this._schedDay;
      const isToday = d === todayName && !isActive;
      return `<div class="day-tab ${isActive ? 'active' : ''} ${isToday ? 'today' : ''}" data-sched-day="${d}">${d.slice(0,3)}</div>`;
    }).join('');

    // Find max periods
    let maxPeriods = 0;
    for (const zid of zoneIds) {
      const dayData = schedule[zid]?.[this._schedDay] || [];
      maxPeriods = Math.max(maxPeriods, dayData.length);
    }
    if (maxPeriods === 0) maxPeriods = 5;

    // Zone name lookup from profiles
    const zoneNames = {};
    for (const z of profiles) {
      zoneNames[z.id] = z.name;
    }

    // Period cards
    let periodCards = '';
    for (let pi = 0; pi < maxPeriods; pi++) {
      let zoneLines = '';
      for (const zid of zoneIds) {
        const periods = schedule[zid]?.[this._schedDay] || [];
        const period = periods[pi];
        if (!period) continue;

        // Check for edits
        const editKey = `${zid}_${this._schedDay}_${pi}`;
        const edit = this._schedEdits[editKey];
        const act = edit?.act ?? period.activity;
        const time = edit?.time ?? period.time;
        const enabled = edit?.enabled ?? period.enabled;

        const zoneName = zoneNames[zid] || `Zone ${zid}`;

        // Get temps from profile for this activity
        const zoneProfile = profiles.find(z => z.id === zid);
        const actProfile = zoneProfile?.activities?.[act];
        const htsp = actProfile?.htsp ? Math.round(parseFloat(actProfile.htsp)) : '–';
        const clsp = actProfile?.clsp ? Math.round(parseFloat(actProfile.clsp)) : '–';

        // Time options
        const timeOpts = this._timeOptions(time);

        // Activity options
        const actOpts = ACTIVITIES.map(a =>
          `<option value="${a}"${a === act ? ' selected' : ''}>${a}</option>`
        ).join('');

        zoneLines += `
          <div class="sched-line ${enabled ? '' : 'disabled'}" data-zone="${zid}" data-pi="${pi}" data-day="${this._schedDay}">
            <span class="sched-name">${zoneName}</span>
            <select class="sched-select" data-sched-field="act">${actOpts}</select>
            <select class="sched-select" data-sched-field="time">${timeOpts}</select>
            <label class="sched-toggle">
              <input type="checkbox" ${enabled ? 'checked' : ''} data-sched-field="enabled">
              <span>on</span>
            </label>
            <div class="sched-temps">
              <span class="sp-heat">${htsp}°</span>
              <span class="sp-cool">${clsp}°</span>
            </div>
          </div>
        `;
      }
      periodCards += `
        <div class="period-card">
          <div class="period-header">Period ${pi + 1}</div>
          ${zoneLines}
        </div>
      `;
    }

    // Copy bar
    const otherDays = DAYS.filter(d => d !== this._schedDay);
    const copyOpts = otherDays.map(d => `<option value="${d}">${d.slice(0,3)}</option>`).join('');

    const hasEdits = Object.keys(this._schedEdits).length > 0;

    return `
      <div class="section-title">Schedule</div>
      <div class="sched-day-tabs">${dayTabs}</div>
      ${periodCards}
      <div class="copy-bar">
        <span>Copy ${this._schedDay.slice(0,3)} →</span>
        <select class="sched-select" id="schedCopyTarget" style="width: auto;">
          <option value="">select day…</option>
          ${copyOpts}
          <option value="__all__">All other days</option>
        </select>
        <button class="btn" data-action="copy-sched">Copy</button>
      </div>
      ${hasEdits ? `
        <div class="action-bar">
          <span class="action-bar-label">● Unsaved changes</span>
          <button class="btn" data-action="discard-sched">Discard</button>
          <button class="btn btn-primary" data-action="save-sched">Save schedule</button>
        </div>
      ` : ''}
    `;
  }

  _timeOptions(selected) {
    let opts = '';
    for (let h = 0; h < 24; h++) {
      for (let m = 0; m < 60; m += 15) {
        const val = `${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}`;
        const ampm = h === 0 ? `12:${String(m).padStart(2,'0')} AM` :
          h < 12 ? `${h}:${String(m).padStart(2,'0')} AM` :
          h === 12 ? `12:${String(m).padStart(2,'0')} PM` :
          `${h-12}:${String(m).padStart(2,'0')} PM`;
        opts += `<option value="${val}"${val === selected ? ' selected' : ''}>${ampm}</option>`;
      }
    }
    return opts;
  }

  // ── Profiles Tab ──────────────────────────────────────────────────────
  _renderProfiles(entities) {
    const profiles = this._getProfilesData();

    if (!profiles.length) {
      return `<div style="padding: 20px; text-align: center; color: var(--secondary-text-color);">
        <ha-icon icon="mdi:tune-vertical" style="--mdc-icon-size: 48px; opacity: 0.3; margin-bottom: 12px; display: block;"></ha-icon>
        No profile data available. Waiting for thermostat data...
      </div>`;
    }

    let cards = '';
    for (const actId of ACTIVITIES) {
      let zoneLines = '';
      for (const zone of profiles) {
        const act = zone.activities?.[actId] || {};
        const editKey = `${zone.id}_${actId}`;
        const edit = this._profileEdits[editKey];

        const htsp = edit?.htsp ?? (act.htsp ? Math.round(parseFloat(act.htsp)) : 68);
        const clsp = edit?.clsp ?? (act.clsp ? Math.round(parseFloat(act.clsp)) : 76);
        const fan = edit?.fan ?? act.fan ?? 'low';

        const fanOpts = FAN_OPTIONS.map(f => `<option value="${f}"${f === fan ? ' selected' : ''}>${f}</option>`).join('');

        zoneLines += `
          <div class="prof-line" data-zone="${zone.id}" data-act="${actId}">
            <span class="prof-name">${zone.name}</span>
            <div class="sp-row">
              <button class="btn-adj" data-prof-adj="-1" data-field="htsp">−</button>
              <span class="sp-val sp-heat" data-field="htsp" data-value="${htsp}">${htsp}°</span>
              <button class="btn-adj" data-prof-adj="1" data-field="htsp">+</button>
            </div>
            <div class="sp-row">
              <button class="btn-adj" data-prof-adj="-1" data-field="clsp">−</button>
              <span class="sp-val sp-cool" data-field="clsp" data-value="${clsp}">${clsp}°</span>
              <button class="btn-adj" data-prof-adj="1" data-field="clsp">+</button>
            </div>
            <div class="prof-fan">
              <span class="prof-fan-label">Fan</span>
              <select class="sched-select" data-prof-field="fan">${fanOpts}</select>
            </div>
          </div>
        `;
      }
      cards += `
        <div class="prof-card">
          <div class="prof-header">${actId}</div>
          ${zoneLines}
        </div>
      `;
    }

    const hasEdits = Object.keys(this._profileEdits).length > 0;

    return `
      <div class="section-title">Comfort Profiles</div>
      ${cards}
      ${hasEdits ? `
        <div class="action-bar">
          <span class="action-bar-label">● Unsaved changes</span>
          <button class="btn" data-action="discard-profiles">Discard</button>
          <button class="btn btn-primary" data-action="save-profiles">Save profiles</button>
        </div>
      ` : ''}
    `;
  }

  // ── Events ────────────────────────────────────────────────────────────
  _attachEvents() {
    const root = this.shadowRoot;

    // Tab clicks
    root.querySelectorAll('.tab').forEach(el => {
      el.addEventListener('click', () => {
        this._tab = el.dataset.tab;
        this._render();
      });
    });

    // Mode pills
    root.querySelectorAll('.mode-pill').forEach(el => {
      el.addEventListener('click', () => {
        const entity = el.dataset.entity;
        const mode = el.dataset.mode;
        this._setHvacMode(entity, mode);
      });
    });

    // Setpoint adjustments
    root.querySelectorAll('.btn-adj[data-adj]').forEach(el => {
      el.addEventListener('click', () => {
        const entity = el.dataset.entity;
        if (!entity) return; // Profile adj handled separately
        const delta = parseInt(el.dataset.adj);
        const sp = el.dataset.sp;
        const s = this._getState(entity);
        if (!s) return;
        const mode = s.state;
        if (mode === 'heat_cool') {
          const low = s.attributes.target_temp_low || 68;
          const high = s.attributes.target_temp_high || 76;
          if (sp === 'heat') {
            this._setTemp(entity, { low: low + delta, high }, mode);
          } else {
            this._setTemp(entity, { low, high: high + delta }, mode);
          }
        } else {
          const temp = s.attributes.temperature || 72;
          this._setTemp(entity, temp + delta, mode);
        }
      });
    });

    // Preset buttons
    root.querySelectorAll('.preset-btn').forEach(el => {
      el.addEventListener('click', () => {
        this._setPreset(el.dataset.entity, el.dataset.preset);
      });
    });

    // Whole house hold cancel
    root.querySelectorAll('[data-action="cancel-wh-hold"]').forEach(el => {
      el.addEventListener('click', () => this._setWholeHouseHold('off'));
    });

    // Schedule day tabs
    root.querySelectorAll('[data-sched-day]').forEach(el => {
      el.addEventListener('click', () => {
        this._schedDay = el.dataset.schedDay;
        this._render();
      });
    });

    // Schedule line changes
    root.querySelectorAll('.sched-line').forEach(line => {
      const zid = line.dataset.zone;
      const pi = line.dataset.pi;
      const day = line.dataset.day;
      const editKey = `${zid}_${day}_${pi}`;

      const actSel = line.querySelector('[data-sched-field="act"]');
      const timeSel = line.querySelector('[data-sched-field="time"]');
      const enabledCb = line.querySelector('[data-sched-field="enabled"]');

      const onChange = () => {
        this._schedEdits[editKey] = {
          act: actSel.value,
          time: timeSel.value,
          enabled: enabledCb.checked,
        };
        this._render();
      };

      if (actSel) actSel.addEventListener('change', onChange);
      if (timeSel) timeSel.addEventListener('change', onChange);
      if (enabledCb) enabledCb.addEventListener('change', onChange);
    });

    // Schedule actions
    root.querySelectorAll('[data-action="save-sched"]').forEach(el => {
      el.addEventListener('click', () => this._doSaveSchedule());
    });
    root.querySelectorAll('[data-action="discard-sched"]').forEach(el => {
      el.addEventListener('click', () => {
        this._schedEdits = {};
        this._render();
      });
    });
    root.querySelectorAll('[data-action="copy-sched"]').forEach(el => {
      el.addEventListener('click', () => this._doCopySchedule());
    });

    // Profile adjustments
    root.querySelectorAll('[data-prof-adj]').forEach(el => {
      el.addEventListener('click', () => {
        const line = el.closest('.prof-line');
        const zid = line.dataset.zone;
        const actId = line.dataset.act;
        const field = el.dataset.field;
        const delta = parseInt(el.dataset.profAdj);
        const span = line.querySelector(`[data-field="${field}"]`);
        if (!span) return;

        const min = field === 'htsp' ? 50 : 60;
        const max = field === 'htsp' ? 90 : 99;
        const cur = parseInt(span.dataset.value) || 70;
        const next = Math.max(min, Math.min(max, cur + delta));

        span.dataset.value = next;
        span.textContent = next + '°';

        const editKey = `${zid}_${actId}`;
        if (!this._profileEdits[editKey]) {
          this._profileEdits[editKey] = { zone_id: zid, activity: actId };
        }
        this._profileEdits[editKey][field] = next;

        // Read fan from select
        const fanSel = line.querySelector('[data-prof-field="fan"]');
        if (fanSel) this._profileEdits[editKey].fan = fanSel.value;

        // Show action bar if not present
        if (!root.querySelector('[data-action="save-profiles"]')) {
          this._render();
        }
      });
    });

    // Profile fan changes
    root.querySelectorAll('[data-prof-field="fan"]').forEach(el => {
      el.addEventListener('change', () => {
        const line = el.closest('.prof-line');
        const zid = line.dataset.zone;
        const actId = line.dataset.act;
        const editKey = `${zid}_${actId}`;
        if (!this._profileEdits[editKey]) {
          // Read current values from spans
          const htspSpan = line.querySelector('[data-field="htsp"]');
          const clspSpan = line.querySelector('[data-field="clsp"]');
          this._profileEdits[editKey] = {
            zone_id: zid, activity: actId,
            htsp: parseInt(htspSpan?.dataset.value) || 68,
            clsp: parseInt(clspSpan?.dataset.value) || 76,
          };
        }
        this._profileEdits[editKey].fan = el.value;
        this._render();
      });
    });

    // Profile actions
    root.querySelectorAll('[data-action="save-profiles"]').forEach(el => {
      el.addEventListener('click', () => this._doSaveProfiles());
    });
    root.querySelectorAll('[data-action="discard-profiles"]').forEach(el => {
      el.addEventListener('click', () => {
        this._profileEdits = {};
        this._render();
      });
    });
  }

  // ── Schedule Save ──────────────────────────────────────────────────────
  async _doSaveSchedule() {
    const schedule = this._getScheduleData();
    const zoneIds = Object.keys(schedule);

    for (const zid of zoneIds) {
      const dayProgram = DAYS.map(day => {
        const periods = schedule[zid]?.[day] || [];
        const dayPeriods = periods.map((p, pi) => {
          const editKey = `${zid}_${day}_${pi}`;
          const edit = this._schedEdits[editKey];
          return {
            id: p.id || String(pi + 1),
            activity: edit?.act ?? p.activity,
            time: edit?.time ?? p.time,
            enabled: (edit?.enabled ?? p.enabled) ? 'on' : 'off',
          };
        });
        return { id: day, period: dayPeriods };
      });

      await this._saveSchedule(zid, JSON.stringify(dayProgram));
    }

    this._schedEdits = {};
    this._render();
  }

  _doCopySchedule() {
    const targetSel = this.shadowRoot.querySelector('#schedCopyTarget');
    if (!targetSel || !targetSel.value) return;

    const schedule = this._getScheduleData();
    const zoneIds = Object.keys(schedule);
    const sourceDay = this._schedDay;
    const targets = targetSel.value === '__all__' ? DAYS.filter(d => d !== sourceDay) : [targetSel.value];

    for (const zid of zoneIds) {
      const periods = schedule[zid]?.[sourceDay] || [];
      for (const tgtDay of targets) {
        periods.forEach((p, pi) => {
          const srcKey = `${zid}_${sourceDay}_${pi}`;
          const srcEdit = this._schedEdits[srcKey];
          const tgtKey = `${zid}_${tgtDay}_${pi}`;
          this._schedEdits[tgtKey] = {
            act: srcEdit?.act ?? p.activity,
            time: srcEdit?.time ?? p.time,
            enabled: srcEdit?.enabled ?? p.enabled,
          };
        });
      }
    }

    this._render();
  }

  // ── Profile Save ──────────────────────────────────────────────────────
  async _doSaveProfiles() {
    for (const [key, edit] of Object.entries(this._profileEdits)) {
      await this._saveProfile(
        edit.zone_id, edit.activity,
        edit.htsp, edit.clsp, edit.fan
      );
    }
    this._profileEdits = {};
    // Delay render to let coordinator refresh
    setTimeout(() => this._render(), 1500);
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
