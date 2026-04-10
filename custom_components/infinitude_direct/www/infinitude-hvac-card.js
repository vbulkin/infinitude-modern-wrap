var J=globalThis,Y=J.ShadowRoot&&(J.ShadyCSS===void 0||J.ShadyCSS.nativeShadow)&&"adoptedStyleSheets"in Document.prototype&&"replace"in CSSStyleSheet.prototype,st=Symbol(),yt=new WeakMap,L=class{constructor(t,e,s){if(this._$cssResult$=!0,s!==st)throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");this.cssText=t,this.t=e}get styleSheet(){let t=this.o,e=this.t;if(Y&&t===void 0){let s=e!==void 0&&e.length===1;s&&(t=yt.get(e)),t===void 0&&((this.o=t=new CSSStyleSheet).replaceSync(this.cssText),s&&yt.set(e,t))}return t}toString(){return this.cssText}},xt=d=>new L(typeof d=="string"?d:d+"",void 0,st),E=(d,...t)=>{let e=d.length===1?d[0]:t.reduce((s,i,o)=>s+(a=>{if(a._$cssResult$===!0)return a.cssText;if(typeof a=="number")return a;throw Error("Value passed to 'css' function must be a 'css' function result: "+a+". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.")})(i)+d[o+1],d[0]);return new L(e,d,st)},$t=(d,t)=>{if(Y)d.adoptedStyleSheets=t.map(e=>e instanceof CSSStyleSheet?e:e.styleSheet);else for(let e of t){let s=document.createElement("style"),i=J.litNonce;i!==void 0&&s.setAttribute("nonce",i),s.textContent=e.cssText,d.appendChild(s)}},it=Y?d=>d:d=>d instanceof CSSStyleSheet?(t=>{let e="";for(let s of t.cssRules)e+=s.cssText;return xt(e)})(d):d;var{is:It,defineProperty:Ut,getOwnPropertyDescriptor:Rt,getOwnPropertyNames:Lt,getOwnPropertySymbols:Ft,getPrototypeOf:Wt}=Object,K=globalThis,wt=K.trustedTypes,Bt=wt?wt.emptyScript:"",Vt=K.reactiveElementPolyfillSupport,F=(d,t)=>d,ot={toAttribute(d,t){switch(t){case Boolean:d=d?Bt:null;break;case Object:case Array:d=d==null?d:JSON.stringify(d)}return d},fromAttribute(d,t){let e=d;switch(t){case Boolean:e=d!==null;break;case Number:e=d===null?null:Number(d);break;case Object:case Array:try{e=JSON.parse(d)}catch{e=null}}return e}},kt=(d,t)=>!It(d,t),At={attribute:!0,type:String,converter:ot,reflect:!1,useDefault:!1,hasChanged:kt};Symbol.metadata??=Symbol("metadata"),K.litPropertyMetadata??=new WeakMap;var H=class extends HTMLElement{static addInitializer(t){this._$Ei(),(this.l??=[]).push(t)}static get observedAttributes(){return this.finalize(),this._$Eh&&[...this._$Eh.keys()]}static createProperty(t,e=At){if(e.state&&(e.attribute=!1),this._$Ei(),this.prototype.hasOwnProperty(t)&&((e=Object.create(e)).wrapped=!0),this.elementProperties.set(t,e),!e.noAccessor){let s=Symbol(),i=this.getPropertyDescriptor(t,s,e);i!==void 0&&Ut(this.prototype,t,i)}}static getPropertyDescriptor(t,e,s){let{get:i,set:o}=Rt(this.prototype,t)??{get(){return this[e]},set(a){this[e]=a}};return{get:i,set(a){let l=i?.call(this);o?.call(this,a),this.requestUpdate(t,l,s)},configurable:!0,enumerable:!0}}static getPropertyOptions(t){return this.elementProperties.get(t)??At}static _$Ei(){if(this.hasOwnProperty(F("elementProperties")))return;let t=Wt(this);t.finalize(),t.l!==void 0&&(this.l=[...t.l]),this.elementProperties=new Map(t.elementProperties)}static finalize(){if(this.hasOwnProperty(F("finalized")))return;if(this.finalized=!0,this._$Ei(),this.hasOwnProperty(F("properties"))){let e=this.properties,s=[...Lt(e),...Ft(e)];for(let i of s)this.createProperty(i,e[i])}let t=this[Symbol.metadata];if(t!==null){let e=litPropertyMetadata.get(t);if(e!==void 0)for(let[s,i]of e)this.elementProperties.set(s,i)}this._$Eh=new Map;for(let[e,s]of this.elementProperties){let i=this._$Eu(e,s);i!==void 0&&this._$Eh.set(i,e)}this.elementStyles=this.finalizeStyles(this.styles)}static finalizeStyles(t){let e=[];if(Array.isArray(t)){let s=new Set(t.flat(1/0).reverse());for(let i of s)e.unshift(it(i))}else t!==void 0&&e.push(it(t));return e}static _$Eu(t,e){let s=e.attribute;return s===!1?void 0:typeof s=="string"?s:typeof t=="string"?t.toLowerCase():void 0}constructor(){super(),this._$Ep=void 0,this.isUpdatePending=!1,this.hasUpdated=!1,this._$Em=null,this._$Ev()}_$Ev(){this._$ES=new Promise(t=>this.enableUpdating=t),this._$AL=new Map,this._$E_(),this.requestUpdate(),this.constructor.l?.forEach(t=>t(this))}addController(t){(this._$EO??=new Set).add(t),this.renderRoot!==void 0&&this.isConnected&&t.hostConnected?.()}removeController(t){this._$EO?.delete(t)}_$E_(){let t=new Map,e=this.constructor.elementProperties;for(let s of e.keys())this.hasOwnProperty(s)&&(t.set(s,this[s]),delete this[s]);t.size>0&&(this._$Ep=t)}createRenderRoot(){let t=this.shadowRoot??this.attachShadow(this.constructor.shadowRootOptions);return $t(t,this.constructor.elementStyles),t}connectedCallback(){this.renderRoot??=this.createRenderRoot(),this.enableUpdating(!0),this._$EO?.forEach(t=>t.hostConnected?.())}enableUpdating(t){}disconnectedCallback(){this._$EO?.forEach(t=>t.hostDisconnected?.())}attributeChangedCallback(t,e,s){this._$AK(t,s)}_$ET(t,e){let s=this.constructor.elementProperties.get(t),i=this.constructor._$Eu(t,s);if(i!==void 0&&s.reflect===!0){let o=(s.converter?.toAttribute!==void 0?s.converter:ot).toAttribute(e,s.type);this._$Em=t,o==null?this.removeAttribute(i):this.setAttribute(i,o),this._$Em=null}}_$AK(t,e){let s=this.constructor,i=s._$Eh.get(t);if(i!==void 0&&this._$Em!==i){let o=s.getPropertyOptions(i),a=typeof o.converter=="function"?{fromAttribute:o.converter}:o.converter?.fromAttribute!==void 0?o.converter:ot;this._$Em=i;let l=a.fromAttribute(e,o.type);this[i]=l??this._$Ej?.get(i)??l,this._$Em=null}}requestUpdate(t,e,s,i=!1,o){if(t!==void 0){let a=this.constructor;if(i===!1&&(o=this[t]),s??=a.getPropertyOptions(t),!((s.hasChanged??kt)(o,e)||s.useDefault&&s.reflect&&o===this._$Ej?.get(t)&&!this.hasAttribute(a._$Eu(t,s))))return;this.C(t,e,s)}this.isUpdatePending===!1&&(this._$ES=this._$EP())}C(t,e,{useDefault:s,reflect:i,wrapped:o},a){s&&!(this._$Ej??=new Map).has(t)&&(this._$Ej.set(t,a??e??this[t]),o!==!0||a!==void 0)||(this._$AL.has(t)||(this.hasUpdated||s||(e=void 0),this._$AL.set(t,e)),i===!0&&this._$Em!==t&&(this._$Eq??=new Set).add(t))}async _$EP(){this.isUpdatePending=!0;try{await this._$ES}catch(e){Promise.reject(e)}let t=this.scheduleUpdate();return t!=null&&await t,!this.isUpdatePending}scheduleUpdate(){return this.performUpdate()}performUpdate(){if(!this.isUpdatePending)return;if(!this.hasUpdated){if(this.renderRoot??=this.createRenderRoot(),this._$Ep){for(let[i,o]of this._$Ep)this[i]=o;this._$Ep=void 0}let s=this.constructor.elementProperties;if(s.size>0)for(let[i,o]of s){let{wrapped:a}=o,l=this[i];a!==!0||this._$AL.has(i)||l===void 0||this.C(i,void 0,o,l)}}let t=!1,e=this._$AL;try{t=this.shouldUpdate(e),t?(this.willUpdate(e),this._$EO?.forEach(s=>s.hostUpdate?.()),this.update(e)):this._$EM()}catch(s){throw t=!1,this._$EM(),s}t&&this._$AE(e)}willUpdate(t){}_$AE(t){this._$EO?.forEach(e=>e.hostUpdated?.()),this.hasUpdated||(this.hasUpdated=!0,this.firstUpdated(t)),this.updated(t)}_$EM(){this._$AL=new Map,this.isUpdatePending=!1}get updateComplete(){return this.getUpdateComplete()}getUpdateComplete(){return this._$ES}shouldUpdate(t){return!0}update(t){this._$Eq&&=this._$Eq.forEach(e=>this._$ET(e,this[e])),this._$EM()}updated(t){}firstUpdated(t){}};H.elementStyles=[],H.shadowRootOptions={mode:"open"},H[F("elementProperties")]=new Map,H[F("finalized")]=new Map,Vt?.({ReactiveElement:H}),(K.reactiveElementVersions??=[]).push("2.1.2");var pt=globalThis,Et=d=>d,G=pt.trustedTypes,St=G?G.createPolicy("lit-html",{createHTML:d=>d}):void 0,Ot="$lit$",D=`lit$${Math.random().toFixed(9).slice(2)}$`,Tt="?"+D,Zt=`<${Tt}>`,P=document,B=()=>P.createComment(""),V=d=>d===null||typeof d!="object"&&typeof d!="function",ht=Array.isArray,qt=d=>ht(d)||typeof d?.[Symbol.iterator]=="function",at=`[ 	
\f\r]`,W=/<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g,Ct=/-->/g,zt=/>/g,O=RegExp(`>|${at}(?:([^\\s"'>=/]+)(${at}*=${at}*(?:[^ 	
\f\r"'\`<>=]|("|')|))|$)`,"g"),Ht=/'/g,Dt=/"/g,Pt=/^(?:script|style|textarea|title)$/i,ut=d=>(t,...e)=>({_$litType$:d,strings:t,values:e}),c=ut(1),ee=ut(2),se=ut(3),j=Symbol.for("lit-noChange"),u=Symbol.for("lit-nothing"),Mt=new WeakMap,T=P.createTreeWalker(P,129);function jt(d,t){if(!ht(d)||!d.hasOwnProperty("raw"))throw Error("invalid template strings array");return St!==void 0?St.createHTML(t):t}var Jt=(d,t)=>{let e=d.length-1,s=[],i,o=t===2?"<svg>":t===3?"<math>":"",a=W;for(let l=0;l<e;l++){let n=d[l],r,p,h=-1,f=0;for(;f<n.length&&(a.lastIndex=f,p=a.exec(n),p!==null);)f=a.lastIndex,a===W?p[1]==="!--"?a=Ct:p[1]!==void 0?a=zt:p[2]!==void 0?(Pt.test(p[2])&&(i=RegExp("</"+p[2],"g")),a=O):p[3]!==void 0&&(a=O):a===O?p[0]===">"?(a=i??W,h=-1):p[1]===void 0?h=-2:(h=a.lastIndex-p[2].length,r=p[1],a=p[3]===void 0?O:p[3]==='"'?Dt:Ht):a===Dt||a===Ht?a=O:a===Ct||a===zt?a=W:(a=O,i=void 0);let v=a===O&&d[l+1].startsWith("/>")?" ":"";o+=a===W?n+Zt:h>=0?(s.push(r),n.slice(0,h)+Ot+n.slice(h)+D+v):n+D+(h===-2?l:v)}return[jt(d,o+(d[e]||"<?>")+(t===2?"</svg>":t===3?"</math>":"")),s]},Z=class d{constructor({strings:t,_$litType$:e},s){let i;this.parts=[];let o=0,a=0,l=t.length-1,n=this.parts,[r,p]=Jt(t,e);if(this.el=d.createElement(r,s),T.currentNode=this.el.content,e===2||e===3){let h=this.el.content.firstChild;h.replaceWith(...h.childNodes)}for(;(i=T.nextNode())!==null&&n.length<l;){if(i.nodeType===1){if(i.hasAttributes())for(let h of i.getAttributeNames())if(h.endsWith(Ot)){let f=p[a++],v=i.getAttribute(h).split(D),b=/([.?@])?(.*)/.exec(f);n.push({type:1,index:o,name:b[2],strings:v,ctor:b[1]==="."?nt:b[1]==="?"?lt:b[1]==="@"?ct:U}),i.removeAttribute(h)}else h.startsWith(D)&&(n.push({type:6,index:o}),i.removeAttribute(h));if(Pt.test(i.tagName)){let h=i.textContent.split(D),f=h.length-1;if(f>0){i.textContent=G?G.emptyScript:"";for(let v=0;v<f;v++)i.append(h[v],B()),T.nextNode(),n.push({type:2,index:++o});i.append(h[f],B())}}}else if(i.nodeType===8)if(i.data===Tt)n.push({type:2,index:o});else{let h=-1;for(;(h=i.data.indexOf(D,h+1))!==-1;)n.push({type:7,index:o}),h+=D.length-1}o++}}static createElement(t,e){let s=P.createElement("template");return s.innerHTML=t,s}};function I(d,t,e=d,s){if(t===j)return t;let i=s!==void 0?e._$Co?.[s]:e._$Cl,o=V(t)?void 0:t._$litDirective$;return i?.constructor!==o&&(i?._$AO?.(!1),o===void 0?i=void 0:(i=new o(d),i._$AT(d,e,s)),s!==void 0?(e._$Co??=[])[s]=i:e._$Cl=i),i!==void 0&&(t=I(d,i._$AS(d,t.values),i,s)),t}var rt=class{constructor(t,e){this._$AV=[],this._$AN=void 0,this._$AD=t,this._$AM=e}get parentNode(){return this._$AM.parentNode}get _$AU(){return this._$AM._$AU}u(t){let{el:{content:e},parts:s}=this._$AD,i=(t?.creationScope??P).importNode(e,!0);T.currentNode=i;let o=T.nextNode(),a=0,l=0,n=s[0];for(;n!==void 0;){if(a===n.index){let r;n.type===2?r=new q(o,o.nextSibling,this,t):n.type===1?r=new n.ctor(o,n.name,n.strings,this,t):n.type===6&&(r=new dt(o,this,t)),this._$AV.push(r),n=s[++l]}a!==n?.index&&(o=T.nextNode(),a++)}return T.currentNode=P,i}p(t){let e=0;for(let s of this._$AV)s!==void 0&&(s.strings!==void 0?(s._$AI(t,s,e),e+=s.strings.length-2):s._$AI(t[e])),e++}},q=class d{get _$AU(){return this._$AM?._$AU??this._$Cv}constructor(t,e,s,i){this.type=2,this._$AH=u,this._$AN=void 0,this._$AA=t,this._$AB=e,this._$AM=s,this.options=i,this._$Cv=i?.isConnected??!0}get parentNode(){let t=this._$AA.parentNode,e=this._$AM;return e!==void 0&&t?.nodeType===11&&(t=e.parentNode),t}get startNode(){return this._$AA}get endNode(){return this._$AB}_$AI(t,e=this){t=I(this,t,e),V(t)?t===u||t==null||t===""?(this._$AH!==u&&this._$AR(),this._$AH=u):t!==this._$AH&&t!==j&&this._(t):t._$litType$!==void 0?this.$(t):t.nodeType!==void 0?this.T(t):qt(t)?this.k(t):this._(t)}O(t){return this._$AA.parentNode.insertBefore(t,this._$AB)}T(t){this._$AH!==t&&(this._$AR(),this._$AH=this.O(t))}_(t){this._$AH!==u&&V(this._$AH)?this._$AA.nextSibling.data=t:this.T(P.createTextNode(t)),this._$AH=t}$(t){let{values:e,_$litType$:s}=t,i=typeof s=="number"?this._$AC(t):(s.el===void 0&&(s.el=Z.createElement(jt(s.h,s.h[0]),this.options)),s);if(this._$AH?._$AD===i)this._$AH.p(e);else{let o=new rt(i,this),a=o.u(this.options);o.p(e),this.T(a),this._$AH=o}}_$AC(t){let e=Mt.get(t.strings);return e===void 0&&Mt.set(t.strings,e=new Z(t)),e}k(t){ht(this._$AH)||(this._$AH=[],this._$AR());let e=this._$AH,s,i=0;for(let o of t)i===e.length?e.push(s=new d(this.O(B()),this.O(B()),this,this.options)):s=e[i],s._$AI(o),i++;i<e.length&&(this._$AR(s&&s._$AB.nextSibling,i),e.length=i)}_$AR(t=this._$AA.nextSibling,e){for(this._$AP?.(!1,!0,e);t!==this._$AB;){let s=Et(t).nextSibling;Et(t).remove(),t=s}}setConnected(t){this._$AM===void 0&&(this._$Cv=t,this._$AP?.(t))}},U=class{get tagName(){return this.element.tagName}get _$AU(){return this._$AM._$AU}constructor(t,e,s,i,o){this.type=1,this._$AH=u,this._$AN=void 0,this.element=t,this.name=e,this._$AM=i,this.options=o,s.length>2||s[0]!==""||s[1]!==""?(this._$AH=Array(s.length-1).fill(new String),this.strings=s):this._$AH=u}_$AI(t,e=this,s,i){let o=this.strings,a=!1;if(o===void 0)t=I(this,t,e,0),a=!V(t)||t!==this._$AH&&t!==j,a&&(this._$AH=t);else{let l=t,n,r;for(t=o[0],n=0;n<o.length-1;n++)r=I(this,l[s+n],e,n),r===j&&(r=this._$AH[n]),a||=!V(r)||r!==this._$AH[n],r===u?t=u:t!==u&&(t+=(r??"")+o[n+1]),this._$AH[n]=r}a&&!i&&this.j(t)}j(t){t===u?this.element.removeAttribute(this.name):this.element.setAttribute(this.name,t??"")}},nt=class extends U{constructor(){super(...arguments),this.type=3}j(t){this.element[this.name]=t===u?void 0:t}},lt=class extends U{constructor(){super(...arguments),this.type=4}j(t){this.element.toggleAttribute(this.name,!!t&&t!==u)}},ct=class extends U{constructor(t,e,s,i,o){super(t,e,s,i,o),this.type=5}_$AI(t,e=this){if((t=I(this,t,e,0)??u)===j)return;let s=this._$AH,i=t===u&&s!==u||t.capture!==s.capture||t.once!==s.once||t.passive!==s.passive,o=t!==u&&(s===u||i);i&&this.element.removeEventListener(this.name,this,s),o&&this.element.addEventListener(this.name,this,t),this._$AH=t}handleEvent(t){typeof this._$AH=="function"?this._$AH.call(this.options?.host??this.element,t):this._$AH.handleEvent(t)}},dt=class{constructor(t,e,s){this.element=t,this.type=6,this._$AN=void 0,this._$AM=e,this.options=s}get _$AU(){return this._$AM._$AU}_$AI(t){I(this,t)}};var Yt=pt.litHtmlPolyfillSupport;Yt?.(Z,q),(pt.litHtmlVersions??=[]).push("3.3.2");var Nt=(d,t,e)=>{let s=e?.renderBefore??t,i=s._$litPart$;if(i===void 0){let o=e?.renderBefore??null;s._$litPart$=i=new q(t.insertBefore(B(),o),o,void 0,e??{})}return i._$AI(d),i};var mt=globalThis,M=class extends H{constructor(){super(...arguments),this.renderOptions={host:this},this._$Do=void 0}createRenderRoot(){let t=super.createRenderRoot();return this.renderOptions.renderBefore??=t.firstChild,t}update(t){let e=this.render();this.hasUpdated||(this.renderOptions.isConnected=this.isConnected),super.update(t),this._$Do=Nt(e,this.renderRoot,this.renderOptions)}connectedCallback(){super.connectedCallback(),this._$Do?.setConnected(!0)}disconnectedCallback(){super.disconnectedCallback(),this._$Do?.setConnected(!1)}render(){return j}};M._$litElement$=!0,M.finalized=!0,mt.litElementHydrateSupport?.({LitElement:M});var Kt=mt.litElementPolyfillSupport;Kt?.({LitElement:M});(mt.litElementVersions??=[]).push("4.2.2");var Q="1.0.81",A=["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"],R=[6,0,1,2,3,4,5],S=["home","away","sleep","wake"],X=["home","away","sleep","wake","manual"],tt=["off","low","med","high"],N=[{v:"60",l:"1 hour"},{v:"120",l:"2 hours"},{v:"240",l:"4 hours"},{v:"forever",l:"Indefinite"},{v:"custom",l:"Custom time\u2026"}],C=["\u2460","\u2461","\u2462","\u2463","\u2464","\u2465","\u2466","\u2467"],et=(()=>{let d=[];for(let t=0;t<24;t++)for(let e=0;e<60;e+=15){let s=`${String(t).padStart(2,"0")}:${String(e).padStart(2,"0")}`,i=t===0?`12:${String(e).padStart(2,"0")} AM`:t<12?`${t}:${String(e).padStart(2,"0")} AM`:t===12?`12:${String(e).padStart(2,"0")} PM`:`${t-12}:${String(e).padStart(2,"0")} PM`;d.push({v:s,l:i})}return d})(),$=class extends M{static get baseProperties(){return{hass:{attribute:!1},_config:{state:!0},_registryLoaded:{state:!0}}}constructor(){super(),this._config={},this._registryEntities=null,this._registryLoaded=!1}setConfig(t){this._config=t}shouldUpdate(t){if(!t.has("hass")||!this._registryLoaded)return!0;let e=t.get("hass");return e?(this._registryEntities||[]).some(i=>this.hass.states[i.entity_id]!==e.states[i.entity_id]):!0}updated(t){t.has("hass")&&this.hass&&!this._registryLoaded&&this._loadRegistry()}async _loadRegistry(){try{let t=await this.hass.connection.sendMessagePromise({type:"config/entity_registry/list"});this._registryEntities=Array.isArray(t)?t.filter(e=>e.platform==="infinitude_direct"):[]}catch(t){console.warn("Failed to load entity registry",t),this._registryEntities=[]}this._registryLoaded=!0}_findEntities(){if(!this.hass)return{climates:[],sensors:{},selects:{},system:{}};let t=this._registryEntities||[],e=this.hass.states,s=[],i={damper:{},fan:{}},o={},a={};if(this._config.climate_entities)for(let l of this._config.climate_entities)e[l]&&s.push(l);for(let l of t){let n=l.entity_id;if(!e[n])continue;let r=n.split(".")[0],p=l.unique_id||"";r==="climate"?this._config.climate_entities||s.push(n):r==="select"?o.wholeHouse=n:r==="sensor"&&(p.includes("damper")?i.damper[n]=e[n]:p.includes("fan")?i.fan[n]=e[n]:p.includes("humidifier")?a.humidifier=n:p.includes("oat")?a.oat=n:p.includes("op_status")?a.opStatus=n:p.includes("system_info")&&(a.info=n))}return s.sort(),{climates:s,sensors:i,selects:o,system:a}}_st(t){return t?this.hass?.states[t]??null:null}_at(t,e){return this._st(t)?.attributes?.[e]}_getScheduleData(){let{system:t}=this._findEntities();if(!t.info)return{};try{return JSON.parse(this._at(t.info,"schedule")||"{}")}catch(e){return console.warn("Failed to parse schedule data",e),{}}}_getProfilesData(){let{system:t}=this._findEntities();if(!t.info)return[];try{return JSON.parse(this._at(t.info,"profiles")||"[]")}catch(e){return console.warn("Failed to parse profiles data",e),[]}}async _svc(t,e,s){try{await this.hass.callService(t,e,s)}catch(i){console.error(`${t}.${e} failed`,i)}}_setHvacMode(t,e){this._svc("climate","set_hvac_mode",{entity_id:t,hvac_mode:e})}_setPreset(t,e){this._svc("climate","set_preset_mode",{entity_id:t,preset_mode:e})}_resolveUntil(t,e){if(t==="forever")return"forever";if(t==="custom")return e||null;let s=new Date;s.setMinutes(s.getMinutes()+parseInt(t));let i=Math.round(s.getMinutes()/15)*15;return s.setMinutes(i,0,0),i===60&&(s.setMinutes(0),s.setHours(s.getHours()+1)),`${String(s.getHours()).padStart(2,"0")}:${String(s.getMinutes()).padStart(2,"0")}`}_otmrRelative(t){if(!t)return"";let[e,s]=t.split(":").map(Number),i=new Date;return i.setHours(e,s,0,0),"until "+i.toLocaleTimeString([],{hour:"numeric",minute:"2-digit"})}_zoneId(t){let e=(this._registryEntities||[]).find(s=>s.entity_id===t);return e?(e.unique_id||"").replace(/^infinitude_/,""):""}_renderLoading(){return c`<ha-card>
      <div style="padding:24px;text-align:center;color:var(--secondary-text-color)">Loading…</div>
    </ha-card>`}},z=E`
  :host { display: block; }
  ha-card { overflow: hidden; }
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
`;var ft=class extends ${static properties={...$.baseProperties,_whHoldOpen:{state:!0},_whHoldActivity:{state:!0},_whHoldDuration:{state:!0},_whHoldCustom:{state:!0}};constructor(){super(),this._whHoldOpen=!1,this._whHoldActivity="home",this._whHoldDuration="120",this._whHoldCustom=""}static getConfigElement(){return document.createElement("div")}static getStubConfig(){return{}}getCardSize(){return 3}static styles=[z,E`
    .card-pad { padding: 16px; }
    .header {
      display: flex; align-items: center; gap: 8px; margin-bottom: 14px;
    }
    .header-title { font-size: 18px; font-weight: 500; color: var(--primary-text-color); }
  `];render(){if(!this.hass)return u;if(!this._registryLoaded)return this._renderLoading();let t=this._findEntities(),{system:e,selects:s,climates:i}=t,o=i.length&&this._st(i[0])?.state||"off",a=["off","heat","cool","heat_cool"],l={off:"Off",heat:"Heat",cool:"Cool",heat_cool:"Auto"},n=this._st(e.oat),r="\u2013";if(n?.state&&n.state!=="unavailable")r=`${Math.round(Number(n.state))}\xB0`;else if(i.length){let g=this._at(i[0],"outdoor_temperature");g!=null&&(r=`${Math.round(Number(g))}\xB0`)}let p=this._st(e.opStatus),h=p?.state&&p.state!=="unavailable"?p.state:"",f=this._st(e.humidifier)?.state==="on",v=this._st(s.wholeHouse),b=v&&v.state!=="off",k=i.length?this._at(i[0],"whole_house_hold_until"):null,y=i.length?this._at(i[0],"current_humidity"):null,_=e.info?this._st(e.info)?.state!=="unavailable":!1,w=e.info?this._at(e.info,"carrier_ok"):null;return c`
      <ha-card>
        <div class="card-pad">
          <div class="header">
            <span class="header-title">infinitude</span>
            <span class="conn-dot ${_?"ok":"err"}" title="${_?"Infinitude: connected":"Infinitude: unavailable"}"></span>
            <span class="conn-dot ${w===!0?"ok":w===!1?"err":"unk"}" title="${w===!0?"Carrier cloud: connected":w===!1?"Carrier cloud: unreachable":"Carrier cloud: checking\u2026"}"></span>
            <span style="font-size:10px;color:var(--secondary-text-color);opacity:0.5">v${Q}</span>
          </div>
          <div class="mode-row">
            <span class="mode-label">Mode</span>
            <div class="mode-pills">
              ${a.map(g=>c`<div class="mode-pill ${g===o?"active":""} ${g==="heat"?"heat":g==="cool"?"cool":g==="heat_cool"?"auto":""}"
                  @click=${()=>this._setHvacMode(i[0],g)}>${l[g]}</div>`)}
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
              <span class="summary-stat-val">${r}</span>
            </div>
            <div class="summary-divider"></div>
            <div class="summary-stat">
              <span class="summary-stat-label">Humidity</span>
              <span class="summary-stat-val">${y!=null?`${y}%`:"\u2013"}</span>
            </div>
            ${f?c`
              <div class="summary-divider"></div>
              <div class="summary-stat">
                <span class="summary-stat-label">Humidifier</span>
                <span class="summary-stat-val" style="color:var(--label-badge-blue,#38bdf8)">💧 On</span>
              </div>`:u}
          </div>
          ${b?c`
            <div class="wh-hold" @click=${()=>this._cancelWholeHouseHold()}>
              <ha-icon icon="mdi:home-lock" style="--mdc-icon-size:16px"></ha-icon>
              <span>Whole house: <strong>${v.state}</strong>${k?c` · <span style="opacity:0.85">${this._otmrRelative(k)}</span>`:u}</span>
              <span style="margin-left:auto;opacity:0.7">Tap to cancel</span>
            </div>`:c`
            ${this._whHoldOpen?c`
              <div class="wh-set">
                <span class="wh-set-label">WH Hold</span>
                <div class="wh-pills">
                  ${S.map(g=>c`
                    <div class="wh-pill ${this._whHoldActivity===g?"active":""}"
                         @click=${()=>{this._whHoldActivity=g}}>${g}</div>`)}
                </div>
                <select class="hold-dur-select" @change=${g=>{this._whHoldDuration=g.target.value}}>
                  ${N.map(g=>c`<option value=${g.v} ?selected=${g.v===this._whHoldDuration}>${g.l}</option>`)}
                </select>
                ${this._whHoldDuration==="custom"?c`
                  <input type="time" class="hold-time-input" step="900" .value=${this._whHoldCustom}
                         @change=${g=>{this._whHoldCustom=g.target.value}}>`:u}
                <button class="btn btn-primary" style="font-size:11px;padding:4px 12px" @click=${()=>this._setWholeHouseHold()}>Apply</button>
                <button class="btn" style="font-size:11px;padding:4px 10px" @click=${()=>{this._whHoldOpen=!1}}>Cancel</button>
              </div>`:c`
              <div>
                <button class="btn" style="font-size:11px;padding:4px 12px" @click=${()=>{this._whHoldOpen=!0}}>
                  <ha-icon icon="mdi:home-lock" style="--mdc-icon-size:14px;vertical-align:middle;margin-right:4px"></ha-icon>Set WH hold
                </button>
              </div>`}
          `}
        </div>
      </ha-card>`}_setWholeHouseHold(){let t=this._resolveUntil(this._whHoldDuration,this._whHoldCustom);t!==null&&(this._svc("infinitude_direct","set_whole_house_hold",{activity:this._whHoldActivity,...t!==void 0&&{until:t}}),this._whHoldOpen=!1)}_cancelWholeHouseHold(){this._svc("infinitude_direct","cancel_whole_house_hold",{})}};customElements.get("infinitude-status-card")||customElements.define("infinitude-status-card",ft);window.customCards=window.customCards||[];window.customCards.some(d=>d.type==="infinitude-status-card")||window.customCards.push({type:"infinitude-status-card",name:"Infinitude Status",description:"System mode, stats, and whole-house hold for Carrier/Bryant Infinity",preview:!1});var vt=class extends ${static properties={...$.baseProperties,_pendingTemps:{state:!0},_holdOpen:{state:!0},_holdActivity:{state:!0},_holdDuration:{state:!0},_holdCustom:{state:!0},_holdHtsp:{state:!0},_holdClsp:{state:!0},_holdFan:{state:!0}};constructor(){super(),this._pendingTemps={},this._tempAdj={},this._holdOpen=!1,this._holdActivity="home",this._holdDuration="120",this._holdCustom="",this._holdHtsp=68,this._holdClsp=76,this._holdFan="auto"}static getConfigElement(){return document.createElement("div")}static getStubConfig(){return{entity:""}}getCardSize(){return 4}static styles=[z,E`
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
  `];render(){if(!this.hass)return u;if(!this._registryLoaded)return this._renderLoading();let t=this._config.entity;if(!t)return c`<ha-card><div class="card-pad" style="color:var(--secondary-text-color)">No entity configured</div></ha-card>`;let e=this._st(t);if(!e)return c`<ha-card><div class="card-pad" style="color:var(--secondary-text-color)">Entity unavailable</div></ha-card>`;let s=e.attributes||{},i=(s.friendly_name||t).replace(/^Infinitude\s+/i,"").replace(/^infinitude_direct\s+/i,""),o=s.current_temperature!=null?Math.round(s.current_temperature):"\u2013",a=s.current_humidity,l=e.state||"off",n=s.hvac_action||"idle",r=s.preset_mode||"\u2013",p=n==="heating"?"heating":n==="cooling"?"cooling":n==="drying"?"drying":"",h=n==="idle"?"Idle":n.charAt(0).toUpperCase()+n.slice(1),f=l==="heat_cool",v=!!s.hold_active,b=s.hold_activity||r,k=s.hold_until,y=this._pendingTemps[t],_=this._hasPending(t),w=y?.heat??s.target_temp_low??s.temperature??null,g=y?.cool??s.target_temp_high??(l==="cool"?s.temperature:null)??null;return c`
      <ha-card class="${p}">
        <div class="card-pad">
          <div class="zone-top">
            <span class="zone-name">${i}</span>
            <span class="zone-badge ${p}">${h}</span>
          </div>
          <div class="zone-body">
            <div>
              <span class="temp-hero">${o}</span><span class="temp-unit">°F</span>
              ${a!=null?c`<div style="font-size:11px;color:var(--secondary-text-color);margin-top:2px">${a}% RH</div>`:u}
            </div>
            <div class="zone-sp">
              ${w!=null?c`
                <div class="sp-row">
                  <button class="btn-adj" @click=${()=>this._adjustTemp(t,-1,"heat")}>−</button>
                  <span class="sp-val sp-heat ${_?"sp-pending":""}">${Math.round(w)}°</span>
                  <button class="btn-adj" @click=${()=>this._adjustTemp(t,1,"heat")}>+</button>
                </div>`:u}
              ${f&&g!=null?c`
                <div class="sp-row">
                  <button class="btn-adj" @click=${()=>this._adjustTemp(t,-1,"cool")}>−</button>
                  <span class="sp-val sp-cool ${_?"sp-pending":""}">${Math.round(g)}°</span>
                  <button class="btn-adj" @click=${()=>this._adjustTemp(t,1,"cool")}>+</button>
                </div>`:u}
            </div>
          </div>
          <div class="zone-meta">
            <span class="meta-item">Activity <span class="meta-val">${r}</span></span>
            ${s.fan_mode?c`<span class="meta-item">Fan <span class="meta-val">${s.fan_mode}</span></span>`:u}
            ${s.damper_position!=null?c`<span class="meta-item">Damper <span class="meta-val">${s.damper_position}%</span></span>`:u}
          </div>
          <div class="zone-preset-row">
            ${S.map(m=>c`
              <div class="preset-btn ${r===m?"active":""}"
                   @click=${()=>this._setPreset(t,m)}>${m}</div>`)}
          </div>
          ${v?c`
            <div class="zone-hold">
              <span class="hold-label">Hold: ${b}${k?` \xB7 ${this._otmrRelative(k)}`:""}</span>
              <button class="btn" style="font-size:11px;padding:3px 10px;color:var(--error-color,#f87171)" @click=${()=>this._cancelHold(t)}>Cancel</button>
            </div>`:u}
          ${this._holdOpen?c`
            <div class="zone-hold-picker">
              <div class="hold-picker-row">
                <div class="wh-pills">
                  ${X.map(m=>c`
                    <div class="wh-pill ${this._holdActivity===m?"active":""}"
                         @click=${()=>{this._holdActivity=m,m==="manual"&&this._initHoldManual(t)}}>${m}</div>`)}
                </div>
              </div>
              ${this._holdActivity==="manual"?c`
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
                    <select class="hold-dur-select" style="width:auto" .value=${this._holdFan} @change=${m=>{this._holdFan=m.target.value}}>
                      <option value="auto">Auto</option>
                      <option value="low">Low</option>
                      <option value="med">Med</option>
                      <option value="high">High</option>
                    </select>
                  </div>
                </div>`:u}
              <div class="hold-picker-row">
                <select class="hold-dur-select" @change=${m=>{this._holdDuration=m.target.value}}>
                  ${N.map(m=>c`<option value=${m.v} ?selected=${m.v===this._holdDuration}>${m.l}</option>`)}
                </select>
                ${this._holdDuration==="custom"?c`
                  <input type="time" class="hold-time-input" step="900" .value=${this._holdCustom}
                         @change=${m=>{this._holdCustom=m.target.value}}>`:u}
              </div>
              <div class="hold-picker-row">
                <button class="btn btn-primary" style="font-size:11px;padding:4px 12px" @click=${()=>this._setZoneHold(t)}>Apply</button>
                <button class="btn" style="font-size:11px;padding:4px 10px" @click=${()=>{this._holdOpen=!1}}>Cancel</button>
              </div>
            </div>`:v?u:c`
            <div class="zone-actions">
              <button class="btn" style="font-size:11px;padding:4px 12px" @click=${()=>{this._holdActivity=r!=="\u2013"?r:"home",this._holdDuration="120",this._holdCustom="",this._holdActivity==="manual"&&this._initHoldManual(t),this._holdOpen=!0}}>Set hold</button>
            </div>`}
        </div>
      </ha-card>`}_adjustTemp(t,e,s){let i=this._st(t);if(!i)return;let o=i.attributes||{},a=this._tempAdj[t]||(this._tempAdj[t]={}),l=a.heat??o.target_temp_low??o.temperature??68,n=a.cool??o.target_temp_high??(i.state==="cool"?o.temperature:null)??76;s==="heat"?a.heat=Math.max(50,Math.min(90,Math.round(l)+e)):a.cool=Math.max(60,Math.min(99,Math.round(n)+e)),this._pendingTemps={...this._pendingTemps,[t]:{heat:a.heat,cool:a.cool}},a.committing||(clearTimeout(a.timer),a.timer=setTimeout(()=>this._commitAdj(t),800))}async _commitAdj(t){let e=this._tempAdj[t];if(!e||e.committing)return;e.committing=!0;let s=this._st(t),i=s?.attributes||{},o=e.heat,a=e.cool,l=o??Math.round(i.target_temp_low??i.temperature??68),n=a??Math.round(i.target_temp_high??(s?.state==="cool"?i.temperature:null)??76),r=s?.state||"off",p={entity_id:t};r==="heat_cool"?(p.target_temp_low=l,p.target_temp_high=n):r==="heat"?p.temperature=l:r==="cool"?p.temperature=n:(p.target_temp_low=l,p.target_temp_high=n);try{await this.hass.callService("climate","set_temperature",p)}catch(h){console.error("set_temperature failed",h)}if(e.committing=!1,e.heat!==o||e.cool!==a){e.timer=setTimeout(()=>this._commitAdj(t),400);return}e.heat=null,e.cool=null,e.timer=null,e.graceUntil=Date.now()+3e4,setTimeout(()=>{if(!this._tempAdj[t]?.heat&&!this._tempAdj[t]?.cool){let{[t]:h,...f}=this._pendingTemps;this._pendingTemps=f}},2e3)}_hasPending(t){let e=this._tempAdj[t];return e&&(e.heat!=null||e.cool!=null||e.committing)}_cancelHold(t){let e=this._zoneId(t);e&&this._svc("infinitude_direct","cancel_hold",{zone_id:e})}_setZoneHold(t){let e=this._zoneId(t);if(!e)return;let s=this._resolveUntil(this._holdDuration,this._holdCustom);s!==null&&(this._holdActivity==="manual"&&this._svc("infinitude_direct","set_profile",{zone_id:e,activity:"manual",htsp:this._holdHtsp,clsp:this._holdClsp,fan:this._holdFan}),this._svc("infinitude_direct","set_hold",{zone_id:e,activity:this._holdActivity,...s!==void 0&&{until:s}}),this._holdOpen=!1)}_initHoldManual(t){let e=this._zoneId(t),s=this._getProfilesData().find(i=>i.id===e)?.activities?.manual||{};this._holdHtsp=s.htsp?Math.round(Number(s.htsp)||68):68,this._holdClsp=s.clsp?Math.round(Number(s.clsp)||76):76,this._holdFan=s.fan||"auto"}};customElements.get("infinitude-zone-card")||customElements.define("infinitude-zone-card",vt);window.customCards=window.customCards||[];window.customCards.some(d=>d.type==="infinitude-zone-card")||window.customCards.push({type:"infinitude-zone-card",name:"Infinitude Zone",description:"Single zone control for Carrier/Bryant Infinity thermostat",preview:!1});var _t=class extends ${static properties={...$.baseProperties,_schedDay:{state:!0},_schedEdits:{state:!0}};constructor(){super(),this._schedDay=A[R[new Date().getDay()]],this._schedEdits={}}static getConfigElement(){return document.createElement("div")}static getStubConfig(){return{}}getCardSize(){return 6}static styles=[z,E`
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
  `];render(){if(!this.hass)return u;if(!this._registryLoaded)return this._renderLoading();let t=this._getScheduleData(),e=this._getProfilesData(),s=Object.keys(t);if(!s.length)return c`<ha-card>
      <div class="card-pad" style="text-align:center;color:var(--secondary-text-color)">
        <ha-icon icon="mdi:calendar-clock" style="--mdc-icon-size:48px;opacity:0.3;margin-bottom:12px;display:block"></ha-icon>
        No schedule data available.
      </div></ha-card>`;let i=A[R[new Date().getDay()]],o={},a={};for(let r=0;r<e.length;r++)o[e[r].id]=e[r].name,a[e[r].id]=r;let l=0;for(let r of s)l=Math.max(l,(t[r]?.[this._schedDay]||[]).length);l||(l=5);let n=Object.keys(this._schedEdits).length>0;return c`
      <ha-card>
        <div class="card-pad">
          <div class="section-title">Schedule</div>
          ${s.length>1?c`<div class="zone-legend">${s.map((r,p)=>c`<span class="legend-item"><span class="legend-num">${C[p]||p+1}</span> ${o[r]||`Zone ${r}`}</span>`)}</div>`:u}
          <div class="sched-day-tabs">
            ${A.map(r=>c`
              <div class="day-tab ${r===this._schedDay?"active":""} ${r===i&&r!==this._schedDay?"today":""}"
                   @click=${()=>{this._schedDay=r}}>${r.slice(0,3)}</div>`)}
          </div>
          ${Array.from({length:l},(r,p)=>this._periodCard(p,s,t,e,o,a))}
          <div class="copy-bar">
            <span>Copy ${this._schedDay.slice(0,3)} →</span>
            <select class="sched-select" @change=${r=>this._copySched(r)}>
              <option value="">select day…</option>
              ${A.filter(r=>r!==this._schedDay).map(r=>c`<option value=${r}>${r.slice(0,3)}</option>`)}
              <option value="__all__">All other days</option>
            </select>
          </div>
          ${n?c`
            <div class="action-bar">
              <span class="action-bar-label">● Unsaved changes</span>
              <button class="btn" @click=${()=>{this._schedEdits={}}}>Discard</button>
              <button class="btn btn-primary" @click=${()=>this._saveSched()}>Save schedule</button>
            </div>`:u}
        </div>
      </ha-card>`}_periodCard(t,e,s,i,o,a){let l=e.length>1;return c`
      <div class="period-card">
        <div class="period-header">Period ${t+1}</div>
        ${e.map(n=>{let r=(s[n]?.[this._schedDay]||[])[t];if(!r)return u;let p=`${n}_${this._schedDay}_${t}`,h=this._schedEdits[p],f=h?.act??r.activity,v=h?.time??r.time,b=h?.enabled??r.enabled,y=i.find(m=>m.id===n)?.activities?.[f],_=y?.htsp?Math.round(Number(y.htsp)||0):"\u2013",w=y?.clsp?Math.round(Number(y.clsp)||0):"\u2013",g=l?C[a[n]]??n:o[n]||`Zone ${n}`;return c`
            <div class="sched-line ${b?"":"disabled"}">
              <span class="sched-name ${l?"sched-name-compact":""}">${g}</span>
              <select class="sched-select" .value=${f} @change=${m=>this._schedEdit(n,t,"act",m.target.value)}>
                ${S.map(m=>c`<option value=${m} ?selected=${m===f}>${m}</option>`)}
              </select>
              <select class="sched-select" .value=${v} @change=${m=>this._schedEdit(n,t,"time",m.target.value)}>
                ${et.map(m=>c`<option value=${m.v} ?selected=${m.v===v}>${m.l}</option>`)}
              </select>
              <label class="sched-toggle">
                <input type="checkbox" .checked=${b}
                       @change=${m=>this._schedEdit(n,t,"enabled",m.target.checked)}>
                <span>on</span>
              </label>
              <div class="sched-temps">
                <span class="sp-heat">${_}°</span>
                <span class="sp-cool">${w}°</span>
              </div>
            </div>`})}
      </div>`}_schedEdit(t,e,s,i){let o=`${t}_${this._schedDay}_${e}`,a=this._schedEdits[o]||{},l=(this._getScheduleData()[t]?.[this._schedDay]||[])[e]||{};this._schedEdits={...this._schedEdits,[o]:{act:s==="act"?i:a.act??l.activity,time:s==="time"?i:a.time??l.time,enabled:s==="enabled"?i:a.enabled??l.enabled}}}_copySched(t){let e=t.target.value;if(!e)return;t.target.value="";let s=this._getScheduleData(),i=e==="__all__"?A.filter(a=>a!==this._schedDay):[e],o={...this._schedEdits};for(let a of Object.keys(s)){let l=s[a]?.[this._schedDay]||[];for(let n of i)l.forEach((r,p)=>{let h=this._schedEdits[`${a}_${this._schedDay}_${p}`];o[`${a}_${n}_${p}`]={act:h?.act??r.activity,time:h?.time??r.time,enabled:h?.enabled??r.enabled}})}this._schedEdits=o}async _saveSched(){if(this._saving)return;this._saving=!0;let t={...this._schedEdits};try{let e=this._getScheduleData();for(let s of Object.keys(e)){let i=A.map(o=>({id:o,period:(e[s]?.[o]||[]).map((a,l)=>{let n=t[`${s}_${o}_${l}`];return{id:a.id||String(l+1),activity:n?.act??a.activity,time:n?.time??a.time,enabled:n?.enabled??a.enabled?"on":"off"}})}));await this._svc("infinitude_direct","save_schedule",{zone_id:s,schedule:JSON.stringify(i)})}}finally{setTimeout(()=>{let e=this._schedEdits,s={};for(let i of Object.keys(e))(!(i in t)||e[i]!==t[i])&&(s[i]=e[i]);this._schedEdits=s,this._saving=!1},500)}}};customElements.get("infinitude-schedule-card")||customElements.define("infinitude-schedule-card",_t);window.customCards=window.customCards||[];window.customCards.some(d=>d.type==="infinitude-schedule-card")||window.customCards.push({type:"infinitude-schedule-card",name:"Infinitude Schedule",description:"Weekly schedule editing for Carrier/Bryant Infinity thermostat",preview:!1});var gt=class extends ${static properties={...$.baseProperties,_profileEdits:{state:!0}};constructor(){super(),this._profileEdits={}}static getConfigElement(){return document.createElement("div")}static getStubConfig(){return{}}getCardSize(){return 6}static styles=[z,E`
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
  `];render(){if(!this.hass)return u;if(!this._registryLoaded)return this._renderLoading();let t=this._getProfilesData();if(!t.length)return c`<ha-card>
      <div class="card-pad" style="text-align:center;color:var(--secondary-text-color)">
        <ha-icon icon="mdi:tune-vertical" style="--mdc-icon-size:48px;opacity:0.3;margin-bottom:12px;display:block"></ha-icon>
        No profile data available.
      </div></ha-card>`;let e=t.length>1,s=Object.keys(this._profileEdits).length>0;return c`
      <ha-card>
        <div class="card-pad">
          <div class="section-title">Comfort Profiles</div>
          ${e?c`<div class="zone-legend">${t.map((i,o)=>c`<span class="legend-item"><span class="legend-num">${C[o]||o+1}</span> ${i.name}</span>`)}</div>`:u}
          ${S.map(i=>c`
            <div class="prof-card">
              <div class="prof-header">${i}</div>
              ${t.map((o,a)=>{let l=o.activities?.[i]||{},n=`${o.id}_${i}`,r=this._profileEdits[n],p=r?.htsp??(l.htsp?Math.round(Number(l.htsp)||68):68),h=r?.clsp??(l.clsp?Math.round(Number(l.clsp)||76):76),f=r?.fan??l.fan??"low",v=e?C[a]||a+1:o.name;return c`
                  <div class="prof-line">
                    <span class="prof-name ${e?"prof-name-compact":""}">${v}</span>
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
                      <select class="sched-select" .value=${f} @change=${b=>this._profFan(o.id,i,b.target.value)}>
                        ${tt.map(b=>c`<option value=${b} ?selected=${b===f}>${b}</option>`)}
                      </select>
                    </div>
                  </div>`})}
            </div>`)}
          ${s?c`
            <div class="action-bar">
              <span class="action-bar-label">● Unsaved changes</span>
              <button class="btn" @click=${()=>{this._profileEdits={}}}>Discard</button>
              <button class="btn btn-primary" @click=${()=>this._saveProfs()}>Save profiles</button>
            </div>`:u}
        </div>
      </ha-card>`}_profAdj(t,e,s,i){let o=`${t}_${e}`,a=this._getProfilesData().find(v=>v.id===t)?.activities?.[e]||{},l=this._profileEdits[o]||{},n=l.htsp??(a.htsp?Math.round(Number(a.htsp)||68):68),r=l.clsp??(a.clsp?Math.round(Number(a.clsp)||76):76),p=s==="htsp"?50:60,h=s==="htsp"?90:99,f=s==="htsp"?n:r;this._profileEdits={...this._profileEdits,[o]:{zone_id:t,activity:e,htsp:s==="htsp"?Math.max(p,Math.min(h,f+i)):n,clsp:s==="clsp"?Math.max(p,Math.min(h,f+i)):r,fan:l.fan??a.fan??"low"}}}_profFan(t,e,s){let i=`${t}_${e}`,o=this._getProfilesData().find(l=>l.id===t)?.activities?.[e]||{},a=this._profileEdits[i]||{};this._profileEdits={...this._profileEdits,[i]:{zone_id:t,activity:e,htsp:a.htsp??(o.htsp?Math.round(Number(o.htsp)||68):68),clsp:a.clsp??(o.clsp?Math.round(Number(o.clsp)||76):76),fan:s}}}async _saveProfs(){if(this._savingProfs)return;this._savingProfs=!0;let t={...this._profileEdits};try{for(let e of Object.values(t)){let s={zone_id:e.zone_id,activity:e.activity,htsp:e.htsp,clsp:e.clsp};e.fan&&(s.fan=e.fan),await this._svc("infinitude_direct","set_profile",s)}}finally{setTimeout(()=>{let e=this._profileEdits,s={};for(let i of Object.keys(e))(!(i in t)||e[i]!==t[i])&&(s[i]=e[i]);this._profileEdits=s,this._savingProfs=!1},500)}}};customElements.get("infinitude-profiles-card")||customElements.define("infinitude-profiles-card",gt);window.customCards=window.customCards||[];window.customCards.some(d=>d.type==="infinitude-profiles-card")||window.customCards.push({type:"infinitude-profiles-card",name:"Infinitude Profiles",description:"Comfort profile editing for Carrier/Bryant Infinity thermostat",preview:!1});var bt=class extends ${static properties={...$.baseProperties,_tab:{state:!0},_schedDay:{state:!0},_schedEdits:{state:!0},_profileEdits:{state:!0},_pendingTemps:{state:!0},_whHoldOpen:{state:!0},_whHoldActivity:{state:!0},_whHoldDuration:{state:!0},_whHoldCustom:{state:!0},_holdOpen:{state:!0},_holdActivity:{state:!0},_holdDuration:{state:!0},_holdCustom:{state:!0},_holdHtsp:{state:!0},_holdClsp:{state:!0},_holdFan:{state:!0}};constructor(){super(),this._tab="status",this._schedDay=A[R[new Date().getDay()]],this._schedEdits={},this._profileEdits={},this._tempAdj={},this._pendingTemps={},this._whHoldOpen=!1,this._whHoldActivity="home",this._whHoldDuration="120",this._whHoldCustom="",this._holdOpen=null,this._holdActivity="home",this._holdDuration="120",this._holdCustom="",this._holdHtsp=68,this._holdClsp=76,this._holdFan="auto"}static getConfigElement(){return document.createElement("div")}static getStubConfig(){return{}}getCardSize(){return 8}static styles=[z,E`
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
  `];render(){if(!this.hass)return u;if(!this._registryLoaded)return c`<ha-card>
        <div style="padding:24px;text-align:center;color:var(--secondary-text-color)">Loading…</div>
      </ha-card>`;let t=this._findEntities();return!t.climates.length&&!this._config.show_empty?c`<ha-card>
        <div style="padding:24px;text-align:center;color:var(--secondary-text-color)">
          <ha-icon icon="mdi:thermostat" style="--mdc-icon-size:48px;opacity:0.3;margin-bottom:12px;display:block"></ha-icon>
          <div style="font-size:14px;font-weight:500">No Infinitude entities found</div>
          <div style="font-size:12px;margin-top:4px">Waiting for thermostat connection…</div>
        </div>
      </ha-card>`:c`
      <ha-card>
        <div class="card-header">${this._hdr(t)}</div>
        <div class="card-tabs">${this._tabs()}</div>
        <div class="card-content">
          ${this._tab==="status"?this._status(t):u}
          ${this._tab==="schedule"?this._sched():u}
          ${this._tab==="profiles"?this._profs():u}
        </div>
      </ha-card>`}_hdr(t){let{system:e}=t,s=e.info?this._st(e.info)?.state!=="unavailable":!1,i=e.info?this._at(e.info,"carrier_ok"):null;return c`
      <div class="header-left">
        <span class="header-title">infinitude</span>
        <span class="conn-dot ${s?"ok":"err"}" title="${s?"Infinitude: connected":"Infinitude: unavailable"}"></span>
        <span class="conn-dot ${i===!0?"ok":i===!1?"err":"unk"}" title="${i===!0?"Carrier cloud: connected":i===!1?"Carrier cloud: unreachable":"Carrier cloud: checking\u2026"}"></span>
        <span style="font-size:10px;color:var(--secondary-text-color);opacity:0.5">v${Q}</span>
      </div>`}_tabs(){return c`${["status","schedule","profiles"].map(e=>c`
      <div class="tab ${this._tab===e?"active":""}"
           @click=${()=>{this._tab=e}}>${e.charAt(0).toUpperCase()+e.slice(1)}</div>`)}`}_status(t){let{climates:e}=t;return e.length?c`
      ${this._summaryStrip(t)}
      <div class="zone-grid">${e.map(s=>this._zoneCard(s))}</div>`:c`<div style="padding:20px;text-align:center;color:var(--secondary-text-color)">No zone entities found</div>`}_summaryStrip(t){let{system:e,selects:s,climates:i}=t,o=i.length&&this._st(i[0])?.state||"off",a=["off","heat","cool","heat_cool"],l={off:"Off",heat:"Heat",cool:"Cool",heat_cool:"Auto"},n=this._st(e.oat),r="\u2013";if(n?.state&&n.state!=="unavailable")r=`${Math.round(Number(n.state))}\xB0`;else if(i.length){let _=this._at(i[0],"outdoor_temperature");_!=null&&(r=`${Math.round(Number(_))}\xB0`)}let p=this._st(e.opStatus),h=p?.state&&p.state!=="unavailable"?p.state:"",f=this._st(e.humidifier)?.state==="on",v=this._st(s.wholeHouse),b=v&&v.state!=="off",k=i.length?this._at(i[0],"whole_house_hold_until"):null,y=i.length?this._at(i[0],"current_humidity"):null;return c`
      <div class="mode-row">
        <span class="mode-label">Mode</span>
        <div class="mode-pills">
          ${a.map(_=>c`<div class="mode-pill ${_===o?"active":""} ${_==="heat"?"heat":_==="cool"?"cool":_==="heat_cool"?"auto":""}"
              @click=${()=>this._setHvacMode(i[0],_)}>${l[_]}</div>`)}
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
          <span class="summary-stat-val">${r}</span>
        </div>
        <div class="summary-divider"></div>
        <div class="summary-stat">
          <span class="summary-stat-label">Humidity</span>
          <span class="summary-stat-val">${y!=null?`${y}%`:"\u2013"}</span>
        </div>
        ${f?c`
          <div class="summary-divider"></div>
          <div class="summary-stat">
            <span class="summary-stat-label">Humidifier</span>
            <span class="summary-stat-val" style="color:var(--label-badge-blue,#38bdf8)">💧 On</span>
          </div>`:u}
      </div>
      ${b?c`
        <div class="wh-hold" @click=${()=>this._cancelWholeHouseHold()}>
          <ha-icon icon="mdi:home-lock" style="--mdc-icon-size:16px"></ha-icon>
          <span>Whole house: <strong>${v.state}</strong>${k?c` · <span style="opacity:0.85">${this._otmrRelative(k)}</span>`:u}</span>
          <span style="margin-left:auto;opacity:0.7">Tap to cancel</span>
        </div>`:c`
        ${this._whHoldOpen?c`
          <div class="wh-set">
            <span class="wh-set-label">WH Hold</span>
            <div class="wh-pills">
              ${S.map(_=>c`
                <div class="wh-pill ${this._whHoldActivity===_?"active":""}"
                     @click=${()=>{this._whHoldActivity=_}}>${_}</div>`)}
            </div>
            <select class="hold-dur-select" @change=${_=>{this._whHoldDuration=_.target.value}}>
              ${N.map(_=>c`<option value=${_.v} ?selected=${_.v===this._whHoldDuration}>${_.l}</option>`)}
            </select>
            ${this._whHoldDuration==="custom"?c`
              <input type="time" class="hold-time-input" step="900" .value=${this._whHoldCustom}
                     @change=${_=>{this._whHoldCustom=_.target.value}}>`:u}
            <button class="btn btn-primary" style="font-size:11px;padding:4px 12px" @click=${()=>this._setWholeHouseHold()}>Apply</button>
            <button class="btn" style="font-size:11px;padding:4px 10px" @click=${()=>{this._whHoldOpen=!1}}>Cancel</button>
          </div>`:c`
          <div>
            <button class="btn" style="font-size:11px;padding:4px 12px" @click=${()=>{this._whHoldOpen=!0}}>
              <ha-icon icon="mdi:home-lock" style="--mdc-icon-size:14px;vertical-align:middle;margin-right:4px"></ha-icon>Set WH hold
            </button>
          </div>`}
      `}`}_zoneCard(t){let e=this._st(t);if(!e)return u;let s=e.attributes||{},i=(s.friendly_name||t).replace(/^Infinitude\s+/i,"").replace(/^infinitude_direct\s+/i,""),o=s.current_temperature!=null?Math.round(s.current_temperature):"\u2013",a=s.current_humidity,l=e.state||"off",n=s.hvac_action||"idle",r=s.preset_mode||"\u2013",p=n==="heating"?"heating":n==="cooling"?"cooling":n==="drying"?"drying":"",h=n==="idle"?"Idle":n.charAt(0).toUpperCase()+n.slice(1),f=l==="heat_cool",v=!!s.hold_active,b=s.hold_activity||r,k=s.hold_until,y=this._holdOpen===t,_=this._pendingTemps[t],w=this._hasPending(t),g=_?.heat??s.target_temp_low??s.temperature??null,m=_?.cool??s.target_temp_high??(l==="cool"?s.temperature:null)??null;return c`
      <div class="zone-card ${p}">
        <div class="zone-top">
          <span class="zone-name">${i}</span>
          <span class="zone-badge ${p}">${h}</span>
        </div>
        <div class="zone-body">
          <div>
            <span class="temp-hero">${o}</span><span class="temp-unit">°F</span>
            ${a!=null?c`<div style="font-size:11px;color:var(--secondary-text-color);margin-top:2px">${a}% RH</div>`:u}
          </div>
          <div class="zone-sp">
            ${g!=null?c`
              <div class="sp-row">
                <button class="btn-adj" @click=${()=>this._adjustTemp(t,-1,"heat")}>−</button>
                <span class="sp-val sp-heat ${w?"sp-pending":""}">${Math.round(g)}°</span>
                <button class="btn-adj" @click=${()=>this._adjustTemp(t,1,"heat")}>+</button>
              </div>`:u}
            ${f&&m!=null?c`
              <div class="sp-row">
                <button class="btn-adj" @click=${()=>this._adjustTemp(t,-1,"cool")}>−</button>
                <span class="sp-val sp-cool ${w?"sp-pending":""}">${Math.round(m)}°</span>
                <button class="btn-adj" @click=${()=>this._adjustTemp(t,1,"cool")}>+</button>
              </div>`:u}
          </div>
        </div>
        <div class="zone-meta">
          <span class="meta-item">Activity <span class="meta-val">${r}</span></span>
          ${s.fan_mode?c`<span class="meta-item">Fan <span class="meta-val">${s.fan_mode}</span></span>`:u}
          ${s.damper_position!=null?c`<span class="meta-item">Damper <span class="meta-val">${s.damper_position}%</span></span>`:u}
        </div>
        <div class="zone-preset-row">
          ${S.map(x=>c`
            <div class="preset-btn ${r===x?"active":""}"
                 @click=${()=>this._setPreset(t,x)}>${x}</div>`)}
        </div>
        ${v?c`
          <div class="zone-hold">
            <span class="hold-label">Hold: ${b}${k?` \xB7 ${this._otmrRelative(k)}`:""}</span>
            <button class="btn" style="font-size:11px;padding:3px 10px;color:var(--error-color,#f87171)" @click=${()=>this._cancelHold(t)}>Cancel</button>
          </div>`:u}
        ${y?c`
          <div class="zone-hold-picker">
            <div class="hold-picker-row">
              <div class="wh-pills">
                ${X.map(x=>c`
                  <div class="wh-pill ${this._holdActivity===x?"active":""}"
                       @click=${()=>{this._holdActivity=x,x==="manual"&&this._initHoldManual(t)}}>${x}</div>`)}
              </div>
            </div>
            ${this._holdActivity==="manual"?c`
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
                ${N.map(x=>c`<option value=${x.v} ?selected=${x.v===this._holdDuration}>${x.l}</option>`)}
              </select>
              ${this._holdDuration==="custom"?c`
                <input type="time" class="hold-time-input" step="900" .value=${this._holdCustom}
                       @change=${x=>{this._holdCustom=x.target.value}}>`:u}
            </div>
            <div class="hold-picker-row">
              <button class="btn btn-primary" style="font-size:11px;padding:4px 12px" @click=${()=>this._setZoneHold(t)}>Apply</button>
              <button class="btn" style="font-size:11px;padding:4px 10px" @click=${()=>{this._holdOpen=null}}>Cancel</button>
            </div>
          </div>`:v?u:c`
          <div class="zone-actions">
            <button class="btn" style="font-size:11px;padding:4px 12px" @click=${()=>{this._holdActivity=r!=="\u2013"?r:"home",this._holdDuration="120",this._holdCustom="",this._holdActivity==="manual"&&this._initHoldManual(t),this._holdOpen=t}}>Set hold</button>
          </div>`}
      </div>`}_adjustTemp(t,e,s){let i=this._st(t);if(!i)return;let o=i.attributes||{},a=this._tempAdj[t]||(this._tempAdj[t]={}),l=a.heat??o.target_temp_low??o.temperature??68,n=a.cool??o.target_temp_high??(i.state==="cool"?o.temperature:null)??76;s==="heat"?a.heat=Math.max(50,Math.min(90,Math.round(l)+e)):a.cool=Math.max(60,Math.min(99,Math.round(n)+e)),this._pendingTemps={...this._pendingTemps,[t]:{heat:a.heat,cool:a.cool}},a.committing||(clearTimeout(a.timer),a.timer=setTimeout(()=>this._commitAdj(t),800))}async _commitAdj(t){let e=this._tempAdj[t];if(!e||e.committing)return;e.committing=!0;let s=this._st(t),i=s?.attributes||{},o=e.heat,a=e.cool,l=o??Math.round(i.target_temp_low??i.temperature??68),n=a??Math.round(i.target_temp_high??(s?.state==="cool"?i.temperature:null)??76),r=s?.state||"off",p={entity_id:t};r==="heat_cool"?(p.target_temp_low=l,p.target_temp_high=n):r==="heat"?p.temperature=l:r==="cool"?p.temperature=n:(p.target_temp_low=l,p.target_temp_high=n);try{await this.hass.callService("climate","set_temperature",p)}catch(h){console.error("set_temperature failed",h)}if(e.committing=!1,e.heat!==o||e.cool!==a){e.timer=setTimeout(()=>this._commitAdj(t),400);return}e.heat=null,e.cool=null,e.timer=null,e.graceUntil=Date.now()+3e4,setTimeout(()=>{if(!this._tempAdj[t]?.heat&&!this._tempAdj[t]?.cool){let{[t]:h,...f}=this._pendingTemps;this._pendingTemps=f}},2e3)}_hasPending(t){let e=this._tempAdj[t];return e&&(e.heat!=null||e.cool!=null||e.committing)}_cancelHold(t){let e=this._zoneId(t);e&&this._svc("infinitude_direct","cancel_hold",{zone_id:e})}_setZoneHold(t){let e=this._zoneId(t);if(!e)return;let s=this._resolveUntil(this._holdDuration,this._holdCustom);s!==null&&(this._holdActivity==="manual"&&this._svc("infinitude_direct","set_profile",{zone_id:e,activity:"manual",htsp:this._holdHtsp,clsp:this._holdClsp,fan:this._holdFan}),this._svc("infinitude_direct","set_hold",{zone_id:e,activity:this._holdActivity,...s!==void 0&&{until:s}}),this._holdOpen=null)}_initHoldManual(t){let e=this._zoneId(t),s=this._getProfilesData().find(i=>i.id===e)?.activities?.manual||{};this._holdHtsp=s.htsp?Math.round(Number(s.htsp)||68):68,this._holdClsp=s.clsp?Math.round(Number(s.clsp)||76):76,this._holdFan=s.fan||"auto"}_setWholeHouseHold(){let t=this._resolveUntil(this._whHoldDuration,this._whHoldCustom);t!==null&&(this._svc("infinitude_direct","set_whole_house_hold",{activity:this._whHoldActivity,...t!==void 0&&{until:t}}),this._whHoldOpen=!1)}_cancelWholeHouseHold(){this._svc("infinitude_direct","cancel_whole_house_hold",{})}_sched(){let t=this._getScheduleData(),e=this._getProfilesData(),s=Object.keys(t);if(!s.length)return c`
      <div style="padding:20px;text-align:center;color:var(--secondary-text-color)">
        <ha-icon icon="mdi:calendar-clock" style="--mdc-icon-size:48px;opacity:0.3;margin-bottom:12px;display:block"></ha-icon>
        No schedule data available. Waiting for thermostat data…
      </div>`;let i=A[R[new Date().getDay()]],o={},a={};for(let r=0;r<e.length;r++)o[e[r].id]=e[r].name,a[e[r].id]=r;let l=0;for(let r of s)l=Math.max(l,(t[r]?.[this._schedDay]||[]).length);l||(l=5);let n=Object.keys(this._schedEdits).length>0;return c`
      <div class="section-title">Schedule</div>
      ${s.length>1?c`<div class="zone-legend">${s.map((r,p)=>c`<span class="legend-item"><span class="legend-num">${C[p]||p+1}</span> ${o[r]||`Zone ${r}`}</span>`)}</div>`:u}
      <div class="sched-day-tabs">
        ${A.map(r=>c`
          <div class="day-tab ${r===this._schedDay?"active":""} ${r===i&&r!==this._schedDay?"today":""}"
               @click=${()=>{this._schedDay=r}}>${r.slice(0,3)}</div>`)}
      </div>
      ${Array.from({length:l},(r,p)=>this._periodCard(p,s,t,e,o,a))}
      <div class="copy-bar">
        <span>Copy ${this._schedDay.slice(0,3)} →</span>
        <select class="sched-select" @change=${r=>this._copySched(r)}>
          <option value="">select day…</option>
          ${A.filter(r=>r!==this._schedDay).map(r=>c`<option value=${r}>${r.slice(0,3)}</option>`)}
          <option value="__all__">All other days</option>
        </select>
      </div>
      ${n?c`
        <div class="action-bar">
          <span class="action-bar-label">● Unsaved changes</span>
          <button class="btn" @click=${()=>{this._schedEdits={}}}>Discard</button>
          <button class="btn btn-primary" @click=${()=>this._saveSched()}>Save schedule</button>
        </div>`:u}`}_periodCard(t,e,s,i,o,a){let l=e.length>1;return c`
      <div class="period-card">
        <div class="period-header">Period ${t+1}</div>
        ${e.map(n=>{let r=(s[n]?.[this._schedDay]||[])[t];if(!r)return u;let p=`${n}_${this._schedDay}_${t}`,h=this._schedEdits[p],f=h?.act??r.activity,v=h?.time??r.time,b=h?.enabled??r.enabled,y=i.find(m=>m.id===n)?.activities?.[f],_=y?.htsp?Math.round(Number(y.htsp)||0):"\u2013",w=y?.clsp?Math.round(Number(y.clsp)||0):"\u2013",g=l?C[a[n]]??n:o[n]||`Zone ${n}`;return c`
            <div class="sched-line ${b?"":"disabled"}">
              <span class="sched-name ${l?"sched-name-compact":""}">${g}</span>
              <select class="sched-select" .value=${f} @change=${m=>this._schedEdit(n,t,"act",m.target.value)}>
                ${S.map(m=>c`<option value=${m} ?selected=${m===f}>${m}</option>`)}
              </select>
              <select class="sched-select" .value=${v} @change=${m=>this._schedEdit(n,t,"time",m.target.value)}>
                ${et.map(m=>c`<option value=${m.v} ?selected=${m.v===v}>${m.l}</option>`)}
              </select>
              <label class="sched-toggle">
                <input type="checkbox" .checked=${b}
                       @change=${m=>this._schedEdit(n,t,"enabled",m.target.checked)}>
                <span>on</span>
              </label>
              <div class="sched-temps">
                <span class="sp-heat">${_}°</span>
                <span class="sp-cool">${w}°</span>
              </div>
            </div>`})}
      </div>`}_schedEdit(t,e,s,i){let o=`${t}_${this._schedDay}_${e}`,a=this._schedEdits[o]||{},l=(this._getScheduleData()[t]?.[this._schedDay]||[])[e]||{};this._schedEdits={...this._schedEdits,[o]:{act:s==="act"?i:a.act??l.activity,time:s==="time"?i:a.time??l.time,enabled:s==="enabled"?i:a.enabled??l.enabled}}}_copySched(t){let e=t.target.value;if(!e)return;t.target.value="";let s=this._getScheduleData(),i=e==="__all__"?A.filter(a=>a!==this._schedDay):[e],o={...this._schedEdits};for(let a of Object.keys(s)){let l=s[a]?.[this._schedDay]||[];for(let n of i)l.forEach((r,p)=>{let h=this._schedEdits[`${a}_${this._schedDay}_${p}`];o[`${a}_${n}_${p}`]={act:h?.act??r.activity,time:h?.time??r.time,enabled:h?.enabled??r.enabled}})}this._schedEdits=o}async _saveSched(){if(this._saving)return;this._saving=!0;let t={...this._schedEdits};try{let e=this._getScheduleData();for(let s of Object.keys(e)){let i=A.map(o=>({id:o,period:(e[s]?.[o]||[]).map((a,l)=>{let n=t[`${s}_${o}_${l}`];return{id:a.id||String(l+1),activity:n?.act??a.activity,time:n?.time??a.time,enabled:n?.enabled??a.enabled?"on":"off"}})}));await this._svc("infinitude_direct","save_schedule",{zone_id:s,schedule:JSON.stringify(i)})}}finally{setTimeout(()=>{let e=this._schedEdits,s={};for(let i of Object.keys(e))(!(i in t)||e[i]!==t[i])&&(s[i]=e[i]);this._schedEdits=s,this._saving=!1},500)}}_profs(){let t=this._getProfilesData();if(!t.length)return c`
      <div style="padding:20px;text-align:center;color:var(--secondary-text-color)">
        <ha-icon icon="mdi:tune-vertical" style="--mdc-icon-size:48px;opacity:0.3;margin-bottom:12px;display:block"></ha-icon>
        No profile data available. Waiting for thermostat data…
      </div>`;let e=t.length>1,s=Object.keys(this._profileEdits).length>0;return c`
      <div class="section-title">Comfort Profiles</div>
      ${e?c`<div class="zone-legend">${t.map((i,o)=>c`<span class="legend-item"><span class="legend-num">${C[o]||o+1}</span> ${i.name}</span>`)}</div>`:u}
      ${S.map(i=>c`
        <div class="prof-card">
          <div class="prof-header">${i}</div>
          ${t.map((o,a)=>{let l=o.activities?.[i]||{},n=`${o.id}_${i}`,r=this._profileEdits[n],p=r?.htsp??(l.htsp?Math.round(Number(l.htsp)||68):68),h=r?.clsp??(l.clsp?Math.round(Number(l.clsp)||76):76),f=r?.fan??l.fan??"low",v=e?C[a]||a+1:o.name;return c`
              <div class="prof-line">
                <span class="prof-name ${e?"prof-name-compact":""}">${v}</span>
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
                  <select class="sched-select" .value=${f} @change=${b=>this._profFan(o.id,i,b.target.value)}>
                    ${tt.map(b=>c`<option value=${b} ?selected=${b===f}>${b}</option>`)}
                  </select>
                </div>
              </div>`})}
        </div>`)}
      ${s?c`
        <div class="action-bar">
          <span class="action-bar-label">● Unsaved changes</span>
          <button class="btn" @click=${()=>{this._profileEdits={}}}>Discard</button>
          <button class="btn btn-primary" @click=${()=>this._saveProfs()}>Save profiles</button>
        </div>`:u}`}_profAdj(t,e,s,i){let o=`${t}_${e}`,a=this._getProfilesData().find(v=>v.id===t)?.activities?.[e]||{},l=this._profileEdits[o]||{},n=l.htsp??(a.htsp?Math.round(Number(a.htsp)||68):68),r=l.clsp??(a.clsp?Math.round(Number(a.clsp)||76):76),p=s==="htsp"?50:60,h=s==="htsp"?90:99,f=s==="htsp"?n:r;this._profileEdits={...this._profileEdits,[o]:{zone_id:t,activity:e,htsp:s==="htsp"?Math.max(p,Math.min(h,f+i)):n,clsp:s==="clsp"?Math.max(p,Math.min(h,f+i)):r,fan:l.fan??a.fan??"low"}}}_profFan(t,e,s){let i=`${t}_${e}`,o=this._getProfilesData().find(l=>l.id===t)?.activities?.[e]||{},a=this._profileEdits[i]||{};this._profileEdits={...this._profileEdits,[i]:{zone_id:t,activity:e,htsp:a.htsp??(o.htsp?Math.round(Number(o.htsp)||68):68),clsp:a.clsp??(o.clsp?Math.round(Number(o.clsp)||76):76),fan:s}}}async _saveProfs(){if(this._savingProfs)return;this._savingProfs=!0;let t={...this._profileEdits};try{for(let e of Object.values(t)){let s={zone_id:e.zone_id,activity:e.activity,htsp:e.htsp,clsp:e.clsp};e.fan&&(s.fan=e.fan),await this._svc("infinitude_direct","set_profile",s)}}finally{setTimeout(()=>{let e=this._profileEdits,s={};for(let i of Object.keys(e))(!(i in t)||e[i]!==t[i])&&(s[i]=e[i]);this._profileEdits=s,this._savingProfs=!1},500)}}};customElements.get("infinitude-hvac-card")||customElements.define("infinitude-hvac-card",bt);window.customCards=window.customCards||[];window.customCards.some(d=>d.type==="infinitude-hvac-card")||window.customCards.push({type:"infinitude-hvac-card",name:"Infinitude HVAC Card",description:"Full HVAC dashboard for Carrier/Bryant Infinity thermostats",preview:!1});
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
