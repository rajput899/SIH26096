'use client';
import {useInterface} from '../../components/InterfaceLanguage';

import Link from 'next/link';
import {useEffect,useState} from 'react';
import RecordingPlayer from '../../components/RecordingPlayer';
type Recording={id:string;title:string;description:string;mime_type:string;language:string;rights_statement:string;source_name?:string;source_record_locator?:string};
export default function Speeches(){
 const {ui}=useInterface();

 const [records,setRecords]=useState<Recording[]>([]);const [message,setMessage]=useState('Loading recordings…');const [failed,setFailed]=useState(false);const [retry,setRetry]=useState(0);
 const [query,setQuery]=useState('');const [language,setLanguage]=useState('');
 useEffect(()=>{const c=new AbortController();fetch('/api/archive/recordings',{cache:'no-store',signal:c.signal}).then(async r=>{if(!r.ok)throw Error();setRecords(await r.json());setMessage('');setFailed(false);}).catch(()=>{if(!c.signal.aborted){setMessage('Recordings are temporarily unavailable. Please retry.');setFailed(true);}});return()=>c.abort();},[retry]);
 const visible=records.filter(r=>(r.title+' '+r.description).toLocaleLowerCase().includes(query.toLocaleLowerCase())&&(!language||r.language===language));
 return <main className="page"><p className="eyebrow">{ui("Listen / Watch / Read")}</p><h1>{ui("Speeches & recordings")}</h1><p className="intro">{ui("Published originals, their provenance and curator-verified transcripts where available. Unreviewed transcripts remain private.")}</p>
 <div className="filters"><label>{ui("Find a recording")}<input type="search" value={query} onChange={e=>setQuery(e.target.value)}/></label><label>{ui("Language")}<select value={language} onChange={e=>setLanguage(e.target.value)}><option value="">{ui("All languages")}</option>{[...new Set(records.map(r=>r.language))].map(l=><option key={l}>{l}</option>)}</select></label><button onClick={()=>{setQuery('');setLanguage('');}}>{ui("Clear recording filters")}</button></div>
 <p role={failed?'alert':'status'}>{ui(message) || ui("{0} published recording{1} shown", visible.length, visible.length===1?'':'s')}</p>
 {failed&&<button onClick={()=>{setFailed(false);setMessage('Loading recordings…');setRetry(n=>n+1);}}>{ui("Retry recordings")}</button>}
 {!message&&!visible.length&&<section className="empty"><h2>{records.length ? ui("No recordings match these filters") : ui("No recordings have been published yet")}</h2><p>{records.length ? ui("Try another title, description or language, or clear the filters.") : ui("Recordings appear here only after provenance, rights and publication review. A recording mentioned in a source does not establish that an authorized recording is available.")}</p><Link className="text-link" href="/archive">{ui("Browse published source records →")}</Link></section>}
 {!message&&visible.map(r=><section key={r.id}><RecordingPlayer record={r}/><Link href={`/archive/${r.id}`}>{ui("Open source metadata and original ↗")}</Link></section>)}
 </main>;
}
