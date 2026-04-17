var et=globalThis,st=et.ShadowRoot&&(et.ShadyCSS===void 0||et.ShadyCSS.nativeShadow)&&"adoptedStyleSheets"in Document.prototype&&"replace"in CSSStyleSheet.prototype,lt=Symbol(),Ct=new WeakMap,J=class{constructor(t,e,s){if(this._$cssResult$=!0,s!==lt)throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");this.cssText=t,this.t=e}get styleSheet(){let t=this.o,e=this.t;if(st&&t===void 0){let s=e!==void 0&&e.length===1;s&&(t=Ct.get(e)),t===void 0&&((this.o=t=new CSSStyleSheet).replaceSync(this.cssText),s&&Ct.set(e,t))}return t}toString(){return this.cssText}},St=l=>new J(typeof l=="string"?l:l+"",void 0,lt),C=(l,...t)=>{let e=l.length===1?l[0]:t.reduce((s,i,o)=>s+(n=>{if(n._$cssResult$===!0)return n.cssText;if(typeof n=="number")return n;throw Error("Value passed to 'css' function must be a 'css' function result: "+n+". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.")})(i)+l[o+1],l[0]);return new J(e,l,lt)},zt=(l,t)=>{if(st)l.adoptedStyleSheets=t.map(e=>e instanceof CSSStyleSheet?e:e.styleSheet);else for(let e of t){let s=document.createElement("style"),i=et.litNonce;i!==void 0&&s.setAttribute("nonce",i),s.textContent=e.cssText,l.appendChild(s)}},ct=st?l=>l:l=>l instanceof CSSStyleSheet?(t=>{let e="";for(let s of t.cssRules)e+=s.cssText;return St(e)})(l):l;var{is:qt,defineProperty:Zt,getOwnPropertyDescriptor:Jt,getOwnPropertyNames:Yt,getOwnPropertySymbols:Xt,getPrototypeOf:Kt}=Object,it=globalThis,Ht=it.trustedTypes,Gt=Ht?Ht.emptyScript:"",Qt=it.reactiveElementPolyfillSupport,Y=(l,t)=>l,dt={toAttribute(l,t){switch(t){case Boolean:l=l?Gt:null;break;case Object:case Array:l=l==null?l:JSON.stringify(l)}return l},fromAttribute(l,t){let e=l;switch(t){case Boolean:e=l!==null;break;case Number:e=l===null?null:Number(l);break;case Object:case Array:try{e=JSON.parse(l)}catch{e=null}}return e}},Tt=(l,t)=>!qt(l,t),Mt={attribute:!0,type:String,converter:dt,reflect:!1,useDefault:!1,hasChanged:Tt};Symbol.metadata??=Symbol("metadata"),it.litPropertyMetadata??=new WeakMap;var T=class extends HTMLElement{static addInitializer(t){this._$Ei(),(this.l??=[]).push(t)}static get observedAttributes(){return this.finalize(),this._$Eh&&[...this._$Eh.keys()]}static createProperty(t,e=Mt){if(e.state&&(e.attribute=!1),this._$Ei(),this.prototype.hasOwnProperty(t)&&((e=Object.create(e)).wrapped=!0),this.elementProperties.set(t,e),!e.noAccessor){let s=Symbol(),i=this.getPropertyDescriptor(t,s,e);i!==void 0&&Zt(this.prototype,t,i)}}static getPropertyDescriptor(t,e,s){let{get:i,set:o}=Jt(this.prototype,t)??{get(){return this[e]},set(n){this[e]=n}};return{get:i,set(n){let d=i?.call(this);o?.call(this,n),this.requestUpdate(t,d,s)},configurable:!0,enumerable:!0}}static getPropertyOptions(t){return this.elementProperties.get(t)??Mt}static _$Ei(){if(this.hasOwnProperty(Y("elementProperties")))return;let t=Kt(this);t.finalize(),t.l!==void 0&&(this.l=[...t.l]),this.elementProperties=new Map(t.elementProperties)}static finalize(){if(this.hasOwnProperty(Y("finalized")))return;if(this.finalized=!0,this._$Ei(),this.hasOwnProperty(Y("properties"))){let e=this.properties,s=[...Yt(e),...Xt(e)];for(let i of s)this.createProperty(i,e[i])}let t=this[Symbol.metadata];if(t!==null){let e=litPropertyMetadata.get(t);if(e!==void 0)for(let[s,i]of e)this.elementProperties.set(s,i)}this._$Eh=new Map;for(let[e,s]of this.elementProperties){let i=this._$Eu(e,s);i!==void 0&&this._$Eh.set(i,e)}this.elementStyles=this.finalizeStyles(this.styles)}static finalizeStyles(t){let e=[];if(Array.isArray(t)){let s=new Set(t.flat(1/0).reverse());for(let i of s)e.unshift(ct(i))}else t!==void 0&&e.push(ct(t));return e}static _$Eu(t,e){let s=e.attribute;return s===!1?void 0:typeof s=="string"?s:typeof t=="string"?t.toLowerCase():void 0}constructor(){super(),this._$Ep=void 0,this.isUpdatePending=!1,this.hasUpdated=!1,this._$Em=null,this._$Ev()}_$Ev(){this._$ES=new Promise(t=>this.enableUpdating=t),this._$AL=new Map,this._$E_(),this.requestUpdate(),this.constructor.l?.forEach(t=>t(this))}addController(t){(this._$EO??=new Set).add(t),this.renderRoot!==void 0&&this.isConnected&&t.hostConnected?.()}removeController(t){this._$EO?.delete(t)}_$E_(){let t=new Map,e=this.constructor.elementProperties;for(let s of e.keys())this.hasOwnProperty(s)&&(t.set(s,this[s]),delete this[s]);t.size>0&&(this._$Ep=t)}createRenderRoot(){let t=this.shadowRoot??this.attachShadow(this.constructor.shadowRootOptions);return zt(t,this.constructor.elementStyles),t}connectedCallback(){this.renderRoot??=this.createRenderRoot(),this.enableUpdating(!0),this._$EO?.forEach(t=>t.hostConnected?.())}enableUpdating(t){}disconnectedCallback(){this._$EO?.forEach(t=>t.hostDisconnected?.())}attributeChangedCallback(t,e,s){this._$AK(t,s)}_$ET(t,e){let s=this.constructor.elementProperties.get(t),i=this.constructor._$Eu(t,s);if(i!==void 0&&s.reflect===!0){let o=(s.converter?.toAttribute!==void 0?s.converter:dt).toAttribute(e,s.type);this._$Em=t,o==null?this.removeAttribute(i):this.setAttribute(i,o),this._$Em=null}}_$AK(t,e){let s=this.constructor,i=s._$Eh.get(t);if(i!==void 0&&this._$Em!==i){let o=s.getPropertyOptions(i),n=typeof o.converter=="function"?{fromAttribute:o.converter}:o.converter?.fromAttribute!==void 0?o.converter:dt;this._$Em=i;let d=n.fromAttribute(e,o.type);this[i]=d??this._$Ej?.get(i)??d,this._$Em=null}}requestUpdate(t,e,s,i=!1,o){if(t!==void 0){let n=this.constructor;if(i===!1&&(o=this[t]),s??=n.getPropertyOptions(t),!((s.hasChanged??Tt)(o,e)||s.useDefault&&s.reflect&&o===this._$Ej?.get(t)&&!this.hasAttribute(n._$Eu(t,s))))return;this.C(t,e,s)}this.isUpdatePending===!1&&(this._$ES=this._$EP())}C(t,e,{useDefault:s,reflect:i,wrapped:o},n){s&&!(this._$Ej??=new Map).has(t)&&(this._$Ej.set(t,n??e??this[t]),o!==!0||n!==void 0)||(this._$AL.has(t)||(this.hasUpdated||s||(e=void 0),this._$AL.set(t,e)),i===!0&&this._$Em!==t&&(this._$Eq??=new Set).add(t))}async _$EP(){this.isUpdatePending=!0;try{await this._$ES}catch(e){Promise.reject(e)}let t=this.scheduleUpdate();return t!=null&&await t,!this.isUpdatePending}scheduleUpdate(){return this.performUpdate()}performUpdate(){if(!this.isUpdatePending)return;if(!this.hasUpdated){if(this.renderRoot??=this.createRenderRoot(),this._$Ep){for(let[i,o]of this._$Ep)this[i]=o;this._$Ep=void 0}let s=this.constructor.elementProperties;if(s.size>0)for(let[i,o]of s){let{wrapped:n}=o,d=this[i];n!==!0||this._$AL.has(i)||d===void 0||this.C(i,void 0,o,d)}}let t=!1,e=this._$AL;try{t=this.shouldUpdate(e),t?(this.willUpdate(e),this._$EO?.forEach(s=>s.hostUpdate?.()),this.update(e)):this._$EM()}catch(s){throw t=!1,this._$EM(),s}t&&this._$AE(e)}willUpdate(t){}_$AE(t){this._$EO?.forEach(e=>e.hostUpdated?.()),this.hasUpdated||(this.hasUpdated=!0,this.firstUpdated(t)),this.updated(t)}_$EM(){this._$AL=new Map,this.isUpdatePending=!1}get updateComplete(){return this.getUpdateComplete()}getUpdateComplete(){return this._$ES}shouldUpdate(t){return!0}update(t){this._$Eq&&=this._$Eq.forEach(e=>this._$ET(e,this[e])),this._$EM()}updated(t){}firstUpdated(t){}};T.elementStyles=[],T.shadowRootOptions={mode:"open"},T[Y("elementProperties")]=new Map,T[Y("finalized")]=new Map,Qt?.({ReactiveElement:T}),(it.reactiveElementVersions??=[]).push("2.1.2");var _t=globalThis,Ot=l=>l,ot=_t.trustedTypes,Dt=ot?ot.createPolicy("lit-html",{createHTML:l=>l}):void 0,Lt="$lit$",O=`lit$${Math.random().toFixed(9).slice(2)}$`,Rt="?"+O,te=`<${Rt}>`,I=document,K=()=>I.createComment(""),G=l=>l===null||typeof l!="object"&&typeof l!="function",gt=Array.isArray,ee=l=>gt(l)||typeof l?.[Symbol.iterator]=="function",pt=`[ 	
\f\r]`,X=/<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g,Pt=/-->/g,jt=/>/g,j=RegExp(`>|${pt}(?:([^\\s"'>=/]+)(${pt}*=${pt}*(?:[^ 	
\f\r"'\`<>=]|("|')|))|$)`,"g"),Nt=/'/g,It=/"/g,Ft=/^(?:script|style|textarea|title)$/i,bt=l=>(t,...e)=>({_$litType$:l,strings:t,values:e}),r=bt(1),me=bt(2),fe=bt(3),U=Symbol.for("lit-noChange"),p=Symbol.for("lit-nothing"),Ut=new WeakMap,N=I.createTreeWalker(I,129);function Wt(l,t){if(!gt(l)||!l.hasOwnProperty("raw"))throw Error("invalid template strings array");return Dt!==void 0?Dt.createHTML(t):t}var se=(l,t)=>{let e=l.length-1,s=[],i,o=t===2?"<svg>":t===3?"<math>":"",n=X;for(let d=0;d<e;d++){let c=l[d],a,h,u=-1,f=0;for(;f<c.length&&(n.lastIndex=f,h=n.exec(c),h!==null);)f=n.lastIndex,n===X?h[1]==="!--"?n=Pt:h[1]!==void 0?n=jt:h[2]!==void 0?(Ft.test(h[2])&&(i=RegExp("</"+h[2],"g")),n=j):h[3]!==void 0&&(n=j):n===j?h[0]===">"?(n=i??X,u=-1):h[1]===void 0?u=-2:(u=n.lastIndex-h[2].length,a=h[1],n=h[3]===void 0?j:h[3]==='"'?It:Nt):n===It||n===Nt?n=j:n===Pt||n===jt?n=X:(n=j,i=void 0);let v=n===j&&l[d+1].startsWith("/>")?" ":"";o+=n===X?c+te:u>=0?(s.push(a),c.slice(0,u)+Lt+c.slice(u)+O+v):c+O+(u===-2?d:v)}return[Wt(l,o+(l[e]||"<?>")+(t===2?"</svg>":t===3?"</math>":"")),s]},Q=class l{constructor({strings:t,_$litType$:e},s){let i;this.parts=[];let o=0,n=0,d=t.length-1,c=this.parts,[a,h]=se(t,e);if(this.el=l.createElement(a,s),N.currentNode=this.el.content,e===2||e===3){let u=this.el.content.firstChild;u.replaceWith(...u.childNodes)}for(;(i=N.nextNode())!==null&&c.length<d;){if(i.nodeType===1){if(i.hasAttributes())for(let u of i.getAttributeNames())if(u.endsWith(Lt)){let f=h[n++],v=i.getAttribute(u).split(O),g=/([.?@])?(.*)/.exec(f);c.push({type:1,index:o,name:g[2],strings:v,ctor:g[1]==="."?ut:g[1]==="?"?mt:g[1]==="@"?ft:F}),i.removeAttribute(u)}else u.startsWith(O)&&(c.push({type:6,index:o}),i.removeAttribute(u));if(Ft.test(i.tagName)){let u=i.textContent.split(O),f=u.length-1;if(f>0){i.textContent=ot?ot.emptyScript:"";for(let v=0;v<f;v++)i.append(u[v],K()),N.nextNode(),c.push({type:2,index:++o});i.append(u[f],K())}}}else if(i.nodeType===8)if(i.data===Rt)c.push({type:2,index:o});else{let u=-1;for(;(u=i.data.indexOf(O,u+1))!==-1;)c.push({type:7,index:o}),u+=O.length-1}o++}}static createElement(t,e){let s=I.createElement("template");return s.innerHTML=t,s}};function R(l,t,e=l,s){if(t===U)return t;let i=s!==void 0?e._$Co?.[s]:e._$Cl,o=G(t)?void 0:t._$litDirective$;return i?.constructor!==o&&(i?._$AO?.(!1),o===void 0?i=void 0:(i=new o(l),i._$AT(l,e,s)),s!==void 0?(e._$Co??=[])[s]=i:e._$Cl=i),i!==void 0&&(t=R(l,i._$AS(l,t.values),i,s)),t}var ht=class{constructor(t,e){this._$AV=[],this._$AN=void 0,this._$AD=t,this._$AM=e}get parentNode(){return this._$AM.parentNode}get _$AU(){return this._$AM._$AU}u(t){let{el:{content:e},parts:s}=this._$AD,i=(t?.creationScope??I).importNode(e,!0);N.currentNode=i;let o=N.nextNode(),n=0,d=0,c=s[0];for(;c!==void 0;){if(n===c.index){let a;c.type===2?a=new tt(o,o.nextSibling,this,t):c.type===1?a=new c.ctor(o,c.name,c.strings,this,t):c.type===6&&(a=new vt(o,this,t)),this._$AV.push(a),c=s[++d]}n!==c?.index&&(o=N.nextNode(),n++)}return N.currentNode=I,i}p(t){let e=0;for(let s of this._$AV)s!==void 0&&(s.strings!==void 0?(s._$AI(t,s,e),e+=s.strings.length-2):s._$AI(t[e])),e++}},tt=class l{get _$AU(){return this._$AM?._$AU??this._$Cv}constructor(t,e,s,i){this.type=2,this._$AH=p,this._$AN=void 0,this._$AA=t,this._$AB=e,this._$AM=s,this.options=i,this._$Cv=i?.isConnected??!0}get parentNode(){let t=this._$AA.parentNode,e=this._$AM;return e!==void 0&&t?.nodeType===11&&(t=e.parentNode),t}get startNode(){return this._$AA}get endNode(){return this._$AB}_$AI(t,e=this){t=R(this,t,e),G(t)?t===p||t==null||t===""?(this._$AH!==p&&this._$AR(),this._$AH=p):t!==this._$AH&&t!==U&&this._(t):t._$litType$!==void 0?this.$(t):t.nodeType!==void 0?this.T(t):ee(t)?this.k(t):this._(t)}O(t){return this._$AA.parentNode.insertBefore(t,this._$AB)}T(t){this._$AH!==t&&(this._$AR(),this._$AH=this.O(t))}_(t){this._$AH!==p&&G(this._$AH)?this._$AA.nextSibling.data=t:this.T(I.createTextNode(t)),this._$AH=t}$(t){let{values:e,_$litType$:s}=t,i=typeof s=="number"?this._$AC(t):(s.el===void 0&&(s.el=Q.createElement(Wt(s.h,s.h[0]),this.options)),s);if(this._$AH?._$AD===i)this._$AH.p(e);else{let o=new ht(i,this),n=o.u(this.options);o.p(e),this.T(n),this._$AH=o}}_$AC(t){let e=Ut.get(t.strings);return e===void 0&&Ut.set(t.strings,e=new Q(t)),e}k(t){gt(this._$AH)||(this._$AH=[],this._$AR());let e=this._$AH,s,i=0;for(let o of t)i===e.length?e.push(s=new l(this.O(K()),this.O(K()),this,this.options)):s=e[i],s._$AI(o),i++;i<e.length&&(this._$AR(s&&s._$AB.nextSibling,i),e.length=i)}_$AR(t=this._$AA.nextSibling,e){for(this._$AP?.(!1,!0,e);t!==this._$AB;){let s=Ot(t).nextSibling;Ot(t).remove(),t=s}}setConnected(t){this._$AM===void 0&&(this._$Cv=t,this._$AP?.(t))}},F=class{get tagName(){return this.element.tagName}get _$AU(){return this._$AM._$AU}constructor(t,e,s,i,o){this.type=1,this._$AH=p,this._$AN=void 0,this.element=t,this.name=e,this._$AM=i,this.options=o,s.length>2||s[0]!==""||s[1]!==""?(this._$AH=Array(s.length-1).fill(new String),this.strings=s):this._$AH=p}_$AI(t,e=this,s,i){let o=this.strings,n=!1;if(o===void 0)t=R(this,t,e,0),n=!G(t)||t!==this._$AH&&t!==U,n&&(this._$AH=t);else{let d=t,c,a;for(t=o[0],c=0;c<o.length-1;c++)a=R(this,d[s+c],e,c),a===U&&(a=this._$AH[c]),n||=!G(a)||a!==this._$AH[c],a===p?t=p:t!==p&&(t+=(a??"")+o[c+1]),this._$AH[c]=a}n&&!i&&this.j(t)}j(t){t===p?this.element.removeAttribute(this.name):this.element.setAttribute(this.name,t??"")}},ut=class extends F{constructor(){super(...arguments),this.type=3}j(t){this.element[this.name]=t===p?void 0:t}},mt=class extends F{constructor(){super(...arguments),this.type=4}j(t){this.element.toggleAttribute(this.name,!!t&&t!==p)}},ft=class extends F{constructor(t,e,s,i,o){super(t,e,s,i,o),this.type=5}_$AI(t,e=this){if((t=R(this,t,e,0)??p)===U)return;let s=this._$AH,i=t===p&&s!==p||t.capture!==s.capture||t.once!==s.once||t.passive!==s.passive,o=t!==p&&(s===p||i);i&&this.element.removeEventListener(this.name,this,s),o&&this.element.addEventListener(this.name,this,t),this._$AH=t}handleEvent(t){typeof this._$AH=="function"?this._$AH.call(this.options?.host??this.element,t):this._$AH.handleEvent(t)}},vt=class{constructor(t,e,s){this.element=t,this.type=6,this._$AN=void 0,this._$AM=e,this.options=s}get _$AU(){return this._$AM._$AU}_$AI(t){R(this,t)}};var ie=_t.litHtmlPolyfillSupport;ie?.(Q,tt),(_t.litHtmlVersions??=[]).push("3.3.2");var Bt=(l,t,e)=>{let s=e?.renderBefore??t,i=s._$litPart$;if(i===void 0){let o=e?.renderBefore??null;s._$litPart$=i=new tt(t.insertBefore(K(),o),o,void 0,e??{})}return i._$AI(l),i};var yt=globalThis,D=class extends T{constructor(){super(...arguments),this.renderOptions={host:this},this._$Do=void 0}createRenderRoot(){let t=super.createRenderRoot();return this.renderOptions.renderBefore??=t.firstChild,t}update(t){let e=this.render();this.hasUpdated||(this.renderOptions.isConnected=this.isConnected),super.update(t),this._$Do=Bt(e,this.renderRoot,this.renderOptions)}connectedCallback(){super.connectedCallback(),this._$Do?.setConnected(!0)}disconnectedCallback(){super.disconnectedCallback(),this._$Do?.setConnected(!1)}render(){return U}};D._$litElement$=!0,D.finalized=!0,yt.litElementHydrateSupport?.({LitElement:D});var oe=yt.litElementPolyfillSupport;oe?.({LitElement:D});(yt.litElementVersions??=[]).push("4.2.2");var at="1.0.84",z=["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"],Z=[6,0,1,2,3,4,5],P=["home","away","sleep","wake"],nt=["home","away","sleep","wake","manual"],rt=["off","low","med","high"],L=[{v:"60",l:"1 hour"},{v:"120",l:"2 hours"},{v:"240",l:"4 hours"},{v:"forever",l:"Indefinite"},{v:"custom",l:"Custom time\u2026"}],H=["\u2460","\u2461","\u2462","\u2463","\u2464","\u2465","\u2466","\u2467"],ae=(()=>{let l=[];for(let t=0;t<24;t++)for(let e=0;e<60;e+=15){let s=`${String(t).padStart(2,"0")}:${String(e).padStart(2,"0")}`,i=t===0?`12:${String(e).padStart(2,"0")} AM`:t<12?`${t}:${String(e).padStart(2,"0")} AM`:t===12?`12:${String(e).padStart(2,"0")} PM`:`${t-12}:${String(e).padStart(2,"0")} PM`;l.push({v:s,l:i})}return l})(),W=50,B=90,V=60,q=99,x=68,$=76,ne=800,re=400,le=2e3,Vt=500,w=class extends D{static get baseProperties(){return{hass:{attribute:!1},_config:{state:!0},_registryLoaded:{state:!0}}}constructor(){super(),this._config={},this._registryEntities=null,this._registryLoaded=!1,this._cachedEntities=null,this._cachedEntitiesHass=null}setConfig(t){this._config=t}shouldUpdate(t){if(!t.has("hass")||!this._registryLoaded)return!0;let e=t.get("hass");return e?(this._registryEntities||[]).some(i=>this.hass.states[i.entity_id]!==e.states[i.entity_id]):!0}updated(t){t.has("hass")&&this.hass&&!this._registryLoaded&&this._loadRegistry(),t.has("hass")&&(this._cachedEntities=null)}async _loadRegistry(){try{let t=await this.hass.connection.sendMessagePromise({type:"config/entity_registry/list"});this._registryEntities=Array.isArray(t)?t.filter(e=>e.platform==="infinitude_direct"):[]}catch(t){console.warn("Failed to load entity registry",t),this._registryEntities=[]}this._registryLoaded=!0,this._cachedEntities=null}_findEntities(){if(this._cachedEntities&&this._cachedEntitiesHass===this.hass)return this._cachedEntities;if(!this.hass)return{climates:[],sensors:{},selects:{},system:{}};let t=this._registryEntities||[],e=this.hass.states,s=[],i={damper:{},fan:{}},o={},n={};if(this._config.climate_entities)for(let c of this._config.climate_entities)e[c]&&s.push(c);for(let c of t){let a=c.entity_id;if(!e[a])continue;let h=a.split(".")[0],u=c.unique_id||"";h==="climate"?this._config.climate_entities||s.push(a):h==="select"?o.wholeHouse=a:h==="sensor"&&(u.includes("damper")?i.damper[a]=e[a]:u.includes("fan")?i.fan[a]=e[a]:u.includes("humidifier")?n.humidifier=a:u.includes("oat")?n.oat=a:u.includes("op_status")?n.opStatus=a:u.includes("system_info")&&(n.info=a))}s.sort();let d={climates:s,sensors:i,selects:o,system:n};return this._cachedEntities=d,this._cachedEntitiesHass=this.hass,d}_st(t){return t?this.hass?.states[t]??null:null}_at(t,e){return this._st(t)?.attributes?.[e]}_getScheduleData(){let{system:t}=this._findEntities();if(!t.info)return{};try{return JSON.parse(this._at(t.info,"schedule")||"{}")}catch(e){return console.warn("Failed to parse schedule data",e),{}}}_getProfilesData(){let{system:t}=this._findEntities();if(!t.info)return[];try{return JSON.parse(this._at(t.info,"profiles")||"[]")}catch(e){return console.warn("Failed to parse profiles data",e),[]}}async _svc(t,e,s){try{await this.hass.callService(t,e,s)}catch(i){console.error(`${t}.${e} failed`,i)}}_setHvacMode(t,e){this._svc("climate","set_hvac_mode",{entity_id:t,hvac_mode:e})}_setPreset(t,e){this._svc("climate","set_preset_mode",{entity_id:t,preset_mode:e})}_resolveUntil(t,e){if(t==="forever")return"forever";if(t==="custom")return e||null;let s=new Date;s.setMinutes(s.getMinutes()+parseInt(t));let i=Math.round(s.getMinutes()/15)*15;return s.setMinutes(i,0,0),i===60&&(s.setMinutes(0),s.setHours(s.getHours()+1)),`${String(s.getHours()).padStart(2,"0")}:${String(s.getMinutes()).padStart(2,"0")}`}_otmrRelative(t){if(!t)return"";let[e,s]=t.split(":").map(Number),i=new Date;return i.setHours(e,s,0,0),"until "+i.toLocaleTimeString([],{hour:"numeric",minute:"2-digit"})}_zoneId(t){let e=(this._registryEntities||[]).find(s=>s.entity_id===t);return e?(e.unique_id||"").replace(/^infinitude_/,""):""}_renderLoading(){return r`<ha-card>
      <div style="padding:24px;text-align:center;color:var(--secondary-text-color)">Loading…</div>
    </ha-card>`}_adjustTemp(t,e,s){let i=this._st(t);if(!i)return;let o=i.attributes||{};this._tempAdj||(this._tempAdj={});let n=this._tempAdj[t]||(this._tempAdj[t]={}),d=n.heat??o.target_temp_low??o.temperature??x,c=n.cool??o.target_temp_high??(i.state==="cool"?o.temperature:null)??$;s==="heat"?n.heat=Math.max(W,Math.min(B,Math.round(d)+e)):n.cool=Math.max(V,Math.min(q,Math.round(c)+e)),this._pendingTemps={...this._pendingTemps,[t]:{heat:n.heat,cool:n.cool}},n.committing||(clearTimeout(n.timer),n.timer=setTimeout(()=>this._commitAdj(t),ne))}async _commitAdj(t){if(!this._tempAdj)return;let e=this._tempAdj[t];if(!e||e.committing)return;e.committing=!0;let s=this._st(t),i=s?.attributes||{},o=e.heat,n=e.cool,d=o??Math.round(i.target_temp_low??i.temperature??x),c=n??Math.round(i.target_temp_high??(s?.state==="cool"?i.temperature:null)??$),a=s?.state||"off",h={entity_id:t};a==="heat_cool"?(h.target_temp_low=d,h.target_temp_high=c):a==="heat"?h.temperature=d:a==="cool"?h.temperature=c:(h.target_temp_low=d,h.target_temp_high=c);try{await this.hass.callService("climate","set_temperature",h)}catch(u){console.error("set_temperature failed",u)}if(e.committing=!1,e.heat!==o||e.cool!==n){e.timer=setTimeout(()=>this._commitAdj(t),re);return}e.heat=null,e.cool=null,e.timer=null,setTimeout(()=>{if(!this._tempAdj[t]?.heat&&!this._tempAdj[t]?.cool){let{[t]:u,...f}=this._pendingTemps;this._pendingTemps=f}},le)}_hasPending(t){let e=this._tempAdj?.[t];return e&&(e.heat!=null||e.cool!=null||e.committing)}_cancelHold(t){let e=this._zoneId(t);e&&this._svc("infinitude_direct","cancel_hold",{zone_id:e})}_setZoneHold(t){let e=this._zoneId(t);if(!e)return;let s=this._resolveUntil(this._holdDuration,this._holdCustom);s!==null&&(this._holdActivity==="manual"&&this._svc("infinitude_direct","set_profile",{zone_id:e,activity:"manual",htsp:this._holdHtsp,clsp:this._holdClsp,fan:this._holdFan}),this._svc("infinitude_direct","set_hold",{zone_id:e,activity:this._holdActivity,...s!==void 0&&{until:s}}),this._holdOpen=null)}_initHoldManual(t){let e=this._zoneId(t),s=this._getProfilesData().find(i=>i.id===e)?.activities?.manual||{};this._holdHtsp=s.htsp?Math.round(Number(s.htsp)||x):x,this._holdClsp=s.clsp?Math.round(Number(s.clsp)||$):$,this._holdFan=s.fan||"auto"}_setWholeHouseHold(){let t=this._resolveUntil(this._whHoldDuration,this._whHoldCustom);t!==null&&(this._svc("infinitude_direct","set_whole_house_hold",{activity:this._whHoldActivity,...t!==void 0&&{until:t}}),this._whHoldOpen=!1)}_cancelWholeHouseHold(){this._svc("infinitude_direct","cancel_whole_house_hold",{})}_periodCard(t,e,s,i,o,n){let d=e.length>1;return r`
      <div class="period-card">
        <div class="period-header">Period ${t+1}</div>
        ${e.map(c=>{let a=(s[c]?.[this._schedDay]||[])[t];if(!a)return p;let h=`${c}_${this._schedDay}_${t}`,u=this._schedEdits[h],f=u?.act??a.activity,v=u?.time??a.time,g=u?.enabled??a.enabled,A=i.find(b=>b.id===c)?.activities?.[f],k=A?.htsp?Math.round(Number(A.htsp)||0):"\u2013",E=A?.clsp?Math.round(Number(A.clsp)||0):"\u2013",_=d?H[n[c]]??c:o[c]||`Zone ${c}`;return r`
            <div class="sched-line ${g?"":"disabled"}">
              <span class="sched-name ${d?"sched-name-compact":""}">${_}</span>
              <select class="sched-select" .value=${f} @change=${b=>this._schedEdit(c,t,"act",b.target.value)}>
                ${P.map(b=>r`<option value=${b} ?selected=${b===f}>${b}</option>`)}
              </select>
              <select class="sched-select" .value=${v} @change=${b=>this._schedEdit(c,t,"time",b.target.value)}>
                ${ae.map(b=>r`<option value=${b.v} ?selected=${b.v===v}>${b.l}</option>`)}
              </select>
              <label class="sched-toggle">
                <input type="checkbox" .checked=${g}
                       @change=${b=>this._schedEdit(c,t,"enabled",b.target.checked)}>
                <span>on</span>
              </label>
              <div class="sched-temps">
                <span class="sp-heat">${k}°</span>
                <span class="sp-cool">${E}°</span>
              </div>
            </div>`})}
      </div>`}_schedEdit(t,e,s,i){let o=`${t}_${this._schedDay}_${e}`,n=this._schedEdits[o]||{},d=(this._getScheduleData()[t]?.[this._schedDay]||[])[e]||{};this._schedEdits={...this._schedEdits,[o]:{act:s==="act"?i:n.act??d.activity,time:s==="time"?i:n.time??d.time,enabled:s==="enabled"?i:n.enabled??d.enabled}}}_copySched(t){let e=t.target.value;if(!e)return;t.target.value="";let s=this._getScheduleData(),i=e==="__all__"?z.filter(n=>n!==this._schedDay):[e],o={...this._schedEdits};for(let n of Object.keys(s)){let d=s[n]?.[this._schedDay]||[];for(let c of i)d.forEach((a,h)=>{let u=this._schedEdits[`${n}_${this._schedDay}_${h}`];o[`${n}_${c}_${h}`]={act:u?.act??a.activity,time:u?.time??a.time,enabled:u?.enabled??a.enabled}})}this._schedEdits=o}async _saveSched(){if(this._saving)return;this._saving=!0;let t={...this._schedEdits};try{let e=this._getScheduleData();for(let s of Object.keys(e)){let i=z.map(o=>({id:o,period:(e[s]?.[o]||[]).map((n,d)=>{let c=t[`${s}_${o}_${d}`];return{id:n.id||String(d+1),activity:c?.act??n.activity,time:c?.time??n.time,enabled:c?.enabled??n.enabled?"on":"off"}})}));await this._svc("infinitude_direct","save_schedule",{zone_id:s,schedule:JSON.stringify(i)})}}finally{setTimeout(()=>{let e=this._schedEdits,s={};for(let i of Object.keys(e))(!(i in t)||e[i]!==t[i])&&(s[i]=e[i]);this._schedEdits=s,this._saving=!1},Vt)}}_profAdj(t,e,s,i){let o=`${t}_${e}`,n=this._getProfilesData().find(v=>v.id===t)?.activities?.[e]||{},d=this._profileEdits[o]||{},c=d.htsp??(n.htsp?Math.round(Number(n.htsp)||x):x),a=d.clsp??(n.clsp?Math.round(Number(n.clsp)||$):$),h=s==="htsp"?W:V,u=s==="htsp"?B:q,f=s==="htsp"?c:a;this._profileEdits={...this._profileEdits,[o]:{zone_id:t,activity:e,htsp:s==="htsp"?Math.max(h,Math.min(u,f+i)):c,clsp:s==="clsp"?Math.max(h,Math.min(u,f+i)):a,fan:d.fan??n.fan??"low"}}}_profFan(t,e,s){let i=`${t}_${e}`,o=this._getProfilesData().find(d=>d.id===t)?.activities?.[e]||{},n=this._profileEdits[i]||{};this._profileEdits={...this._profileEdits,[i]:{zone_id:t,activity:e,htsp:n.htsp??(o.htsp?Math.round(Number(o.htsp)||x):x),clsp:n.clsp??(o.clsp?Math.round(Number(o.clsp)||$):$),fan:s}}}async _saveProfs(){if(this._savingProfs)return;this._savingProfs=!0;let t={...this._profileEdits};try{for(let e of Object.values(t)){let s={zone_id:e.zone_id,activity:e.activity,htsp:e.htsp,clsp:e.clsp};e.fan&&(s.fan=e.fan),await this._svc("infinitude_direct","set_profile",s)}}finally{setTimeout(()=>{let e=this._profileEdits,s={};for(let i of Object.keys(e))(!(i in t)||e[i]!==t[i])&&(s[i]=e[i]);this._profileEdits=s,this._savingProfs=!1},Vt)}}},M=C`
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
`;var xt=class extends w{static properties={...w.baseProperties,_whHoldOpen:{state:!0},_whHoldActivity:{state:!0},_whHoldDuration:{state:!0},_whHoldCustom:{state:!0}};constructor(){super(),this._whHoldOpen=!1,this._whHoldActivity="home",this._whHoldDuration="120",this._whHoldCustom=""}static getConfigElement(){return document.createElement("div")}static getStubConfig(){return{}}getCardSize(){return 3}static styles=[M,C`
    .card-pad { padding: 16px; }
    .header {
      display: flex; align-items: center; gap: 8px; margin-bottom: 14px;
    }
    .header-title { font-size: 18px; font-weight: 500; color: var(--primary-text-color); }
  `];render(){if(!this.hass)return p;if(!this._registryLoaded)return this._renderLoading();let t=this._findEntities(),{system:e,selects:s,climates:i}=t,o=i.length&&this._st(i[0])?.state||"off",n=["off","heat","cool","heat_cool"],d={off:"Off",heat:"Heat",cool:"Cool",heat_cool:"Auto"},c=this._st(e.oat),a="\u2013";if(c?.state&&c.state!=="unavailable")a=`${Math.round(Number(c.state))}\xB0`;else if(i.length){let _=this._at(i[0],"outdoor_temperature");_!=null&&(a=`${Math.round(Number(_))}\xB0`)}let h=this._st(e.opStatus),u=h?.state&&h.state!=="unavailable"?h.state:"",f=this._st(e.humidifier)?.state==="on",v=this._st(s.wholeHouse),g=v&&v.state!=="off",S=i.length?this._at(i[0],"whole_house_hold_until"):null,A=i.length?this._at(i[0],"current_humidity"):null,k=e.info?this._st(e.info)?.state!=="unavailable":!1,E=e.info?this._at(e.info,"carrier_ok"):null;return r`
      <ha-card>
        <div class="card-pad">
          <div class="header">
            <span class="header-title">infinitude</span>
            <span class="conn-dot ${k?"ok":"err"}" title="${k?"Infinitude: connected":"Infinitude: unavailable"}"></span>
            <span class="conn-dot ${E===!0?"ok":E===!1?"err":"unk"}" title="${E===!0?"Carrier cloud: connected":E===!1?"Carrier cloud: unreachable":"Carrier cloud: checking\u2026"}"></span>
            <span style="font-size:10px;color:var(--secondary-text-color);opacity:0.5">v${at}</span>
          </div>
          <div class="mode-row">
            <span class="mode-label">Mode</span>
            <div class="mode-pills">
              ${n.map(_=>r`<div class="mode-pill ${_===o?"active":""} ${_==="heat"?"heat":_==="cool"?"cool":_==="heat_cool"?"auto":""}"
                  @click=${()=>this._setHvacMode(i[0],_)}>${d[_]}</div>`)}
            </div>
          </div>
          <div class="summary-stats">
            <div class="summary-stat">
              <span class="summary-stat-label">Status</span>
              <span class="summary-stat-val ${u.toLowerCase().includes("heat")?"heat":u.toLowerCase().includes("cool")?"cool":""}">${u||"Idle"}</span>
            </div>
            <div class="summary-divider"></div>
            <div class="summary-stat">
              <span class="summary-stat-label">Outdoor</span>
              <span class="summary-stat-val">${a}</span>
            </div>
            <div class="summary-divider"></div>
            <div class="summary-stat">
              <span class="summary-stat-label">Humidity</span>
              <span class="summary-stat-val">${A!=null?`${A}%`:"\u2013"}</span>
            </div>
            ${f?r`
              <div class="summary-divider"></div>
              <div class="summary-stat">
                <span class="summary-stat-label">Humidifier</span>
                <span class="summary-stat-val" style="color:var(--label-badge-blue,#38bdf8)">💧 On</span>
              </div>`:p}
          </div>
          ${g?r`
            <div class="wh-hold" @click=${()=>this._cancelWholeHouseHold()}>
              <ha-icon icon="mdi:home-lock" style="--mdc-icon-size:16px"></ha-icon>
              <span>Whole house: <strong>${v.state}</strong>${S?r` · <span style="opacity:0.85">${this._otmrRelative(S)}</span>`:p}</span>
              <span style="margin-left:auto;opacity:0.7">Tap to cancel</span>
            </div>`:r`
            ${this._whHoldOpen?r`
              <div class="wh-set">
                <span class="wh-set-label">WH Hold</span>
                <div class="wh-pills">
                  ${P.map(_=>r`
                    <div class="wh-pill ${this._whHoldActivity===_?"active":""}"
                         @click=${()=>{this._whHoldActivity=_}}>${_}</div>`)}
                </div>
                <select class="hold-dur-select" @change=${_=>{this._whHoldDuration=_.target.value}}>
                  ${L.map(_=>r`<option value=${_.v} ?selected=${_.v===this._whHoldDuration}>${_.l}</option>`)}
                </select>
                ${this._whHoldDuration==="custom"?r`
                  <input type="time" class="hold-time-input" step="900" .value=${this._whHoldCustom}
                         @change=${_=>{this._whHoldCustom=_.target.value}}>`:p}
                <button class="btn btn-primary" style="font-size:11px;padding:4px 12px" @click=${()=>this._setWholeHouseHold()}>Apply</button>
                <button class="btn" style="font-size:11px;padding:4px 10px" @click=${()=>{this._whHoldOpen=!1}}>Cancel</button>
              </div>`:r`
              <div>
                <button class="btn" style="font-size:11px;padding:4px 12px" @click=${()=>{this._whHoldOpen=!0}}>
                  <ha-icon icon="mdi:home-lock" style="--mdc-icon-size:14px;vertical-align:middle;margin-right:4px"></ha-icon>Set WH hold
                </button>
              </div>`}
          `}
        </div>
      </ha-card>`}};customElements.get("infinitude-status-card")||customElements.define("infinitude-status-card",xt);window.customCards=window.customCards||[];window.customCards.some(l=>l.type==="infinitude-status-card")||window.customCards.push({type:"infinitude-status-card",name:"Infinitude Status",description:"System mode, stats, and whole-house hold for Carrier/Bryant Infinity",preview:!1});var $t=class extends w{static properties={...w.baseProperties,_pendingTemps:{state:!0},_holdOpen:{state:!0},_holdActivity:{state:!0},_holdDuration:{state:!0},_holdCustom:{state:!0},_holdHtsp:{state:!0},_holdClsp:{state:!0},_holdFan:{state:!0}};constructor(){super(),this._pendingTemps={},this._tempAdj={},this._holdOpen=!1,this._holdActivity="home",this._holdDuration="120",this._holdCustom="",this._holdHtsp=x,this._holdClsp=$,this._holdFan="auto"}static getConfigElement(){return document.createElement("div")}static getStubConfig(){return{entity:""}}getCardSize(){return 4}static styles=[M,C`
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
  `];render(){if(!this.hass)return p;if(!this._registryLoaded)return this._renderLoading();let t=this._config.entity;if(!t)return r`<ha-card><div class="card-pad" style="color:var(--secondary-text-color)">No entity configured</div></ha-card>`;let e=this._st(t);if(!e)return r`<ha-card><div class="card-pad" style="color:var(--secondary-text-color)">Entity unavailable</div></ha-card>`;let s=e.attributes||{},i=(s.friendly_name||t).replace(/^Infinitude\s+/i,"").replace(/^infinitude_direct\s+/i,""),o=s.current_temperature!=null?Math.round(s.current_temperature):"\u2013",n=s.current_humidity,d=e.state||"off",c=s.hvac_action||"idle",a=s.preset_mode||"\u2013",h=c==="heating"?"heating":c==="cooling"?"cooling":c==="drying"?"drying":"",u=c==="idle"?"Idle":c.charAt(0).toUpperCase()+c.slice(1),f=d==="heat_cool",v=!!s.hold_active,g=s.hold_activity||a,S=s.hold_until,A=this._pendingTemps[t],k=this._hasPending(t),E=A?.heat??s.target_temp_low??s.temperature??null,_=A?.cool??s.target_temp_high??(d==="cool"?s.temperature:null)??null;return r`
      <ha-card class="${h}">
        <div class="card-pad">
          <div class="zone-top">
            <div style="display:flex;align-items:center;gap:8px">
              <span class="zone-cond-dot ${h||"idle"}" title="${c==="drying"?"Dehumidifying":u}"></span>
              <span class="zone-name">${i}</span>
            </div>
            <span class="zone-activity-pill">${a}</span>
          </div>
          <div class="zone-body">
            <div>
              <span class="temp-hero">${o}</span><span class="temp-unit">°F</span>
            </div>
            <div class="zone-sp">
              ${E!=null?r`
                <div class="sp-row">
                  <button class="btn-adj" @click=${()=>this._adjustTemp(t,-1,"heat")}>−</button>
                  <span class="sp-val sp-heat ${k?"sp-pending":""}">${Math.round(E)}°</span>
                  <button class="btn-adj" @click=${()=>this._adjustTemp(t,1,"heat")}>+</button>
                </div>`:p}
              ${f&&_!=null?r`
                <div class="sp-row">
                  <button class="btn-adj" @click=${()=>this._adjustTemp(t,-1,"cool")}>−</button>
                  <span class="sp-val sp-cool ${k?"sp-pending":""}">${Math.round(_)}°</span>
                  <button class="btn-adj" @click=${()=>this._adjustTemp(t,1,"cool")}>+</button>
                </div>`:p}
            </div>
          </div>
          <div class="zone-meta">
            ${n!=null?r`<span class="meta-item">RH <span class="meta-val">${n}%</span></span>`:p}
            ${s.fan_mode?r`<span class="meta-item">Fan <span class="meta-val">${s.fan_mode}</span></span>`:p}
            ${s.damper_position!=null?r`<span class="meta-item">Damper <span class="meta-val">${s.damper_position}%</span></span>`:p}
          </div>
          ${v?r`
            <div class="zone-hold">
              <span class="hold-label">Hold: ${g}${S?` \xB7 ${this._otmrRelative(S)}`:""}</span>
              <button class="btn" style="font-size:11px;padding:3px 10px;color:var(--error-color,#f87171)" @click=${()=>this._cancelHold(t)}>Cancel</button>
            </div>`:p}
          ${this._holdOpen?r`
            <div class="zone-hold-picker">
              <div class="hold-picker-row">
                <div class="wh-pills">
                  ${nt.map(y=>r`
                    <div class="wh-pill ${this._holdActivity===y?"active":""}"
                         @click=${()=>{this._holdActivity=y,y==="manual"&&this._initHoldManual(t)}}>${y}</div>`)}
                </div>
              </div>
              ${this._holdActivity==="manual"?r`
                <div class="hold-picker-row" style="gap:10px;flex-wrap:wrap">
                  <div class="sp-row">
                  <button class="btn-adj" @click=${()=>{this._holdHtsp=Math.max(W,this._holdHtsp-1)}}>−</button>
                  <span class="sp-val sp-heat">${this._holdHtsp}°</span>
                  <button class="btn-adj" @click=${()=>{this._holdHtsp=Math.min(B,this._holdHtsp+1)}}>+</button>
                </div>
                <div class="sp-row">
                  <button class="btn-adj" @click=${()=>{this._holdClsp=Math.max(V,this._holdClsp-1)}}>−</button>
                  <span class="sp-val sp-cool">${this._holdClsp}°</span>
                  <button class="btn-adj" @click=${()=>{this._holdClsp=Math.min(q,this._holdClsp+1)}}>+</button>
                  </div>
                  <div style="display:flex;align-items:center;gap:4px">
                    <span style="font-size:10px;color:var(--secondary-text-color)">Fan</span>
                    <select class="hold-dur-select" style="width:auto" .value=${this._holdFan} @change=${y=>{this._holdFan=y.target.value}}>
                      <option value="auto">Auto</option>
                      <option value="low">Low</option>
                      <option value="med">Med</option>
                      <option value="high">High</option>
                    </select>
                  </div>
                </div>`:p}
              <div class="hold-picker-row">
                <select class="hold-dur-select" @change=${y=>{this._holdDuration=y.target.value}}>
                  ${L.map(y=>r`<option value=${y.v} ?selected=${y.v===this._holdDuration}>${y.l}</option>`)}
                </select>
                ${this._holdDuration==="custom"?r`
                  <input type="time" class="hold-time-input" step="900" .value=${this._holdCustom}
                         @change=${y=>{this._holdCustom=y.target.value}}>`:p}
              </div>
              <div class="hold-picker-row">
                <button class="btn btn-primary" style="font-size:11px;padding:4px 12px" @click=${()=>this._setZoneHold(t)}>Apply</button>
                <button class="btn" style="font-size:11px;padding:4px 10px" @click=${()=>{this._holdOpen=!1}}>Cancel</button>
              </div>
            </div>`:v?p:r`
            <div class="zone-actions">
              <button class="btn" style="font-size:11px;padding:4px 12px" @click=${()=>{this._holdActivity=a!=="\u2013"?a:"home",this._holdDuration="120",this._holdCustom="",this._holdActivity==="manual"&&this._initHoldManual(t),this._holdOpen=!0}}>Set hold</button>
            </div>`}
        </div>
      </ha-card>`}};customElements.get("infinitude-zone-card")||customElements.define("infinitude-zone-card",$t);window.customCards=window.customCards||[];window.customCards.some(l=>l.type==="infinitude-zone-card")||window.customCards.push({type:"infinitude-zone-card",name:"Infinitude Zone",description:"Single zone control for Carrier/Bryant Infinity thermostat",preview:!1});var wt=class extends w{static properties={...w.baseProperties,_schedDay:{state:!0},_schedEdits:{state:!0}};constructor(){super(),this._schedDay=z[Z[new Date().getDay()]],this._schedEdits={},this._saving=!1}static getConfigElement(){return document.createElement("div")}static getStubConfig(){return{}}getCardSize(){return 6}static styles=[M,C`
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
  `];render(){if(!this.hass)return p;if(!this._registryLoaded)return this._renderLoading();let t=this._getScheduleData(),e=this._getProfilesData(),s=Object.keys(t);if(!s.length)return r`<ha-card>
      <div class="card-pad" style="text-align:center;color:var(--secondary-text-color)">
        <ha-icon icon="mdi:calendar-clock" style="--mdc-icon-size:48px;opacity:0.3;margin-bottom:12px;display:block"></ha-icon>
        No schedule data available.
      </div></ha-card>`;let i=z[Z[new Date().getDay()]],o={},n={};for(let a=0;a<e.length;a++)o[e[a].id]=e[a].name,n[e[a].id]=a;let d=0;for(let a of s)d=Math.max(d,(t[a]?.[this._schedDay]||[]).length);d||(d=5);let c=Object.keys(this._schedEdits).length>0;return r`
      <ha-card>
        <div class="card-pad">
          <div class="section-title">Schedule</div>
          ${s.length>1?r`<div class="zone-legend">${s.map((a,h)=>r`<span class="legend-item"><span class="legend-num">${H[h]||h+1}</span> ${o[a]||`Zone ${a}`}</span>`)}</div>`:p}
          <div class="sched-day-tabs">
            ${z.map(a=>r`
              <div class="day-tab ${a===this._schedDay?"active":""} ${a===i&&a!==this._schedDay?"today":""}"
                   @click=${()=>{this._schedDay=a}}>${a.slice(0,3)}</div>`)}
          </div>
          ${Array.from({length:d},(a,h)=>this._periodCard(h,s,t,e,o,n))}
          <div class="copy-bar">
            <span>Copy ${this._schedDay.slice(0,3)} →</span>
            <select class="sched-select" @change=${a=>this._copySched(a)}>
              <option value="">select day…</option>
              ${z.filter(a=>a!==this._schedDay).map(a=>r`<option value=${a}>${a.slice(0,3)}</option>`)}
              <option value="__all__">All other days</option>
            </select>
          </div>
          ${c?r`
            <div class="action-bar">
              <span class="action-bar-label">● Unsaved changes</span>
              <button class="btn" @click=${()=>{this._schedEdits={}}}>Discard</button>
              <button class="btn btn-primary" @click=${()=>this._saveSched()}>Save schedule</button>
            </div>`:p}
        </div>
      </ha-card>`}};customElements.get("infinitude-schedule-card")||customElements.define("infinitude-schedule-card",wt);window.customCards=window.customCards||[];window.customCards.some(l=>l.type==="infinitude-schedule-card")||window.customCards.push({type:"infinitude-schedule-card",name:"Infinitude Schedule",description:"Weekly schedule editing for Carrier/Bryant Infinity thermostat",preview:!1});var At=class extends w{static properties={...w.baseProperties,_profileEdits:{state:!0}};constructor(){super(),this._profileEdits={},this._savingProfs=!1}static getConfigElement(){return document.createElement("div")}static getStubConfig(){return{}}getCardSize(){return 6}static styles=[M,C`
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
  `];render(){if(!this.hass)return p;if(!this._registryLoaded)return this._renderLoading();let t=this._getProfilesData();if(!t.length)return r`<ha-card>
      <div class="card-pad" style="text-align:center;color:var(--secondary-text-color)">
        <ha-icon icon="mdi:tune-vertical" style="--mdc-icon-size:48px;opacity:0.3;margin-bottom:12px;display:block"></ha-icon>
        No profile data available.
      </div></ha-card>`;let e=t.length>1,s=Object.keys(this._profileEdits).length>0;return r`
      <ha-card>
        <div class="card-pad">
          <div class="section-title">Comfort Profiles</div>
          ${e?r`<div class="zone-legend">${t.map((i,o)=>r`<span class="legend-item"><span class="legend-num">${H[o]||o+1}</span> ${i.name}</span>`)}</div>`:p}
          ${P.map(i=>r`
            <div class="prof-card">
              <div class="prof-header">${i}</div>
              ${t.map((o,n)=>{let d=o.activities?.[i]||{},c=`${o.id}_${i}`,a=this._profileEdits[c],h=a?.htsp??(d.htsp?Math.round(Number(d.htsp)||x):x),u=a?.clsp??(d.clsp?Math.round(Number(d.clsp)||$):$),f=a?.fan??d.fan??"low",v=e?H[n]||n+1:o.name;return r`
                  <div class="prof-line">
                    <span class="prof-name ${e?"prof-name-compact":""}">${v}</span>
                    <div class="sp-row">
                      <button class="btn-adj" @click=${()=>this._profAdj(o.id,i,"htsp",-1)}>−</button>
                      <span class="sp-val sp-heat">${h}°</span>
                      <button class="btn-adj" @click=${()=>this._profAdj(o.id,i,"htsp",1)}>+</button>
                    </div>
                    <div class="sp-row">
                      <button class="btn-adj" @click=${()=>this._profAdj(o.id,i,"clsp",-1)}>−</button>
                      <span class="sp-val sp-cool">${u}°</span>
                      <button class="btn-adj" @click=${()=>this._profAdj(o.id,i,"clsp",1)}>+</button>
                    </div>
                    <div class="prof-fan">
                      <span class="prof-fan-label">Fan</span>
                      <select class="sched-select" .value=${f} @change=${g=>this._profFan(o.id,i,g.target.value)}>
                        ${rt.map(g=>r`<option value=${g} ?selected=${g===f}>${g}</option>`)}
                      </select>
                    </div>
                  </div>`})}
            </div>`)}
          ${s?r`
            <div class="action-bar">
              <span class="action-bar-label">● Unsaved changes</span>
              <button class="btn" @click=${()=>{this._profileEdits={}}}>Discard</button>
              <button class="btn btn-primary" @click=${()=>this._saveProfs()}>Save profiles</button>
            </div>`:p}
        </div>
      </ha-card>`}};customElements.get("infinitude-profiles-card")||customElements.define("infinitude-profiles-card",At);window.customCards=window.customCards||[];window.customCards.some(l=>l.type==="infinitude-profiles-card")||window.customCards.push({type:"infinitude-profiles-card",name:"Infinitude Profiles",description:"Comfort profile editing for Carrier/Bryant Infinity thermostat",preview:!1});var Et=class extends w{static properties={...w.baseProperties,_tab:{state:!0},_schedDay:{state:!0},_schedEdits:{state:!0},_profileEdits:{state:!0},_pendingTemps:{state:!0},_whHoldOpen:{state:!0},_whHoldActivity:{state:!0},_whHoldDuration:{state:!0},_whHoldCustom:{state:!0},_holdOpen:{state:!0},_holdActivity:{state:!0},_holdDuration:{state:!0},_holdCustom:{state:!0},_holdHtsp:{state:!0},_holdClsp:{state:!0},_holdFan:{state:!0}};constructor(){super(),this._tab="status",this._schedDay=z[Z[new Date().getDay()]],this._schedEdits={},this._profileEdits={},this._tempAdj={},this._pendingTemps={},this._whHoldOpen=!1,this._whHoldActivity="home",this._whHoldDuration="120",this._whHoldCustom="",this._holdOpen=null,this._holdActivity="home",this._holdDuration="120",this._holdCustom="",this._holdHtsp=x,this._holdClsp=$,this._holdFan="auto",this._saving=!1,this._savingProfs=!1,this._lastEntityUpdate=0}updated(t){super.updated(t),t.has("hass")&&this.hass&&(this._lastEntityUpdate=Date.now())}connectedCallback(){super.connectedCallback(),this._staleTimer=setInterval(()=>this.requestUpdate(),3e4)}disconnectedCallback(){super.disconnectedCallback(),clearInterval(this._staleTimer)}static getConfigElement(){return document.createElement("div")}static getStubConfig(){return{}}getCardSize(){return 8}static styles=[M,C`
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
  `];render(){if(!this.hass)return p;if(!this._registryLoaded)return r`<ha-card>
        <div style="padding:24px;text-align:center;color:var(--secondary-text-color)">Loading…</div>
      </ha-card>`;let t=this._findEntities();return!t.climates.length&&!this._config.show_empty?r`<ha-card>
        <div style="padding:24px;text-align:center;color:var(--secondary-text-color)">
          <ha-icon icon="mdi:thermostat" style="--mdc-icon-size:48px;opacity:0.3;margin-bottom:12px;display:block"></ha-icon>
          <div style="font-size:14px;font-weight:500">No Infinitude entities found</div>
          <div style="font-size:12px;margin-top:4px">Waiting for thermostat connection…</div>
        </div>
      </ha-card>`:r`
      <ha-card>
        <div class="card-header">${this._hdr(t)}</div>
        <div class="card-tabs">${this._tabs()}</div>
        <div class="card-content">
          ${this._tab==="status"?this._status(t):p}
          ${this._tab==="schedule"?this._sched():p}
          ${this._tab==="profiles"?this._profs():p}
        </div>
      </ha-card>`}_hdr(t){let{system:e}=t,s=e.info?this._st(e.info)?.state!=="unavailable":!1,i=e.info?this._at(e.info,"carrier_ok"):null;return r`
      <div class="header-left">
        <span class="header-title">infinitude</span>
        <span class="conn-dot ${s?"ok":"err"}" title="${s?"Infinitude: connected":"Infinitude: unavailable"}"></span>
        <span class="conn-dot ${i===!0?"ok":i===!1?"err":"unk"}" title="${i===!0?"Carrier cloud: connected":i===!1?"Carrier cloud: unreachable":"Carrier cloud: checking\u2026"}"></span>
        <span style="font-size:10px;color:var(--secondary-text-color);opacity:0.5">v${at}</span>
      </div>`}_tabs(){return r`${["status","schedule","profiles"].map(e=>r`
      <div class="tab ${this._tab===e?"active":""}"
           @click=${()=>{this._tab=e}}>${e.charAt(0).toUpperCase()+e.slice(1)}</div>`)}`}_status(t){let{climates:e}=t;return e.length?r`
      ${this._summaryStrip(t)}
      <div class="zone-grid">${e.map(s=>this._zoneCard(s))}</div>`:r`<div style="padding:20px;text-align:center;color:var(--secondary-text-color)">No zone entities found</div>`}_summaryStrip(t){let{system:e,selects:s,climates:i}=t,o=i.length&&this._st(i[0])?.state||"off",n=["off","heat","cool","heat_cool"],d={off:"Off",heat:"Heat",cool:"Cool",heat_cool:"Auto"},c=this._st(e.oat),a="\u2013";if(c?.state&&c.state!=="unavailable")a=`${Math.round(Number(c.state))}\xB0`;else if(i.length){let m=this._at(i[0],"outdoor_temperature");m!=null&&(a=`${Math.round(Number(m))}\xB0`)}let h=this._st(e.opStatus),u=h?.state&&h.state!=="unavailable"?h.state:"",f=this._st(e.humidifier)?.state==="on",v=this._st(s.wholeHouse),g=v&&v.state!=="off",S=i.length?this._at(i[0],"whole_house_hold_until"):null,A=i.length?this._at(i[0],"current_humidity"):null,k=i.some(m=>this._at(m,"hvac_action")==="heating"),E=i.some(m=>this._at(m,"hvac_action")==="cooling"),_=i.some(m=>this._at(m,"hvac_action")==="drying"),b=k?"Heating":E?"Cooling":_?"Dehumidifying":u||"Idle",y=k?"heat":E?"cool":"",kt=this._lastEntityUpdate>0&&Date.now()-this._lastEntityUpdate>18e4;return r`
      <div class="mode-row">
        <span class="mode-label">Mode</span>
        <div class="mode-pills">
          ${n.map(m=>r`<div class="mode-pill ${m===o?"active":""} ${m==="heat"?"heat":m==="cool"?"cool":m==="heat_cool"?"auto":""}"
              @click=${()=>this._setHvacMode(i[0],m)}>${d[m]}</div>`)}
        </div>
      </div>
      <div class="summary-stats">
        <div class="summary-stat">
          <span class="summary-stat-label">Status</span>
          <span class="summary-stat-val ${y}">${b}</span>
        </div>
        <div class="summary-divider"></div>
        <div class="summary-stat">
          <span class="summary-stat-label">Outdoor</span>
          <span class="summary-stat-val">${a}</span>
        </div>
        <div class="summary-divider"></div>
        <div class="summary-stat">
          <span class="summary-stat-label">Humidity</span>
          <span class="summary-stat-val">${A!=null?`${A}%`:"\u2013"}</span>
        </div>
        ${f?r`
          <div class="summary-divider"></div>
          <div class="summary-stat">
            <span class="summary-stat-label">Humidifier</span>
            <span class="summary-stat-val" style="color:var(--label-badge-blue,#38bdf8)">💧 On</span>
          </div>`:p}
      </div>
      ${kt?r`<div class="stale-warn">⚠ Thermostat data is stale — system may be offline</div>`:p}
      ${g?r`
        <div class="wh-hold" @click=${()=>this._cancelWholeHouseHold()}>
          <ha-icon icon="mdi:home-lock" style="--mdc-icon-size:16px"></ha-icon>
          <span>Whole house: <strong>${v.state}</strong>${S?r` · <span style="opacity:0.85">${this._otmrRelative(S)}</span>`:p}</span>
          <span style="margin-left:auto;opacity:0.7">Tap to cancel</span>
        </div>`:r`
        ${this._whHoldOpen?r`
          <div class="wh-set">
            <span class="wh-set-label">WH Hold</span>
            <div class="wh-pills">
              ${P.map(m=>r`
                <div class="wh-pill ${this._whHoldActivity===m?"active":""}"
                     @click=${()=>{this._whHoldActivity=m}}>${m}</div>`)}
            </div>
            <select class="hold-dur-select" @change=${m=>{this._whHoldDuration=m.target.value}}>
              ${L.map(m=>r`<option value=${m.v} ?selected=${m.v===this._whHoldDuration}>${m.l}</option>`)}
            </select>
            ${this._whHoldDuration==="custom"?r`
              <input type="time" class="hold-time-input" step="900" .value=${this._whHoldCustom}
                     @change=${m=>{this._whHoldCustom=m.target.value}}>`:p}
            <button class="btn btn-primary" style="font-size:11px;padding:4px 12px" @click=${()=>this._setWholeHouseHold()}>Apply</button>
            <button class="btn" style="font-size:11px;padding:4px 10px" @click=${()=>{this._whHoldOpen=!1}}>Cancel</button>
          </div>`:r`
          <div>
            <button class="btn" style="font-size:11px;padding:4px 12px" @click=${()=>{this._whHoldOpen=!0}}>
              <ha-icon icon="mdi:home-lock" style="--mdc-icon-size:14px;vertical-align:middle;margin-right:4px"></ha-icon>Set WH hold
            </button>
          </div>`}
      `}`}_zoneCard(t){let e=this._st(t);if(!e)return p;let s=e.attributes||{},i=(s.friendly_name||t).replace(/^Infinitude\s+/i,"").replace(/^infinitude_direct\s+/i,""),o=s.current_temperature!=null?Math.round(s.current_temperature):"\u2013",n=s.current_humidity,d=e.state||"off",c=s.hvac_action||"idle",a=s.preset_mode||"\u2013",h=c==="heating"?"heating":c==="cooling"?"cooling":c==="drying"?"drying":"",u=c==="idle"?"Idle":c.charAt(0).toUpperCase()+c.slice(1),f=d==="heat_cool",v=!!s.hold_active,g=s.hold_activity||a,S=s.hold_until,A=this._holdOpen===t,k=this._pendingTemps[t],E=this._hasPending(t),_=k?.heat??s.target_temp_low??s.temperature??null,b=k?.cool??s.target_temp_high??(d==="cool"?s.temperature:null)??null;return r`
      <div class="zone-card ${h}">
        <div class="zone-top">
          <div style="display:flex;align-items:center;gap:8px">
            <span class="zone-cond-dot ${h||"idle"}" title="${c==="drying"?"Dehumidifying":u}"></span>
            <span class="zone-name">${i}</span>
          </div>
          <span class="zone-activity-pill">${a}</span>
        </div>
        <div class="zone-body">
          <div>
            <span class="temp-hero">${o}</span><span class="temp-unit">°F</span>
          </div>
          <div class="zone-sp">
            ${_!=null?r`
              <div class="sp-row">
                <button class="btn-adj" @click=${()=>this._adjustTemp(t,-1,"heat")}>−</button>
                <span class="sp-val sp-heat ${E?"sp-pending":""}">${Math.round(_)}°</span>
                <button class="btn-adj" @click=${()=>this._adjustTemp(t,1,"heat")}>+</button>
              </div>`:p}
            ${f&&b!=null?r`
              <div class="sp-row">
                <button class="btn-adj" @click=${()=>this._adjustTemp(t,-1,"cool")}>−</button>
                <span class="sp-val sp-cool ${E?"sp-pending":""}">${Math.round(b)}°</span>
                <button class="btn-adj" @click=${()=>this._adjustTemp(t,1,"cool")}>+</button>
              </div>`:p}
          </div>
        </div>
        <div class="zone-meta">
          ${n!=null?r`<span class="meta-item">RH <span class="meta-val">${n}%</span></span>`:p}
          ${s.fan_mode?r`<span class="meta-item">Fan <span class="meta-val">${s.fan_mode}</span></span>`:p}
          ${s.damper_position!=null?r`<span class="meta-item">Damper <span class="meta-val">${s.damper_position}%</span></span>`:p}
        </div>
        ${v?r`
          <div class="zone-hold">
            <span class="hold-label">Hold: ${g}${S?` \xB7 ${this._otmrRelative(S)}`:""}</span>
            <button class="btn" style="font-size:11px;padding:3px 10px;color:var(--error-color,#f87171)" @click=${()=>this._cancelHold(t)}>Cancel</button>
          </div>`:p}
        ${A?r`
          <div class="zone-hold-picker">
            <div class="hold-picker-row">
              <div class="wh-pills">
                ${nt.map(m=>r`
                  <div class="wh-pill ${this._holdActivity===m?"active":""}"
                       @click=${()=>{this._holdActivity=m,m==="manual"&&this._initHoldManual(t)}}>${m}</div>`)}
              </div>
            </div>
            ${this._holdActivity==="manual"?r`
              <div class="hold-picker-row" style="gap:10px;flex-wrap:wrap">
                <div class="sp-row">
                  <button class="btn-adj" @click=${()=>{this._holdHtsp=Math.max(W,this._holdHtsp-1)}}>−</button>
                  <span class="sp-val sp-heat">${this._holdHtsp}°</span>
                  <button class="btn-adj" @click=${()=>{this._holdHtsp=Math.min(B,this._holdHtsp+1)}}>+</button>
                </div>
                <div class="sp-row">
                  <button class="btn-adj" @click=${()=>{this._holdClsp=Math.max(V,this._holdClsp-1)}}>−</button>
                  <span class="sp-val sp-cool">${this._holdClsp}°</span>
                  <button class="btn-adj" @click=${()=>{this._holdClsp=Math.min(q,this._holdClsp+1)}}>+</button>
                </div>
                <div style="display:flex;align-items:center;gap:4px">
                  <span style="font-size:10px;color:var(--secondary-text-color)">Fan</span>
                  <select class="hold-dur-select" style="width:auto" .value=${this._holdFan} @change=${m=>{this._holdFan=m.target.value}}>
                    <option value="auto">Auto</option>
                    <option value="low">Low</option>
                    <option value="med">Med</option>
                    <option value="high">High</option>
                  </select>
                </div>
              </div>`:p}
            <div class="hold-picker-row">
              <select class="hold-dur-select" @change=${m=>{this._holdDuration=m.target.value}}>
                ${L.map(m=>r`<option value=${m.v} ?selected=${m.v===this._holdDuration}>${m.l}</option>`)}
              </select>
              ${this._holdDuration==="custom"?r`
                <input type="time" class="hold-time-input" step="900" .value=${this._holdCustom}
                       @change=${m=>{this._holdCustom=m.target.value}}>`:p}
            </div>
            <div class="hold-picker-row">
              <button class="btn btn-primary" style="font-size:11px;padding:4px 12px" @click=${()=>this._setZoneHold(t)}>Apply</button>
              <button class="btn" style="font-size:11px;padding:4px 10px" @click=${()=>{this._holdOpen=null}}>Cancel</button>
            </div>
          </div>`:v?p:r`
          <div class="zone-actions">
            <button class="btn" style="font-size:11px;padding:4px 12px" @click=${()=>{this._holdActivity=a!=="\u2013"?a:"home",this._holdDuration="120",this._holdCustom="",this._holdActivity==="manual"&&this._initHoldManual(t),this._holdOpen=t}}>Set hold</button>
          </div>`}
      </div>`}_sched(){let t=this._getScheduleData(),e=this._getProfilesData(),s=Object.keys(t);if(!s.length)return r`
      <div style="padding:20px;text-align:center;color:var(--secondary-text-color)">
        <ha-icon icon="mdi:calendar-clock" style="--mdc-icon-size:48px;opacity:0.3;margin-bottom:12px;display:block"></ha-icon>
        No schedule data available. Waiting for thermostat data…
      </div>`;let i=z[Z[new Date().getDay()]],o={},n={};for(let a=0;a<e.length;a++)o[e[a].id]=e[a].name,n[e[a].id]=a;let d=0;for(let a of s)d=Math.max(d,(t[a]?.[this._schedDay]||[]).length);d||(d=5);let c=Object.keys(this._schedEdits).length>0;return r`
      <div class="section-title">Schedule</div>
      ${s.length>1?r`<div class="zone-legend">${s.map((a,h)=>r`<span class="legend-item"><span class="legend-num">${H[h]||h+1}</span> ${o[a]||`Zone ${a}`}</span>`)}</div>`:p}
      <div class="sched-day-tabs">
        ${z.map(a=>r`
          <div class="day-tab ${a===this._schedDay?"active":""} ${a===i&&a!==this._schedDay?"today":""}"
               @click=${()=>{this._schedDay=a}}>${a.slice(0,3)}</div>`)}
      </div>
      ${Array.from({length:d},(a,h)=>this._periodCard(h,s,t,e,o,n))}
      <div class="copy-bar">
        <span>Copy ${this._schedDay.slice(0,3)} →</span>
        <select class="sched-select" @change=${a=>this._copySched(a)}>
          <option value="">select day…</option>
          ${z.filter(a=>a!==this._schedDay).map(a=>r`<option value=${a}>${a.slice(0,3)}</option>`)}
          <option value="__all__">All other days</option>
        </select>
      </div>
      ${c?r`
        <div class="action-bar">
          <span class="action-bar-label">● Unsaved changes</span>
          <button class="btn" @click=${()=>{this._schedEdits={}}}>Discard</button>
          <button class="btn btn-primary" @click=${()=>this._saveSched()}>Save schedule</button>
        </div>`:p}`}_profs(){let t=this._getProfilesData();if(!t.length)return r`
      <div style="padding:20px;text-align:center;color:var(--secondary-text-color)">
        <ha-icon icon="mdi:tune-vertical" style="--mdc-icon-size:48px;opacity:0.3;margin-bottom:12px;display:block"></ha-icon>
        No profile data available. Waiting for thermostat data…
      </div>`;let e=t.length>1,s=Object.keys(this._profileEdits).length>0;return r`
      <div class="section-title">Comfort Profiles</div>
      ${e?r`<div class="zone-legend">${t.map((i,o)=>r`<span class="legend-item"><span class="legend-num">${H[o]||o+1}</span> ${i.name}</span>`)}</div>`:p}
      ${P.map(i=>r`
        <div class="prof-card">
          <div class="prof-header">${i}</div>
          ${t.map((o,n)=>{let d=o.activities?.[i]||{},c=`${o.id}_${i}`,a=this._profileEdits[c],h=a?.htsp??(d.htsp?Math.round(Number(d.htsp)||x):x),u=a?.clsp??(d.clsp?Math.round(Number(d.clsp)||$):$),f=a?.fan??d.fan??"low",v=e?H[n]||n+1:o.name;return r`
              <div class="prof-line">
                <span class="prof-name ${e?"prof-name-compact":""}">${v}</span>
                <div class="sp-row">
                  <button class="btn-adj" @click=${()=>this._profAdj(o.id,i,"htsp",-1)}>−</button>
                  <span class="sp-val sp-heat">${h}°</span>
                  <button class="btn-adj" @click=${()=>this._profAdj(o.id,i,"htsp",1)}>+</button>
                </div>
                <div class="sp-row">
                  <button class="btn-adj" @click=${()=>this._profAdj(o.id,i,"clsp",-1)}>−</button>
                  <span class="sp-val sp-cool">${u}°</span>
                  <button class="btn-adj" @click=${()=>this._profAdj(o.id,i,"clsp",1)}>+</button>
                </div>
                <div class="prof-fan">
                  <span class="prof-fan-label">Fan</span>
                  <select class="sched-select" .value=${f} @change=${g=>this._profFan(o.id,i,g.target.value)}>
                    ${rt.map(g=>r`<option value=${g} ?selected=${g===f}>${g}</option>`)}
                  </select>
                </div>
              </div>`})}
        </div>`)}
      ${s?r`
        <div class="action-bar">
          <span class="action-bar-label">● Unsaved changes</span>
          <button class="btn" @click=${()=>{this._profileEdits={}}}>Discard</button>
          <button class="btn btn-primary" @click=${()=>this._saveProfs()}>Save profiles</button>
        </div>`:p}`}};customElements.get("infinitude-hvac-card")||customElements.define("infinitude-hvac-card",Et);window.customCards=window.customCards||[];window.customCards.some(l=>l.type==="infinitude-hvac-card")||window.customCards.push({type:"infinitude-hvac-card",name:"Infinitude HVAC Card",description:"Full HVAC dashboard for Carrier/Bryant Infinity thermostats",preview:!1});
/*! Bundled license information:

@lit/reactive-element/css-tag.js:
  (**
   * @license
   * Copyright 2019 Google LLC
   * SPDX-License-Identifier: BSD-3-Clause
   *)

@lit/reactive-element/reactive-element.js:
lit-html/lit-html.js:
lit-element/lit-element.js:
  (**
   * @license
   * Copyright 2017 Google LLC
   * SPDX-License-Identifier: BSD-3-Clause
   *)

lit-html/is-server.js:
  (**
   * @license
   * Copyright 2022 Google LLC
   * SPDX-License-Identifier: BSD-3-Clause
   *)
*/
