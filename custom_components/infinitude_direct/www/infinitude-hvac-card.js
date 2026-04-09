var I=globalThis,F=I.ShadowRoot&&(I.ShadyCSS===void 0||I.ShadyCSS.nativeShadow)&&"adoptedStyleSheets"in Document.prototype&&"replace"in CSSStyleSheet.prototype,Z=Symbol(),lt=new WeakMap,D=class{constructor(t,e,s){if(this._$cssResult$=!0,s!==Z)throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");this.cssText=t,this.t=e}get styleSheet(){let t=this.o,e=this.t;if(F&&t===void 0){let s=e!==void 0&&e.length===1;s&&(t=lt.get(e)),t===void 0&&((this.o=t=new CSSStyleSheet).replaceSync(this.cssText),s&&lt.set(e,t))}return t}toString(){return this.cssText}},ct=a=>new D(typeof a=="string"?a:a+"",void 0,Z),J=(a,...t)=>{let e=a.length===1?a[0]:t.reduce((s,i,o)=>s+(r=>{if(r._$cssResult$===!0)return r.cssText;if(typeof r=="number")return r;throw Error("Value passed to 'css' function must be a 'css' function result: "+r+". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.")})(i)+a[o+1],a[0]);return new D(e,a,Z)},dt=(a,t)=>{if(F)a.adoptedStyleSheets=t.map(e=>e instanceof CSSStyleSheet?e:e.styleSheet);else for(let e of t){let s=document.createElement("style"),i=I.litNonce;i!==void 0&&s.setAttribute("nonce",i),s.textContent=e.cssText,a.appendChild(s)}},K=F?a=>a:a=>a instanceof CSSStyleSheet?(t=>{let e="";for(let s of t.cssRules)e+=s.cssText;return ct(e)})(a):a;var{is:Ct,defineProperty:zt,getOwnPropertyDescriptor:Ht,getOwnPropertyNames:Mt,getOwnPropertySymbols:Pt,getPrototypeOf:Dt}=Object,W=globalThis,pt=W.trustedTypes,Ot=pt?pt.emptyScript:"",Tt=W.reactiveElementPolyfillSupport,O=(a,t)=>a,Y={toAttribute(a,t){switch(t){case Boolean:a=a?Ot:null;break;case Object:case Array:a=a==null?a:JSON.stringify(a)}return a},fromAttribute(a,t){let e=a;switch(t){case Boolean:e=a!==null;break;case Number:e=a===null?null:Number(a);break;case Object:case Array:try{e=JSON.parse(a)}catch{e=null}}return e}},ut=(a,t)=>!Ct(a,t),ht={attribute:!0,type:String,converter:Y,reflect:!1,useDefault:!1,hasChanged:ut};Symbol.metadata??=Symbol("metadata"),W.litPropertyMetadata??=new WeakMap;var x=class extends HTMLElement{static addInitializer(t){this._$Ei(),(this.l??=[]).push(t)}static get observedAttributes(){return this.finalize(),this._$Eh&&[...this._$Eh.keys()]}static createProperty(t,e=ht){if(e.state&&(e.attribute=!1),this._$Ei(),this.prototype.hasOwnProperty(t)&&((e=Object.create(e)).wrapped=!0),this.elementProperties.set(t,e),!e.noAccessor){let s=Symbol(),i=this.getPropertyDescriptor(t,s,e);i!==void 0&&zt(this.prototype,t,i)}}static getPropertyDescriptor(t,e,s){let{get:i,set:o}=Ht(this.prototype,t)??{get(){return this[e]},set(r){this[e]=r}};return{get:i,set(r){let c=i?.call(this);o?.call(this,r),this.requestUpdate(t,c,s)},configurable:!0,enumerable:!0}}static getPropertyOptions(t){return this.elementProperties.get(t)??ht}static _$Ei(){if(this.hasOwnProperty(O("elementProperties")))return;let t=Dt(this);t.finalize(),t.l!==void 0&&(this.l=[...t.l]),this.elementProperties=new Map(t.elementProperties)}static finalize(){if(this.hasOwnProperty(O("finalized")))return;if(this.finalized=!0,this._$Ei(),this.hasOwnProperty(O("properties"))){let e=this.properties,s=[...Mt(e),...Pt(e)];for(let i of s)this.createProperty(i,e[i])}let t=this[Symbol.metadata];if(t!==null){let e=litPropertyMetadata.get(t);if(e!==void 0)for(let[s,i]of e)this.elementProperties.set(s,i)}this._$Eh=new Map;for(let[e,s]of this.elementProperties){let i=this._$Eu(e,s);i!==void 0&&this._$Eh.set(i,e)}this.elementStyles=this.finalizeStyles(this.styles)}static finalizeStyles(t){let e=[];if(Array.isArray(t)){let s=new Set(t.flat(1/0).reverse());for(let i of s)e.unshift(K(i))}else t!==void 0&&e.push(K(t));return e}static _$Eu(t,e){let s=e.attribute;return s===!1?void 0:typeof s=="string"?s:typeof t=="string"?t.toLowerCase():void 0}constructor(){super(),this._$Ep=void 0,this.isUpdatePending=!1,this.hasUpdated=!1,this._$Em=null,this._$Ev()}_$Ev(){this._$ES=new Promise(t=>this.enableUpdating=t),this._$AL=new Map,this._$E_(),this.requestUpdate(),this.constructor.l?.forEach(t=>t(this))}addController(t){(this._$EO??=new Set).add(t),this.renderRoot!==void 0&&this.isConnected&&t.hostConnected?.()}removeController(t){this._$EO?.delete(t)}_$E_(){let t=new Map,e=this.constructor.elementProperties;for(let s of e.keys())this.hasOwnProperty(s)&&(t.set(s,this[s]),delete this[s]);t.size>0&&(this._$Ep=t)}createRenderRoot(){let t=this.shadowRoot??this.attachShadow(this.constructor.shadowRootOptions);return dt(t,this.constructor.elementStyles),t}connectedCallback(){this.renderRoot??=this.createRenderRoot(),this.enableUpdating(!0),this._$EO?.forEach(t=>t.hostConnected?.())}enableUpdating(t){}disconnectedCallback(){this._$EO?.forEach(t=>t.hostDisconnected?.())}attributeChangedCallback(t,e,s){this._$AK(t,s)}_$ET(t,e){let s=this.constructor.elementProperties.get(t),i=this.constructor._$Eu(t,s);if(i!==void 0&&s.reflect===!0){let o=(s.converter?.toAttribute!==void 0?s.converter:Y).toAttribute(e,s.type);this._$Em=t,o==null?this.removeAttribute(i):this.setAttribute(i,o),this._$Em=null}}_$AK(t,e){let s=this.constructor,i=s._$Eh.get(t);if(i!==void 0&&this._$Em!==i){let o=s.getPropertyOptions(i),r=typeof o.converter=="function"?{fromAttribute:o.converter}:o.converter?.fromAttribute!==void 0?o.converter:Y;this._$Em=i;let c=r.fromAttribute(e,o.type);this[i]=c??this._$Ej?.get(i)??c,this._$Em=null}}requestUpdate(t,e,s,i=!1,o){if(t!==void 0){let r=this.constructor;if(i===!1&&(o=this[t]),s??=r.getPropertyOptions(t),!((s.hasChanged??ut)(o,e)||s.useDefault&&s.reflect&&o===this._$Ej?.get(t)&&!this.hasAttribute(r._$Eu(t,s))))return;this.C(t,e,s)}this.isUpdatePending===!1&&(this._$ES=this._$EP())}C(t,e,{useDefault:s,reflect:i,wrapped:o},r){s&&!(this._$Ej??=new Map).has(t)&&(this._$Ej.set(t,r??e??this[t]),o!==!0||r!==void 0)||(this._$AL.has(t)||(this.hasUpdated||s||(e=void 0),this._$AL.set(t,e)),i===!0&&this._$Em!==t&&(this._$Eq??=new Set).add(t))}async _$EP(){this.isUpdatePending=!0;try{await this._$ES}catch(e){Promise.reject(e)}let t=this.scheduleUpdate();return t!=null&&await t,!this.isUpdatePending}scheduleUpdate(){return this.performUpdate()}performUpdate(){if(!this.isUpdatePending)return;if(!this.hasUpdated){if(this.renderRoot??=this.createRenderRoot(),this._$Ep){for(let[i,o]of this._$Ep)this[i]=o;this._$Ep=void 0}let s=this.constructor.elementProperties;if(s.size>0)for(let[i,o]of s){let{wrapped:r}=o,c=this[i];r!==!0||this._$AL.has(i)||c===void 0||this.C(i,void 0,o,c)}}let t=!1,e=this._$AL;try{t=this.shouldUpdate(e),t?(this.willUpdate(e),this._$EO?.forEach(s=>s.hostUpdate?.()),this.update(e)):this._$EM()}catch(s){throw t=!1,this._$EM(),s}t&&this._$AE(e)}willUpdate(t){}_$AE(t){this._$EO?.forEach(e=>e.hostUpdated?.()),this.hasUpdated||(this.hasUpdated=!0,this.firstUpdated(t)),this.updated(t)}_$EM(){this._$AL=new Map,this.isUpdatePending=!1}get updateComplete(){return this.getUpdateComplete()}getUpdateComplete(){return this._$ES}shouldUpdate(t){return!0}update(t){this._$Eq&&=this._$Eq.forEach(e=>this._$ET(e,this[e])),this._$EM()}updated(t){}firstUpdated(t){}};x.elementStyles=[],x.shadowRootOptions={mode:"open"},x[O("elementProperties")]=new Map,x[O("finalized")]=new Map,Tt?.({ReactiveElement:x}),(W.reactiveElementVersions??=[]).push("2.1.2");var it=globalThis,mt=a=>a,B=it.trustedTypes,ft=B?B.createPolicy("lit-html",{createHTML:a=>a}):void 0,xt="$lit$",$=`lit$${Math.random().toFixed(9).slice(2)}$`,$t="?"+$,jt=`<${$t}>`,E=document,j=()=>E.createComment(""),N=a=>a===null||typeof a!="object"&&typeof a!="function",ot=Array.isArray,Nt=a=>ot(a)||typeof a?.[Symbol.iterator]=="function",G=`[ 	
\f\r]`,T=/<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g,_t=/-->/g,vt=/>/g,A=RegExp(`>|${G}(?:([^\\s"'>=/]+)(${G}*=${G}*(?:[^ 	
\f\r"'\`<>=]|("|')|))|$)`,"g"),gt=/'/g,bt=/"/g,wt=/^(?:script|style|textarea|title)$/i,rt=a=>(t,...e)=>({_$litType$:a,strings:t,values:e}),p=rt(1),Kt=rt(2),Yt=rt(3),k=Symbol.for("lit-noChange"),u=Symbol.for("lit-nothing"),yt=new WeakMap,S=E.createTreeWalker(E,129);function At(a,t){if(!ot(a)||!a.hasOwnProperty("raw"))throw Error("invalid template strings array");return ft!==void 0?ft.createHTML(t):t}var Ut=(a,t)=>{let e=a.length-1,s=[],i,o=t===2?"<svg>":t===3?"<math>":"",r=T;for(let c=0;c<e;c++){let n=a[c],l,d,h=-1,f=0;for(;f<n.length&&(r.lastIndex=f,d=r.exec(n),d!==null);)f=r.lastIndex,r===T?d[1]==="!--"?r=_t:d[1]!==void 0?r=vt:d[2]!==void 0?(wt.test(d[2])&&(i=RegExp("</"+d[2],"g")),r=A):d[3]!==void 0&&(r=A):r===A?d[0]===">"?(r=i??T,h=-1):d[1]===void 0?h=-2:(h=r.lastIndex-d[2].length,l=d[1],r=d[3]===void 0?A:d[3]==='"'?bt:gt):r===bt||r===gt?r=A:r===_t||r===vt?r=T:(r=A,i=void 0);let _=r===A&&a[c+1].startsWith("/>")?" ":"";o+=r===T?n+jt:h>=0?(s.push(l),n.slice(0,h)+xt+n.slice(h)+$+_):n+$+(h===-2?c:_)}return[At(a,o+(a[e]||"<?>")+(t===2?"</svg>":t===3?"</math>":"")),s]},U=class a{constructor({strings:t,_$litType$:e},s){let i;this.parts=[];let o=0,r=0,c=t.length-1,n=this.parts,[l,d]=Ut(t,e);if(this.el=a.createElement(l,s),S.currentNode=this.el.content,e===2||e===3){let h=this.el.content.firstChild;h.replaceWith(...h.childNodes)}for(;(i=S.nextNode())!==null&&n.length<c;){if(i.nodeType===1){if(i.hasAttributes())for(let h of i.getAttributeNames())if(h.endsWith(xt)){let f=d[r++],_=i.getAttribute(h).split($),b=/([.?@])?(.*)/.exec(f);n.push({type:1,index:o,name:b[2],strings:_,ctor:b[1]==="."?X:b[1]==="?"?tt:b[1]==="@"?et:H}),i.removeAttribute(h)}else h.startsWith($)&&(n.push({type:6,index:o}),i.removeAttribute(h));if(wt.test(i.tagName)){let h=i.textContent.split($),f=h.length-1;if(f>0){i.textContent=B?B.emptyScript:"";for(let _=0;_<f;_++)i.append(h[_],j()),S.nextNode(),n.push({type:2,index:++o});i.append(h[f],j())}}}else if(i.nodeType===8)if(i.data===$t)n.push({type:2,index:o});else{let h=-1;for(;(h=i.data.indexOf($,h+1))!==-1;)n.push({type:7,index:o}),h+=$.length-1}o++}}static createElement(t,e){let s=E.createElement("template");return s.innerHTML=t,s}};function z(a,t,e=a,s){if(t===k)return t;let i=s!==void 0?e._$Co?.[s]:e._$Cl,o=N(t)?void 0:t._$litDirective$;return i?.constructor!==o&&(i?._$AO?.(!1),o===void 0?i=void 0:(i=new o(a),i._$AT(a,e,s)),s!==void 0?(e._$Co??=[])[s]=i:e._$Cl=i),i!==void 0&&(t=z(a,i._$AS(a,t.values),i,s)),t}var Q=class{constructor(t,e){this._$AV=[],this._$AN=void 0,this._$AD=t,this._$AM=e}get parentNode(){return this._$AM.parentNode}get _$AU(){return this._$AM._$AU}u(t){let{el:{content:e},parts:s}=this._$AD,i=(t?.creationScope??E).importNode(e,!0);S.currentNode=i;let o=S.nextNode(),r=0,c=0,n=s[0];for(;n!==void 0;){if(r===n.index){let l;n.type===2?l=new R(o,o.nextSibling,this,t):n.type===1?l=new n.ctor(o,n.name,n.strings,this,t):n.type===6&&(l=new st(o,this,t)),this._$AV.push(l),n=s[++c]}r!==n?.index&&(o=S.nextNode(),r++)}return S.currentNode=E,i}p(t){let e=0;for(let s of this._$AV)s!==void 0&&(s.strings!==void 0?(s._$AI(t,s,e),e+=s.strings.length-2):s._$AI(t[e])),e++}},R=class a{get _$AU(){return this._$AM?._$AU??this._$Cv}constructor(t,e,s,i){this.type=2,this._$AH=u,this._$AN=void 0,this._$AA=t,this._$AB=e,this._$AM=s,this.options=i,this._$Cv=i?.isConnected??!0}get parentNode(){let t=this._$AA.parentNode,e=this._$AM;return e!==void 0&&t?.nodeType===11&&(t=e.parentNode),t}get startNode(){return this._$AA}get endNode(){return this._$AB}_$AI(t,e=this){t=z(this,t,e),N(t)?t===u||t==null||t===""?(this._$AH!==u&&this._$AR(),this._$AH=u):t!==this._$AH&&t!==k&&this._(t):t._$litType$!==void 0?this.$(t):t.nodeType!==void 0?this.T(t):Nt(t)?this.k(t):this._(t)}O(t){return this._$AA.parentNode.insertBefore(t,this._$AB)}T(t){this._$AH!==t&&(this._$AR(),this._$AH=this.O(t))}_(t){this._$AH!==u&&N(this._$AH)?this._$AA.nextSibling.data=t:this.T(E.createTextNode(t)),this._$AH=t}$(t){let{values:e,_$litType$:s}=t,i=typeof s=="number"?this._$AC(t):(s.el===void 0&&(s.el=U.createElement(At(s.h,s.h[0]),this.options)),s);if(this._$AH?._$AD===i)this._$AH.p(e);else{let o=new Q(i,this),r=o.u(this.options);o.p(e),this.T(r),this._$AH=o}}_$AC(t){let e=yt.get(t.strings);return e===void 0&&yt.set(t.strings,e=new U(t)),e}k(t){ot(this._$AH)||(this._$AH=[],this._$AR());let e=this._$AH,s,i=0;for(let o of t)i===e.length?e.push(s=new a(this.O(j()),this.O(j()),this,this.options)):s=e[i],s._$AI(o),i++;i<e.length&&(this._$AR(s&&s._$AB.nextSibling,i),e.length=i)}_$AR(t=this._$AA.nextSibling,e){for(this._$AP?.(!1,!0,e);t!==this._$AB;){let s=mt(t).nextSibling;mt(t).remove(),t=s}}setConnected(t){this._$AM===void 0&&(this._$Cv=t,this._$AP?.(t))}},H=class{get tagName(){return this.element.tagName}get _$AU(){return this._$AM._$AU}constructor(t,e,s,i,o){this.type=1,this._$AH=u,this._$AN=void 0,this.element=t,this.name=e,this._$AM=i,this.options=o,s.length>2||s[0]!==""||s[1]!==""?(this._$AH=Array(s.length-1).fill(new String),this.strings=s):this._$AH=u}_$AI(t,e=this,s,i){let o=this.strings,r=!1;if(o===void 0)t=z(this,t,e,0),r=!N(t)||t!==this._$AH&&t!==k,r&&(this._$AH=t);else{let c=t,n,l;for(t=o[0],n=0;n<o.length-1;n++)l=z(this,c[s+n],e,n),l===k&&(l=this._$AH[n]),r||=!N(l)||l!==this._$AH[n],l===u?t=u:t!==u&&(t+=(l??"")+o[n+1]),this._$AH[n]=l}r&&!i&&this.j(t)}j(t){t===u?this.element.removeAttribute(this.name):this.element.setAttribute(this.name,t??"")}},X=class extends H{constructor(){super(...arguments),this.type=3}j(t){this.element[this.name]=t===u?void 0:t}},tt=class extends H{constructor(){super(...arguments),this.type=4}j(t){this.element.toggleAttribute(this.name,!!t&&t!==u)}},et=class extends H{constructor(t,e,s,i,o){super(t,e,s,i,o),this.type=5}_$AI(t,e=this){if((t=z(this,t,e,0)??u)===k)return;let s=this._$AH,i=t===u&&s!==u||t.capture!==s.capture||t.once!==s.once||t.passive!==s.passive,o=t!==u&&(s===u||i);i&&this.element.removeEventListener(this.name,this,s),o&&this.element.addEventListener(this.name,this,t),this._$AH=t}handleEvent(t){typeof this._$AH=="function"?this._$AH.call(this.options?.host??this.element,t):this._$AH.handleEvent(t)}},st=class{constructor(t,e,s){this.element=t,this.type=6,this._$AN=void 0,this._$AM=e,this.options=s}get _$AU(){return this._$AM._$AU}_$AI(t){z(this,t)}};var Rt=it.litHtmlPolyfillSupport;Rt?.(U,R),(it.litHtmlVersions??=[]).push("3.3.2");var St=(a,t,e)=>{let s=e?.renderBefore??t,i=s._$litPart$;if(i===void 0){let o=e?.renderBefore??null;s._$litPart$=i=new R(t.insertBefore(j(),o),o,void 0,e??{})}return i._$AI(a),i};var at=globalThis,w=class extends x{constructor(){super(...arguments),this.renderOptions={host:this},this._$Do=void 0}createRenderRoot(){let t=super.createRenderRoot();return this.renderOptions.renderBefore??=t.firstChild,t}update(t){let e=this.render();this.hasUpdated||(this.renderOptions.isConnected=this.isConnected),super.update(t),this._$Do=St(e,this.renderRoot,this.renderOptions)}connectedCallback(){super.connectedCallback(),this._$Do?.setConnected(!0)}disconnectedCallback(){super.disconnectedCallback(),this._$Do?.setConnected(!1)}render(){return k}};w._$litElement$=!0,w.finalized=!0,at.litElementHydrateSupport?.({LitElement:w});var Lt=at.litElementPolyfillSupport;Lt?.({LitElement:w});(at.litElementVersions??=[]).push("4.2.2");var It="1.0.76",M=["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"],Et=[6,0,1,2,3,4,5],V=["home","away","sleep","wake"],Ft=["home","away","sleep","wake","manual"],Wt=["off","low","med","high"],kt=[{v:"60",l:"1 hour"},{v:"120",l:"2 hours"},{v:"240",l:"4 hours"},{v:"forever",l:"Indefinite"},{v:"custom",l:"Custom time\u2026"}],q=["\u2460","\u2461","\u2462","\u2463","\u2464","\u2465","\u2466","\u2467"],Bt=(()=>{let a=[];for(let t=0;t<24;t++)for(let e=0;e<60;e+=15){let s=`${String(t).padStart(2,"0")}:${String(e).padStart(2,"0")}`,i=t===0?`12:${String(e).padStart(2,"0")} AM`:t<12?`${t}:${String(e).padStart(2,"0")} AM`:t===12?`12:${String(e).padStart(2,"0")} PM`:`${t-12}:${String(e).padStart(2,"0")} PM`;a.push({v:s,l:i})}return a})(),nt=class extends w{static properties={hass:{attribute:!1},_config:{state:!0},_tab:{state:!0},_schedDay:{state:!0},_schedEdits:{state:!0},_profileEdits:{state:!0},_registryLoaded:{state:!0},_pendingTemps:{state:!0},_whHoldOpen:{state:!0},_whHoldActivity:{state:!0},_whHoldDuration:{state:!0},_whHoldCustom:{state:!0},_holdOpen:{state:!0},_holdActivity:{state:!0},_holdDuration:{state:!0},_holdCustom:{state:!0},_holdHtsp:{state:!0},_holdClsp:{state:!0},_holdFan:{state:!0}};constructor(){super(),this._config={},this._tab="status",this._schedDay=M[Et[new Date().getDay()]],this._schedEdits={},this._profileEdits={},this._registryEntities=null,this._registryLoaded=!1,this._tempAdj={},this._pendingTemps={},this._whHoldOpen=!1,this._whHoldActivity="home",this._whHoldDuration="120",this._whHoldCustom="",this._holdOpen=null,this._holdActivity="home",this._holdDuration="120",this._holdCustom="",this._holdHtsp=68,this._holdClsp=76,this._holdFan="auto"}static getConfigElement(){return document.createElement("div")}static getStubConfig(){return{}}setConfig(t){this._config=t}getCardSize(){return 8}shouldUpdate(t){if(!t.has("hass")||!this._registryLoaded)return!0;let e=t.get("hass");return e?(this._registryEntities||[]).some(i=>this.hass.states[i.entity_id]!==e.states[i.entity_id]):!0}updated(t){t.has("hass")&&this.hass&&!this._registryLoaded&&this._loadRegistry()}async _loadRegistry(){try{let t=await this.hass.connection.sendMessagePromise({type:"config/entity_registry/list"});this._registryEntities=Array.isArray(t)?t.filter(e=>e.platform==="infinitude_direct"):[]}catch(t){console.warn("Failed to load entity registry",t),this._registryEntities=[]}this._registryLoaded=!0}_findEntities(){if(!this.hass)return{climates:[],sensors:{},selects:{},system:{}};let t=this._registryEntities||[],e=this.hass.states,s=[],i={damper:{},fan:{}},o={},r={};if(this._config.climate_entities)for(let c of this._config.climate_entities)e[c]&&s.push(c);for(let c of t){let n=c.entity_id;if(!e[n])continue;let l=n.split(".")[0],d=c.unique_id||"";l==="climate"?this._config.climate_entities||s.push(n):l==="select"?o.wholeHouse=n:l==="sensor"&&(d.includes("damper")?i.damper[n]=e[n]:d.includes("fan")?i.fan[n]=e[n]:d.includes("humidifier")?r.humidifier=n:d.includes("oat")?r.oat=n:d.includes("op_status")?r.opStatus=n:d.includes("system_info")&&(r.info=n))}return s.sort(),{climates:s,sensors:i,selects:o,system:r}}_st(t){return t?this.hass?.states[t]??null:null}_at(t,e){return this._st(t)?.attributes?.[e]}_getScheduleData(){let{system:t}=this._findEntities();if(!t.info)return{};try{return JSON.parse(this._at(t.info,"schedule")||"{}")}catch(e){return console.warn("Failed to parse schedule data",e),{}}}_getProfilesData(){let{system:t}=this._findEntities();if(!t.info)return[];try{return JSON.parse(this._at(t.info,"profiles")||"[]")}catch(e){return console.warn("Failed to parse profiles data",e),[]}}async _svc(t,e,s){try{await this.hass.callService(t,e,s)}catch(i){console.error(`${t}.${e} failed`,i)}}_setHvacMode(t,e){this._svc("climate","set_hvac_mode",{entity_id:t,hvac_mode:e})}_setPreset(t,e){this._svc("climate","set_preset_mode",{entity_id:t,preset_mode:e})}_adjustTemp(t,e,s){let i=this._st(t);if(!i)return;let o=i.attributes||{},r=this._tempAdj[t]||(this._tempAdj[t]={}),c=r.heat??o.target_temp_low??o.temperature??68,n=r.cool??o.target_temp_high??(i.state==="cool"?o.temperature:null)??76;s==="heat"?r.heat=Math.max(50,Math.min(90,Math.round(c)+e)):r.cool=Math.max(60,Math.min(99,Math.round(n)+e)),this._pendingTemps={...this._pendingTemps,[t]:{heat:r.heat,cool:r.cool}},r.committing||(clearTimeout(r.timer),r.timer=setTimeout(()=>this._commitAdj(t),800))}async _commitAdj(t){let e=this._tempAdj[t];if(!e||e.committing)return;e.committing=!0;let s=this._st(t),i=s?.attributes||{},o=e.heat,r=e.cool,c=o??Math.round(i.target_temp_low??i.temperature??68),n=r??Math.round(i.target_temp_high??(s?.state==="cool"?i.temperature:null)??76),l=s?.state||"off",d={entity_id:t};l==="heat_cool"?(d.target_temp_low=c,d.target_temp_high=n):l==="heat"?d.temperature=c:l==="cool"?d.temperature=n:(d.target_temp_low=c,d.target_temp_high=n);try{await this.hass.callService("climate","set_temperature",d)}catch(h){console.error("set_temperature failed",h)}if(e.committing=!1,e.heat!==o||e.cool!==r){e.timer=setTimeout(()=>this._commitAdj(t),400);return}e.heat=null,e.cool=null,e.timer=null,e.graceUntil=Date.now()+3e4,setTimeout(()=>{if(!this._tempAdj[t]?.heat&&!this._tempAdj[t]?.cool){let{[t]:h,...f}=this._pendingTemps;this._pendingTemps=f}},2e3)}_hasPending(t){let e=this._tempAdj[t];return e&&(e.heat!=null||e.cool!=null||e.committing)}_cancelHold(t){let e=(this._registryEntities||[]).find(i=>i.entity_id===t);if(!e)return;let s=(e.unique_id||"").replace(/^infinitude_/,"");s&&this._svc("infinitude_direct","cancel_hold",{zone_id:s})}_setZoneHold(t){let e=(this._registryEntities||[]).find(o=>o.entity_id===t);if(!e)return;let s=(e.unique_id||"").replace(/^infinitude_/,"");if(!s)return;let i=this._resolveUntil(this._holdDuration,this._holdCustom);i!==null&&(this._holdActivity==="manual"&&this._svc("infinitude_direct","set_profile",{zone_id:s,activity:"manual",htsp:this._holdHtsp,clsp:this._holdClsp,fan:this._holdFan}),this._svc("infinitude_direct","set_hold",{zone_id:s,activity:this._holdActivity,...i!==void 0&&{until:i}}),this._holdOpen=null)}_initHoldManual(t){let e=this._zoneId(t),s=this._getProfilesData().find(i=>i.id===e)?.activities?.manual||{};this._holdHtsp=s.htsp?Math.round(Number(s.htsp)||68):68,this._holdClsp=s.clsp?Math.round(Number(s.clsp)||76):76,this._holdFan=s.fan||"auto"}_setWholeHouseHold(){let t=this._resolveUntil(this._whHoldDuration,this._whHoldCustom);t!==null&&(this._svc("infinitude_direct","set_whole_house_hold",{activity:this._whHoldActivity,...t!==void 0&&{until:t}}),this._whHoldOpen=!1)}_cancelWholeHouseHold(){this._svc("infinitude_direct","cancel_whole_house_hold",{})}_resolveUntil(t,e){if(t==="forever")return"forever";if(t==="custom")return e||null;let s=new Date;s.setMinutes(s.getMinutes()+parseInt(t));let i=Math.round(s.getMinutes()/15)*15;return s.setMinutes(i,0,0),i===60&&(s.setMinutes(0),s.setHours(s.getHours()+1)),`${String(s.getHours()).padStart(2,"0")}:${String(s.getMinutes()).padStart(2,"0")}`}_otmrRelative(t){if(!t)return"";let[e,s]=t.split(":").map(Number),i=new Date;return i.setHours(e,s,0,0),"until "+i.toLocaleTimeString([],{hour:"numeric",minute:"2-digit"})}_zoneId(t){let e=(this._registryEntities||[]).find(s=>s.entity_id===t);return e?(e.unique_id||"").replace(/^infinitude_/,""):""}static styles=J`
    :host { display: block; }
    ha-card { overflow: hidden; }
    .card-header {
      display: flex; align-items: center;
      padding: 12px 16px 8px; gap: 8px;
    }
    .header-left { display: flex; align-items: center; gap: 8px; }
    .header-title { font-size: 18px; font-weight: 500; color: var(--primary-text-color); }
    .conn-dot { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; }
    .conn-dot.ok { background: var(--label-badge-green, #34d399); animation: pulse-dot 2.5s ease infinite; }
    .conn-dot.err { background: #ef4444; }
    .conn-dot.unk { background: var(--secondary-text-color); opacity: 0.4; }
    @keyframes pulse-dot { 0%,100% { opacity: 1; } 50% { opacity: 0.4; } }
    .summary-stats {
      display: flex; align-items: center; gap: 0; margin-bottom: 14px;
      border: 1px solid var(--divider-color); border-radius: 8px; overflow: hidden;
    }
    .summary-stat {
      display: flex; flex-direction: column; align-items: center; gap: 2px;
      padding: 8px 14px; flex: 1; min-width: 0;
    }
    .summary-stat-label { font-size: 10px; color: var(--secondary-text-color); text-transform: uppercase; letter-spacing: 0.5px; }
    .summary-stat-val { font-size: 14px; font-weight: 700; color: var(--primary-text-color); }
    .summary-stat-val.heat { color: var(--label-badge-red, #f97316); }
    .summary-stat-val.cool { color: var(--label-badge-blue, #38bdf8); }
    .summary-divider { width: 1px; align-self: stretch; background: var(--divider-color); }
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
  `;render(){if(!this.hass)return u;if(!this._registryLoaded)return p`<ha-card>
        <div style="padding:24px;text-align:center;color:var(--secondary-text-color)">Loading…</div>
      </ha-card>`;let t=this._findEntities();return!t.climates.length&&!this._config.show_empty?p`<ha-card>
        <div style="padding:24px;text-align:center;color:var(--secondary-text-color)">
          <ha-icon icon="mdi:thermostat" style="--mdc-icon-size:48px;opacity:0.3;margin-bottom:12px;display:block"></ha-icon>
          <div style="font-size:14px;font-weight:500">No Infinitude entities found</div>
          <div style="font-size:12px;margin-top:4px">Waiting for thermostat connection…</div>
        </div>
      </ha-card>`:p`
      <ha-card>
        <div class="card-header">${this._hdr(t)}</div>
        <div class="card-tabs">${this._tabs()}</div>
        <div class="card-content">
          ${this._tab==="status"?this._status(t):u}
          ${this._tab==="schedule"?this._sched(t):u}
          ${this._tab==="profiles"?this._profs():u}
        </div>
      </ha-card>`}_hdr(t){let{system:e}=t,s=e.info?this._st(e.info)?.state!=="unavailable":!1,i=e.info?this._at(e.info,"carrier_ok"):null;return p`
      <div class="header-left">
        <span class="header-title">infinitude</span>
        <span class="conn-dot ${s?"ok":"err"}" title="${s?"Infinitude: connected":"Infinitude: unavailable"}"></span>
        <span class="conn-dot ${i===!0?"ok":i===!1?"err":"unk"}" title="${i===!0?"Carrier cloud: connected":i===!1?"Carrier cloud: unreachable":"Carrier cloud: checking\u2026"}"></span>
        <span style="font-size:10px;color:var(--secondary-text-color);opacity:0.5">v${It}</span>
      </div>`}_summaryStrip(t){let{system:e,selects:s,climates:i}=t,o=i.length&&this._st(i[0])?.state||"off",r=["off","heat","cool","heat_cool"],c={off:"Off",heat:"Heat",cool:"Cool",heat_cool:"Auto"},n=this._st(e.oat),l="\u2013";if(n?.state&&n.state!=="unavailable")l=`${Math.round(Number(n.state))}\xB0`;else if(i.length){let m=this._at(i[0],"outdoor_temperature");m!=null&&(l=`${Math.round(Number(m))}\xB0`)}let d=this._st(e.opStatus),h=d?.state&&d.state!=="unavailable"?d.state:"",f=this._st(e.humidifier)?.state==="on",_=this._st(s.wholeHouse),b=_&&_.state!=="off",C=i.length?this._at(i[0],"whole_house_hold_until"):null,y=i.length?this._at(i[0],"current_humidity"):null;return p`
      <div class="mode-row">
        <span class="mode-label">Mode</span>
        <div class="mode-pills">
          ${r.map(m=>p`<div class="mode-pill ${m===o?"active":""} ${m==="heat"?"heat":m==="cool"?"cool":m==="heat_cool"?"auto":""}"
              @click=${()=>this._setHvacMode(i[0],m)}>${c[m]}</div>`)}
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
          <span class="summary-stat-val">${l}</span>
        </div>
        <div class="summary-divider"></div>
        <div class="summary-stat">
          <span class="summary-stat-label">Humidity</span>
          <span class="summary-stat-val">${y!=null?`${y}%`:"\u2013"}</span>
        </div>
        ${f?p`
          <div class="summary-divider"></div>
          <div class="summary-stat">
            <span class="summary-stat-label">Humidifier</span>
            <span class="summary-stat-val" style="color:var(--label-badge-blue,#38bdf8)">💧 On</span>
          </div>`:u}
      </div>
      ${b?p`
        <div class="wh-hold" @click=${()=>this._cancelWholeHouseHold()}>
          <ha-icon icon="mdi:home-lock" style="--mdc-icon-size:16px"></ha-icon>
          <span>Whole house: <strong>${_.state}</strong>${C?p` · <span style="opacity:0.85">${this._otmrRelative(C)}</span>`:u}</span>
          <span style="margin-left:auto;opacity:0.7">Tap to cancel</span>
        </div>`:p`
        ${this._whHoldOpen?p`
          <div class="wh-set">
            <span class="wh-set-label">WH Hold</span>
            <div class="wh-pills">
              ${V.map(m=>p`
                <div class="wh-pill ${this._whHoldActivity===m?"active":""}"
                     @click=${()=>{this._whHoldActivity=m}}>${m}</div>`)}
            </div>
            <select class="hold-dur-select" @change=${m=>{this._whHoldDuration=m.target.value}}>
              ${kt.map(m=>p`<option value=${m.v} ?selected=${m.v===this._whHoldDuration}>${m.l}</option>`)}
            </select>
            ${this._whHoldDuration==="custom"?p`
              <input type="time" class="hold-time-input" step="900" .value=${this._whHoldCustom}
                     @change=${m=>{this._whHoldCustom=m.target.value}}>`:u}
            <button class="btn btn-primary" style="font-size:11px;padding:4px 12px" @click=${()=>this._setWholeHouseHold()}>Apply</button>
            <button class="btn" style="font-size:11px;padding:4px 10px" @click=${()=>{this._whHoldOpen=!1}}>Cancel</button>
          </div>`:p`
          <div>
            <button class="btn" style="font-size:11px;padding:4px 12px" @click=${()=>{this._whHoldOpen=!0}}>
              <ha-icon icon="mdi:home-lock" style="--mdc-icon-size:14px;vertical-align:middle;margin-right:4px"></ha-icon>Set WH hold
            </button>
          </div>`}
      `}`}_tabs(){return p`${["status","schedule","profiles"].map(e=>p`
      <div class="tab ${this._tab===e?"active":""}"
           @click=${()=>{this._tab=e}}>${e.charAt(0).toUpperCase()+e.slice(1)}</div>`)}`}_status(t){let{climates:e}=t;return e.length?p`
      ${this._summaryStrip(t)}
      <div class="zone-grid">${e.map(s=>this._zoneCard(s))}</div>`:p`<div style="padding:20px;text-align:center;color:var(--secondary-text-color)">No zone entities found</div>`}_zoneCard(t){let e=this._st(t);if(!e)return u;let s=e.attributes||{},i=(s.friendly_name||t).replace(/^Infinitude\s+/i,"").replace(/^infinitude_direct\s+/i,""),o=s.current_temperature!=null?Math.round(s.current_temperature):"\u2013",r=s.current_humidity,c=e.state||"off",n=s.hvac_action||"idle",l=s.preset_mode||"\u2013",d=n==="heating"?"heating":n==="cooling"?"cooling":n==="drying"?"drying":"",h=n==="idle"?"Idle":n.charAt(0).toUpperCase()+n.slice(1),f=c==="heat_cool",_=!!s.hold_active,b=s.hold_activity||l,C=s.hold_until,y=this._holdOpen===t,m=this._pendingTemps[t],P=this._hasPending(t),L=m?.heat??s.target_temp_low??s.temperature??null,v=m?.cool??s.target_temp_high??(c==="cool"?s.temperature:null)??null;return p`
      <div class="zone-card ${d}">
        <div class="zone-top">
          <span class="zone-name">${i}</span>
          <span class="zone-badge ${d}">${h}</span>
        </div>
        <div class="zone-body">
          <div>
            <span class="temp-hero">${o}</span><span class="temp-unit">°F</span>
            ${r!=null?p`<div style="font-size:11px;color:var(--secondary-text-color);margin-top:2px">${r}% RH</div>`:u}
          </div>
          <div class="zone-sp">
            ${L!=null?p`
              <div class="sp-row">
                <button class="btn-adj" @click=${()=>this._adjustTemp(t,-1,"heat")}>−</button>
                <span class="sp-val sp-heat ${P?"sp-pending":""}">${Math.round(L)}°</span>
                <button class="btn-adj" @click=${()=>this._adjustTemp(t,1,"heat")}>+</button>
              </div>`:u}
            ${f&&v!=null?p`
              <div class="sp-row">
                <button class="btn-adj" @click=${()=>this._adjustTemp(t,-1,"cool")}>−</button>
                <span class="sp-val sp-cool ${P?"sp-pending":""}">${Math.round(v)}°</span>
                <button class="btn-adj" @click=${()=>this._adjustTemp(t,1,"cool")}>+</button>
              </div>`:u}
          </div>
        </div>
        <div class="zone-meta">
          <span class="meta-item">Activity <span class="meta-val">${l}</span></span>
          ${s.fan_mode?p`<span class="meta-item">Fan <span class="meta-val">${s.fan_mode}</span></span>`:u}
          ${s.damper_position!=null?p`<span class="meta-item">Damper <span class="meta-val">${s.damper_position}%</span></span>`:u}
        </div>
        <div class="zone-preset-row">
          ${V.map(g=>p`
            <div class="preset-btn ${l===g?"active":""}"
                 @click=${()=>this._setPreset(t,g)}>${g}</div>`)}
        </div>
        ${_?p`
          <div class="zone-hold">
            <span class="hold-label">Hold: ${b}${C?` \xB7 ${this._otmrRelative(C)}`:""}</span>
            <button class="btn" style="font-size:11px;padding:3px 10px;color:var(--error-color,#f87171)" @click=${()=>this._cancelHold(t)}>Cancel</button>
          </div>`:u}
        ${y?p`
          <div class="zone-hold-picker">
            <div class="hold-picker-row">
              <div class="wh-pills">
                ${Ft.map(g=>p`
                  <div class="wh-pill ${this._holdActivity===g?"active":""}"
                       @click=${()=>{this._holdActivity=g,g==="manual"&&this._initHoldManual(t)}}>${g}</div>`)}
              </div>
            </div>
            ${this._holdActivity==="manual"?p`
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
                  <select class="hold-dur-select" style="width:auto" .value=${this._holdFan} @change=${g=>{this._holdFan=g.target.value}}>
                    <option value="auto">Auto</option>
                    <option value="low">Low</option>
                    <option value="med">Med</option>
                    <option value="high">High</option>
                  </select>
                </div>
              </div>`:u}
            <div class="hold-picker-row">
              <select class="hold-dur-select" @change=${g=>{this._holdDuration=g.target.value}}>
                ${kt.map(g=>p`<option value=${g.v} ?selected=${g.v===this._holdDuration}>${g.l}</option>`)}
              </select>
              ${this._holdDuration==="custom"?p`
                <input type="time" class="hold-time-input" step="900" .value=${this._holdCustom}
                       @change=${g=>{this._holdCustom=g.target.value}}>`:u}
            </div>
            <div class="hold-picker-row">
              <button class="btn btn-primary" style="font-size:11px;padding:4px 12px" @click=${()=>this._setZoneHold(t)}>Apply</button>
              <button class="btn" style="font-size:11px;padding:4px 10px" @click=${()=>{this._holdOpen=null}}>Cancel</button>
            </div>
          </div>`:_?u:p`
          <div class="zone-actions">
            <button class="btn" style="font-size:11px;padding:4px 12px" @click=${()=>{this._holdActivity=l!=="\u2013"?l:"home",this._holdDuration="120",this._holdCustom="",this._holdActivity==="manual"&&this._initHoldManual(t),this._holdOpen=t}}>Set hold</button>
          </div>`}
      </div>`}_sched(){let t=this._getScheduleData(),e=this._getProfilesData(),s=Object.keys(t);if(!s.length)return p`
      <div style="padding:20px;text-align:center;color:var(--secondary-text-color)">
        <ha-icon icon="mdi:calendar-clock" style="--mdc-icon-size:48px;opacity:0.3;margin-bottom:12px;display:block"></ha-icon>
        No schedule data available. Waiting for thermostat data…
      </div>`;let i=M[Et[new Date().getDay()]],o={},r={};for(let l=0;l<e.length;l++)o[e[l].id]=e[l].name,r[e[l].id]=l;let c=0;for(let l of s)c=Math.max(c,(t[l]?.[this._schedDay]||[]).length);c||(c=5);let n=Object.keys(this._schedEdits).length>0;return p`
      <div class="section-title">Schedule</div>
      ${s.length>1?p`<div class="zone-legend">${s.map((l,d)=>p`<span class="legend-item"><span class="legend-num">${q[d]||d+1}</span> ${o[l]||`Zone ${l}`}</span>`)}</div>`:u}
      <div class="sched-day-tabs">
        ${M.map(l=>p`
          <div class="day-tab ${l===this._schedDay?"active":""} ${l===i&&l!==this._schedDay?"today":""}"
               @click=${()=>{this._schedDay=l}}>${l.slice(0,3)}</div>`)}
      </div>
      ${Array.from({length:c},(l,d)=>this._periodCard(d,s,t,e,o,r))}
      <div class="copy-bar">
        <span>Copy ${this._schedDay.slice(0,3)} →</span>
        <select class="sched-select" @change=${l=>this._copySched(l)}>
          <option value="">select day…</option>
          ${M.filter(l=>l!==this._schedDay).map(l=>p`<option value=${l}>${l.slice(0,3)}</option>`)}
          <option value="__all__">All other days</option>
        </select>
      </div>
      ${n?p`
        <div class="action-bar">
          <span class="action-bar-label">● Unsaved changes</span>
          <button class="btn" @click=${()=>{this._schedEdits={}}}>Discard</button>
          <button class="btn btn-primary" @click=${()=>this._saveSched()}>Save schedule</button>
        </div>`:u}`}_periodCard(t,e,s,i,o,r){let c=e.length>1;return p`
      <div class="period-card">
        <div class="period-header">Period ${t+1}</div>
        ${e.map(n=>{let l=(s[n]?.[this._schedDay]||[])[t];if(!l)return u;let d=`${n}_${this._schedDay}_${t}`,h=this._schedEdits[d],f=h?.act??l.activity,_=h?.time??l.time,b=h?.enabled??l.enabled,y=i.find(v=>v.id===n)?.activities?.[f],m=y?.htsp?Math.round(Number(y.htsp)||0):"\u2013",P=y?.clsp?Math.round(Number(y.clsp)||0):"\u2013",L=c?q[r[n]]??n:o[n]||`Zone ${n}`;return p`
            <div class="sched-line ${b?"":"disabled"}">
              <span class="sched-name ${c?"sched-name-compact":""}">${L}</span>
              <select class="sched-select" @change=${v=>this._schedEdit(n,t,"act",v.target.value)}>
                ${V.map(v=>p`<option value=${v} ?selected=${v===f}>${v}</option>`)}
              </select>
              <select class="sched-select" @change=${v=>this._schedEdit(n,t,"time",v.target.value)}>
                ${Bt.map(v=>p`<option value=${v.v} ?selected=${v.v===_}>${v.l}</option>`)}
              </select>
              <label class="sched-toggle">
                <input type="checkbox" ?checked=${b}
                       @change=${v=>this._schedEdit(n,t,"enabled",v.target.checked)}>
                <span>on</span>
              </label>
              <div class="sched-temps">
                <span class="sp-heat">${m}°</span>
                <span class="sp-cool">${P}°</span>
              </div>
            </div>`})}
      </div>`}_schedEdit(t,e,s,i){let o=`${t}_${this._schedDay}_${e}`,r=this._schedEdits[o]||{},c=(this._getScheduleData()[t]?.[this._schedDay]||[])[e]||{};this._schedEdits={...this._schedEdits,[o]:{act:s==="act"?i:r.act??c.activity,time:s==="time"?i:r.time??c.time,enabled:s==="enabled"?i:r.enabled??c.enabled}}}_copySched(t){let e=t.target.value;if(!e)return;t.target.value="";let s=this._getScheduleData(),i=e==="__all__"?M.filter(r=>r!==this._schedDay):[e],o={...this._schedEdits};for(let r of Object.keys(s)){let c=s[r]?.[this._schedDay]||[];for(let n of i)c.forEach((l,d)=>{let h=this._schedEdits[`${r}_${this._schedDay}_${d}`];o[`${r}_${n}_${d}`]={act:h?.act??l.activity,time:h?.time??l.time,enabled:h?.enabled??l.enabled}})}this._schedEdits=o}async _saveSched(){let t=this._getScheduleData();for(let e of Object.keys(t)){let s=M.map(i=>({id:i,period:(t[e]?.[i]||[]).map((o,r)=>{let c=this._schedEdits[`${e}_${i}_${r}`];return{id:o.id||String(r+1),activity:c?.act??o.activity,time:c?.time??o.time,enabled:c?.enabled??o.enabled?"on":"off"}})}));await this._svc("infinitude_direct","save_schedule",{zone_id:e,schedule:JSON.stringify(s)})}this._schedEdits={}}_profs(){let t=this._getProfilesData();if(!t.length)return p`
      <div style="padding:20px;text-align:center;color:var(--secondary-text-color)">
        <ha-icon icon="mdi:tune-vertical" style="--mdc-icon-size:48px;opacity:0.3;margin-bottom:12px;display:block"></ha-icon>
        No profile data available. Waiting for thermostat data…
      </div>`;let e=t.length>1,s=Object.keys(this._profileEdits).length>0;return p`
      <div class="section-title">Comfort Profiles</div>
      ${e?p`<div class="zone-legend">${t.map((i,o)=>p`<span class="legend-item"><span class="legend-num">${q[o]||o+1}</span> ${i.name}</span>`)}</div>`:u}
      ${V.map(i=>p`
        <div class="prof-card">
          <div class="prof-header">${i}</div>
          ${t.map((o,r)=>{let c=o.activities?.[i]||{},n=`${o.id}_${i}`,l=this._profileEdits[n],d=l?.htsp??(c.htsp?Math.round(Number(c.htsp)||68):68),h=l?.clsp??(c.clsp?Math.round(Number(c.clsp)||76):76),f=l?.fan??c.fan??"low",_=e?q[r]||r+1:o.name;return p`
              <div class="prof-line">
                <span class="prof-name ${e?"prof-name-compact":""}">${_}</span>
                <div class="sp-row">
                  <button class="btn-adj" @click=${()=>this._profAdj(o.id,i,"htsp",-1)}>−</button>
                  <span class="sp-val sp-heat">${d}°</span>
                  <button class="btn-adj" @click=${()=>this._profAdj(o.id,i,"htsp",1)}>+</button>
                </div>
                <div class="sp-row">
                  <button class="btn-adj" @click=${()=>this._profAdj(o.id,i,"clsp",-1)}>−</button>
                  <span class="sp-val sp-cool">${h}°</span>
                  <button class="btn-adj" @click=${()=>this._profAdj(o.id,i,"clsp",1)}>+</button>
                </div>
                <div class="prof-fan">
                  <span class="prof-fan-label">Fan</span>
                  <select class="sched-select" @change=${b=>this._profFan(o.id,i,b.target.value)}>
                    ${Wt.map(b=>p`<option value=${b} ?selected=${b===f}>${b}</option>`)}
                  </select>
                </div>
              </div>`})}
        </div>`)}
      ${s?p`
        <div class="action-bar">
          <span class="action-bar-label">● Unsaved changes</span>
          <button class="btn" @click=${()=>{this._profileEdits={}}}>Discard</button>
          <button class="btn btn-primary" @click=${()=>this._saveProfs()}>Save profiles</button>
        </div>`:u}`}_profAdj(t,e,s,i){let o=`${t}_${e}`,r=this._getProfilesData().find(_=>_.id===t)?.activities?.[e]||{},c=this._profileEdits[o]||{},n=c.htsp??(r.htsp?Math.round(Number(r.htsp)||68):68),l=c.clsp??(r.clsp?Math.round(Number(r.clsp)||76):76),d=s==="htsp"?50:60,h=s==="htsp"?90:99,f=s==="htsp"?n:l;this._profileEdits={...this._profileEdits,[o]:{zone_id:t,activity:e,htsp:s==="htsp"?Math.max(d,Math.min(h,f+i)):n,clsp:s==="clsp"?Math.max(d,Math.min(h,f+i)):l,fan:c.fan??r.fan??"low"}}}_profFan(t,e,s){let i=`${t}_${e}`,o=this._getProfilesData().find(c=>c.id===t)?.activities?.[e]||{},r=this._profileEdits[i]||{};this._profileEdits={...this._profileEdits,[i]:{zone_id:t,activity:e,htsp:r.htsp??(o.htsp?Math.round(Number(o.htsp)||68):68),clsp:r.clsp??(o.clsp?Math.round(Number(o.clsp)||76):76),fan:s}}}async _saveProfs(){for(let t of Object.values(this._profileEdits)){let e={zone_id:t.zone_id,activity:t.activity,htsp:t.htsp,clsp:t.clsp};t.fan&&(e.fan=t.fan),await this._svc("infinitude_direct","set_profile",e)}this._profileEdits={}}};customElements.get("infinitude-hvac-card")||customElements.define("infinitude-hvac-card",nt);window.customCards=window.customCards||[];window.customCards.some(a=>a.type==="infinitude-hvac-card")||window.customCards.push({type:"infinitude-hvac-card",name:"Infinitude HVAC Card",description:"Full HVAC dashboard for Carrier/Bryant Infinity thermostats",preview:!1});
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
