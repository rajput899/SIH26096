'use client';
import {createContext,useCallback,useContext,useEffect,useState} from 'react';
import strings from '../interface-strings.json';

type Capability={code:string;label:string;enabled:boolean};
const preferenceKey='archive-interface-language';
const defaults:Capability[]=[{code:'en',label:'English',enabled:true},{code:'hi',label:'हिन्दी - Hindi',enabled:false}];
const original=(text:string,...values:unknown[])=>text.replace(/\{(\d+)\}/g,(_,n)=>String(values[Number(n)]??`{${n}}`));
const Context=createContext({language:'en',setLanguage:(value:string)=>{void value;},ui:original,languages:[{code:'en',label:'English',enabled:true}],notice:'',retry:()=>{}});
export const useInterface=()=>useContext(Context);
const ids=new Map(Object.entries(strings).map(([key,text])=>[text,key]));
const templates=Object.entries(strings).filter(([,text])=>/\{\d+\}/.test(text)).map(([key,text])=>({key,pattern:new RegExp('^'+text.split(/\{\d+\}/).map(part=>part.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')).join('(.*?)')+'$')}));

function validCapabilities(data:unknown):data is {languages:Capability[];confirmed_pairs:string[][]}{
 if(!data||typeof data!=='object')return false;
 const candidate=data as {languages?:unknown;confirmed_pairs?:unknown};
 return Array.isArray(candidate.languages)&&candidate.languages.length>0
  &&candidate.languages.every(option=>option&&typeof option==='object'
   &&typeof option.code==='string'&&/^[a-z]{2,3}(?:-[A-Za-z]{4})?$/.test(option.code)
   &&typeof option.label==='string'&&option.label.length>0&&option.label.length<=100&&typeof option.enabled==='boolean')
  &&new Set(candidate.languages.map(option=>option.code)).size===candidate.languages.length
  &&candidate.languages.some(option=>option.code==='en'&&option.enabled)
  &&Array.isArray(candidate.confirmed_pairs)
  &&candidate.confirmed_pairs.every(pair=>Array.isArray(pair)&&pair.length===2&&pair[0]==='en'
   &&pair[1]!=='en'&&(candidate.languages as Capability[]).some(option=>option.code===pair[1]&&option.enabled))
  &&candidate.languages.every(option=>option.code==='en'||!option.enabled
   ||(candidate.confirmed_pairs as string[][]).some(pair=>pair[1]===option.code));
}

export default function InterfaceLanguage({children}:{children:React.ReactNode}){
 const [language,selectLanguage]=useState('en');
 const [dictionaries,setDictionaries]=useState<Record<string,Record<string,string>>>({});
 const dictionary=dictionaries[language];
 const [languages,setLanguages]=useState<Capability[]>(defaults);
 const [notice,setNotice]=useState('Checking interface languages…');const [attempt,setAttempt]=useState(0);
 const setLanguage=useCallback((value:string)=>{
  if(!languages.some(option=>option.code===value&&option.enabled))return;
  selectLanguage(value);
  setNotice(value==='en'?'English interface.':'Loading interface translation; English is the fallback.');
  try{window.localStorage.setItem(preferenceKey,value);}catch{/* Selection still works without storage. */}
 },[languages]);
 useEffect(()=>{
  const controller=new AbortController();
  fetch('/api/archive/interface/languages',{cache:'no-store',signal:controller.signal}).then(async response=>{
   if(!response.ok)throw Error();const data:unknown=await response.json();
   if(!validCapabilities(data))throw Error();if(controller.signal.aborted)return;
   setLanguages(data.languages);
   let saved:string|null=null;try{saved=window.localStorage.getItem(preferenceKey);}catch{}
   selectLanguage(current=>data.languages.some(option=>option.code===(saved??current)&&option.enabled)?(saved??current):'en');
   setNotice(data.confirmed_pairs.length?'Interface languages are available. English is the fallback.':'Translation unavailable. English remains available.');
  }).catch(()=>{if(!controller.signal.aborted){setLanguages(defaults);selectLanguage('en');setNotice('Language service unavailable. English remains available.');}});
  return()=>controller.abort();
 },[attempt]);
 useEffect(()=>{
  if(language==='en')return;
  const controller=new AbortController();
  void (async()=>{const all=Object.keys(strings);let missing=0;
   try{for(let start=0;start<all.length;start+=30){
    const keys=all.slice(start,start+30);
    const response=await fetch('/api/archive/interface/translations',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({target_language:language,keys}),signal:controller.signal});
    if(!response.ok)throw Error();const data=await response.json();
    if(!data||typeof data.translations!=='object'||!data.translations||Array.isArray(data.translations)
     ||!Array.isArray(data.missing)||!data.missing.every((key:unknown)=>typeof key==='string'&&keys.includes(key))
     ||(data.target_language!==undefined&&data.target_language!==language)
     ||!Object.entries(data.translations).every(([key,value])=>keys.includes(key)&&typeof value==='string'&&value.trim().length>0))throw Error();
    if(controller.signal.aborted)return;
    missing+=keys.filter(key=>!(key in data.translations)).length;
    setDictionaries(old=>({...old,[language]:{...old[language],...data.translations}}));
   }
    if(!controller.signal.aborted)setNotice(missing?'Some interface text remains English.':'Machine-translated interface; source content is unchanged.');
   }catch{if(!controller.signal.aborted)setNotice('Translation unavailable; missing text remains English.');}
  })();return()=>controller.abort();
 },[language,attempt]);
 useEffect(()=>{document.documentElement.lang=language!=='en'&&dictionary&&Object.keys(dictionary).length?language:'en';},[language,dictionary]);
 const ui=useCallback((text:string,...values:unknown[])=>{
  let translated=language!=='en'?dictionary?.[ids.get(text.trim())??'']:undefined;
  if(language!=='en'&&!translated&&!values.length){for(const template of templates){const match=text.match(template.pattern);if(match&&dictionary?.[template.key]){translated=dictionary[template.key];values=match.slice(1);break;}}}
  return original(translated ? (text.match(/^\s*/)?.[0]||'')+translated+(text.match(/\s*$/)?.[0]||'') : text,...values);
 },[language,dictionary]);
 return <Context.Provider value={{language,setLanguage,ui,languages,notice,retry:()=>setAttempt(n=>n+1)}}>{children}</Context.Provider>;
}
