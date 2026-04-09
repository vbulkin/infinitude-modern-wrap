var I=globalThis,F=I.ShadowRoot&&(I.ShadyCSS===void 0||I.ShadyCSS.nativeShadow)&&"adoptedStyleSheets"in Document.prototype&&"replace"in CSSStyleSheet.prototype,Z=Symbol(),lt=new WeakMap,P=class{constructor(t,e,s){if(this._$cssResult$=!0,s!==Z)throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");this.cssText=t,this.t=e}get styleSheet(){let t=this.o,e=this.t;if(F&&t===void 0){let s=e!==void 0&&e.length===1;s&&(t=lt.get(e)),t===void 0&&((this.o=t=new CSSStyleSheet).replaceSync(this.cssText),s&&lt.set(e,t))}return t}toString(){return this.cssText}},ct=a=>new P(typeof a=="string"?a:a+"",void 0,Z),J=(a,...t)=>{let e=a.length===1?a[0]:t.reduce((s,o,i)=>s+(r=>{if(r._$cssResult$===!0)return r.cssText;if(typeof r=="number")return r;throw Error("Value passed to 'css' function must be a 'css' function result: "+r+". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.")})(o)+a[i+1],a[0]);return new P(e,a,Z)},dt=(a,t)=>{if(F)a.adoptedStyleSheets=t.map(e=>e instanceof CSSStyleSheet?e:e.styleSheet);else for(let e of t){let s=document.createElement("style"),o=I.litNonce;o!==void 0&&s.setAttribute("nonce",o),s.textContent=e.cssText,a.appendChild(s)}},K=F?a=>a:a=>a instanceof CSSStyleSheet?(t=>{let e="";for(let s of t.cssRules)e+=s.cssText;return ct(e)})(a):a;var{is:Ct,defineProperty:zt,getOwnPropertyDescriptor:Ht,getOwnPropertyNames:Mt,getOwnPropertySymbols:Pt,getPrototypeOf:Dt}=Object,W=globalThis,pt=W.trustedTypes,Ot=pt?pt.emptyScript:"",Tt=W.reactiveElementPolyfillSupport,D=(a,t)=>a,Y={toAttribute(a,t){switch(t){case Boolean:a=a?Ot:null;break;case Object:case Array:a=a==null?a:JSON.stringify(a)}return a},fromAttribute(a,t){let e=a;switch(t){case Boolean:e=a!==null;break;case Number:e=a===null?null:Number(a);break;case Object:case Array:try{e=JSON.parse(a)}catch{e=null}}return e}},ut=(a,t)=>!Ct(a,t),ht={attribute:!0,type:String,converter:Y,reflect:!1,useDefault:!1,hasChanged:ut};Symbol.metadata??=Symbol("metadata"),W.litPropertyMetadata??=new WeakMap;var x=class extends HTMLElement{static addInitializer(t){this._$Ei(),(this.l??=[]).push(t)}static get observedAttributes(){return this.finalize(),this._$Eh&&[...this._$Eh.keys()]}static createProperty(t,e=ht){if(e.state&&(e.attribute=!1),this._$Ei(),this.prototype.hasOwnProperty(t)&&((e=Object.create(e)).wrapped=!0),this.elementProperties.set(t,e),!e.noAccessor){let s=Symbol(),o=this.getPropertyDescriptor(t,s,e);o!==void 0&&zt(this.prototype,t,o)}}static getPropertyDescriptor(t,e,s){let{get:o,set:i}=Ht(this.prototype,t)??{get(){return this[e]},set(r){this[e]=r}};return{get:o,set(r){let c=o?.call(this);i?.call(this,r),this.requestUpdate(t,c,s)},configurable:!0,enumerable:!0}}static getPropertyOptions(t){return this.elementProperties.get(t)??ht}static _$Ei(){if(this.hasOwnProperty(D("elementProperties")))return;let t=Dt(this);t.finalize(),t.l!==void 0&&(this.l=[...t.l]),this.elementProperties=new Map(t.elementProperties)}static finalize(){if(this.hasOwnProperty(D("finalized")))return;if(this.finalized=!0,this._$Ei(),this.hasOwnProperty(D("properties"))){let e=this.properties,s=[...Mt(e),...Pt(e)];for(let o of s)this.createProperty(o,e[o])}let t=this[Symbol.metadata];if(t!==null){let e=litPropertyMetadata.get(t);if(e!==void 0)for(let[s,o]of e)this.elementProperties.set(s,o)}this._$Eh=new Map;for(let[e,s]of this.elementProperties){let o=this._$Eu(e,s);o!==void 0&&this._$Eh.set(o,e)}this.elementStyles=this.finalizeStyles(this.styles)}static finalizeStyles(t){let e=[];if(Array.isArray(t)){let s=new Set(t.flat(1/0).reverse());for(let o of s)e.unshift(K(o))}else t!==void 0&&e.push(K(t));return e}static _$Eu(t,e){let s=e.attribute;return s===!1?void 0:typeof s=="string"?s:typeof t=="string"?t.toLowerCase():void 0}constructor(){super(),this._$Ep=void 0,this.isUpdatePending=!1,this.hasUpdated=!1,this._$Em=null,this._$Ev()}_$Ev(){this._$ES=new Promise(t=>this.enableUpdating=t),this._$AL=new Map,this._$E_(),this.requestUpdate(),this.constructor.l?.forEach(t=>t(this))}addController(t){(this._$EO??=new Set).add(t),this.renderRoot!==void 0&&this.isConnected&&t.hostConnected?.()}removeController(t){this._$EO?.delete(t)}_$E_(){let t=new Map,e=this.constructor.elementProperties;for(let s of e.keys())this.hasOwnProperty(s)&&(t.set(s,this[s]),delete this[s]);t.size>0&&(this._$Ep=t)}createRenderRoot(){let t=this.shadowRoot??this.attachShadow(this.constructor.shadowRootOptions);return dt(t,this.constructor.elementStyles),t}connectedCallback(){this.renderRoot??=this.createRenderRoot(),this.enableUpdating(!0),this._$EO?.forEach(t=>t.hostConnected?.())}enableUpdating(t){}disconnectedCallback(){this._$EO?.forEach(t=>t.hostDisconnected?.())}attributeChangedCallback(t,e,s){this._$AK(t,s)}_$ET(t,e){let s=this.constructor.elementProperties.get(t),o=this.constructor._$Eu(t,s);if(o!==void 0&&s.reflect===!0){let i=(s.converter?.toAttribute!==void 0?s.converter:Y).toAttribute(e,s.type);this._$Em=t,i==null?this.removeAttribute(o):this.setAttribute(o,i),this._$Em=null}}_$AK(t,e){let s=this.constructor,o=s._$Eh.get(t);if(o!==void 0&&this._$Em!==o){let i=s.getPropertyOptions(o),r=typeof i.converter=="function"?{fromAttribute:i.converter}:i.converter?.fromAttribute!==void 0?i.converter:Y;this._$Em=o;let c=r.fromAttribute(e,i.type);this[o]=c??this._$Ej?.get(o)??c,this._$Em=null}}requestUpdate(t,e,s,o=!1,i){if(t!==void 0){let r=this.constructor;if(o===!1&&(i=this[t]),s??=r.getPropertyOptions(t),!((s.hasChanged??ut)(i,e)||s.useDefault&&s.reflect&&i===this._$Ej?.get(t)&&!this.hasAttribute(r._$Eu(t,s))))return;this.C(t,e,s)}this.isUpdatePending===!1&&(this._$ES=this._$EP())}C(t,e,{useDefault:s,reflect:o,wrapped:i},r){s&&!(this._$Ej??=new Map).has(t)&&(this._$Ej.set(t,r??e??this[t]),i!==!0||r!==void 0)||(this._$AL.has(t)||(this.hasUpdated||s||(e=void 0),this._$AL.set(t,e)),o===!0&&this._$Em!==t&&(this._$Eq??=new Set).add(t))}async _$EP(){this.isUpdatePending=!0;try{await this._$ES}catch(e){Promise.reject(e)}let t=this.scheduleUpdate();return t!=null&&await t,!this.isUpdatePending}scheduleUpdate(){return this.performUpdate()}performUpdate(){if(!this.isUpdatePending)return;if(!this.hasUpdated){if(this.renderRoot??=this.createRenderRoot(),this._$Ep){for(let[o,i]of this._$Ep)this[o]=i;this._$Ep=void 0}let s=this.constructor.elementProperties;if(s.size>0)for(let[o,i]of s){let{wrapped:r}=i,c=this[o];r!==!0||this._$AL.has(o)||c===void 0||this.C(o,void 0,i,c)}}let t=!1,e=this._$AL;try{t=this.shouldUpdate(e),t?(this.willUpdate(e),this._$EO?.forEach(s=>s.hostUpdate?.()),this.update(e)):this._$EM()}catch(s){throw t=!1,this._$EM(),s}t&&this._$AE(e)}willUpdate(t){}_$AE(t){this._$EO?.forEach(e=>e.hostUpdated?.()),this.hasUpdated||(this.hasUpdated=!0,this.firstUpdated(t)),this.updated(t)}_$EM(){this._$AL=new Map,this.isUpdatePending=!1}get updateComplete(){return this.getUpdateComplete()}getUpdateComplete(){return this._$ES}shouldUpdate(t){return!0}update(t){this._$Eq&&=this._$Eq.forEach(e=>this._$ET(e,this[e])),this._$EM()}updated(t){}firstUpdated(t){}};x.elementStyles=[],x.shadowRootOptions={mode:"open"},x[D("elementProperties")]=new Map,x[D("finalized")]=new Map,Tt?.({ReactiveElement:x}),(W.reactiveElementVersions??=[]).push("2.1.2");var ot=globalThis,mt=a=>a,B=ot.trustedTypes,ft=B?B.createPolicy("lit-html",{createHTML:a=>a}):void 0,xt="$lit$",$=`lit$${Math.random().toFixed(9).slice(2)}$`,$t="?"+$,jt=`<${$t}>`,E=document,T=()=>E.createComment(""),j=a=>a===null||typeof a!="object"&&typeof a!="function",it=Array.isArray,Nt=a=>it(a)||typeof a?.[Symbol.iterator]=="function",G=`[ 	
\f\r]`,O=/<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g,_t=/-->/g,gt=/>/g,A=RegExp(`>|${G}(?:([^\\s"'>=/]+)(${G}*=${G}*(?:[^ 	
\f\r"'\`<>=]|("|')|))|$)`,"g"),vt=/'/g,bt=/"/g,wt=/^(?:script|style|textarea|title)$/i,rt=a=>(t,...e)=>({_$litType$:a,strings:t,values:e}),d=rt(1),Kt=rt(2),Yt=rt(3),k=Symbol.for("lit-noChange"),u=Symbol.for("lit-nothing"),yt=new WeakMap,S=E.createTreeWalker(E,129);function At(a,t){if(!it(a)||!a.hasOwnProperty("raw"))throw Error("invalid template strings array");return ft!==void 0?ft.createHTML(t):t}var Ut=(a,t)=>{let e=a.length-1,s=[],o,i=t===2?"<svg>":t===3?"<math>":"",r=O;for(let c=0;c<e;c++){let n=a[c],l,p,h=-1,m=0;for(;m<n.length&&(r.lastIndex=m,p=r.exec(n),p!==null);)m=r.lastIndex,r===O?p[1]==="!--"?r=_t:p[1]!==void 0?r=gt:p[2]!==void 0?(wt.test(p[2])&&(o=RegExp("</"+p[2],"g")),r=A):p[3]!==void 0&&(r=A):r===A?p[0]===">"?(r=o??O,h=-1):p[1]===void 0?h=-2:(h=r.lastIndex-p[2].length,l=p[1],r=p[3]===void 0?A:p[3]==='"'?bt:vt):r===bt||r===vt?r=A:r===_t||r===gt?r=O:(r=A,o=void 0);let f=r===A&&a[c+1].startsWith("/>")?" ":"";i+=r===O?n+jt:h>=0?(s.push(l),n.slice(0,h)+xt+n.slice(h)+$+f):n+$+(h===-2?c:f)}return[At(a,i+(a[e]||"<?>")+(t===2?"</svg>":t===3?"</math>":"")),s]},N=class a{constructor({strings:t,_$litType$:e},s){let o;this.parts=[];let i=0,r=0,c=t.length-1,n=this.parts,[l,p]=Ut(t,e);if(this.el=a.createElement(l,s),S.currentNode=this.el.content,e===2||e===3){let h=this.el.content.firstChild;h.replaceWith(...h.childNodes)}for(;(o=S.nextNode())!==null&&n.length<c;){if(o.nodeType===1){if(o.hasAttributes())for(let h of o.getAttributeNames())if(h.endsWith(xt)){let m=p[r++],f=o.getAttribute(h).split($),b=/([.?@])?(.*)/.exec(m);n.push({type:1,index:i,name:b[2],strings:f,ctor:b[1]==="."?X:b[1]==="?"?tt:b[1]==="@"?et:H}),o.removeAttribute(h)}else h.startsWith($)&&(n.push({type:6,index:i}),o.removeAttribute(h));if(wt.test(o.tagName)){let h=o.textContent.split($),m=h.length-1;if(m>0){o.textContent=B?B.emptyScript:"";for(let f=0;f<m;f++)o.append(h[f],T()),S.nextNode(),n.push({type:2,index:++i});o.append(h[m],T())}}}else if(o.nodeType===8)if(o.data===$t)n.push({type:2,index:i});else{let h=-1;for(;(h=o.data.indexOf($,h+1))!==-1;)n.push({type:7,index:i}),h+=$.length-1}i++}}static createElement(t,e){let s=E.createElement("template");return s.innerHTML=t,s}};function z(a,t,e=a,s){if(t===k)return t;let o=s!==void 0?e._$Co?.[s]:e._$Cl,i=j(t)?void 0:t._$litDirective$;return o?.constructor!==i&&(o?._$AO?.(!1),i===void 0?o=void 0:(o=new i(a),o._$AT(a,e,s)),s!==void 0?(e._$Co??=[])[s]=o:e._$Cl=o),o!==void 0&&(t=z(a,o._$AS(a,t.values),o,s)),t}var Q=class{constructor(t,e){this._$AV=[],this._$AN=void 0,this._$AD=t,this._$AM=e}get parentNode(){return this._$AM.parentNode}get _$AU(){return this._$AM._$AU}u(t){let{el:{content:e},parts:s}=this._$AD,o=(t?.creationScope??E).importNode(e,!0);S.currentNode=o;let i=S.nextNode(),r=0,c=0,n=s[0];for(;n!==void 0;){if(r===n.index){let l;n.type===2?l=new U(i,i.nextSibling,this,t):n.type===1?l=new n.ctor(i,n.name,n.strings,this,t):n.type===6&&(l=new st(i,this,t)),this._$AV.push(l),n=s[++c]}r!==n?.index&&(i=S.nextNode(),r++)}return S.currentNode=E,o}p(t){let e=0;for(let s of this._$AV)s!==void 0&&(s.strings!==void 0?(s._$AI(t,s,e),e+=s.strings.length-2):s._$AI(t[e])),e++}},U=class a{get _$AU(){return this._$AM?._$AU??this._$Cv}constructor(t,e,s,o){this.type=2,this._$AH=u,this._$AN=void 0,this._$AA=t,this._$AB=e,this._$AM=s,this.options=o,this._$Cv=o?.isConnected??!0}get parentNode(){let t=this._$AA.parentNode,e=this._$AM;return e!==void 0&&t?.nodeType===11&&(t=e.parentNode),t}get startNode(){return this._$AA}get endNode(){return this._$AB}_$AI(t,e=this){t=z(this,t,e),j(t)?t===u||t==null||t===""?(this._$AH!==u&&this._$AR(),this._$AH=u):t!==this._$AH&&t!==k&&this._(t):t._$litType$!==void 0?this.$(t):t.nodeType!==void 0?this.T(t):Nt(t)?this.k(t):this._(t)}O(t){return this._$AA.parentNode.insertBefore(t,this._$AB)}T(t){this._$AH!==t&&(this._$AR(),this._$AH=this.O(t))}_(t){this._$AH!==u&&j(this._$AH)?this._$AA.nextSibling.data=t:this.T(E.createTextNode(t)),this._$AH=t}$(t){let{values:e,_$litType$:s}=t,o=typeof s=="number"?this._$AC(t):(s.el===void 0&&(s.el=N.createElement(At(s.h,s.h[0]),this.options)),s);if(this._$AH?._$AD===o)this._$AH.p(e);else{let i=new Q(o,this),r=i.u(this.options);i.p(e),this.T(r),this._$AH=i}}_$AC(t){let e=yt.get(t.strings);return e===void 0&&yt.set(t.strings,e=new N(t)),e}k(t){it(this._$AH)||(this._$AH=[],this._$AR());let e=this._$AH,s,o=0;for(let i of t)o===e.length?e.push(s=new a(this.O(T()),this.O(T()),this,this.options)):s=e[o],s._$AI(i),o++;o<e.length&&(this._$AR(s&&s._$AB.nextSibling,o),e.length=o)}_$AR(t=this._$AA.nextSibling,e){for(this._$AP?.(!1,!0,e);t!==this._$AB;){let s=mt(t).nextSibling;mt(t).remove(),t=s}}setConnected(t){this._$AM===void 0&&(this._$Cv=t,this._$AP?.(t))}},H=class{get tagName(){return this.element.tagName}get _$AU(){return this._$AM._$AU}constructor(t,e,s,o,i){this.type=1,this._$AH=u,this._$AN=void 0,this.element=t,this.name=e,this._$AM=o,this.options=i,s.length>2||s[0]!==""||s[1]!==""?(this._$AH=Array(s.length-1).fill(new String),this.strings=s):this._$AH=u}_$AI(t,e=this,s,o){let i=this.strings,r=!1;if(i===void 0)t=z(this,t,e,0),r=!j(t)||t!==this._$AH&&t!==k,r&&(this._$AH=t);else{let c=t,n,l;for(t=i[0],n=0;n<i.length-1;n++)l=z(this,c[s+n],e,n),l===k&&(l=this._$AH[n]),r||=!j(l)||l!==this._$AH[n],l===u?t=u:t!==u&&(t+=(l??"")+i[n+1]),this._$AH[n]=l}r&&!o&&this.j(t)}j(t){t===u?this.element.removeAttribute(this.name):this.element.setAttribute(this.name,t??"")}},X=class extends H{constructor(){super(...arguments),this.type=3}j(t){this.element[this.name]=t===u?void 0:t}},tt=class extends H{constructor(){super(...arguments),this.type=4}j(t){this.element.toggleAttribute(this.name,!!t&&t!==u)}},et=class extends H{constructor(t,e,s,o,i){super(t,e,s,o,i),this.type=5}_$AI(t,e=this){if((t=z(this,t,e,0)??u)===k)return;let s=this._$AH,o=t===u&&s!==u||t.capture!==s.capture||t.once!==s.once||t.passive!==s.passive,i=t!==u&&(s===u||o);o&&this.element.removeEventListener(this.name,this,s),i&&this.element.addEventListener(this.name,this,t),this._$AH=t}handleEvent(t){typeof this._$AH=="function"?this._$AH.call(this.options?.host??this.element,t):this._$AH.handleEvent(t)}},st=class{constructor(t,e,s){this.element=t,this.type=6,this._$AN=void 0,this._$AM=e,this.options=s}get _$AU(){return this._$AM._$AU}_$AI(t){z(this,t)}};var Rt=ot.litHtmlPolyfillSupport;Rt?.(N,U),(ot.litHtmlVersions??=[]).push("3.3.2");var St=(a,t,e)=>{let s=e?.renderBefore??t,o=s._$litPart$;if(o===void 0){let i=e?.renderBefore??null;s._$litPart$=o=new U(t.insertBefore(T(),i),i,void 0,e??{})}return o._$AI(a),o};var at=globalThis,w=class extends x{constructor(){super(...arguments),this.renderOptions={host:this},this._$Do=void 0}createRenderRoot(){let t=super.createRenderRoot();return this.renderOptions.renderBefore??=t.firstChild,t}update(t){let e=this.render();this.hasUpdated||(this.renderOptions.isConnected=this.isConnected),super.update(t),this._$Do=St(e,this.renderRoot,this.renderOptions)}connectedCallback(){super.connectedCallback(),this._$Do?.setConnected(!0)}disconnectedCallback(){super.disconnectedCallback(),this._$Do?.setConnected(!1)}render(){return k}};w._$litElement$=!0,w.finalized=!0,at.litElementHydrateSupport?.({LitElement:w});var Lt=at.litElementPolyfillSupport;Lt?.({LitElement:w});(at.litElementVersions??=[]).push("4.2.2");var It="1.0.75",M=["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"],Et=[6,0,1,2,3,4,5],V=["home","away","sleep","wake"],Ft=["home","away","sleep","wake","manual"],Wt=["off","low","med","high"],kt=[{v:"60",l:"1 hour"},{v:"120",l:"2 hours"},{v:"240",l:"4 hours"},{v:"forever",l:"Indefinite"},{v:"custom",l:"Custom time\u2026"}],q=["\u2460","\u2461","\u2462","\u2463","\u2464","\u2465","\u2466","\u2467"],Bt=(()=>{let a=[];for(let t=0;t<24;t++)for(let e=0;e<60;e+=15){let s=`${String(t).padStart(2,"0")}:${String(e).padStart(2,"0")}`,o=t===0?`12:${String(e).padStart(2,"0")} AM`:t<12?`${t}:${String(e).padStart(2,"0")} AM`:t===12?`12:${String(e).padStart(2,"0")} PM`:`${t-12}:${String(e).padStart(2,"0")} PM`;a.push({v:s,l:o})}return a})(),nt=class extends w{static properties={hass:{attribute:!1},_config:{state:!0},_tab:{state:!0},_schedDay:{state:!0},_schedEdits:{state:!0},_profileEdits:{state:!0},_registryLoaded:{state:!0},_pendingTemps:{state:!0},_whHoldOpen:{state:!0},_whHoldActivity:{state:!0},_whHoldDuration:{state:!0},_whHoldCustom:{state:!0},_holdOpen:{state:!0},_holdActivity:{state:!0},_holdDuration:{state:!0},_holdCustom:{state:!0},_holdHtsp:{state:!0},_holdClsp:{state:!0},_holdFan:{state:!0}};constructor(){super(),this._config={},this._tab="zones",this._schedDay=M[Et[new Date().getDay()]],this._schedEdits={},this._profileEdits={},this._registryEntities=null,this._registryLoaded=!1,this._tempAdj={},this._pendingTemps={},this._whHoldOpen=!1,this._whHoldActivity="home",this._whHoldDuration="120",this._whHoldCustom="",this._holdOpen=null,this._holdActivity="home",this._holdDuration="120",this._holdCustom="",this._holdHtsp=68,this._holdClsp=76,this._holdFan="auto"}static getConfigElement(){return document.createElement("div")}static getStubConfig(){return{}}setConfig(t){this._config=t}getCardSize(){return 8}shouldUpdate(t){if(!t.has("hass")||!this._registryLoaded)return!0;let e=t.get("hass");return e?(this._registryEntities||[]).some(o=>this.hass.states[o.entity_id]!==e.states[o.entity_id]):!0}updated(t){t.has("hass")&&this.hass&&!this._registryLoaded&&this._loadRegistry()}async _loadRegistry(){try{let t=await this.hass.connection.sendMessagePromise({type:"config/entity_registry/list"});this._registryEntities=Array.isArray(t)?t.filter(e=>e.platform==="infinitude_direct"):[]}catch(t){console.warn("Failed to load entity registry",t),this._registryEntities=[]}this._registryLoaded=!0}_findEntities(){if(!this.hass)return{climates:[],sensors:{},selects:{},system:{}};let t=this._registryEntities||[],e=this.hass.states,s=[],o={damper:{},fan:{}},i={},r={};if(this._config.climate_entities)for(let c of this._config.climate_entities)e[c]&&s.push(c);for(let c of t){let n=c.entity_id;if(!e[n])continue;let l=n.split(".")[0],p=c.unique_id||"";l==="climate"?this._config.climate_entities||s.push(n):l==="select"?i.wholeHouse=n:l==="sensor"&&(p.includes("damper")?o.damper[n]=e[n]:p.includes("fan")?o.fan[n]=e[n]:p.includes("humidifier")?r.humidifier=n:p.includes("oat")?r.oat=n:p.includes("op_status")?r.opStatus=n:p.includes("system_info")&&(r.info=n))}return s.sort(),{climates:s,sensors:o,selects:i,system:r}}_st(t){return t?this.hass?.states[t]??null:null}_at(t,e){return this._st(t)?.attributes?.[e]}_getScheduleData(){let{system:t}=this._findEntities();if(!t.info)return{};try{return JSON.parse(this._at(t.info,"schedule")||"{}")}catch(e){return console.warn("Failed to parse schedule data",e),{}}}_getProfilesData(){let{system:t}=this._findEntities();if(!t.info)return[];try{return JSON.parse(this._at(t.info,"profiles")||"[]")}catch(e){return console.warn("Failed to parse profiles data",e),[]}}async _svc(t,e,s){try{await this.hass.callService(t,e,s)}catch(o){console.error(`${t}.${e} failed`,o)}}_setHvacMode(t,e){this._svc("climate","set_hvac_mode",{entity_id:t,hvac_mode:e})}_setPreset(t,e){this._svc("climate","set_preset_mode",{entity_id:t,preset_mode:e})}_adjustTemp(t,e,s){let o=this._st(t);if(!o)return;let i=o.attributes||{},r=this._tempAdj[t]||(this._tempAdj[t]={}),c=r.heat??i.target_temp_low??i.temperature??68,n=r.cool??i.target_temp_high??(o.state==="cool"?i.temperature:null)??76;s==="heat"?r.heat=Math.max(50,Math.min(90,Math.round(c)+e)):r.cool=Math.max(60,Math.min(99,Math.round(n)+e)),this._pendingTemps={...this._pendingTemps,[t]:{heat:r.heat,cool:r.cool}},r.committing||(clearTimeout(r.timer),r.timer=setTimeout(()=>this._commitAdj(t),800))}async _commitAdj(t){let e=this._tempAdj[t];if(!e||e.committing)return;e.committing=!0;let s=this._st(t),o=s?.attributes||{},i=e.heat,r=e.cool,c=i??Math.round(o.target_temp_low??o.temperature??68),n=r??Math.round(o.target_temp_high??(s?.state==="cool"?o.temperature:null)??76),l=s?.state||"off",p={entity_id:t};l==="heat_cool"?(p.target_temp_low=c,p.target_temp_high=n):l==="heat"?p.temperature=c:l==="cool"?p.temperature=n:(p.target_temp_low=c,p.target_temp_high=n);try{await this.hass.callService("climate","set_temperature",p)}catch(h){console.error("set_temperature failed",h)}if(e.committing=!1,e.heat!==i||e.cool!==r){e.timer=setTimeout(()=>this._commitAdj(t),400);return}e.heat=null,e.cool=null,e.timer=null,e.graceUntil=Date.now()+3e4,setTimeout(()=>{if(!this._tempAdj[t]?.heat&&!this._tempAdj[t]?.cool){let{[t]:h,...m}=this._pendingTemps;this._pendingTemps=m}},2e3)}_hasPending(t){let e=this._tempAdj[t];return e&&(e.heat!=null||e.cool!=null||e.committing)}_cancelHold(t){let e=(this._registryEntities||[]).find(o=>o.entity_id===t);if(!e)return;let s=(e.unique_id||"").replace(/^infinitude_/,"");s&&this._svc("infinitude_direct","cancel_hold",{zone_id:s})}_setZoneHold(t){let e=(this._registryEntities||[]).find(i=>i.entity_id===t);if(!e)return;let s=(e.unique_id||"").replace(/^infinitude_/,"");if(!s)return;let o=this._resolveUntil(this._holdDuration,this._holdCustom);o!==null&&(this._holdActivity==="manual"&&this._svc("infinitude_direct","set_profile",{zone_id:s,activity:"manual",htsp:this._holdHtsp,clsp:this._holdClsp,fan:this._holdFan}),this._svc("infinitude_direct","set_hold",{zone_id:s,activity:this._holdActivity,...o!==void 0&&{until:o}}),this._holdOpen=null)}_initHoldManual(t){let e=this._zoneId(t),s=this._getProfilesData().find(o=>o.id===e)?.activities?.manual||{};this._holdHtsp=s.htsp?Math.round(Number(s.htsp)||68):68,this._holdClsp=s.clsp?Math.round(Number(s.clsp)||76):76,this._holdFan=s.fan||"auto"}_setWholeHouseHold(){let t=this._resolveUntil(this._whHoldDuration,this._whHoldCustom);t!==null&&(this._svc("infinitude_direct","set_whole_house_hold",{activity:this._whHoldActivity,...t!==void 0&&{until:t}}),this._whHoldOpen=!1)}_cancelWholeHouseHold(){this._svc("infinitude_direct","cancel_whole_house_hold",{})}_resolveUntil(t,e){if(t==="forever")return"forever";if(t==="custom")return e||null;let s=new Date;s.setMinutes(s.getMinutes()+parseInt(t));let o=Math.round(s.getMinutes()/15)*15;return s.setMinutes(o,0,0),o===60&&(s.setMinutes(0),s.setHours(s.getHours()+1)),`${String(s.getHours()).padStart(2,"0")}:${String(s.getMinutes()).padStart(2,"0")}`}_otmrRelative(t){if(!t)return"";let[e,s]=t.split(":").map(Number),o=new Date;return o.setHours(e,s,0,0),"until "+o.toLocaleTimeString([],{hour:"numeric",minute:"2-digit"})}_zoneId(t){let e=(this._registryEntities||[]).find(s=>s.entity_id===t);return e?(e.unique_id||"").replace(/^infinitude_/,""):""}static styles=J`
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
    .zone-hold-picker {
      padding: 8px 14px; border-top: 1px solid var(--divider-color);
      display: flex; flex-direction: column; gap: 8px; font-size: 11px;
    }
    .hold-picker-row { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
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
    .zone-legend { display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 10px; font-size: 12px; color: var(--secondary-text-color); }
    .legend-item { display: flex; align-items: center; gap: 4px; }
    .legend-num { font-weight: 700; color: var(--primary-text-color); font-size: 14px; }
    .sched-name-compact { width: 28px; min-width: 28px; font-size: 14px; text-align: center; }
    .prof-name-compact { width: 28px; min-width: 28px; font-size: 14px; text-align: center; }
  `;render(){if(!this.hass)return u;if(!this._registryLoaded)return d`<ha-card>
        <div style="padding:24px;text-align:center;color:var(--secondary-text-color)">Loading…</div>
      </ha-card>`;let t=this._findEntities();return!t.climates.length&&!this._config.show_empty?d`<ha-card>
        <div style="padding:24px;text-align:center;color:var(--secondary-text-color)">
          <ha-icon icon="mdi:thermostat" style="--mdc-icon-size:48px;opacity:0.3;margin-bottom:12px;display:block"></ha-icon>
          <div style="font-size:14px;font-weight:500">No Infinitude entities found</div>
          <div style="font-size:12px;margin-top:4px">Waiting for thermostat connection…</div>
        </div>
      </ha-card>`:d`
      <ha-card>
        <div class="card-header">${this._hdr(t)}</div>
        <div class="card-tabs">${this._tabs()}</div>
        <div class="card-content">
          ${this._tab==="zones"?this._zones(t):u}
          ${this._tab==="schedule"?this._sched(t):u}
          ${this._tab==="profiles"?this._profs():u}
        </div>
      </ha-card>`}_hdr(t){let{system:e,selects:s,climates:o}=t,i=o.length&&this._st(o[0])?.state||"off",r=i==="heat"?"heat":i==="cool"?"cool":i==="heat_cool"||i==="auto"?"auto":"",c=i==="heat_cool"?"Auto":i.charAt(0).toUpperCase()+i.slice(1),n=this._st(e.oat),l="\u2013";if(n?.state&&n.state!=="unavailable")l=`${Math.round(Number(n.state))}\xB0`;else if(o.length){let _=this._at(o[0],"outdoor_temperature");_!=null&&(l=`${Math.round(Number(_))}\xB0`)}let p=this._st(e.opStatus),h=p?.state&&p.state!=="unavailable"?p.state:"",m=this._st(e.humidifier)?.state==="on",f=this._st(s.wholeHouse),b=f&&f.state!=="off",C=o.length?this._at(o[0],"whole_house_hold_until"):null,y=o.length?this._at(o[0],"current_humidity"):null;return d`
      <div class="header-left">
        <span class="header-title">HVAC</span>
        <span class="header-mode ${r}">${c}</span>
        <span style="font-size:10px;color:var(--secondary-text-color);opacity:0.5">v${It}</span>
      </div>
      <div class="header-stats">
        <span>Outside <span class="stat-val">${l}</span></span>
        ${y!=null?d`<span>Indoor RH <span class="stat-val">${y}%</span></span>`:u}
        ${m?d`<span style="color:var(--label-badge-blue,#38bdf8)">💧 Humidifier On</span>`:u}
        ${h?d`<span>${h}</span>`:u}
      </div>
      ${b?d`
        <div class="wh-hold" @click=${()=>this._cancelWholeHouseHold()}>
          <ha-icon icon="mdi:home-lock" style="--mdc-icon-size:16px"></ha-icon>
          <span>Whole house: <strong>${f.state}</strong>${C?d` · <span style="opacity:0.85">${this._otmrRelative(C)}</span>`:u}</span>
          <span style="margin-left:auto;opacity:0.7">Tap to cancel</span>
        </div>`:d`
        ${this._whHoldOpen?d`
          <div class="wh-set">
            <span class="wh-set-label">WH Hold</span>
            <div class="wh-pills">
              ${V.map(_=>d`
                <div class="wh-pill ${this._whHoldActivity===_?"active":""}"
                     @click=${()=>{this._whHoldActivity=_}}>${_}</div>`)}
            </div>
            <select class="hold-dur-select" @change=${_=>{this._whHoldDuration=_.target.value}}>
              ${kt.map(_=>d`<option value=${_.v} ?selected=${_.v===this._whHoldDuration}>${_.l}</option>`)}
            </select>
            ${this._whHoldDuration==="custom"?d`
              <input type="time" class="hold-time-input" step="900" .value=${this._whHoldCustom}
                     @change=${_=>{this._whHoldCustom=_.target.value}}>`:u}
            <button class="btn btn-primary" style="font-size:11px;padding:4px 12px" @click=${()=>this._setWholeHouseHold()}>Apply</button>
            <button class="btn" style="font-size:11px;padding:4px 10px" @click=${()=>{this._whHoldOpen=!1}}>Cancel</button>
          </div>`:d`
          <div style="width:100%;margin-top:4px">
            <button class="btn" style="font-size:11px;padding:4px 12px" @click=${()=>{this._whHoldOpen=!0}}>
              <ha-icon icon="mdi:home-lock" style="--mdc-icon-size:14px;vertical-align:middle;margin-right:4px"></ha-icon>Set WH hold
            </button>
          </div>`}
      `}`}_tabs(){return d`${["zones","schedule","profiles"].map(t=>d`
      <div class="tab ${this._tab===t?"active":""}"
           @click=${()=>{this._tab=t}}>${t.charAt(0).toUpperCase()+t.slice(1)}</div>`)}`}_zones(t){let{climates:e}=t;if(!e.length)return d`<div style="padding:20px;text-align:center;color:var(--secondary-text-color)">No zone entities found</div>`;let s=this._st(e[0])?.state||"off",o=["off","heat","cool","heat_cool"],i={off:"Off",heat:"Heat",cool:"Cool",heat_cool:"Auto"};return d`
      <div class="mode-row">
        <span class="mode-label">Mode</span>
        <div class="mode-pills">
          ${o.map(r=>d`<div class="mode-pill ${r===s?"active":""} ${r==="heat"?"heat":r==="cool"?"cool":r==="heat_cool"?"auto":""}"
              @click=${()=>this._setHvacMode(e[0],r)}>${i[r]}</div>`)}
        </div>
      </div>
      <div class="zone-grid">${e.map(r=>this._zoneCard(r))}</div>`}_zoneCard(t){let e=this._st(t);if(!e)return u;let s=e.attributes||{},o=(s.friendly_name||t).replace(/^Infinitude\s+/i,"").replace(/^infinitude_direct\s+/i,""),i=s.current_temperature!=null?Math.round(s.current_temperature):"\u2013",r=s.current_humidity,c=e.state||"off",n=s.hvac_action||"idle",l=s.preset_mode||"\u2013",p=n==="heating"?"heating":n==="cooling"?"cooling":n==="drying"?"drying":"",h=n==="idle"?"Idle":n.charAt(0).toUpperCase()+n.slice(1),m=c==="heat_cool",f=!!s.hold_active,b=s.hold_activity||l,C=s.hold_until,y=this._holdOpen===t,_=this._pendingTemps[t],R=this._hasPending(t),L=_?.heat??s.target_temp_low??s.temperature??null,g=_?.cool??s.target_temp_high??(c==="cool"?s.temperature:null)??null;return d`
      <div class="zone-card ${p}">
        <div class="zone-top">
          <span class="zone-name">${o}</span>
          <span class="zone-badge ${p}">${h}</span>
        </div>
        <div class="zone-body">
          <div>
            <span class="temp-hero">${i}</span><span class="temp-unit">°F</span>
            ${r!=null?d`<div style="font-size:11px;color:var(--secondary-text-color);margin-top:2px">${r}% RH</div>`:u}
          </div>
          <div class="zone-sp">
            ${L!=null?d`
              <div class="sp-row">
                <button class="btn-adj" @click=${()=>this._adjustTemp(t,-1,"heat")}>−</button>
                <span class="sp-val sp-heat ${R?"sp-pending":""}">${Math.round(L)}°</span>
                <button class="btn-adj" @click=${()=>this._adjustTemp(t,1,"heat")}>+</button>
              </div>`:u}
            ${m&&g!=null?d`
              <div class="sp-row">
                <button class="btn-adj" @click=${()=>this._adjustTemp(t,-1,"cool")}>−</button>
                <span class="sp-val sp-cool ${R?"sp-pending":""}">${Math.round(g)}°</span>
                <button class="btn-adj" @click=${()=>this._adjustTemp(t,1,"cool")}>+</button>
              </div>`:u}
          </div>
        </div>
        <div class="zone-meta">
          <span class="meta-item">Activity <span class="meta-val">${l}</span></span>
          ${s.fan_mode?d`<span class="meta-item">Fan <span class="meta-val">${s.fan_mode}</span></span>`:u}
          ${s.damper_position!=null?d`<span class="meta-item">Damper <span class="meta-val">${s.damper_position}%</span></span>`:u}
        </div>
        <div class="zone-preset-row">
          ${V.map(v=>d`
            <div class="preset-btn ${l===v?"active":""}"
                 @click=${()=>this._setPreset(t,v)}>${v}</div>`)}
        </div>
        ${f?d`
          <div class="zone-hold">
            <span class="hold-label">Hold: ${b}${C?` \xB7 ${this._otmrRelative(C)}`:""}</span>
            <button class="btn" style="font-size:11px;padding:3px 10px;color:var(--error-color,#f87171)" @click=${()=>this._cancelHold(t)}>Cancel</button>
          </div>`:u}
        ${y?d`
          <div class="zone-hold-picker">
            <div class="hold-picker-row">
              <div class="wh-pills">
                ${Ft.map(v=>d`
                  <div class="wh-pill ${this._holdActivity===v?"active":""}"
                       @click=${()=>{this._holdActivity=v,v==="manual"&&this._initHoldManual(t)}}>${v}</div>`)}
              </div>
            </div>
            ${this._holdActivity==="manual"?d`
              <div class="hold-picker-row" style="gap:10px;flex-wrap:wrap">
                <div class="sp-row">
                  <button class="btn-adj" @click=${()=>{this._holdHtsp=Math.max(50,this._holdHtsp-1)}}>−</button>
                  <span class="sp-val sp-heat">${this._holdHtsp}°</span>
                  <button class="btn-adj" @click=${()=>{this._holdHtsp=Math.min(90,this._holdHtsp+1)}}>+</button>
                </div>
                <div class="sp-row">
                  <button class="btn-adj" @click=${()=>{this._holdClsp=Math.max(60,this._holdClsp-1)}}>−</button>
                  <span class="sp-val sp-cool">${this._holdClsp}°</span>
                  <button class="btn-adj" @click=${()=>{this._holdClsp=Math.min(99,this._holdClsp+1)}}>+</button>
                </div>
                <div style="display:flex;align-items:center;gap:4px">
                  <span style="font-size:10px;color:var(--secondary-text-color)">Fan</span>
                  <select class="hold-dur-select" style="width:auto" .value=${this._holdFan} @change=${v=>{this._holdFan=v.target.value}}>
                    <option value="auto">Auto</option>
                    <option value="low">Low</option>
                    <option value="med">Med</option>
                    <option value="high">High</option>
                  </select>
                </div>
              </div>`:u}
            <div class="hold-picker-row">
              <select class="hold-dur-select" @change=${v=>{this._holdDuration=v.target.value}}>
                ${kt.map(v=>d`<option value=${v.v} ?selected=${v.v===this._holdDuration}>${v.l}</option>`)}
              </select>
              ${this._holdDuration==="custom"?d`
                <input type="time" class="hold-time-input" step="900" .value=${this._holdCustom}
                       @change=${v=>{this._holdCustom=v.target.value}}>`:u}
            </div>
            <div class="hold-picker-row">
              <button class="btn btn-primary" style="font-size:11px;padding:4px 12px" @click=${()=>this._setZoneHold(t)}>Apply</button>
              <button class="btn" style="font-size:11px;padding:4px 10px" @click=${()=>{this._holdOpen=null}}>Cancel</button>
            </div>
          </div>`:f?u:d`
          <div class="zone-actions">
            <button class="btn" style="font-size:11px;padding:4px 12px" @click=${()=>{this._holdActivity=l!=="\u2013"?l:"home",this._holdDuration="120",this._holdCustom="",this._holdActivity==="manual"&&this._initHoldManual(t),this._holdOpen=t}}>Set hold</button>
          </div>`}
      </div>`}_sched(){let t=this._getScheduleData(),e=this._getProfilesData(),s=Object.keys(t);if(!s.length)return d`
      <div style="padding:20px;text-align:center;color:var(--secondary-text-color)">
        <ha-icon icon="mdi:calendar-clock" style="--mdc-icon-size:48px;opacity:0.3;margin-bottom:12px;display:block"></ha-icon>
        No schedule data available. Waiting for thermostat data…
      </div>`;let o=M[Et[new Date().getDay()]],i={},r={};for(let l=0;l<e.length;l++)i[e[l].id]=e[l].name,r[e[l].id]=l;let c=0;for(let l of s)c=Math.max(c,(t[l]?.[this._schedDay]||[]).length);c||(c=5);let n=Object.keys(this._schedEdits).length>0;return d`
      <div class="section-title">Schedule</div>
      ${s.length>1?d`<div class="zone-legend">${s.map((l,p)=>d`<span class="legend-item"><span class="legend-num">${q[p]||p+1}</span> ${i[l]||`Zone ${l}`}</span>`)}</div>`:u}
      <div class="sched-day-tabs">
        ${M.map(l=>d`
          <div class="day-tab ${l===this._schedDay?"active":""} ${l===o&&l!==this._schedDay?"today":""}"
               @click=${()=>{this._schedDay=l}}>${l.slice(0,3)}</div>`)}
      </div>
      ${Array.from({length:c},(l,p)=>this._periodCard(p,s,t,e,i,r))}
      <div class="copy-bar">
        <span>Copy ${this._schedDay.slice(0,3)} →</span>
        <select class="sched-select" @change=${l=>this._copySched(l)}>
          <option value="">select day…</option>
          ${M.filter(l=>l!==this._schedDay).map(l=>d`<option value=${l}>${l.slice(0,3)}</option>`)}
          <option value="__all__">All other days</option>
        </select>
      </div>
      ${n?d`
        <div class="action-bar">
          <span class="action-bar-label">● Unsaved changes</span>
          <button class="btn" @click=${()=>{this._schedEdits={}}}>Discard</button>
          <button class="btn btn-primary" @click=${()=>this._saveSched()}>Save schedule</button>
        </div>`:u}`}_periodCard(t,e,s,o,i,r){let c=e.length>1;return d`
      <div class="period-card">
        <div class="period-header">Period ${t+1}</div>
        ${e.map(n=>{let l=(s[n]?.[this._schedDay]||[])[t];if(!l)return u;let p=`${n}_${this._schedDay}_${t}`,h=this._schedEdits[p],m=h?.act??l.activity,f=h?.time??l.time,b=h?.enabled??l.enabled,y=o.find(g=>g.id===n)?.activities?.[m],_=y?.htsp?Math.round(Number(y.htsp)||0):"\u2013",R=y?.clsp?Math.round(Number(y.clsp)||0):"\u2013",L=c?q[r[n]]??n:i[n]||`Zone ${n}`;return d`
            <div class="sched-line ${b?"":"disabled"}">
              <span class="sched-name ${c?"sched-name-compact":""}">${L}</span>
              <select class="sched-select" @change=${g=>this._schedEdit(n,t,"act",g.target.value)}>
                ${V.map(g=>d`<option value=${g} ?selected=${g===m}>${g}</option>`)}
              </select>
              <select class="sched-select" @change=${g=>this._schedEdit(n,t,"time",g.target.value)}>
                ${Bt.map(g=>d`<option value=${g.v} ?selected=${g.v===f}>${g.l}</option>`)}
              </select>
              <label class="sched-toggle">
                <input type="checkbox" ?checked=${b}
                       @change=${g=>this._schedEdit(n,t,"enabled",g.target.checked)}>
                <span>on</span>
              </label>
              <div class="sched-temps">
                <span class="sp-heat">${_}°</span>
                <span class="sp-cool">${R}°</span>
              </div>
            </div>`})}
      </div>`}_schedEdit(t,e,s,o){let i=`${t}_${this._schedDay}_${e}`,r=this._schedEdits[i]||{},c=(this._getScheduleData()[t]?.[this._schedDay]||[])[e]||{};this._schedEdits={...this._schedEdits,[i]:{act:s==="act"?o:r.act??c.activity,time:s==="time"?o:r.time??c.time,enabled:s==="enabled"?o:r.enabled??c.enabled}}}_copySched(t){let e=t.target.value;if(!e)return;t.target.value="";let s=this._getScheduleData(),o=e==="__all__"?M.filter(r=>r!==this._schedDay):[e],i={...this._schedEdits};for(let r of Object.keys(s)){let c=s[r]?.[this._schedDay]||[];for(let n of o)c.forEach((l,p)=>{let h=this._schedEdits[`${r}_${this._schedDay}_${p}`];i[`${r}_${n}_${p}`]={act:h?.act??l.activity,time:h?.time??l.time,enabled:h?.enabled??l.enabled}})}this._schedEdits=i}async _saveSched(){let t=this._getScheduleData();for(let e of Object.keys(t)){let s=M.map(o=>({id:o,period:(t[e]?.[o]||[]).map((i,r)=>{let c=this._schedEdits[`${e}_${o}_${r}`];return{id:i.id||String(r+1),activity:c?.act??i.activity,time:c?.time??i.time,enabled:c?.enabled??i.enabled?"on":"off"}})}));await this._svc("infinitude_direct","save_schedule",{zone_id:e,schedule:JSON.stringify(s)})}this._schedEdits={}}_profs(){let t=this._getProfilesData();if(!t.length)return d`
      <div style="padding:20px;text-align:center;color:var(--secondary-text-color)">
        <ha-icon icon="mdi:tune-vertical" style="--mdc-icon-size:48px;opacity:0.3;margin-bottom:12px;display:block"></ha-icon>
        No profile data available. Waiting for thermostat data…
      </div>`;let e=t.length>1,s=Object.keys(this._profileEdits).length>0;return d`
      <div class="section-title">Comfort Profiles</div>
      ${e?d`<div class="zone-legend">${t.map((o,i)=>d`<span class="legend-item"><span class="legend-num">${q[i]||i+1}</span> ${o.name}</span>`)}</div>`:u}
      ${V.map(o=>d`
        <div class="prof-card">
          <div class="prof-header">${o}</div>
          ${t.map((i,r)=>{let c=i.activities?.[o]||{},n=`${i.id}_${o}`,l=this._profileEdits[n],p=l?.htsp??(c.htsp?Math.round(Number(c.htsp)||68):68),h=l?.clsp??(c.clsp?Math.round(Number(c.clsp)||76):76),m=l?.fan??c.fan??"low",f=e?q[r]||r+1:i.name;return d`
              <div class="prof-line">
                <span class="prof-name ${e?"prof-name-compact":""}">${f}</span>
                <div class="sp-row">
                  <button class="btn-adj" @click=${()=>this._profAdj(i.id,o,"htsp",-1)}>−</button>
                  <span class="sp-val sp-heat">${p}°</span>
                  <button class="btn-adj" @click=${()=>this._profAdj(i.id,o,"htsp",1)}>+</button>
                </div>
                <div class="sp-row">
                  <button class="btn-adj" @click=${()=>this._profAdj(i.id,o,"clsp",-1)}>−</button>
                  <span class="sp-val sp-cool">${h}°</span>
                  <button class="btn-adj" @click=${()=>this._profAdj(i.id,o,"clsp",1)}>+</button>
                </div>
                <div class="prof-fan">
                  <span class="prof-fan-label">Fan</span>
                  <select class="sched-select" @change=${b=>this._profFan(i.id,o,b.target.value)}>
                    ${Wt.map(b=>d`<option value=${b} ?selected=${b===m}>${b}</option>`)}
                  </select>
                </div>
              </div>`})}
        </div>`)}
      ${s?d`
        <div class="action-bar">
          <span class="action-bar-label">● Unsaved changes</span>
          <button class="btn" @click=${()=>{this._profileEdits={}}}>Discard</button>
          <button class="btn btn-primary" @click=${()=>this._saveProfs()}>Save profiles</button>
        </div>`:u}`}_profAdj(t,e,s,o){let i=`${t}_${e}`,r=this._getProfilesData().find(f=>f.id===t)?.activities?.[e]||{},c=this._profileEdits[i]||{},n=c.htsp??(r.htsp?Math.round(Number(r.htsp)||68):68),l=c.clsp??(r.clsp?Math.round(Number(r.clsp)||76):76),p=s==="htsp"?50:60,h=s==="htsp"?90:99,m=s==="htsp"?n:l;this._profileEdits={...this._profileEdits,[i]:{zone_id:t,activity:e,htsp:s==="htsp"?Math.max(p,Math.min(h,m+o)):n,clsp:s==="clsp"?Math.max(p,Math.min(h,m+o)):l,fan:c.fan??r.fan??"low"}}}_profFan(t,e,s){let o=`${t}_${e}`,i=this._getProfilesData().find(c=>c.id===t)?.activities?.[e]||{},r=this._profileEdits[o]||{};this._profileEdits={...this._profileEdits,[o]:{zone_id:t,activity:e,htsp:r.htsp??(i.htsp?Math.round(Number(i.htsp)||68):68),clsp:r.clsp??(i.clsp?Math.round(Number(i.clsp)||76):76),fan:s}}}async _saveProfs(){for(let t of Object.values(this._profileEdits)){let e={zone_id:t.zone_id,activity:t.activity,htsp:t.htsp,clsp:t.clsp};t.fan&&(e.fan=t.fan),await this._svc("infinitude_direct","set_profile",e)}this._profileEdits={}}};customElements.get("infinitude-hvac-card")||customElements.define("infinitude-hvac-card",nt);window.customCards=window.customCards||[];window.customCards.some(a=>a.type==="infinitude-hvac-card")||window.customCards.push({type:"infinitude-hvac-card",name:"Infinitude HVAC Card",description:"Full HVAC dashboard for Carrier/Bryant Infinity thermostats",preview:!1});
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
