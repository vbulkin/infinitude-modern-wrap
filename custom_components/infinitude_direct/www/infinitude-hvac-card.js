var at=globalThis,nt=at.ShadowRoot&&(at.ShadyCSS===void 0||at.ShadyCSS.nativeShadow)&&"adoptedStyleSheets"in Document.prototype&&"replace"in CSSStyleSheet.prototype,ht=Symbol(),Ot=new WeakMap,G=class{constructor(t,e,s){if(this._$cssResult$=!0,s!==ht)throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");this.cssText=t,this.t=e}get styleSheet(){let t=this.o,e=this.t;if(nt&&t===void 0){let s=e!==void 0&&e.length===1;s&&(t=Ot.get(e)),t===void 0&&((this.o=t=new CSSStyleSheet).replaceSync(this.cssText),s&&Ot.set(e,t))}return t}toString(){return this.cssText}},Tt=l=>new G(typeof l=="string"?l:l+"",void 0,ht),C=(l,...t)=>{let e=l.length===1?l[0]:t.reduce((s,i,o)=>s+(a=>{if(a._$cssResult$===!0)return a.cssText;if(typeof a=="number")return a;throw Error("Value passed to 'css' function must be a 'css' function result: "+a+". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.")})(i)+l[o+1],l[0]);return new G(e,l,ht)},Dt=(l,t)=>{if(nt)l.adoptedStyleSheets=t.map(e=>e instanceof CSSStyleSheet?e:e.styleSheet);else for(let e of t){let s=document.createElement("style"),i=at.litNonce;i!==void 0&&s.setAttribute("nonce",i),s.textContent=e.cssText,l.appendChild(s)}},ut=nt?l=>l:l=>l instanceof CSSStyleSheet?(t=>{let e="";for(let s of t.cssRules)e+=s.cssText;return Tt(e)})(l):l;var{is:Kt,defineProperty:Gt,getOwnPropertyDescriptor:Qt,getOwnPropertyNames:te,getOwnPropertySymbols:ee,getPrototypeOf:se}=Object,rt=globalThis,Pt=rt.trustedTypes,ie=Pt?Pt.emptyScript:"",oe=rt.reactiveElementPolyfillSupport,Q=(l,t)=>l,mt={toAttribute(l,t){switch(t){case Boolean:l=l?ie:null;break;case Object:case Array:l=l==null?l:JSON.stringify(l)}return l},fromAttribute(l,t){let e=l;switch(t){case Boolean:e=l!==null;break;case Number:e=l===null?null:Number(l);break;case Object:case Array:try{e=JSON.parse(l)}catch{e=null}}return e}},jt=(l,t)=>!Kt(l,t),Nt={attribute:!0,type:String,converter:mt,reflect:!1,useDefault:!1,hasChanged:jt};Symbol.metadata??=Symbol("metadata"),rt.litPropertyMetadata??=new WeakMap;var D=class extends HTMLElement{static addInitializer(t){this._$Ei(),(this.l??=[]).push(t)}static get observedAttributes(){return this.finalize(),this._$Eh&&[...this._$Eh.keys()]}static createProperty(t,e=Nt){if(e.state&&(e.attribute=!1),this._$Ei(),this.prototype.hasOwnProperty(t)&&((e=Object.create(e)).wrapped=!0),this.elementProperties.set(t,e),!e.noAccessor){let s=Symbol(),i=this.getPropertyDescriptor(t,s,e);i!==void 0&&Gt(this.prototype,t,i)}}static getPropertyDescriptor(t,e,s){let{get:i,set:o}=Qt(this.prototype,t)??{get(){return this[e]},set(a){this[e]=a}};return{get:i,set(a){let d=i?.call(this);o?.call(this,a),this.requestUpdate(t,d,s)},configurable:!0,enumerable:!0}}static getPropertyOptions(t){return this.elementProperties.get(t)??Nt}static _$Ei(){if(this.hasOwnProperty(Q("elementProperties")))return;let t=se(this);t.finalize(),t.l!==void 0&&(this.l=[...t.l]),this.elementProperties=new Map(t.elementProperties)}static finalize(){if(this.hasOwnProperty(Q("finalized")))return;if(this.finalized=!0,this._$Ei(),this.hasOwnProperty(Q("properties"))){let e=this.properties,s=[...te(e),...ee(e)];for(let i of s)this.createProperty(i,e[i])}let t=this[Symbol.metadata];if(t!==null){let e=litPropertyMetadata.get(t);if(e!==void 0)for(let[s,i]of e)this.elementProperties.set(s,i)}this._$Eh=new Map;for(let[e,s]of this.elementProperties){let i=this._$Eu(e,s);i!==void 0&&this._$Eh.set(i,e)}this.elementStyles=this.finalizeStyles(this.styles)}static finalizeStyles(t){let e=[];if(Array.isArray(t)){let s=new Set(t.flat(1/0).reverse());for(let i of s)e.unshift(ut(i))}else t!==void 0&&e.push(ut(t));return e}static _$Eu(t,e){let s=e.attribute;return s===!1?void 0:typeof s=="string"?s:typeof t=="string"?t.toLowerCase():void 0}constructor(){super(),this._$Ep=void 0,this.isUpdatePending=!1,this.hasUpdated=!1,this._$Em=null,this._$Ev()}_$Ev(){this._$ES=new Promise(t=>this.enableUpdating=t),this._$AL=new Map,this._$E_(),this.requestUpdate(),this.constructor.l?.forEach(t=>t(this))}addController(t){(this._$EO??=new Set).add(t),this.renderRoot!==void 0&&this.isConnected&&t.hostConnected?.()}removeController(t){this._$EO?.delete(t)}_$E_(){let t=new Map,e=this.constructor.elementProperties;for(let s of e.keys())this.hasOwnProperty(s)&&(t.set(s,this[s]),delete this[s]);t.size>0&&(this._$Ep=t)}createRenderRoot(){let t=this.shadowRoot??this.attachShadow(this.constructor.shadowRootOptions);return Dt(t,this.constructor.elementStyles),t}connectedCallback(){this.renderRoot??=this.createRenderRoot(),this.enableUpdating(!0),this._$EO?.forEach(t=>t.hostConnected?.())}enableUpdating(t){}disconnectedCallback(){this._$EO?.forEach(t=>t.hostDisconnected?.())}attributeChangedCallback(t,e,s){this._$AK(t,s)}_$ET(t,e){let s=this.constructor.elementProperties.get(t),i=this.constructor._$Eu(t,s);if(i!==void 0&&s.reflect===!0){let o=(s.converter?.toAttribute!==void 0?s.converter:mt).toAttribute(e,s.type);this._$Em=t,o==null?this.removeAttribute(i):this.setAttribute(i,o),this._$Em=null}}_$AK(t,e){let s=this.constructor,i=s._$Eh.get(t);if(i!==void 0&&this._$Em!==i){let o=s.getPropertyOptions(i),a=typeof o.converter=="function"?{fromAttribute:o.converter}:o.converter?.fromAttribute!==void 0?o.converter:mt;this._$Em=i;let d=a.fromAttribute(e,o.type);this[i]=d??this._$Ej?.get(i)??d,this._$Em=null}}requestUpdate(t,e,s,i=!1,o){if(t!==void 0){let a=this.constructor;if(i===!1&&(o=this[t]),s??=a.getPropertyOptions(t),!((s.hasChanged??jt)(o,e)||s.useDefault&&s.reflect&&o===this._$Ej?.get(t)&&!this.hasAttribute(a._$Eu(t,s))))return;this.C(t,e,s)}this.isUpdatePending===!1&&(this._$ES=this._$EP())}C(t,e,{useDefault:s,reflect:i,wrapped:o},a){s&&!(this._$Ej??=new Map).has(t)&&(this._$Ej.set(t,a??e??this[t]),o!==!0||a!==void 0)||(this._$AL.has(t)||(this.hasUpdated||s||(e=void 0),this._$AL.set(t,e)),i===!0&&this._$Em!==t&&(this._$Eq??=new Set).add(t))}async _$EP(){this.isUpdatePending=!0;try{await this._$ES}catch(e){Promise.reject(e)}let t=this.scheduleUpdate();return t!=null&&await t,!this.isUpdatePending}scheduleUpdate(){return this.performUpdate()}performUpdate(){if(!this.isUpdatePending)return;if(!this.hasUpdated){if(this.renderRoot??=this.createRenderRoot(),this._$Ep){for(let[i,o]of this._$Ep)this[i]=o;this._$Ep=void 0}let s=this.constructor.elementProperties;if(s.size>0)for(let[i,o]of s){let{wrapped:a}=o,d=this[i];a!==!0||this._$AL.has(i)||d===void 0||this.C(i,void 0,o,d)}}let t=!1,e=this._$AL;try{t=this.shouldUpdate(e),t?(this.willUpdate(e),this._$EO?.forEach(s=>s.hostUpdate?.()),this.update(e)):this._$EM()}catch(s){throw t=!1,this._$EM(),s}t&&this._$AE(e)}willUpdate(t){}_$AE(t){this._$EO?.forEach(e=>e.hostUpdated?.()),this.hasUpdated||(this.hasUpdated=!0,this.firstUpdated(t)),this.updated(t)}_$EM(){this._$AL=new Map,this.isUpdatePending=!1}get updateComplete(){return this.getUpdateComplete()}getUpdateComplete(){return this._$ES}shouldUpdate(t){return!0}update(t){this._$Eq&&=this._$Eq.forEach(e=>this._$ET(e,this[e])),this._$EM()}updated(t){}firstUpdated(t){}};D.elementStyles=[],D.shadowRootOptions={mode:"open"},D[Q("elementProperties")]=new Map,D[Q("finalized")]=new Map,oe?.({ReactiveElement:D}),(rt.reactiveElementVersions??=[]).push("2.1.2");var xt=globalThis,It=l=>l,lt=xt.trustedTypes,Lt=lt?lt.createPolicy("lit-html",{createHTML:l=>l}):void 0,Vt="$lit$",N=`lit$${Math.random().toFixed(9).slice(2)}$`,qt="?"+N,ae=`<${qt}>`,F=document,et=()=>F.createComment(""),st=l=>l===null||typeof l!="object"&&typeof l!="function",$t=Array.isArray,ne=l=>$t(l)||typeof l?.[Symbol.iterator]=="function",ft=`[ 	
\f\r]`,tt=/<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g,Ut=/-->/g,Rt=/>/g,U=RegExp(`>|${ft}(?:([^\\s"'>=/]+)(${ft}*=${ft}*(?:[^ 	
\f\r"'\`<>=]|("|')|))|$)`,"g"),Ft=/'/g,Wt=/"/g,Zt=/^(?:script|style|textarea|title)$/i,wt=l=>(t,...e)=>({_$litType$:l,strings:t,values:e}),r=wt(1),_e=wt(2),be=wt(3),W=Symbol.for("lit-noChange"),u=Symbol.for("lit-nothing"),Bt=new WeakMap,R=F.createTreeWalker(F,129);function Jt(l,t){if(!$t(l)||!l.hasOwnProperty("raw"))throw Error("invalid template strings array");return Lt!==void 0?Lt.createHTML(t):t}var re=(l,t)=>{let e=l.length-1,s=[],i,o=t===2?"<svg>":t===3?"<math>":"",a=tt;for(let d=0;d<e;d++){let c=l[d],n,p,h=-1,m=0;for(;m<c.length&&(a.lastIndex=m,p=a.exec(c),p!==null);)m=a.lastIndex,a===tt?p[1]==="!--"?a=Ut:p[1]!==void 0?a=Rt:p[2]!==void 0?(Zt.test(p[2])&&(i=RegExp("</"+p[2],"g")),a=U):p[3]!==void 0&&(a=U):a===U?p[0]===">"?(a=i??tt,h=-1):p[1]===void 0?h=-2:(h=a.lastIndex-p[2].length,n=p[1],a=p[3]===void 0?U:p[3]==='"'?Wt:Ft):a===Wt||a===Ft?a=U:a===Ut||a===Rt?a=tt:(a=U,i=void 0);let f=a===U&&l[d+1].startsWith("/>")?" ":"";o+=a===tt?c+ae:h>=0?(s.push(n),c.slice(0,h)+Vt+c.slice(h)+N+f):c+N+(h===-2?d:f)}return[Jt(l,o+(l[e]||"<?>")+(t===2?"</svg>":t===3?"</math>":"")),s]},it=class l{constructor({strings:t,_$litType$:e},s){let i;this.parts=[];let o=0,a=0,d=t.length-1,c=this.parts,[n,p]=re(t,e);if(this.el=l.createElement(n,s),R.currentNode=this.el.content,e===2||e===3){let h=this.el.content.firstChild;h.replaceWith(...h.childNodes)}for(;(i=R.nextNode())!==null&&c.length<d;){if(i.nodeType===1){if(i.hasAttributes())for(let h of i.getAttributeNames())if(h.endsWith(Vt)){let m=p[a++],f=i.getAttribute(h).split(N),_=/([.?@])?(.*)/.exec(m);c.push({type:1,index:o,name:_[2],strings:f,ctor:_[1]==="."?gt:_[1]==="?"?_t:_[1]==="@"?bt:q}),i.removeAttribute(h)}else h.startsWith(N)&&(c.push({type:6,index:o}),i.removeAttribute(h));if(Zt.test(i.tagName)){let h=i.textContent.split(N),m=h.length-1;if(m>0){i.textContent=lt?lt.emptyScript:"";for(let f=0;f<m;f++)i.append(h[f],et()),R.nextNode(),c.push({type:2,index:++o});i.append(h[m],et())}}}else if(i.nodeType===8)if(i.data===qt)c.push({type:2,index:o});else{let h=-1;for(;(h=i.data.indexOf(N,h+1))!==-1;)c.push({type:7,index:o}),h+=N.length-1}o++}}static createElement(t,e){let s=F.createElement("template");return s.innerHTML=t,s}};function V(l,t,e=l,s){if(t===W)return t;let i=s!==void 0?e._$Co?.[s]:e._$Cl,o=st(t)?void 0:t._$litDirective$;return i?.constructor!==o&&(i?._$AO?.(!1),o===void 0?i=void 0:(i=new o(l),i._$AT(l,e,s)),s!==void 0?(e._$Co??=[])[s]=i:e._$Cl=i),i!==void 0&&(t=V(l,i._$AS(l,t.values),i,s)),t}var vt=class{constructor(t,e){this._$AV=[],this._$AN=void 0,this._$AD=t,this._$AM=e}get parentNode(){return this._$AM.parentNode}get _$AU(){return this._$AM._$AU}u(t){let{el:{content:e},parts:s}=this._$AD,i=(t?.creationScope??F).importNode(e,!0);R.currentNode=i;let o=R.nextNode(),a=0,d=0,c=s[0];for(;c!==void 0;){if(a===c.index){let n;c.type===2?n=new ot(o,o.nextSibling,this,t):c.type===1?n=new c.ctor(o,c.name,c.strings,this,t):c.type===6&&(n=new yt(o,this,t)),this._$AV.push(n),c=s[++d]}a!==c?.index&&(o=R.nextNode(),a++)}return R.currentNode=F,i}p(t){let e=0;for(let s of this._$AV)s!==void 0&&(s.strings!==void 0?(s._$AI(t,s,e),e+=s.strings.length-2):s._$AI(t[e])),e++}},ot=class l{get _$AU(){return this._$AM?._$AU??this._$Cv}constructor(t,e,s,i){this.type=2,this._$AH=u,this._$AN=void 0,this._$AA=t,this._$AB=e,this._$AM=s,this.options=i,this._$Cv=i?.isConnected??!0}get parentNode(){let t=this._$AA.parentNode,e=this._$AM;return e!==void 0&&t?.nodeType===11&&(t=e.parentNode),t}get startNode(){return this._$AA}get endNode(){return this._$AB}_$AI(t,e=this){t=V(this,t,e),st(t)?t===u||t==null||t===""?(this._$AH!==u&&this._$AR(),this._$AH=u):t!==this._$AH&&t!==W&&this._(t):t._$litType$!==void 0?this.$(t):t.nodeType!==void 0?this.T(t):ne(t)?this.k(t):this._(t)}O(t){return this._$AA.parentNode.insertBefore(t,this._$AB)}T(t){this._$AH!==t&&(this._$AR(),this._$AH=this.O(t))}_(t){this._$AH!==u&&st(this._$AH)?this._$AA.nextSibling.data=t:this.T(F.createTextNode(t)),this._$AH=t}$(t){let{values:e,_$litType$:s}=t,i=typeof s=="number"?this._$AC(t):(s.el===void 0&&(s.el=it.createElement(Jt(s.h,s.h[0]),this.options)),s);if(this._$AH?._$AD===i)this._$AH.p(e);else{let o=new vt(i,this),a=o.u(this.options);o.p(e),this.T(a),this._$AH=o}}_$AC(t){let e=Bt.get(t.strings);return e===void 0&&Bt.set(t.strings,e=new it(t)),e}k(t){$t(this._$AH)||(this._$AH=[],this._$AR());let e=this._$AH,s,i=0;for(let o of t)i===e.length?e.push(s=new l(this.O(et()),this.O(et()),this,this.options)):s=e[i],s._$AI(o),i++;i<e.length&&(this._$AR(s&&s._$AB.nextSibling,i),e.length=i)}_$AR(t=this._$AA.nextSibling,e){for(this._$AP?.(!1,!0,e);t!==this._$AB;){let s=It(t).nextSibling;It(t).remove(),t=s}}setConnected(t){this._$AM===void 0&&(this._$Cv=t,this._$AP?.(t))}},q=class{get tagName(){return this.element.tagName}get _$AU(){return this._$AM._$AU}constructor(t,e,s,i,o){this.type=1,this._$AH=u,this._$AN=void 0,this.element=t,this.name=e,this._$AM=i,this.options=o,s.length>2||s[0]!==""||s[1]!==""?(this._$AH=Array(s.length-1).fill(new String),this.strings=s):this._$AH=u}_$AI(t,e=this,s,i){let o=this.strings,a=!1;if(o===void 0)t=V(this,t,e,0),a=!st(t)||t!==this._$AH&&t!==W,a&&(this._$AH=t);else{let d=t,c,n;for(t=o[0],c=0;c<o.length-1;c++)n=V(this,d[s+c],e,c),n===W&&(n=this._$AH[c]),a||=!st(n)||n!==this._$AH[c],n===u?t=u:t!==u&&(t+=(n??"")+o[c+1]),this._$AH[c]=n}a&&!i&&this.j(t)}j(t){t===u?this.element.removeAttribute(this.name):this.element.setAttribute(this.name,t??"")}},gt=class extends q{constructor(){super(...arguments),this.type=3}j(t){this.element[this.name]=t===u?void 0:t}},_t=class extends q{constructor(){super(...arguments),this.type=4}j(t){this.element.toggleAttribute(this.name,!!t&&t!==u)}},bt=class extends q{constructor(t,e,s,i,o){super(t,e,s,i,o),this.type=5}_$AI(t,e=this){if((t=V(this,t,e,0)??u)===W)return;let s=this._$AH,i=t===u&&s!==u||t.capture!==s.capture||t.once!==s.once||t.passive!==s.passive,o=t!==u&&(s===u||i);i&&this.element.removeEventListener(this.name,this,s),o&&this.element.addEventListener(this.name,this,t),this._$AH=t}handleEvent(t){typeof this._$AH=="function"?this._$AH.call(this.options?.host??this.element,t):this._$AH.handleEvent(t)}},yt=class{constructor(t,e,s){this.element=t,this.type=6,this._$AN=void 0,this._$AM=e,this.options=s}get _$AU(){return this._$AM._$AU}_$AI(t){V(this,t)}};var le=xt.litHtmlPolyfillSupport;le?.(it,ot),(xt.litHtmlVersions??=[]).push("3.3.2");var Yt=(l,t,e)=>{let s=e?.renderBefore??t,i=s._$litPart$;if(i===void 0){let o=e?.renderBefore??null;s._$litPart$=i=new ot(t.insertBefore(et(),o),o,void 0,e??{})}return i._$AI(l),i};var At=globalThis,O=class extends D{constructor(){super(...arguments),this.renderOptions={host:this},this._$Do=void 0}createRenderRoot(){let t=super.createRenderRoot();return this.renderOptions.renderBefore??=t.firstChild,t}update(t){let e=this.render();this.hasUpdated||(this.renderOptions.isConnected=this.isConnected),super.update(t),this._$Do=Yt(e,this.renderRoot,this.renderOptions)}connectedCallback(){super.connectedCallback(),this._$Do?.setConnected(!0)}disconnectedCallback(){super.disconnectedCallback(),this._$Do?.setConnected(!1)}render(){return W}};O._$litElement$=!0,O.finalized=!0,At.litElementHydrateSupport?.({LitElement:O});var ce=At.litElementPolyfillSupport;ce?.({LitElement:O});(At.litElementVersions??=[]).push("4.2.2");var ct="2.0.0-alpha.19",z=["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"],K=[6,0,1,2,3,4,5],j=["home","away","sleep","wake"],dt=["home","away","sleep","wake","manual"],pt=["off","low","med","high"],B=[{v:"60",l:"1 hour"},{v:"120",l:"2 hours"},{v:"240",l:"4 hours"},{v:"forever",l:"Indefinite"},{v:"custom",l:"Custom time\u2026"}],S=["\u2460","\u2461","\u2462","\u2463","\u2464","\u2465","\u2466","\u2467"],de=(()=>{let l=[];for(let t=0;t<24;t++)for(let e=0;e<60;e+=15){let s=`${String(t).padStart(2,"0")}:${String(e).padStart(2,"0")}`,i=t===0?`12:${String(e).padStart(2,"0")} AM`:t<12?`${t}:${String(e).padStart(2,"0")} AM`:t===12?`12:${String(e).padStart(2,"0")} PM`:`${t-12}:${String(e).padStart(2,"0")} PM`;l.push({v:s,l:i})}return l})(),Z=50,J=90,Y=60,X=99,$=68,w=76,pe=800,he=400,ue=2e3,Xt=500,A=class extends O{static get baseProperties(){return{hass:{attribute:!1},_config:{state:!0},_registryLoaded:{state:!0}}}constructor(){super(),this._config={},this._registryEntities=null,this._registryLoaded=!1,this._cachedEntities=null,this._cachedEntitiesHass=null}setConfig(t){this._config=t}shouldUpdate(t){if(!t.has("hass")||!this._registryLoaded)return!0;let e=t.get("hass");return e?(this._registryEntities||[]).some(i=>this.hass.states[i.entity_id]!==e.states[i.entity_id]):!0}updated(t){t.has("hass")&&this.hass&&!this._registryLoaded&&this._loadRegistry(),t.has("hass")&&(this._cachedEntities=null)}async _loadRegistry(){try{let t=await this.hass.connection.sendMessagePromise({type:"config/entity_registry/list"});this._registryEntities=Array.isArray(t)?t.filter(e=>e.platform==="infinitude_direct"):[]}catch(t){console.warn("Failed to load entity registry",t),this._registryEntities=[]}this._registryLoaded=!0,this._cachedEntities=null}_findEntities(){if(this._cachedEntities&&this._cachedEntitiesHass===this.hass)return this._cachedEntities;if(!this.hass)return{climates:[],sensors:{},selects:{},system:{}};let t=this._registryEntities||[],e=this.hass.states,s=[],i={damper:{},fan:{}},o={},a={};if(this._config.climate_entities)for(let n of this._config.climate_entities)e[n]&&s.push(n);for(let n of t){let p=n.entity_id;if(!e[p])continue;let h=p.split(".")[0],m=n.unique_id||"";h==="climate"?this._config.climate_entities||s.push(p):h==="select"?o.wholeHouse=p:h==="sensor"&&(m.includes("damper")?i.damper[p]=e[p]:m.includes("fan")?i.fan[p]=e[p]:m.includes("humidifier")?a.humidifier=p:m.includes("oat")?a.oat=p:m.includes("op_status")?a.opStatus=p:m.includes("system_info")&&(a.info=p))}let d=n=>{let p=t.find(h=>h.entity_id===n);return parseInt((p?.unique_id||"").replace(/^infinitude_/,""))||0};s.sort((n,p)=>d(n)-d(p));let c={climates:s,sensors:i,selects:o,system:a};return this._cachedEntities=c,this._cachedEntitiesHass=this.hass,c}_st(t){return t?this.hass?.states[t]??null:null}_at(t,e){return this._st(t)?.attributes?.[e]}_getScheduleData(){let{system:t}=this._findEntities();if(!t.info)return{};try{return JSON.parse(this._at(t.info,"schedule")||"{}")}catch(e){return console.warn("Failed to parse schedule data",e),{}}}_getProfilesData(){let{system:t}=this._findEntities();if(!t.info)return[];try{return JSON.parse(this._at(t.info,"profiles")||"[]")}catch(e){return console.warn("Failed to parse profiles data",e),[]}}async _svc(t,e,s){try{await this.hass.callService(t,e,s)}catch(i){console.error(`${t}.${e} failed`,i)}}_setHvacMode(t,e){this._svc("climate","set_hvac_mode",{entity_id:t,hvac_mode:e})}_setPreset(t,e){this._svc("climate","set_preset_mode",{entity_id:t,preset_mode:e})}_resolveUntil(t,e){if(t==="forever")return"forever";if(t==="custom")return e||null;let s=new Date;s.setMinutes(s.getMinutes()+parseInt(t));let i=Math.round(s.getMinutes()/15)*15;return s.setMinutes(i,0,0),i===60&&(s.setMinutes(0),s.setHours(s.getHours()+1)),`${String(s.getHours()).padStart(2,"0")}:${String(s.getMinutes()).padStart(2,"0")}`}_otmrRelative(t){if(!t)return"";let[e,s]=t.split(":").map(Number),i=new Date;return i.setHours(e,s,0,0),"until "+i.toLocaleTimeString([],{hour:"numeric",minute:"2-digit"})}_zoneId(t){let e=(this._registryEntities||[]).find(s=>s.entity_id===t);return e?(e.unique_id||"").replace(/^infinitude_/,""):""}_renderLoading(){return r`<ha-card>
      <div style="padding:24px;text-align:center;color:var(--secondary-text-color)">Loading…</div>
    </ha-card>`}_adjustTemp(t,e,s){let i=this._st(t);if(!i)return;let o=i.attributes||{};this._tempAdj||(this._tempAdj={});let a=this._tempAdj[t]||(this._tempAdj[t]={}),d=a.heat??o.target_temp_low??o.temperature??$,c=a.cool??o.target_temp_high??(i.state==="cool"?o.temperature:null)??w;s==="heat"?a.heat=Math.max(Z,Math.min(J,Math.round(d)+e)):a.cool=Math.max(Y,Math.min(X,Math.round(c)+e)),this._pendingTemps={...this._pendingTemps,[t]:{heat:a.heat,cool:a.cool}},a.committing||(clearTimeout(a.timer),a.timer=setTimeout(()=>this._commitAdj(t),pe))}async _commitAdj(t){if(!this._tempAdj)return;let e=this._tempAdj[t];if(!e||e.committing)return;e.committing=!0;let s=this._st(t),i=s?.attributes||{},o=e.heat,a=e.cool,d=o??Math.round(i.target_temp_low??i.temperature??$),c=a??Math.round(i.target_temp_high??(s?.state==="cool"?i.temperature:null)??w),n=s?.state||"off",p={entity_id:t};n==="heat_cool"?(p.target_temp_low=d,p.target_temp_high=c):n==="heat"?p.temperature=d:n==="cool"?p.temperature=c:(p.target_temp_low=d,p.target_temp_high=c);try{await this.hass.callService("climate","set_temperature",p)}catch(h){console.error("set_temperature failed",h)}if(e.committing=!1,e.heat!==o||e.cool!==a){e.timer=setTimeout(()=>this._commitAdj(t),he);return}e.heat=null,e.cool=null,e.timer=null,setTimeout(()=>{if(!this._tempAdj[t]?.heat&&!this._tempAdj[t]?.cool){let{[t]:h,...m}=this._pendingTemps;this._pendingTemps=m}},ue)}_hasPending(t){let e=this._tempAdj?.[t];return e&&(e.heat!=null||e.cool!=null||e.committing)}_cancelHold(t){let e=this._zoneId(t);e&&this._svc("infinitude_direct","cancel_hold",{zone_id:e})}_setZoneHold(t){let e=this._zoneId(t);if(!e)return;let s=this._resolveUntil(this._holdDuration,this._holdCustom);s!==null&&(this._holdActivity==="manual"&&this._svc("infinitude_direct","set_profile",{zone_id:e,activity:"manual",htsp:this._holdHtsp,clsp:this._holdClsp,fan:this._holdFan}),this._svc("infinitude_direct","set_hold",{zone_id:e,activity:this._holdActivity,...s!==void 0&&{until:s}}),this._holdOpen=null)}_initHoldManual(t){let e=this._zoneId(t),s=this._getProfilesData().find(i=>i.id===e)?.activities?.manual||{};this._holdHtsp=s.htsp?Math.round(Number(s.htsp)||$):$,this._holdClsp=s.clsp?Math.round(Number(s.clsp)||w):w,this._holdFan=s.fan||"auto"}_setWholeHouseHold(){let t=this._resolveUntil(this._whHoldDuration,this._whHoldCustom);t!==null&&(this._svc("infinitude_direct","set_whole_house_hold",{activity:this._whHoldActivity,...t!==void 0&&{until:t}}),this._whHoldOpen=!1)}_cancelWholeHouseHold(){this._svc("infinitude_direct","cancel_whole_house_hold",{})}_periodCard(t,e,s,i,o,a){let d=e.length>1;return r`
      <div class="period-card">
        <div class="period-header">Period ${t+1}</div>
        ${e.map(c=>{let n=(s[c]?.[this._schedDay]||[])[t];if(!n)return u;let p=`${c}_${this._schedDay}_${t}`,h=this._schedEdits[p],m=h?.act??n.activity,f=h?.time??n.time,_=h?.enabled??n.enabled,E=i.find(b=>b.id===c)?.activities?.[m],H=E?.htsp?Math.round(Number(E.htsp)||0):"\u2013",k=E?.clsp?Math.round(Number(E.clsp)||0):"\u2013",v=d?S[a[c]]??c:o[c]||`Zone ${c}`;return r`
            <div class="sched-line ${_?"":"disabled"}">
              <span class="sched-name ${d?"sched-name-compact":""}">${v}</span>
              <select class="sched-select" .value=${m} @change=${b=>this._schedEdit(c,t,"act",b.target.value)}>
                ${j.map(b=>r`<option value=${b} ?selected=${b===m}>${b}</option>`)}
              </select>
              <select class="sched-select" .value=${f} @change=${b=>this._schedEdit(c,t,"time",b.target.value)}>
                ${de.map(b=>r`<option value=${b.v} ?selected=${b.v===f}>${b.l}</option>`)}
              </select>
              <label class="sched-toggle">
                <input type="checkbox" .checked=${_}
                       @change=${b=>this._schedEdit(c,t,"enabled",b.target.checked)}>
                <span>on</span>
              </label>
              <div class="sched-temps">
                <span class="sp-heat">${H}°</span>
                <span class="sp-cool">${k}°</span>
              </div>
            </div>`})}
      </div>`}_schedEdit(t,e,s,i){let o=`${t}_${this._schedDay}_${e}`,a=this._schedEdits[o]||{},d=(this._getScheduleData()[t]?.[this._schedDay]||[])[e]||{};this._schedEdits={...this._schedEdits,[o]:{act:s==="act"?i:a.act??d.activity,time:s==="time"?i:a.time??d.time,enabled:s==="enabled"?i:a.enabled??d.enabled}}}_copySched(t){let e=t.target.value;if(!e)return;t.target.value="";let s=this._getScheduleData(),i=e==="__all__"?z.filter(a=>a!==this._schedDay):[e],o={...this._schedEdits};for(let a of Object.keys(s)){let d=s[a]?.[this._schedDay]||[];for(let c of i)d.forEach((n,p)=>{let h=this._schedEdits[`${a}_${this._schedDay}_${p}`];o[`${a}_${c}_${p}`]={act:h?.act??n.activity,time:h?.time??n.time,enabled:h?.enabled??n.enabled}})}this._schedEdits=o}async _saveSched(){if(this._saving)return;this._saving=!0;let t={...this._schedEdits};try{let e=this._getScheduleData();for(let s of Object.keys(e)){let i=z.map(o=>({id:o,period:(e[s]?.[o]||[]).map((a,d)=>{let c=t[`${s}_${o}_${d}`];return{id:a.id||String(d+1),activity:c?.act??a.activity,time:c?.time??a.time,enabled:c?.enabled??a.enabled?"on":"off"}})}));await this._svc("infinitude_direct","save_schedule",{zone_id:s,schedule:JSON.stringify(i)})}}finally{setTimeout(()=>{let e=this._schedEdits,s={};for(let i of Object.keys(e))(!(i in t)||e[i]!==t[i])&&(s[i]=e[i]);this._schedEdits=s,this._saving=!1},Xt)}}_profAdj(t,e,s,i){let o=`${t}_${e}`,a=this._getProfilesData().find(f=>f.id===t)?.activities?.[e]||{},d=this._profileEdits[o]||{},c=d.htsp??(a.htsp?Math.round(Number(a.htsp)||$):$),n=d.clsp??(a.clsp?Math.round(Number(a.clsp)||w):w),p=s==="htsp"?Z:Y,h=s==="htsp"?J:X,m=s==="htsp"?c:n;this._profileEdits={...this._profileEdits,[o]:{zone_id:t,activity:e,htsp:s==="htsp"?Math.max(p,Math.min(h,m+i)):c,clsp:s==="clsp"?Math.max(p,Math.min(h,m+i)):n,fan:d.fan??a.fan??"low"}}}_profFan(t,e,s){let i=`${t}_${e}`,o=this._getProfilesData().find(d=>d.id===t)?.activities?.[e]||{},a=this._profileEdits[i]||{};this._profileEdits={...this._profileEdits,[i]:{zone_id:t,activity:e,htsp:a.htsp??(o.htsp?Math.round(Number(o.htsp)||$):$),clsp:a.clsp??(o.clsp?Math.round(Number(o.clsp)||w):w),fan:s}}}async _saveProfs(){if(this._savingProfs)return;this._savingProfs=!0;let t={...this._profileEdits};try{for(let e of Object.values(t)){let s={zone_id:e.zone_id,activity:e.activity,htsp:e.htsp,clsp:e.clsp};e.fan&&(s.fan=e.fan),await this._svc("infinitude_direct","set_profile",s)}}finally{setTimeout(()=>{let e=this._profileEdits,s={};for(let i of Object.keys(e))(!(i in t)||e[i]!==t[i])&&(s[i]=e[i]);this._profileEdits=s,this._savingProfs=!1},Xt)}}},T=C`
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
`;var Et=class extends A{static properties={...A.baseProperties,_whHoldOpen:{state:!0},_whHoldActivity:{state:!0},_whHoldDuration:{state:!0},_whHoldCustom:{state:!0}};constructor(){super(),this._whHoldOpen=!1,this._whHoldActivity="home",this._whHoldDuration="120",this._whHoldCustom=""}static getStubConfig(){return{}}getCardSize(){return 3}static styles=[T,C`
    .card-pad { padding: 16px; }
    .header {
      display: flex; align-items: center; gap: 8px; margin-bottom: 14px;
    }
    .header-title { font-size: 18px; font-weight: 500; color: var(--primary-text-color); }
  `];render(){if(!this.hass)return u;if(!this._registryLoaded)return this._renderLoading();let t=this._findEntities(),{system:e,selects:s,climates:i}=t,o=i.length&&this._st(i[0])?.state||"off",a=["off","heat","cool","heat_cool"],d={off:"Off",heat:"Heat",cool:"Cool",heat_cool:"Auto"},c=this._st(e.oat),n="\u2013";if(c?.state&&c.state!=="unavailable")n=`${Math.round(Number(c.state))}\xB0`;else if(i.length){let v=this._at(i[0],"outdoor_temperature");v!=null&&(n=`${Math.round(Number(v))}\xB0`)}let p=this._st(e.opStatus),h=p?.state&&p.state!=="unavailable"?p.state:"",m=this._st(e.humidifier)?.state==="on",f=this._st(s.wholeHouse),_=f&&f.state!=="off",M=i.length?this._at(i[0],"whole_house_hold_until"):null,E=i.length?this._at(i[0],"current_humidity"):null,H=e.info?this._st(e.info)?.state!=="unavailable":!1,k=e.info?this._at(e.info,"carrier_ok"):null;return r`
      <ha-card>
        <div class="card-pad">
          <div class="header">
            <span class="header-title">infinitude</span>
            <span class="conn-dot ${H?"ok":"err"}" title="${H?"Infinitude: connected":"Infinitude: unavailable"}"></span>
            <span class="conn-dot ${k===!0?"ok":k===!1?"err":"unk"}" title="${k===!0?"Carrier cloud: connected":k===!1?"Carrier cloud: unreachable":"Carrier cloud: checking\u2026"}"></span>
            <span style="font-size:10px;color:var(--secondary-text-color);opacity:0.5">v${ct}</span>
          </div>
          <div class="mode-row">
            <span class="mode-label">Mode</span>
            <div class="mode-pills">
              ${a.map(v=>r`<div class="mode-pill ${v===o?"active":""} ${v==="heat"?"heat":v==="cool"?"cool":v==="heat_cool"?"auto":""}"
                  @click=${()=>this._setHvacMode(i[0],v)}>${d[v]}</div>`)}
            </div>
          </div>
          <div class="summary-stats">
            <div class="summary-stat">
              <span class="summary-stat-label">Status</span>
              <span class="summary-stat-val ${h.toLowerCase().includes("heat")?"heat":h.toLowerCase().includes("cool")?"cool":""}">${h||"Idle"}</span>
            </div>
            <div class="summary-divider"></div>
            <div class="summary-stat">
              <span class="summary-stat-label">Outdoor</span>
              <span class="summary-stat-val">${n}</span>
            </div>
            <div class="summary-divider"></div>
            <div class="summary-stat">
              <span class="summary-stat-label">Humidity</span>
              <span class="summary-stat-val">${E!=null?`${E}%`:"\u2013"}</span>
            </div>
            ${m?r`
              <div class="summary-divider"></div>
              <div class="summary-stat">
                <span class="summary-stat-label">Humidifier</span>
                <span class="summary-stat-val" style="color:var(--label-badge-blue,#38bdf8)">💧 On</span>
              </div>`:u}
          </div>
          ${_?r`
            <div class="wh-hold" @click=${()=>this._cancelWholeHouseHold()}>
              <ha-icon icon="mdi:home-lock" style="--mdc-icon-size:16px"></ha-icon>
              <span>Whole house: <strong>${f.state}</strong>${M?r` · <span style="opacity:0.85">${this._otmrRelative(M)}</span>`:u}</span>
              <span style="margin-left:auto;opacity:0.7">Tap to cancel</span>
            </div>`:r`
            ${this._whHoldOpen?r`
              <div class="wh-set">
                <span class="wh-set-label">WH Hold</span>
                <div class="wh-pills">
                  ${j.map(v=>r`
                    <div class="wh-pill ${this._whHoldActivity===v?"active":""}"
                         @click=${()=>{this._whHoldActivity=v}}>${v}</div>`)}
                </div>
                <select class="hold-dur-select" @change=${v=>{this._whHoldDuration=v.target.value}}>
                  ${B.map(v=>r`<option value=${v.v} ?selected=${v.v===this._whHoldDuration}>${v.l}</option>`)}
                </select>
                ${this._whHoldDuration==="custom"?r`
                  <input type="time" class="hold-time-input" step="900" .value=${this._whHoldCustom}
                         @change=${v=>{this._whHoldCustom=v.target.value}}>`:u}
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
      </ha-card>`}};customElements.get("infinitude-status-card")||customElements.define("infinitude-status-card",Et);window.customCards=window.customCards||[];window.customCards.some(l=>l.type==="infinitude-status-card")||window.customCards.push({type:"infinitude-status-card",name:"Infinitude Status",description:"System mode, stats, and whole-house hold for Carrier/Bryant Infinity",preview:!1});var kt=class extends A{static properties={...A.baseProperties,_pendingTemps:{state:!0},_holdOpen:{state:!0},_holdActivity:{state:!0},_holdDuration:{state:!0},_holdCustom:{state:!0},_holdHtsp:{state:!0},_holdClsp:{state:!0},_holdFan:{state:!0}};constructor(){super(),this._pendingTemps={},this._tempAdj={},this._holdOpen=!1,this._holdActivity="home",this._holdDuration="120",this._holdCustom="",this._holdHtsp=$,this._holdClsp=w,this._holdFan="auto"}static getConfigElement(){return document.createElement("infinitude-zone-card-editor")}static getStubConfig(){return{entity:""}}getCardSize(){return 4}static styles=[T,C`
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
  `];render(){if(!this.hass)return u;if(!this._registryLoaded)return this._renderLoading();let t=this._config.entity;if(!t)return r`<ha-card><div class="card-pad" style="color:var(--secondary-text-color)">No entity configured</div></ha-card>`;let e=this._st(t);if(!e)return r`<ha-card><div class="card-pad" style="color:var(--secondary-text-color)">Entity unavailable</div></ha-card>`;let s=e.attributes||{},i=this._zoneId(t),o=S[parseInt(i)-1]||i,a=(s.friendly_name||t).replace(/^Infinitude\s+/i,"").replace(/^infinitude_direct\s+/i,""),d=o?`${o} ${a}`:a,c=s.current_temperature!=null?Math.round(s.current_temperature):"\u2013",n=s.current_humidity,p=e.state||"off",h=s.hvac_action||"idle",m=s.preset_mode||"\u2013",f=h==="heating"?"heating":h==="cooling"?"cooling":h==="drying"?"drying":"",_=h==="idle"?"Idle":h.charAt(0).toUpperCase()+h.slice(1),M=p==="heat_cool",E=!!s.hold_active,H=s.hold_activity||m,k=s.hold_until,v=this._pendingTemps[t],b=this._hasPending(t),I=v?.heat??s.target_temp_low??s.temperature??null,L=v?.cool??s.target_temp_high??(p==="cool"?s.temperature:null)??null;return r`
      <ha-card class="${f}">
        <div class="card-pad">
          <div class="zone-top">
            <div style="display:flex;align-items:center;gap:8px">
              <span class="zone-cond-dot ${f||"idle"}" title="${h==="drying"?"Dehumidifying":_}"></span>
              <span class="zone-name">${d}</span>
            </div>
            <span class="zone-activity-pill">${m}</span>
          </div>
          <div class="zone-body">
            <div>
              <span class="temp-hero">${c}</span><span class="temp-unit">°F</span>
            </div>
            <div class="zone-sp">
              ${I!=null?r`
                <div class="sp-row">
                  <button class="btn-adj" @click=${()=>this._adjustTemp(t,-1,"heat")}>−</button>
                  <span class="sp-val sp-heat ${b?"sp-pending":""}">${Math.round(I)}°</span>
                  <button class="btn-adj" @click=${()=>this._adjustTemp(t,1,"heat")}>+</button>
                </div>`:u}
              ${M&&L!=null?r`
                <div class="sp-row">
                  <button class="btn-adj" @click=${()=>this._adjustTemp(t,-1,"cool")}>−</button>
                  <span class="sp-val sp-cool ${b?"sp-pending":""}">${Math.round(L)}°</span>
                  <button class="btn-adj" @click=${()=>this._adjustTemp(t,1,"cool")}>+</button>
                </div>`:u}
            </div>
          </div>
          <div class="zone-meta">
            ${n!=null?r`<span class="meta-item">RH <span class="meta-val">${n}%</span></span>`:u}
            ${s.fan_mode?r`<span class="meta-item">Fan <span class="meta-val">${s.fan_mode}</span></span>`:u}
            ${s.damper_position!=null?r`<span class="meta-item">Damper <span class="meta-val">${s.damper_position}%</span></span>`:u}
          </div>
          ${E?r`
            <div class="zone-hold">
              <span class="hold-label">Hold: ${H}${k?` \xB7 ${this._otmrRelative(k)}`:""}</span>
              <button class="btn" style="font-size:11px;padding:3px 10px;color:var(--error-color,#f87171)" @click=${()=>this._cancelHold(t)}>Cancel</button>
            </div>`:u}
          ${this._holdOpen?r`
            <div class="zone-hold-picker">
              <div class="hold-picker-row">
                <div class="wh-pills">
                  ${dt.map(x=>r`
                    <div class="wh-pill ${this._holdActivity===x?"active":""}"
                         @click=${()=>{this._holdActivity=x,x==="manual"&&this._initHoldManual(t)}}>${x}</div>`)}
                </div>
              </div>
              ${this._holdActivity==="manual"?r`
                <div class="hold-picker-row" style="gap:10px;flex-wrap:wrap">
                  <div class="sp-row">
                  <button class="btn-adj" @click=${()=>{this._holdHtsp=Math.max(Z,this._holdHtsp-1)}}>−</button>
                  <span class="sp-val sp-heat">${this._holdHtsp}°</span>
                  <button class="btn-adj" @click=${()=>{this._holdHtsp=Math.min(J,this._holdHtsp+1)}}>+</button>
                </div>
                <div class="sp-row">
                  <button class="btn-adj" @click=${()=>{this._holdClsp=Math.max(Y,this._holdClsp-1)}}>−</button>
                  <span class="sp-val sp-cool">${this._holdClsp}°</span>
                  <button class="btn-adj" @click=${()=>{this._holdClsp=Math.min(X,this._holdClsp+1)}}>+</button>
                  </div>
                  <div style="display:flex;align-items:center;gap:4px">
                    <span style="font-size:10px;color:var(--secondary-text-color)">Fan</span>
                    <select class="hold-dur-select" style="width:auto" .value=${this._holdFan} @change=${x=>{this._holdFan=x.target.value}}>
                      <option value="auto">Auto</option>
                      <option value="low">Low</option>
                      <option value="med">Med</option>
                      <option value="high">High</option>
                    </select>
                  </div>
                </div>`:u}
              <div class="hold-picker-row">
                <select class="hold-dur-select" @change=${x=>{this._holdDuration=x.target.value}}>
                  ${B.map(x=>r`<option value=${x.v} ?selected=${x.v===this._holdDuration}>${x.l}</option>`)}
                </select>
                ${this._holdDuration==="custom"?r`
                  <input type="time" class="hold-time-input" step="900" .value=${this._holdCustom}
                         @change=${x=>{this._holdCustom=x.target.value}}>`:u}
              </div>
              <div class="hold-picker-row">
                <button class="btn btn-primary" style="font-size:11px;padding:4px 12px" @click=${()=>this._setZoneHold(t)}>Apply</button>
                <button class="btn" style="font-size:11px;padding:4px 10px" @click=${()=>{this._holdOpen=!1}}>Cancel</button>
              </div>
            </div>`:E?u:r`
            <div class="zone-actions">
              <button class="btn" style="font-size:11px;padding:4px 12px" @click=${()=>{this._holdActivity=m!=="\u2013"?m:"home",this._holdDuration="120",this._holdCustom="",this._holdActivity==="manual"&&this._initHoldManual(t),this._holdOpen=!0}}>Set hold</button>
            </div>`}
        </div>
      </ha-card>`}},Ct=class extends O{static properties={hass:{attribute:!1},_config:{state:!0},_infEntities:{state:!0}};constructor(){super(),this._infEntities=null}setConfig(t){this._config=t||{}}async _loadRegistry(){if(!(this._infEntities||!this.hass))try{let t=await this.hass.callWS({type:"config/entity_registry/list"});this._infEntities=new Set((t||[]).filter(e=>e.platform==="infinitude_direct"&&e.entity_id.startsWith("climate.")).map(e=>e.entity_id))}catch{this._infEntities=new Set}}updated(t){t.has("hass")&&!this._infEntities&&this._loadRegistry()}_entityChanged(t){if(t.stopPropagation(),!this._config)return;let e=t.target?.value??"";if(e===this._config.entity)return;let s={...this._config,entity:e};this.dispatchEvent(new CustomEvent("config-changed",{detail:{config:s},bubbles:!0,composed:!0}))}_label(t){let s=this.hass.states[t]?.attributes?.friendly_name;return s?`${s}  \u2014  ${t}`:t}render(){if(!this.hass)return r``;let t=this._infEntities?[...this._infEntities].sort():[],e=this._config?.entity||"";return r`
      <div style="padding:8px 0">
        <label style="display:block;font-size:12px;color:var(--secondary-text-color);margin-bottom:6px">Zone entity</label>
        <select
          style="width:100%;padding:8px 10px;background:var(--card-background-color);border:1px solid var(--divider-color);border-radius:4px;color:var(--primary-text-color);font-size:14px"
          .value=${e}
          @change=${this._entityChanged}>
          <option value="" ?selected=${!e}>— select a zone —</option>
          ${t.map(s=>r`<option value=${s} ?selected=${s===e}>${this._label(s)}</option>`)}
        </select>
        <div style="font-size:11px;color:var(--secondary-text-color);margin-top:6px">
          ${t.length?r`${t.length} climate entit${t.length===1?"y":"ies"} from the Infinitude Direct integration.`:r`No Infinitude Direct climate entities found.`}
        </div>
      </div>
    `}};customElements.get("infinitude-zone-card-editor")||customElements.define("infinitude-zone-card-editor",Ct);customElements.get("infinitude-zone-card")||customElements.define("infinitude-zone-card",kt);window.customCards=window.customCards||[];window.customCards.some(l=>l.type==="infinitude-zone-card")||window.customCards.push({type:"infinitude-zone-card",name:"Infinitude Zone",description:"Single zone control for Carrier/Bryant Infinity thermostat",preview:!1});var St=class extends A{static properties={...A.baseProperties,_schedDay:{state:!0},_schedEdits:{state:!0}};constructor(){super(),this._schedDay=z[K[new Date().getDay()]],this._schedEdits={},this._saving=!1}static getStubConfig(){return{}}getCardSize(){return 6}static styles=[T,C`
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
  `];render(){if(!this.hass)return u;if(!this._registryLoaded)return this._renderLoading();let t=this._getScheduleData(),e=this._getProfilesData(),s=Object.keys(t);if(!s.length)return r`<ha-card>
      <div class="card-pad" style="text-align:center;color:var(--secondary-text-color)">
        <ha-icon icon="mdi:calendar-clock" style="--mdc-icon-size:48px;opacity:0.3;margin-bottom:12px;display:block"></ha-icon>
        No schedule data available.
      </div></ha-card>`;let i=z[K[new Date().getDay()]],o={},a={};for(let n=0;n<e.length;n++)o[e[n].id]=e[n].name,a[e[n].id]=n;let d=0;for(let n of s)d=Math.max(d,(t[n]?.[this._schedDay]||[]).length);d||(d=5);let c=Object.keys(this._schedEdits).length>0;return r`
      <ha-card>
        <div class="card-pad">
          <div class="section-title">Schedule</div>
          ${s.length>1?r`<div class="zone-legend">${s.map((n,p)=>r`<span class="legend-item"><span class="legend-num">${S[p]||p+1}</span> ${o[n]||`Zone ${n}`}</span>`)}</div>`:u}
          <div class="sched-day-tabs">
            ${z.map(n=>r`
              <div class="day-tab ${n===this._schedDay?"active":""} ${n===i&&n!==this._schedDay?"today":""}"
                   @click=${()=>{this._schedDay=n}}>${n.slice(0,3)}</div>`)}
          </div>
          ${Array.from({length:d},(n,p)=>this._periodCard(p,s,t,e,o,a))}
          <div class="copy-bar">
            <span>Copy ${this._schedDay.slice(0,3)} →</span>
            <select class="sched-select" @change=${n=>this._copySched(n)}>
              <option value="">select day…</option>
              ${z.filter(n=>n!==this._schedDay).map(n=>r`<option value=${n}>${n.slice(0,3)}</option>`)}
              <option value="__all__">All other days</option>
            </select>
          </div>
          ${c?r`
            <div class="action-bar">
              <span class="action-bar-label">● Unsaved changes</span>
              <button class="btn" @click=${()=>{this._schedEdits={}}}>Discard</button>
              <button class="btn btn-primary" @click=${()=>this._saveSched()}>Save schedule</button>
            </div>`:u}
        </div>
      </ha-card>`}};customElements.get("infinitude-schedule-card")||customElements.define("infinitude-schedule-card",St);window.customCards=window.customCards||[];window.customCards.some(l=>l.type==="infinitude-schedule-card")||window.customCards.push({type:"infinitude-schedule-card",name:"Infinitude Schedule",description:"Weekly schedule editing for Carrier/Bryant Infinity thermostat",preview:!1});var zt=class extends A{static properties={...A.baseProperties,_profileEdits:{state:!0}};constructor(){super(),this._profileEdits={},this._savingProfs=!1}static getStubConfig(){return{}}getCardSize(){return 6}static styles=[T,C`
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
  `];render(){if(!this.hass)return u;if(!this._registryLoaded)return this._renderLoading();let t=this._getProfilesData();if(!t.length)return r`<ha-card>
      <div class="card-pad" style="text-align:center;color:var(--secondary-text-color)">
        <ha-icon icon="mdi:tune-vertical" style="--mdc-icon-size:48px;opacity:0.3;margin-bottom:12px;display:block"></ha-icon>
        No profile data available.
      </div></ha-card>`;let e=t.length>1,s=Object.keys(this._profileEdits).length>0;return r`
      <ha-card>
        <div class="card-pad">
          <div class="section-title">Comfort Profiles</div>
          ${e?r`<div class="zone-legend">${t.map((i,o)=>r`<span class="legend-item"><span class="legend-num">${S[o]||o+1}</span> ${i.name}</span>`)}</div>`:u}
          ${j.map(i=>r`
            <div class="prof-card">
              <div class="prof-header">${i}</div>
              ${t.map((o,a)=>{let d=o.activities?.[i]||{},c=`${o.id}_${i}`,n=this._profileEdits[c],p=n?.htsp??(d.htsp?Math.round(Number(d.htsp)||$):$),h=n?.clsp??(d.clsp?Math.round(Number(d.clsp)||w):w),m=n?.fan??d.fan??"low",f=e?S[a]||a+1:o.name;return r`
                  <div class="prof-line">
                    <span class="prof-name ${e?"prof-name-compact":""}">${f}</span>
                    <div class="sp-row">
                      <button class="btn-adj" @click=${()=>this._profAdj(o.id,i,"htsp",-1)}>−</button>
                      <span class="sp-val sp-heat">${p}°</span>
                      <button class="btn-adj" @click=${()=>this._profAdj(o.id,i,"htsp",1)}>+</button>
                    </div>
                    <div class="sp-row">
                      <button class="btn-adj" @click=${()=>this._profAdj(o.id,i,"clsp",-1)}>−</button>
                      <span class="sp-val sp-cool">${h}°</span>
                      <button class="btn-adj" @click=${()=>this._profAdj(o.id,i,"clsp",1)}>+</button>
                    </div>
                    <div class="prof-fan">
                      <span class="prof-fan-label">Fan</span>
                      <select class="sched-select" .value=${m} @change=${_=>this._profFan(o.id,i,_.target.value)}>
                        ${pt.map(_=>r`<option value=${_} ?selected=${_===m}>${_}</option>`)}
                      </select>
                    </div>
                  </div>`})}
            </div>`)}
          ${s?r`
            <div class="action-bar">
              <span class="action-bar-label">● Unsaved changes</span>
              <button class="btn" @click=${()=>{this._profileEdits={}}}>Discard</button>
              <button class="btn btn-primary" @click=${()=>this._saveProfs()}>Save profiles</button>
            </div>`:u}
        </div>
      </ha-card>`}};customElements.get("infinitude-profiles-card")||customElements.define("infinitude-profiles-card",zt);window.customCards=window.customCards||[];window.customCards.some(l=>l.type==="infinitude-profiles-card")||window.customCards.push({type:"infinitude-profiles-card",name:"Infinitude Profiles",description:"Comfort profile editing for Carrier/Bryant Infinity thermostat",preview:!1});var Ht=class extends A{static properties={...A.baseProperties,_tab:{state:!0},_schedDay:{state:!0},_schedEdits:{state:!0},_profileEdits:{state:!0},_pendingTemps:{state:!0},_whHoldOpen:{state:!0},_whHoldActivity:{state:!0},_whHoldDuration:{state:!0},_whHoldCustom:{state:!0},_holdOpen:{state:!0},_holdActivity:{state:!0},_holdDuration:{state:!0},_holdCustom:{state:!0},_holdHtsp:{state:!0},_holdClsp:{state:!0},_holdFan:{state:!0}};constructor(){super(),this._tab="status",this._schedDay=z[K[new Date().getDay()]],this._schedEdits={},this._profileEdits={},this._tempAdj={},this._pendingTemps={},this._whHoldOpen=!1,this._whHoldActivity="home",this._whHoldDuration="120",this._whHoldCustom="",this._holdOpen=null,this._holdActivity="home",this._holdDuration="120",this._holdCustom="",this._holdHtsp=$,this._holdClsp=w,this._holdFan="auto",this._saving=!1,this._savingProfs=!1}connectedCallback(){super.connectedCallback(),this._staleTimer=setInterval(()=>this.requestUpdate(),3e4)}disconnectedCallback(){super.disconnectedCallback(),clearInterval(this._staleTimer)}static getStubConfig(){return{}}getCardSize(){return 8}static styles=[T,C`
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
  `];render(){if(!this.hass)return u;if(!this._registryLoaded)return r`<ha-card>
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
          ${this._tab==="status"?this._status(t):u}
          ${this._tab==="schedule"?this._sched():u}
          ${this._tab==="profiles"?this._profs():u}
        </div>
      </ha-card>`}_hdr(t){let{system:e}=t,s=e.info?this._st(e.info)?.state!=="unavailable":!1,i=e.info?this._at(e.info,"carrier_ok"):null;return r`
      <div class="header-left">
        <span class="header-title">infinitude</span>
        <span class="conn-dot ${s?"ok":"err"}" title="${s?"Infinitude: connected":"Infinitude: unavailable"}"></span>
        <span class="conn-dot ${i===!0?"ok":i===!1?"err":"unk"}" title="${i===!0?"Carrier cloud: connected":i===!1?"Carrier cloud: unreachable":"Carrier cloud: checking\u2026"}"></span>
        <span style="font-size:10px;color:var(--secondary-text-color);opacity:0.5">v${ct}</span>
      </div>`}_tabs(){return r`${["status","schedule","profiles"].map(e=>r`
      <div class="tab ${this._tab===e?"active":""}"
           @click=${()=>{this._tab=e}}>${e.charAt(0).toUpperCase()+e.slice(1)}</div>`)}`}_status(t){let{climates:e}=t;return e.length?r`
      ${this._summaryStrip(t)}
      <div class="zone-grid">${e.map(s=>this._zoneCard(s))}</div>`:r`<div style="padding:20px;text-align:center;color:var(--secondary-text-color)">No zone entities found</div>`}_summaryStrip(t){let{system:e,selects:s,climates:i}=t,o=i.length&&this._st(i[0])?.state||"off",a=["off","heat","cool","heat_cool","fan_only"],d={off:"Off",heat:"Heat",cool:"Cool",heat_cool:"Auto",fan_only:"Fan"},c=this._st(e.oat),n="\u2013";if(c?.state&&c.state!=="unavailable")n=`${Math.round(Number(c.state))}\xB0`;else if(i.length){let g=this._at(i[0],"outdoor_temperature");g!=null&&(n=`${Math.round(Number(g))}\xB0`)}let p=this._st(e.opStatus),h=p?.state&&p.state!=="unavailable"?p.state:"",m=this._st(e.humidifier)?.state==="on",f=this._st(s.wholeHouse),_=f&&f.state!=="off",M=i.length?this._at(i[0],"whole_house_hold_until"):null,E=i.length?this._at(i[0],"current_humidity"):null,H=i.some(g=>this._at(g,"hvac_action")==="heating"),k=i.some(g=>this._at(g,"hvac_action")==="cooling"),v=i.some(g=>this._at(g,"hvac_action")==="drying"),b=H?"Heating":k?"Cooling":v?"Dehumidifying":h||"Idle",I=H?"heat":k?"cool":"",L=this._registryEntities||[],P=0;for(let g of L){let y=this.hass.states[g.entity_id]?.last_reported;if(!y)continue;let Mt=Date.parse(y);Mt>P&&(P=Mt)}let x=P>0&&Date.now()-P>9e4;return r`
      <div class="mode-row">
        <span class="mode-label">Mode</span>
        <div class="mode-pills">
          ${a.map(g=>r`<div class="mode-pill ${g===o?"active":""} ${g==="heat"?"heat":g==="cool"?"cool":g==="heat_cool"?"auto":""}"
              @click=${()=>this._setHvacMode(i[0],g)}>${d[g]}</div>`)}
        </div>
      </div>
      <div class="summary-stats">
        <div class="summary-stat">
          <span class="summary-stat-label">Status</span>
          <span class="summary-stat-val ${I}">${b}</span>
        </div>
        <div class="summary-divider"></div>
        <div class="summary-stat">
          <span class="summary-stat-label">Outdoor</span>
          <span class="summary-stat-val">${n}</span>
        </div>
        <div class="summary-divider"></div>
        <div class="summary-stat">
          <span class="summary-stat-label">Humidity</span>
          <span class="summary-stat-val">${E!=null?`${E}%`:"\u2013"}</span>
        </div>
        ${m?r`
          <div class="summary-divider"></div>
          <div class="summary-stat">
            <span class="summary-stat-label">Humidifier</span>
            <span class="summary-stat-val" style="color:var(--label-badge-blue,#38bdf8)">💧 On</span>
          </div>`:u}
      </div>
      ${x?r`<div class="stale-warn">⚠ Thermostat data is stale — system may be offline</div>`:u}
      ${_?r`
        <div class="wh-hold" @click=${()=>this._cancelWholeHouseHold()}>
          <ha-icon icon="mdi:home-lock" style="--mdc-icon-size:16px"></ha-icon>
          <span>Whole house: <strong>${f.state}</strong>${M?r` · <span style="opacity:0.85">${this._otmrRelative(M)}</span>`:u}</span>
          <span style="margin-left:auto;opacity:0.7">Tap to cancel</span>
        </div>`:r`
        ${this._whHoldOpen?r`
          <div class="wh-set">
            <span class="wh-set-label">WH Hold</span>
            <div class="wh-pills">
              ${j.map(g=>r`
                <div class="wh-pill ${this._whHoldActivity===g?"active":""}"
                     @click=${()=>{this._whHoldActivity=g}}>${g}</div>`)}
            </div>
            <select class="hold-dur-select" @change=${g=>{this._whHoldDuration=g.target.value}}>
              ${B.map(g=>r`<option value=${g.v} ?selected=${g.v===this._whHoldDuration}>${g.l}</option>`)}
            </select>
            ${this._whHoldDuration==="custom"?r`
              <input type="time" class="hold-time-input" step="900" .value=${this._whHoldCustom}
                     @change=${g=>{this._whHoldCustom=g.target.value}}>`:u}
            <button class="btn btn-primary" style="font-size:11px;padding:4px 12px" @click=${()=>this._setWholeHouseHold()}>Apply</button>
            <button class="btn" style="font-size:11px;padding:4px 10px" @click=${()=>{this._whHoldOpen=!1}}>Cancel</button>
          </div>`:r`
          <div style="margin-bottom:12px">
            <button class="btn" style="font-size:11px;padding:4px 12px" @click=${()=>{this._whHoldOpen=!0}}>
              <ha-icon icon="mdi:home-lock" style="--mdc-icon-size:14px;vertical-align:middle;margin-right:4px"></ha-icon>Set WH hold
            </button>
          </div>`}
      `}`}_zoneCard(t){let e=this._st(t);if(!e)return u;let s=e.attributes||{},i=this._zoneId(t),o=S[parseInt(i)-1]||i,a=(s.friendly_name||t).replace(/^Infinitude\s+/i,"").replace(/^infinitude_direct\s+/i,""),d=o?`${o} ${a}`:a,c=s.current_temperature!=null?Math.round(s.current_temperature):"\u2013",n=s.current_humidity,p=e.state||"off",h=s.hvac_action||"idle",m=s.preset_mode||"\u2013",f=h==="heating"?"heating":h==="cooling"?"cooling":h==="drying"?"drying":"",_=h==="idle"?"Idle":h.charAt(0).toUpperCase()+h.slice(1),M=p==="heat_cool",E=!!s.hold_active,H=s.hold_activity||m,k=s.hold_until,v=this._holdOpen===t,b=this._pendingTemps[t],I=this._hasPending(t),L=b?.heat??s.target_temp_low??s.temperature??null,P=b?.cool??s.target_temp_high??(p==="cool"?s.temperature:null)??null;return r`
      <div class="zone-card ${f}">
        <div class="zone-top">
          <div style="display:flex;align-items:center;gap:8px">
            <span class="zone-cond-dot ${f||"idle"}" title="${h==="drying"?"Dehumidifying":_}"></span>
            <span class="zone-name">${d}</span>
          </div>
          <span class="zone-activity-pill">${m}</span>
        </div>
        <div class="zone-body">
          <div>
            <span class="temp-hero">${c}</span><span class="temp-unit">°F</span>
          </div>
          <div class="zone-sp">
            ${L!=null?r`
              <div class="sp-row">
                <button class="btn-adj" @click=${()=>this._adjustTemp(t,-1,"heat")}>−</button>
                <span class="sp-val sp-heat ${I?"sp-pending":""}">${Math.round(L)}°</span>
                <button class="btn-adj" @click=${()=>this._adjustTemp(t,1,"heat")}>+</button>
              </div>`:u}
            ${M&&P!=null?r`
              <div class="sp-row">
                <button class="btn-adj" @click=${()=>this._adjustTemp(t,-1,"cool")}>−</button>
                <span class="sp-val sp-cool ${I?"sp-pending":""}">${Math.round(P)}°</span>
                <button class="btn-adj" @click=${()=>this._adjustTemp(t,1,"cool")}>+</button>
              </div>`:u}
          </div>
        </div>
        <div class="zone-meta">
          ${n!=null?r`<span class="meta-item">RH <span class="meta-val">${n}%</span></span>`:u}
          ${s.fan_mode?r`<span class="meta-item">Fan <span class="meta-val">${s.fan_mode}</span></span>`:u}
          ${s.damper_position!=null?r`<span class="meta-item">Damper <span class="meta-val">${s.damper_position}%</span></span>`:u}
        </div>
        ${E?r`
          <div class="zone-hold">
            <span class="hold-label">Hold: ${H}${k?` \xB7 ${this._otmrRelative(k)}`:""}</span>
            <button class="btn" style="font-size:11px;padding:3px 10px;color:var(--error-color,#f87171)" @click=${()=>this._cancelHold(t)}>Cancel</button>
          </div>`:u}
        ${v?r`
          <div class="zone-hold-picker">
            <div class="hold-picker-row">
              <div class="wh-pills">
                ${dt.map(y=>r`
                  <div class="wh-pill ${this._holdActivity===y?"active":""}"
                       @click=${()=>{this._holdActivity=y,y==="manual"&&this._initHoldManual(t)}}>${y}</div>`)}
              </div>
            </div>
            ${this._holdActivity==="manual"?r`
              <div class="hold-picker-row" style="gap:10px;flex-wrap:wrap">
                <div class="sp-row">
                  <button class="btn-adj" @click=${()=>{this._holdHtsp=Math.max(Z,this._holdHtsp-1)}}>−</button>
                  <span class="sp-val sp-heat">${this._holdHtsp}°</span>
                  <button class="btn-adj" @click=${()=>{this._holdHtsp=Math.min(J,this._holdHtsp+1)}}>+</button>
                </div>
                <div class="sp-row">
                  <button class="btn-adj" @click=${()=>{this._holdClsp=Math.max(Y,this._holdClsp-1)}}>−</button>
                  <span class="sp-val sp-cool">${this._holdClsp}°</span>
                  <button class="btn-adj" @click=${()=>{this._holdClsp=Math.min(X,this._holdClsp+1)}}>+</button>
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
              </div>`:u}
            <div class="hold-picker-row">
              <select class="hold-dur-select" @change=${y=>{this._holdDuration=y.target.value}}>
                ${B.map(y=>r`<option value=${y.v} ?selected=${y.v===this._holdDuration}>${y.l}</option>`)}
              </select>
              ${this._holdDuration==="custom"?r`
                <input type="time" class="hold-time-input" step="900" .value=${this._holdCustom}
                       @change=${y=>{this._holdCustom=y.target.value}}>`:u}
            </div>
            <div class="hold-picker-row">
              <button class="btn btn-primary" style="font-size:11px;padding:4px 12px" @click=${()=>this._setZoneHold(t)}>Apply</button>
              <button class="btn" style="font-size:11px;padding:4px 10px" @click=${()=>{this._holdOpen=null}}>Cancel</button>
            </div>
          </div>`:E?u:r`
          <div class="zone-actions">
            <button class="btn" style="font-size:11px;padding:4px 12px" @click=${()=>{this._holdActivity=m!=="\u2013"?m:"home",this._holdDuration="120",this._holdCustom="",this._holdActivity==="manual"&&this._initHoldManual(t),this._holdOpen=t}}>Set hold</button>
          </div>`}
      </div>`}_sched(){let t=this._getScheduleData(),e=this._getProfilesData(),s=Object.keys(t);if(!s.length)return r`
      <div style="padding:20px;text-align:center;color:var(--secondary-text-color)">
        <ha-icon icon="mdi:calendar-clock" style="--mdc-icon-size:48px;opacity:0.3;margin-bottom:12px;display:block"></ha-icon>
        No schedule data available. Waiting for thermostat data…
      </div>`;let i=z[K[new Date().getDay()]],o={},a={};for(let n=0;n<e.length;n++)o[e[n].id]=e[n].name,a[e[n].id]=n;let d=0;for(let n of s)d=Math.max(d,(t[n]?.[this._schedDay]||[]).length);d||(d=5);let c=Object.keys(this._schedEdits).length>0;return r`
      <div class="section-title">Schedule</div>
      ${s.length>1?r`<div class="zone-legend">${s.map((n,p)=>r`<span class="legend-item"><span class="legend-num">${S[p]||p+1}</span> ${o[n]||`Zone ${n}`}</span>`)}</div>`:u}
      <div class="sched-day-tabs">
        ${z.map(n=>r`
          <div class="day-tab ${n===this._schedDay?"active":""} ${n===i&&n!==this._schedDay?"today":""}"
               @click=${()=>{this._schedDay=n}}>${n.slice(0,3)}</div>`)}
      </div>
      ${Array.from({length:d},(n,p)=>this._periodCard(p,s,t,e,o,a))}
      <div class="copy-bar">
        <span>Copy ${this._schedDay.slice(0,3)} →</span>
        <select class="sched-select" @change=${n=>this._copySched(n)}>
          <option value="">select day…</option>
          ${z.filter(n=>n!==this._schedDay).map(n=>r`<option value=${n}>${n.slice(0,3)}</option>`)}
          <option value="__all__">All other days</option>
        </select>
      </div>
      ${c?r`
        <div class="action-bar">
          <span class="action-bar-label">● Unsaved changes</span>
          <button class="btn" @click=${()=>{this._schedEdits={}}}>Discard</button>
          <button class="btn btn-primary" @click=${()=>this._saveSched()}>Save schedule</button>
        </div>`:u}`}_profs(){let t=this._getProfilesData();if(!t.length)return r`
      <div style="padding:20px;text-align:center;color:var(--secondary-text-color)">
        <ha-icon icon="mdi:tune-vertical" style="--mdc-icon-size:48px;opacity:0.3;margin-bottom:12px;display:block"></ha-icon>
        No profile data available. Waiting for thermostat data…
      </div>`;let e=t.length>1,s=Object.keys(this._profileEdits).length>0;return r`
      <div class="section-title">Comfort Profiles</div>
      ${e?r`<div class="zone-legend">${t.map((i,o)=>r`<span class="legend-item"><span class="legend-num">${S[o]||o+1}</span> ${i.name}</span>`)}</div>`:u}
      ${j.map(i=>r`
        <div class="prof-card">
          <div class="prof-header">${i}</div>
          ${t.map((o,a)=>{let d=o.activities?.[i]||{},c=`${o.id}_${i}`,n=this._profileEdits[c],p=n?.htsp??(d.htsp?Math.round(Number(d.htsp)||$):$),h=n?.clsp??(d.clsp?Math.round(Number(d.clsp)||w):w),m=n?.fan??d.fan??"low",f=e?S[a]||a+1:o.name;return r`
              <div class="prof-line">
                <span class="prof-name ${e?"prof-name-compact":""}">${f}</span>
                <div class="sp-row">
                  <button class="btn-adj" @click=${()=>this._profAdj(o.id,i,"htsp",-1)}>−</button>
                  <span class="sp-val sp-heat">${p}°</span>
                  <button class="btn-adj" @click=${()=>this._profAdj(o.id,i,"htsp",1)}>+</button>
                </div>
                <div class="sp-row">
                  <button class="btn-adj" @click=${()=>this._profAdj(o.id,i,"clsp",-1)}>−</button>
                  <span class="sp-val sp-cool">${h}°</span>
                  <button class="btn-adj" @click=${()=>this._profAdj(o.id,i,"clsp",1)}>+</button>
                </div>
                <div class="prof-fan">
                  <span class="prof-fan-label">Fan</span>
                  <select class="sched-select" .value=${m} @change=${_=>this._profFan(o.id,i,_.target.value)}>
                    ${pt.map(_=>r`<option value=${_} ?selected=${_===m}>${_}</option>`)}
                  </select>
                </div>
              </div>`})}
        </div>`)}
      ${s?r`
        <div class="action-bar">
          <span class="action-bar-label">● Unsaved changes</span>
          <button class="btn" @click=${()=>{this._profileEdits={}}}>Discard</button>
          <button class="btn btn-primary" @click=${()=>this._saveProfs()}>Save profiles</button>
        </div>`:u}`}};customElements.get("infinitude-hvac-card")||customElements.define("infinitude-hvac-card",Ht);window.customCards=window.customCards||[];window.customCards.some(l=>l.type==="infinitude-hvac-card")||window.customCards.push({type:"infinitude-hvac-card",name:"Infinitude HVAC Card",description:"Full HVAC dashboard for Carrier/Bryant Infinity thermostats",preview:!1});
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
