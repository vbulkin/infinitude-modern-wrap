var U=globalThis,N=U.ShadowRoot&&(U.ShadyCSS===void 0||U.ShadyCSS.nativeShadow)&&"adoptedStyleSheets"in Document.prototype&&"replace"in CSSStyleSheet.prototype,B=Symbol(),rt=new WeakMap,H=class{constructor(t,e,s){if(this._$cssResult$=!0,s!==B)throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");this.cssText=t,this.t=e}get styleSheet(){let t=this.o,e=this.t;if(N&&t===void 0){let s=e!==void 0&&e.length===1;s&&(t=rt.get(e)),t===void 0&&((this.o=t=new CSSStyleSheet).replaceSync(this.cssText),s&&rt.set(e,t))}return t}toString(){return this.cssText}},at=n=>new H(typeof n=="string"?n:n+"",void 0,B),I=(n,...t)=>{let e=n.length===1?n[0]:t.reduce((s,o,r)=>s+(i=>{if(i._$cssResult$===!0)return i.cssText;if(typeof i=="number")return i;throw Error("Value passed to 'css' function must be a 'css' function result: "+i+". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.")})(o)+n[r+1],n[0]);return new H(e,n,B)},nt=(n,t)=>{if(N)n.adoptedStyleSheets=t.map(e=>e instanceof CSSStyleSheet?e:e.styleSheet);else for(let e of t){let s=document.createElement("style"),o=U.litNonce;o!==void 0&&s.setAttribute("nonce",o),s.textContent=e.cssText,n.appendChild(s)}},V=N?n=>n:n=>n instanceof CSSStyleSheet?(t=>{let e="";for(let s of t.cssRules)e+=s.cssText;return at(e)})(n):n;var{is:At,defineProperty:Et,getOwnPropertyDescriptor:St,getOwnPropertyNames:kt,getOwnPropertySymbols:zt,getPrototypeOf:Ct}=Object,R=globalThis,ct=R.trustedTypes,Ht=ct?ct.emptyScript:"",Pt=R.reactiveElementPolyfillSupport,P=(n,t)=>n,q={toAttribute(n,t){switch(t){case Boolean:n=n?Ht:null;break;case Object:case Array:n=n==null?n:JSON.stringify(n)}return n},fromAttribute(n,t){let e=n;switch(t){case Boolean:e=n!==null;break;case Number:e=n===null?null:Number(n);break;case Object:case Array:try{e=JSON.parse(n)}catch{e=null}}return e}},dt=(n,t)=>!At(n,t),lt={attribute:!0,type:String,converter:q,reflect:!1,useDefault:!1,hasChanged:dt};Symbol.metadata??=Symbol("metadata"),R.litPropertyMetadata??=new WeakMap;var b=class extends HTMLElement{static addInitializer(t){this._$Ei(),(this.l??=[]).push(t)}static get observedAttributes(){return this.finalize(),this._$Eh&&[...this._$Eh.keys()]}static createProperty(t,e=lt){if(e.state&&(e.attribute=!1),this._$Ei(),this.prototype.hasOwnProperty(t)&&((e=Object.create(e)).wrapped=!0),this.elementProperties.set(t,e),!e.noAccessor){let s=Symbol(),o=this.getPropertyDescriptor(t,s,e);o!==void 0&&Et(this.prototype,t,o)}}static getPropertyDescriptor(t,e,s){let{get:o,set:r}=St(this.prototype,t)??{get(){return this[e]},set(i){this[e]=i}};return{get:o,set(i){let c=o?.call(this);r?.call(this,i),this.requestUpdate(t,c,s)},configurable:!0,enumerable:!0}}static getPropertyOptions(t){return this.elementProperties.get(t)??lt}static _$Ei(){if(this.hasOwnProperty(P("elementProperties")))return;let t=Ct(this);t.finalize(),t.l!==void 0&&(this.l=[...t.l]),this.elementProperties=new Map(t.elementProperties)}static finalize(){if(this.hasOwnProperty(P("finalized")))return;if(this.finalized=!0,this._$Ei(),this.hasOwnProperty(P("properties"))){let e=this.properties,s=[...kt(e),...zt(e)];for(let o of s)this.createProperty(o,e[o])}let t=this[Symbol.metadata];if(t!==null){let e=litPropertyMetadata.get(t);if(e!==void 0)for(let[s,o]of e)this.elementProperties.set(s,o)}this._$Eh=new Map;for(let[e,s]of this.elementProperties){let o=this._$Eu(e,s);o!==void 0&&this._$Eh.set(o,e)}this.elementStyles=this.finalizeStyles(this.styles)}static finalizeStyles(t){let e=[];if(Array.isArray(t)){let s=new Set(t.flat(1/0).reverse());for(let o of s)e.unshift(V(o))}else t!==void 0&&e.push(V(t));return e}static _$Eu(t,e){let s=e.attribute;return s===!1?void 0:typeof s=="string"?s:typeof t=="string"?t.toLowerCase():void 0}constructor(){super(),this._$Ep=void 0,this.isUpdatePending=!1,this.hasUpdated=!1,this._$Em=null,this._$Ev()}_$Ev(){this._$ES=new Promise(t=>this.enableUpdating=t),this._$AL=new Map,this._$E_(),this.requestUpdate(),this.constructor.l?.forEach(t=>t(this))}addController(t){(this._$EO??=new Set).add(t),this.renderRoot!==void 0&&this.isConnected&&t.hostConnected?.()}removeController(t){this._$EO?.delete(t)}_$E_(){let t=new Map,e=this.constructor.elementProperties;for(let s of e.keys())this.hasOwnProperty(s)&&(t.set(s,this[s]),delete this[s]);t.size>0&&(this._$Ep=t)}createRenderRoot(){let t=this.shadowRoot??this.attachShadow(this.constructor.shadowRootOptions);return nt(t,this.constructor.elementStyles),t}connectedCallback(){this.renderRoot??=this.createRenderRoot(),this.enableUpdating(!0),this._$EO?.forEach(t=>t.hostConnected?.())}enableUpdating(t){}disconnectedCallback(){this._$EO?.forEach(t=>t.hostDisconnected?.())}attributeChangedCallback(t,e,s){this._$AK(t,s)}_$ET(t,e){let s=this.constructor.elementProperties.get(t),o=this.constructor._$Eu(t,s);if(o!==void 0&&s.reflect===!0){let r=(s.converter?.toAttribute!==void 0?s.converter:q).toAttribute(e,s.type);this._$Em=t,r==null?this.removeAttribute(o):this.setAttribute(o,r),this._$Em=null}}_$AK(t,e){let s=this.constructor,o=s._$Eh.get(t);if(o!==void 0&&this._$Em!==o){let r=s.getPropertyOptions(o),i=typeof r.converter=="function"?{fromAttribute:r.converter}:r.converter?.fromAttribute!==void 0?r.converter:q;this._$Em=o;let c=i.fromAttribute(e,r.type);this[o]=c??this._$Ej?.get(o)??c,this._$Em=null}}requestUpdate(t,e,s,o=!1,r){if(t!==void 0){let i=this.constructor;if(o===!1&&(r=this[t]),s??=i.getPropertyOptions(t),!((s.hasChanged??dt)(r,e)||s.useDefault&&s.reflect&&r===this._$Ej?.get(t)&&!this.hasAttribute(i._$Eu(t,s))))return;this.C(t,e,s)}this.isUpdatePending===!1&&(this._$ES=this._$EP())}C(t,e,{useDefault:s,reflect:o,wrapped:r},i){s&&!(this._$Ej??=new Map).has(t)&&(this._$Ej.set(t,i??e??this[t]),r!==!0||i!==void 0)||(this._$AL.has(t)||(this.hasUpdated||s||(e=void 0),this._$AL.set(t,e)),o===!0&&this._$Em!==t&&(this._$Eq??=new Set).add(t))}async _$EP(){this.isUpdatePending=!0;try{await this._$ES}catch(e){Promise.reject(e)}let t=this.scheduleUpdate();return t!=null&&await t,!this.isUpdatePending}scheduleUpdate(){return this.performUpdate()}performUpdate(){if(!this.isUpdatePending)return;if(!this.hasUpdated){if(this.renderRoot??=this.createRenderRoot(),this._$Ep){for(let[o,r]of this._$Ep)this[o]=r;this._$Ep=void 0}let s=this.constructor.elementProperties;if(s.size>0)for(let[o,r]of s){let{wrapped:i}=r,c=this[o];i!==!0||this._$AL.has(o)||c===void 0||this.C(o,void 0,r,c)}}let t=!1,e=this._$AL;try{t=this.shouldUpdate(e),t?(this.willUpdate(e),this._$EO?.forEach(s=>s.hostUpdate?.()),this.update(e)):this._$EM()}catch(s){throw t=!1,this._$EM(),s}t&&this._$AE(e)}willUpdate(t){}_$AE(t){this._$EO?.forEach(e=>e.hostUpdated?.()),this.hasUpdated||(this.hasUpdated=!0,this.firstUpdated(t)),this.updated(t)}_$EM(){this._$AL=new Map,this.isUpdatePending=!1}get updateComplete(){return this.getUpdateComplete()}getUpdateComplete(){return this._$ES}shouldUpdate(t){return!0}update(t){this._$Eq&&=this._$Eq.forEach(e=>this._$ET(e,this[e])),this._$EM()}updated(t){}firstUpdated(t){}};b.elementStyles=[],b.shadowRootOptions={mode:"open"},b[P("elementProperties")]=new Map,b[P("finalized")]=new Map,Pt?.({ReactiveElement:b}),(R.reactiveElementVersions??=[]).push("2.1.2");var X=globalThis,pt=n=>n,L=X.trustedTypes,ht=L?L.createPolicy("lit-html",{createHTML:n=>n}):void 0,vt="$lit$",y=`lit$${Math.random().toFixed(9).slice(2)}$`,bt="?"+y,Mt=`<${bt}>`,E=document,O=()=>E.createComment(""),j=n=>n===null||typeof n!="object"&&typeof n!="function",tt=Array.isArray,Ot=n=>tt(n)||typeof n?.[Symbol.iterator]=="function",J=`[ 	
\f\r]`,M=/<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g,ut=/-->/g,ft=/>/g,w=RegExp(`>|${J}(?:([^\\s"'>=/]+)(${J}*=${J}*(?:[^ 	
\f\r"'\`<>=]|("|')|))|$)`,"g"),mt=/'/g,gt=/"/g,yt=/^(?:script|style|textarea|title)$/i,et=n=>(t,...e)=>({_$litType$:n,strings:t,values:e}),h=et(1),Bt=et(2),It=et(3),S=Symbol.for("lit-noChange"),u=Symbol.for("lit-nothing"),_t=new WeakMap,A=E.createTreeWalker(E,129);function xt(n,t){if(!tt(n)||!n.hasOwnProperty("raw"))throw Error("invalid template strings array");return ht!==void 0?ht.createHTML(t):t}var jt=(n,t)=>{let e=n.length-1,s=[],o,r=t===2?"<svg>":t===3?"<math>":"",i=M;for(let c=0;c<e;c++){let a=n[c],l,d,p=-1,f=0;for(;f<a.length&&(i.lastIndex=f,d=i.exec(a),d!==null);)f=i.lastIndex,i===M?d[1]==="!--"?i=ut:d[1]!==void 0?i=ft:d[2]!==void 0?(yt.test(d[2])&&(o=RegExp("</"+d[2],"g")),i=w):d[3]!==void 0&&(i=w):i===w?d[0]===">"?(i=o??M,p=-1):d[1]===void 0?p=-2:(p=i.lastIndex-d[2].length,l=d[1],i=d[3]===void 0?w:d[3]==='"'?gt:mt):i===gt||i===mt?i=w:i===ut||i===ft?i=M:(i=w,o=void 0);let g=i===w&&n[c+1].startsWith("/>")?" ":"";r+=i===M?a+Mt:p>=0?(s.push(l),a.slice(0,p)+vt+a.slice(p)+y+g):a+y+(p===-2?c:g)}return[xt(n,r+(n[e]||"<?>")+(t===2?"</svg>":t===3?"</math>":"")),s]},T=class n{constructor({strings:t,_$litType$:e},s){let o;this.parts=[];let r=0,i=0,c=t.length-1,a=this.parts,[l,d]=jt(t,e);if(this.el=n.createElement(l,s),A.currentNode=this.el.content,e===2||e===3){let p=this.el.content.firstChild;p.replaceWith(...p.childNodes)}for(;(o=A.nextNode())!==null&&a.length<c;){if(o.nodeType===1){if(o.hasAttributes())for(let p of o.getAttributeNames())if(p.endsWith(vt)){let f=d[i++],g=o.getAttribute(p).split(y),_=/([.?@])?(.*)/.exec(f);a.push({type:1,index:r,name:_[2],strings:g,ctor:_[1]==="."?Y:_[1]==="?"?Z:_[1]==="@"?G:z}),o.removeAttribute(p)}else p.startsWith(y)&&(a.push({type:6,index:r}),o.removeAttribute(p));if(yt.test(o.tagName)){let p=o.textContent.split(y),f=p.length-1;if(f>0){o.textContent=L?L.emptyScript:"";for(let g=0;g<f;g++)o.append(p[g],O()),A.nextNode(),a.push({type:2,index:++r});o.append(p[f],O())}}}else if(o.nodeType===8)if(o.data===bt)a.push({type:2,index:r});else{let p=-1;for(;(p=o.data.indexOf(y,p+1))!==-1;)a.push({type:7,index:r}),p+=y.length-1}r++}}static createElement(t,e){let s=E.createElement("template");return s.innerHTML=t,s}};function k(n,t,e=n,s){if(t===S)return t;let o=s!==void 0?e._$Co?.[s]:e._$Cl,r=j(t)?void 0:t._$litDirective$;return o?.constructor!==r&&(o?._$AO?.(!1),r===void 0?o=void 0:(o=new r(n),o._$AT(n,e,s)),s!==void 0?(e._$Co??=[])[s]=o:e._$Cl=o),o!==void 0&&(t=k(n,o._$AS(n,t.values),o,s)),t}var K=class{constructor(t,e){this._$AV=[],this._$AN=void 0,this._$AD=t,this._$AM=e}get parentNode(){return this._$AM.parentNode}get _$AU(){return this._$AM._$AU}u(t){let{el:{content:e},parts:s}=this._$AD,o=(t?.creationScope??E).importNode(e,!0);A.currentNode=o;let r=A.nextNode(),i=0,c=0,a=s[0];for(;a!==void 0;){if(i===a.index){let l;a.type===2?l=new D(r,r.nextSibling,this,t):a.type===1?l=new a.ctor(r,a.name,a.strings,this,t):a.type===6&&(l=new Q(r,this,t)),this._$AV.push(l),a=s[++c]}i!==a?.index&&(r=A.nextNode(),i++)}return A.currentNode=E,o}p(t){let e=0;for(let s of this._$AV)s!==void 0&&(s.strings!==void 0?(s._$AI(t,s,e),e+=s.strings.length-2):s._$AI(t[e])),e++}},D=class n{get _$AU(){return this._$AM?._$AU??this._$Cv}constructor(t,e,s,o){this.type=2,this._$AH=u,this._$AN=void 0,this._$AA=t,this._$AB=e,this._$AM=s,this.options=o,this._$Cv=o?.isConnected??!0}get parentNode(){let t=this._$AA.parentNode,e=this._$AM;return e!==void 0&&t?.nodeType===11&&(t=e.parentNode),t}get startNode(){return this._$AA}get endNode(){return this._$AB}_$AI(t,e=this){t=k(this,t,e),j(t)?t===u||t==null||t===""?(this._$AH!==u&&this._$AR(),this._$AH=u):t!==this._$AH&&t!==S&&this._(t):t._$litType$!==void 0?this.$(t):t.nodeType!==void 0?this.T(t):Ot(t)?this.k(t):this._(t)}O(t){return this._$AA.parentNode.insertBefore(t,this._$AB)}T(t){this._$AH!==t&&(this._$AR(),this._$AH=this.O(t))}_(t){this._$AH!==u&&j(this._$AH)?this._$AA.nextSibling.data=t:this.T(E.createTextNode(t)),this._$AH=t}$(t){let{values:e,_$litType$:s}=t,o=typeof s=="number"?this._$AC(t):(s.el===void 0&&(s.el=T.createElement(xt(s.h,s.h[0]),this.options)),s);if(this._$AH?._$AD===o)this._$AH.p(e);else{let r=new K(o,this),i=r.u(this.options);r.p(e),this.T(i),this._$AH=r}}_$AC(t){let e=_t.get(t.strings);return e===void 0&&_t.set(t.strings,e=new T(t)),e}k(t){tt(this._$AH)||(this._$AH=[],this._$AR());let e=this._$AH,s,o=0;for(let r of t)o===e.length?e.push(s=new n(this.O(O()),this.O(O()),this,this.options)):s=e[o],s._$AI(r),o++;o<e.length&&(this._$AR(s&&s._$AB.nextSibling,o),e.length=o)}_$AR(t=this._$AA.nextSibling,e){for(this._$AP?.(!1,!0,e);t!==this._$AB;){let s=pt(t).nextSibling;pt(t).remove(),t=s}}setConnected(t){this._$AM===void 0&&(this._$Cv=t,this._$AP?.(t))}},z=class{get tagName(){return this.element.tagName}get _$AU(){return this._$AM._$AU}constructor(t,e,s,o,r){this.type=1,this._$AH=u,this._$AN=void 0,this.element=t,this.name=e,this._$AM=o,this.options=r,s.length>2||s[0]!==""||s[1]!==""?(this._$AH=Array(s.length-1).fill(new String),this.strings=s):this._$AH=u}_$AI(t,e=this,s,o){let r=this.strings,i=!1;if(r===void 0)t=k(this,t,e,0),i=!j(t)||t!==this._$AH&&t!==S,i&&(this._$AH=t);else{let c=t,a,l;for(t=r[0],a=0;a<r.length-1;a++)l=k(this,c[s+a],e,a),l===S&&(l=this._$AH[a]),i||=!j(l)||l!==this._$AH[a],l===u?t=u:t!==u&&(t+=(l??"")+r[a+1]),this._$AH[a]=l}i&&!o&&this.j(t)}j(t){t===u?this.element.removeAttribute(this.name):this.element.setAttribute(this.name,t??"")}},Y=class extends z{constructor(){super(...arguments),this.type=3}j(t){this.element[this.name]=t===u?void 0:t}},Z=class extends z{constructor(){super(...arguments),this.type=4}j(t){this.element.toggleAttribute(this.name,!!t&&t!==u)}},G=class extends z{constructor(t,e,s,o,r){super(t,e,s,o,r),this.type=5}_$AI(t,e=this){if((t=k(this,t,e,0)??u)===S)return;let s=this._$AH,o=t===u&&s!==u||t.capture!==s.capture||t.once!==s.once||t.passive!==s.passive,r=t!==u&&(s===u||o);o&&this.element.removeEventListener(this.name,this,s),r&&this.element.addEventListener(this.name,this,t),this._$AH=t}handleEvent(t){typeof this._$AH=="function"?this._$AH.call(this.options?.host??this.element,t):this._$AH.handleEvent(t)}},Q=class{constructor(t,e,s){this.element=t,this.type=6,this._$AN=void 0,this._$AM=e,this.options=s}get _$AU(){return this._$AM._$AU}_$AI(t){k(this,t)}};var Tt=X.litHtmlPolyfillSupport;Tt?.(T,D),(X.litHtmlVersions??=[]).push("3.3.2");var $t=(n,t,e)=>{let s=e?.renderBefore??t,o=s._$litPart$;if(o===void 0){let r=e?.renderBefore??null;s._$litPart$=o=new D(t.insertBefore(O(),r),r,void 0,e??{})}return o._$AI(n),o};var st=globalThis,x=class extends b{constructor(){super(...arguments),this.renderOptions={host:this},this._$Do=void 0}createRenderRoot(){let t=super.createRenderRoot();return this.renderOptions.renderBefore??=t.firstChild,t}update(t){let e=this.render();this.hasUpdated||(this.renderOptions.isConnected=this.isConnected),super.update(t),this._$Do=$t(e,this.renderRoot,this.renderOptions)}connectedCallback(){super.connectedCallback(),this._$Do?.setConnected(!0)}disconnectedCallback(){super.disconnectedCallback(),this._$Do?.setConnected(!1)}render(){return S}};x._$litElement$=!0,x.finalized=!0,st.litElementHydrateSupport?.({LitElement:x});var Dt=st.litElementPolyfillSupport;Dt?.({LitElement:x});(st.litElementVersions??=[]).push("4.2.2");var C=["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"],wt=[6,0,1,2,3,4,5],F=["home","away","sleep","wake"],Ut=["off","low","med","high"],Nt=(()=>{let n=[];for(let t=0;t<24;t++)for(let e=0;e<60;e+=15){let s=`${String(t).padStart(2,"0")}:${String(e).padStart(2,"0")}`,o=t===0?`12:${String(e).padStart(2,"0")} AM`:t<12?`${t}:${String(e).padStart(2,"0")} AM`:t===12?`12:${String(e).padStart(2,"0")} PM`:`${t-12}:${String(e).padStart(2,"0")} PM`;n.push({v:s,l:o})}return n})(),ot=class extends x{static properties={hass:{attribute:!1},_config:{state:!0},_tab:{state:!0},_schedDay:{state:!0},_schedEdits:{state:!0},_profileEdits:{state:!0},_registryLoaded:{state:!0},_pendingTemps:{state:!0},_whHoldOpen:{state:!0},_whHoldActivity:{state:!0}};constructor(){super(),this._config={},this._tab="zones",this._schedDay=C[wt[new Date().getDay()]],this._schedEdits={},this._profileEdits={},this._registryEntities=null,this._registryLoaded=!1,this._tempAdj={},this._pendingTemps={},this._whHoldOpen=!1,this._whHoldActivity="home"}static getConfigElement(){return document.createElement("div")}static getStubConfig(){return{}}setConfig(t){this._config=t}getCardSize(){return 8}shouldUpdate(t){if(!t.has("hass")||!this._registryLoaded)return!0;let e=t.get("hass");return e?(this._registryEntities||[]).some(o=>this.hass.states[o.entity_id]!==e.states[o.entity_id]):!0}updated(t){t.has("hass")&&this.hass&&!this._registryLoaded&&this._loadRegistry()}async _loadRegistry(){try{let t=await this.hass.connection.sendMessagePromise({type:"config/entity_registry/list"});this._registryEntities=t.filter(e=>e.platform==="infinitude_direct")}catch(t){console.warn("Failed to load entity registry",t),this._registryEntities=[]}this._registryLoaded=!0}_findEntities(){if(!this.hass)return{climates:[],sensors:{},selects:{},system:{}};let t=this._registryEntities||[],e=this.hass.states,s=[],o={damper:{},fan:{}},r={},i={};if(this._config.climate_entities)for(let c of this._config.climate_entities)e[c]&&s.push(c);for(let c of t){let a=c.entity_id;if(!e[a])continue;let l=a.split(".")[0],d=c.unique_id||"";l==="climate"?this._config.climate_entities||s.push(a):l==="select"?r.wholeHouse=a:l==="sensor"&&(d.includes("damper")?o.damper[a]=e[a]:d.includes("fan")?o.fan[a]=e[a]:d.includes("humidifier")?i.humidifier=a:d.includes("oat")?i.oat=a:d.includes("op_status")?i.opStatus=a:d.includes("system_info")&&(i.info=a))}return s.sort(),{climates:s,sensors:o,selects:r,system:i}}_st(t){return t?this.hass?.states[t]??null:null}_at(t,e){return this._st(t)?.attributes?.[e]}_getScheduleData(){let{system:t}=this._findEntities();if(!t.info)return{};try{return JSON.parse(this._at(t.info,"schedule")||"{}")}catch{return{}}}_getProfilesData(){let{system:t}=this._findEntities();if(!t.info)return[];try{return JSON.parse(this._at(t.info,"profiles")||"[]")}catch{return[]}}async _svc(t,e,s){try{await this.hass.callService(t,e,s)}catch(o){console.error(`${t}.${e} failed`,o)}}_setHvacMode(t,e){this._svc("climate","set_hvac_mode",{entity_id:t,hvac_mode:e})}_setPreset(t,e){this._svc("climate","set_preset_mode",{entity_id:t,preset_mode:e})}_adjustTemp(t,e,s){let o=this._st(t);if(!o)return;let r=o.attributes,i=this._tempAdj[t]||(this._tempAdj[t]={}),c=i.heat??r.target_temp_low??r.temperature??68,a=i.cool??r.target_temp_high??(o.state==="cool"?r.temperature:null)??76;s==="heat"?i.heat=Math.max(50,Math.min(90,Math.round(c)+e)):i.cool=Math.max(60,Math.min(99,Math.round(a)+e)),this._pendingTemps={...this._pendingTemps,[t]:{heat:i.heat,cool:i.cool}},i.committing||(clearTimeout(i.timer),i.timer=setTimeout(()=>this._commitAdj(t),800))}async _commitAdj(t){let e=this._tempAdj[t];if(!e||e.committing)return;e.committing=!0;let s=this._st(t),o=s?.attributes||{},r=e.heat,i=e.cool,c=r??Math.round(o.target_temp_low??o.temperature??68),a=i??Math.round(o.target_temp_high??(s?.state==="cool"?o.temperature:null)??76),l=s?.state||"off",d={entity_id:t};l==="heat_cool"?(d.target_temp_low=c,d.target_temp_high=a):l==="heat"?d.temperature=c:l==="cool"?d.temperature=a:(d.target_temp_low=c,d.target_temp_high=a);try{await this.hass.callService("climate","set_temperature",d)}catch(p){console.error("set_temperature failed",p)}if(e.committing=!1,e.heat!==r||e.cool!==i){e.timer=setTimeout(()=>this._commitAdj(t),400);return}e.heat=null,e.cool=null,e.timer=null,e.graceUntil=Date.now()+3e4,setTimeout(()=>{if(!this._tempAdj[t]?.heat&&!this._tempAdj[t]?.cool){let{[t]:p,...f}=this._pendingTemps;this._pendingTemps=f}},2e3)}_hasPending(t){let e=this._tempAdj[t];return e&&(e.heat!=null||e.cool!=null||e.committing)}_cancelHold(t){let e=(this._registryEntities||[]).find(o=>o.entity_id===t);if(!e)return;let s=(e.unique_id||"").replace(/^infinitude_/,"");s&&this._svc("infinitude_direct","cancel_hold",{zone_id:s})}_setWholeHouseHold(t){let{selects:e}=this._findEntities();e.wholeHouse&&this._svc("select","select_option",{entity_id:e.wholeHouse,option:t})}static styles=I`
    :host { display: block; }
    ha-card { overflow: hidden; }
    .card-header {
      display: flex; align-items: center; justify-content: space-between;
      padding: 16px 16px 8px; flex-wrap: wrap; gap: 8px;
    }
    .header-left { display: flex; align-items: center; gap: 12px; }
    .header-title { font-size: 18px; font-weight: 500; color: var(--primary-text-color); }
    .header-mode {
      font-size: 11px; font-weight: 600; text-transform: uppercase;
      padding: 3px 8px; border-radius: 4px;
      background: var(--primary-color); color: var(--text-primary-color, #fff);
    }
    .header-mode.heat { background: var(--label-badge-red, #f97316); }
    .header-mode.cool { background: var(--label-badge-blue, #38bdf8); }
    .header-mode.auto { background: var(--label-badge-green, #34d399); }
    .header-stats { display: flex; gap: 16px; align-items: center; font-size: 12px; color: var(--secondary-text-color); }
    .stat-val { font-weight: 600; color: var(--primary-text-color); }
    .wh-hold {
      display: flex; align-items: center; gap: 6px; width: 100%;
      padding: 8px 12px; margin-top: 4px;
      background: rgba(251,191,36,0.08); border: 1px solid rgba(251,191,36,0.2);
      border-radius: 8px; font-size: 12px; color: var(--warning-color, #fbbf24); cursor: pointer;
    }
    .wh-hold:hover { background: rgba(251,191,36,0.14); }
    .wh-set {
      display: flex; align-items: center; gap: 8px; width: 100%; margin-top: 4px;
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
    .zone-meta { display: flex; gap: 10px; padding: 0 14px 10px; font-size: 11px; color: var(--secondary-text-color); flex-wrap: wrap; }
    .meta-item { display: flex; align-items: center; gap: 4px; }
    .meta-val { color: var(--primary-text-color); font-weight: 500; }
    .zone-hold {
      display: flex; align-items: center; gap: 6px; padding: 8px 14px;
      background: rgba(251,191,36,0.06); border-top: 1px solid rgba(251,191,36,0.15); font-size: 11px;
    }
    .hold-label { color: var(--warning-color, #fbbf24); font-weight: 500; flex: 1; }
    .sp-pending { animation: sp-pulse 0.8s ease-in-out infinite; color: var(--warning-color, #fbbf24) !important; }
    @keyframes sp-pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.4; } }
    .zone-actions { padding: 0 14px 10px; display: flex; gap: 8px; }
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
    .preset-btn:hover, .preset-btn.active { background: var(--primary-color); color: var(--text-primary-color, #fff); }
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
      border-radius: 4px; color: var(--primary-text-color); font-size: 11px; padding: 3px 6px; outline: none;
    }
    .sched-select:focus { border-color: var(--primary-color); }
    .sched-temps { display: flex; gap: 6px; align-items: center; font-size: 12px; font-variant-numeric: tabular-nums; }
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
    .prof-fan { display: flex; align-items: center; gap: 4px; }
    .prof-fan-label { font-size: 10px; color: var(--secondary-text-color); }
    .copy-bar { display: flex; align-items: center; gap: 8px; margin-top: 10px; font-size: 12px; color: var(--secondary-text-color); }
    .section-title { font-size: 11px; font-weight: 600; color: var(--secondary-text-color); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 10px; }
  `;render(){if(!this.hass)return u;if(!this._registryLoaded)return h`<ha-card>
        <div style="padding:24px;text-align:center;color:var(--secondary-text-color)">Loading…</div>
      </ha-card>`;let t=this._findEntities();return!t.climates.length&&!this._config.show_empty?h`<ha-card>
        <div style="padding:24px;text-align:center;color:var(--secondary-text-color)">
          <ha-icon icon="mdi:thermostat" style="--mdc-icon-size:48px;opacity:0.3;margin-bottom:12px;display:block"></ha-icon>
          <div style="font-size:14px;font-weight:500">No Infinitude entities found</div>
          <div style="font-size:12px;margin-top:4px">Waiting for thermostat connection…</div>
        </div>
      </ha-card>`:h`
      <ha-card>
        <div class="card-header">${this._hdr(t)}</div>
        <div class="card-tabs">${this._tabs()}</div>
        <div class="card-content">
          ${this._tab==="zones"?this._zones(t):u}
          ${this._tab==="schedule"?this._sched(t):u}
          ${this._tab==="profiles"?this._profs():u}
        </div>
      </ha-card>`}_hdr(t){let{system:e,selects:s,climates:o}=t,r=o.length&&this._st(o[0])?.state||"off",i=r==="heat"?"heat":r==="cool"?"cool":r==="heat_cool"||r==="auto"?"auto":"",c=r==="heat_cool"?"Auto":r.charAt(0).toUpperCase()+r.slice(1),a=this._st(e.oat),l="\u2013";if(a?.state&&a.state!=="unavailable")l=`${Math.round(Number(a.state))}\xB0`;else if(o.length){let v=this._at(o[0],"outdoor_temperature");v!=null&&(l=`${Math.round(Number(v))}\xB0`)}let d=this._st(e.opStatus),p=d?.state&&d.state!=="unavailable"?d.state:"",f=this._st(e.humidifier)?.state==="on",g=this._st(s.wholeHouse),_=g&&g.state!=="off",$=o.length?this._at(o[0],"current_humidity"):null;return h`
      <div class="header-left">
        <span class="header-title">HVAC</span>
        <span class="header-mode ${i}">${c}</span>
      </div>
      <div class="header-stats">
        <span>Outside <span class="stat-val">${l}</span></span>
        ${$!=null?h`<span>Indoor RH <span class="stat-val">${$}%</span></span>`:u}
        ${f?h`<span style="color:var(--label-badge-blue,#38bdf8)">💧 Humidifier On</span>`:u}
        ${p?h`<span>${p}</span>`:u}
      </div>
      ${_?h`
        <div class="wh-hold" @click=${()=>this._setWholeHouseHold("off")}>
          <ha-icon icon="mdi:home-lock" style="--mdc-icon-size:16px"></ha-icon>
          <span>Whole house: <strong>${g.state}</strong></span>
          <span style="margin-left:auto;opacity:0.7">Tap to cancel</span>
        </div>`:h`
        ${this._whHoldOpen?h`
          <div class="wh-set">
            <span class="wh-set-label">WH Hold</span>
            <div class="wh-pills">
              ${F.map(v=>h`
                <div class="wh-pill ${this._whHoldActivity===v?"active":""}"
                     @click=${()=>{this._whHoldActivity=v}}>${v}</div>`)}
            </div>
            <button class="btn btn-primary" style="font-size:11px;padding:4px 12px" @click=${()=>{this._setWholeHouseHold(this._whHoldActivity),this._whHoldOpen=!1}}>Apply</button>
            <button class="btn" style="font-size:11px;padding:4px 10px" @click=${()=>{this._whHoldOpen=!1}}>Cancel</button>
          </div>`:h`
          <div style="width:100%;margin-top:4px">
            <button class="btn" style="font-size:11px;padding:4px 12px" @click=${()=>{this._whHoldOpen=!0}}>
              <ha-icon icon="mdi:home-lock" style="--mdc-icon-size:14px;vertical-align:middle;margin-right:4px"></ha-icon>Set WH hold
            </button>
          </div>`}
      `}`}_tabs(){return h`${["zones","schedule","profiles"].map(t=>h`
      <div class="tab ${this._tab===t?"active":""}"
           @click=${()=>{this._tab=t}}>${t.charAt(0).toUpperCase()+t.slice(1)}</div>`)}`}_zones(t){let{climates:e}=t;if(!e.length)return h`<div style="padding:20px;text-align:center;color:var(--secondary-text-color)">No zone entities found</div>`;let s=this._st(e[0])?.state||"off",o=["off","heat","cool","heat_cool"],r={off:"Off",heat:"Heat",cool:"Cool",heat_cool:"Auto"};return h`
      <div class="mode-row">
        <span class="mode-label">Mode</span>
        <div class="mode-pills">
          ${o.map(i=>h`<div class="mode-pill ${i===s?"active":""} ${i==="heat"?"heat":i==="cool"?"cool":i==="heat_cool"?"auto":""}"
              @click=${()=>this._setHvacMode(e[0],i)}>${r[i]}</div>`)}
        </div>
      </div>
      <div class="zone-grid">${e.map(i=>this._zoneCard(i))}</div>`}_zoneCard(t){let e=this._st(t);if(!e)return u;let s=e.attributes||{},o=(s.friendly_name||t).replace(/^Infinitude\s+/i,"").replace(/^infinitude_direct\s+/i,""),r=s.current_temperature!=null?Math.round(s.current_temperature):"\u2013",i=s.current_humidity,c=e.state||"off",a=s.hvac_action||"idle",l=s.preset_mode||"\u2013",d=a==="heating"?"heating":a==="cooling"?"cooling":a==="drying"?"drying":"",p=a==="idle"?"Idle":a.charAt(0).toUpperCase()+a.slice(1),f=c==="heat_cool",g=!!s.hold_active,_=s.hold_activity||l,$=this._pendingTemps[t],v=this._hasPending(t),m=$?.heat??s.target_temp_low??s.temperature??null,it=$?.cool??s.target_temp_high??(c==="cool"?s.temperature:null)??null;return h`
      <div class="zone-card ${d}">
        <div class="zone-top">
          <span class="zone-name">${o}</span>
          <span class="zone-badge ${d}">${p}</span>
        </div>
        <div class="zone-body">
          <div>
            <span class="temp-hero">${r}</span><span class="temp-unit">°F</span>
            ${i!=null?h`<div style="font-size:11px;color:var(--secondary-text-color);margin-top:2px">${i}% RH</div>`:u}
          </div>
          <div class="zone-sp">
            ${m!=null?h`
              <div class="sp-row">
                <button class="btn-adj" @click=${()=>this._adjustTemp(t,-1,"heat")}>−</button>
                <span class="sp-val sp-heat ${v?"sp-pending":""}">${Math.round(m)}°</span>
                <button class="btn-adj" @click=${()=>this._adjustTemp(t,1,"heat")}>+</button>
              </div>`:u}
            ${f&&it!=null?h`
              <div class="sp-row">
                <button class="btn-adj" @click=${()=>this._adjustTemp(t,-1,"cool")}>−</button>
                <span class="sp-val sp-cool ${v?"sp-pending":""}">${Math.round(it)}°</span>
                <button class="btn-adj" @click=${()=>this._adjustTemp(t,1,"cool")}>+</button>
              </div>`:u}
          </div>
        </div>
        <div class="zone-meta">
          <span class="meta-item">Activity <span class="meta-val">${l}</span></span>
          ${s.fan_mode?h`<span class="meta-item">Fan <span class="meta-val">${s.fan_mode}</span></span>`:u}
          ${s.damper_position!=null?h`<span class="meta-item">Damper <span class="meta-val">${s.damper_position}%</span></span>`:u}
        </div>
        <div class="zone-preset-row">
          ${F.map(W=>h`
            <div class="preset-btn ${l===W?"active":""}"
                 @click=${()=>this._setPreset(t,W)}>${W}</div>`)}
        </div>
        ${g?h`
          <div class="zone-hold">
            <span class="hold-label">Hold: ${_}</span>
            <button class="btn" style="font-size:11px;padding:3px 10px;color:var(--error-color,#f87171)" @click=${()=>this._cancelHold(t)}>Cancel</button>
          </div>`:h`
          <div class="zone-actions">
            <button class="btn" style="font-size:11px;padding:4px 12px" @click=${()=>this._setPreset(t,l!=="\u2013"?l:"home")}>Set hold</button>
          </div>`}
      </div>`}_sched(){let t=this._getScheduleData(),e=this._getProfilesData(),s=Object.keys(t);if(!s.length)return h`
      <div style="padding:20px;text-align:center;color:var(--secondary-text-color)">
        <ha-icon icon="mdi:calendar-clock" style="--mdc-icon-size:48px;opacity:0.3;margin-bottom:12px;display:block"></ha-icon>
        No schedule data available. Waiting for thermostat data…
      </div>`;let o=C[wt[new Date().getDay()]],r={};for(let a of e)r[a.id]=a.name;let i=0;for(let a of s)i=Math.max(i,(t[a]?.[this._schedDay]||[]).length);i||(i=5);let c=Object.keys(this._schedEdits).length>0;return h`
      <div class="section-title">Schedule</div>
      <div class="sched-day-tabs">
        ${C.map(a=>h`
          <div class="day-tab ${a===this._schedDay?"active":""} ${a===o&&a!==this._schedDay?"today":""}"
               @click=${()=>{this._schedDay=a}}>${a.slice(0,3)}</div>`)}
      </div>
      ${Array.from({length:i},(a,l)=>this._periodCard(l,s,t,e,r))}
      <div class="copy-bar">
        <span>Copy ${this._schedDay.slice(0,3)} →</span>
        <select class="sched-select" @change=${a=>this._copySched(a)}>
          <option value="">select day…</option>
          ${C.filter(a=>a!==this._schedDay).map(a=>h`<option value=${a}>${a.slice(0,3)}</option>`)}
          <option value="__all__">All other days</option>
        </select>
      </div>
      ${c?h`
        <div class="action-bar">
          <span class="action-bar-label">● Unsaved changes</span>
          <button class="btn" @click=${()=>{this._schedEdits={}}}>Discard</button>
          <button class="btn btn-primary" @click=${()=>this._saveSched()}>Save schedule</button>
        </div>`:u}`}_periodCard(t,e,s,o,r){return h`
      <div class="period-card">
        <div class="period-header">Period ${t+1}</div>
        ${e.map(i=>{let c=(s[i]?.[this._schedDay]||[])[t];if(!c)return u;let a=`${i}_${this._schedDay}_${t}`,l=this._schedEdits[a],d=l?.act??c.activity,p=l?.time??c.time,f=l?.enabled??c.enabled,_=o.find(m=>m.id===i)?.activities?.[d],$=_?.htsp?Math.round(parseFloat(_.htsp)):"\u2013",v=_?.clsp?Math.round(parseFloat(_.clsp)):"\u2013";return h`
            <div class="sched-line ${f?"":"disabled"}">
              <span class="sched-name">${r[i]||`Zone ${i}`}</span>
              <select class="sched-select" @change=${m=>this._schedEdit(i,t,"act",m.target.value)}>
                ${F.map(m=>h`<option value=${m} ?selected=${m===d}>${m}</option>`)}
              </select>
              <select class="sched-select" @change=${m=>this._schedEdit(i,t,"time",m.target.value)}>
                ${Nt.map(m=>h`<option value=${m.v} ?selected=${m.v===p}>${m.l}</option>`)}
              </select>
              <label class="sched-toggle">
                <input type="checkbox" ?checked=${f}
                       @change=${m=>this._schedEdit(i,t,"enabled",m.target.checked)}>
                <span>on</span>
              </label>
              <div class="sched-temps">
                <span class="sp-heat">${$}°</span>
                <span class="sp-cool">${v}°</span>
              </div>
            </div>`})}
      </div>`}_schedEdit(t,e,s,o){let r=`${t}_${this._schedDay}_${e}`,i=this._schedEdits[r]||{},c=(this._getScheduleData()[t]?.[this._schedDay]||[])[e]||{};this._schedEdits={...this._schedEdits,[r]:{act:s==="act"?o:i.act??c.activity,time:s==="time"?o:i.time??c.time,enabled:s==="enabled"?o:i.enabled??c.enabled}}}_copySched(t){let e=t.target.value;if(!e)return;t.target.value="";let s=this._getScheduleData(),o=e==="__all__"?C.filter(i=>i!==this._schedDay):[e],r={...this._schedEdits};for(let i of Object.keys(s)){let c=s[i]?.[this._schedDay]||[];for(let a of o)c.forEach((l,d)=>{let p=this._schedEdits[`${i}_${this._schedDay}_${d}`];r[`${i}_${a}_${d}`]={act:p?.act??l.activity,time:p?.time??l.time,enabled:p?.enabled??l.enabled}})}this._schedEdits=r}async _saveSched(){let t=this._getScheduleData();for(let e of Object.keys(t)){let s=C.map(o=>({id:o,period:(t[e]?.[o]||[]).map((r,i)=>{let c=this._schedEdits[`${e}_${o}_${i}`];return{id:r.id||String(i+1),activity:c?.act??r.activity,time:c?.time??r.time,enabled:c?.enabled??r.enabled?"on":"off"}})}));await this._svc("infinitude_direct","save_schedule",{zone_id:e,schedule:JSON.stringify(s)})}this._schedEdits={}}_profs(){let t=this._getProfilesData();if(!t.length)return h`
      <div style="padding:20px;text-align:center;color:var(--secondary-text-color)">
        <ha-icon icon="mdi:tune-vertical" style="--mdc-icon-size:48px;opacity:0.3;margin-bottom:12px;display:block"></ha-icon>
        No profile data available. Waiting for thermostat data…
      </div>`;let e=Object.keys(this._profileEdits).length>0;return h`
      <div class="section-title">Comfort Profiles</div>
      ${F.map(s=>h`
        <div class="prof-card">
          <div class="prof-header">${s}</div>
          ${t.map(o=>{let r=o.activities?.[s]||{},i=`${o.id}_${s}`,c=this._profileEdits[i],a=c?.htsp??(r.htsp?Math.round(parseFloat(r.htsp)):68),l=c?.clsp??(r.clsp?Math.round(parseFloat(r.clsp)):76),d=c?.fan??r.fan??"low";return h`
              <div class="prof-line">
                <span class="prof-name">${o.name}</span>
                <div class="sp-row">
                  <button class="btn-adj" @click=${()=>this._profAdj(o.id,s,"htsp",-1)}>−</button>
                  <span class="sp-val sp-heat">${a}°</span>
                  <button class="btn-adj" @click=${()=>this._profAdj(o.id,s,"htsp",1)}>+</button>
                </div>
                <div class="sp-row">
                  <button class="btn-adj" @click=${()=>this._profAdj(o.id,s,"clsp",-1)}>−</button>
                  <span class="sp-val sp-cool">${l}°</span>
                  <button class="btn-adj" @click=${()=>this._profAdj(o.id,s,"clsp",1)}>+</button>
                </div>
                <div class="prof-fan">
                  <span class="prof-fan-label">Fan</span>
                  <select class="sched-select" @change=${p=>this._profFan(o.id,s,p.target.value)}>
                    ${Ut.map(p=>h`<option value=${p} ?selected=${p===d}>${p}</option>`)}
                  </select>
                </div>
              </div>`})}
        </div>`)}
      ${e?h`
        <div class="action-bar">
          <span class="action-bar-label">● Unsaved changes</span>
          <button class="btn" @click=${()=>{this._profileEdits={}}}>Discard</button>
          <button class="btn btn-primary" @click=${()=>this._saveProfs()}>Save profiles</button>
        </div>`:u}`}_profAdj(t,e,s,o){let r=`${t}_${e}`,i=this._getProfilesData().find(g=>g.id===t)?.activities?.[e]||{},c=this._profileEdits[r]||{},a=c.htsp??(i.htsp?Math.round(parseFloat(i.htsp)):68),l=c.clsp??(i.clsp?Math.round(parseFloat(i.clsp)):76),d=s==="htsp"?50:60,p=s==="htsp"?90:99,f=s==="htsp"?a:l;this._profileEdits={...this._profileEdits,[r]:{zone_id:t,activity:e,htsp:s==="htsp"?Math.max(d,Math.min(p,f+o)):a,clsp:s==="clsp"?Math.max(d,Math.min(p,f+o)):l,fan:c.fan??i.fan??"low"}}}_profFan(t,e,s){let o=`${t}_${e}`,r=this._getProfilesData().find(c=>c.id===t)?.activities?.[e]||{},i=this._profileEdits[o]||{};this._profileEdits={...this._profileEdits,[o]:{zone_id:t,activity:e,htsp:i.htsp??(r.htsp?Math.round(parseFloat(r.htsp)):68),clsp:i.clsp??(r.clsp?Math.round(parseFloat(r.clsp)):76),fan:s}}}async _saveProfs(){for(let t of Object.values(this._profileEdits)){let e={zone_id:t.zone_id,activity:t.activity,htsp:t.htsp,clsp:t.clsp};t.fan&&(e.fan=t.fan),await this._svc("infinitude_direct","set_profile",e)}this._profileEdits={}}};customElements.get("infinitude-hvac-card")||customElements.define("infinitude-hvac-card",ot);window.customCards=window.customCards||[];window.customCards.some(n=>n.type==="infinitude-hvac-card")||window.customCards.push({type:"infinitude-hvac-card",name:"Infinitude HVAC Card",description:"Full HVAC dashboard for Carrier/Bryant Infinity thermostats",preview:!1});
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
