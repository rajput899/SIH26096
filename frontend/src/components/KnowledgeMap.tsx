'use client';
import {useInterface} from './InterfaceLanguage';

import Link from 'next/link';
import {useEffect,useState} from 'react';
type Entry={id:string;kind:string;title:string;topic:string;evidence:{item_id:string;title:string;revision:number|null;quote:string}[]};
export default function KnowledgeMap({initialTopic=''}:{initialTopic?:string}){
 const {ui}=useInterface();

 const [rows,setRows]=useState<Entry[]>([]);const [message,setMessage]=useState('Loading source connections…');const [topic,setTopic]=useState(initialTopic);
 useEffect(()=>{const controller=new AbortController();Promise.all(['timeline','story','quiz'].map(async kind=>{const r=await fetch(`/api/archive/learning?kind=${kind}`,{cache:'no-store',signal:controller.signal});if(!r.ok)throw Error('Source connections unavailable. Reload to retry.');return r.json() as Promise<Entry[]>;})).then(groups=>{setRows(groups.flat());setMessage('');}).catch(e=>{if(!controller.signal.aborted)setMessage(e.message);});return()=>controller.abort();},[]);
 return <section aria-label={ui("Knowledge map")}><h2>{ui("Connections through sources")}</h2><p>{ui("Follow curator-assigned topics to published activities and their archival evidence. Connections describe these source references; they do not imply unverified historical relationships.")}</p><p role="status">{ui(message)}</p><label>{ui("Map topic")}<select value={topic} onChange={e=>setTopic(e.target.value)}><option value="">{ui("All reviewed topics")}</option>{[...new Set(rows.map(r=>r.topic).filter(Boolean))].sort().map(t=><option key={t}>{t}</option>)}</select></label>{!message&&!rows.length&&<p>{ui("No approved source connections are available yet.")}</p>}<div className="knowledge-connections">{rows.filter(r=>!topic||r.topic===topic).map(r=><article className="source" key={r.id}><p className="eyebrow">{r.topic || ui("Topic not assigned")} {ui(" → ")}{r.kind}</p><h3>{r.title}</h3><ul>{r.evidence.map(e=><li key={e.item_id}><Link href={`/archive/${e.item_id}${e.revision?`?revision=${e.revision}`:''}`}>{e.title}</Link>{e.quote&&<details><summary>{ui("Read supporting excerpt")}</summary><blockquote lang="en" translate="no">{e.quote}</blockquote></details>}</li>)}</ul><Link className="text-link" href={`/experience/${encodeURIComponent(r.topic||"Reviewed activities")}#activity-${r.id}`}>{ui("Explore activity →")}</Link>{r.kind==='quiz'&&<Link href={`/quiz/${r.id}`}>{ui("Open reviewed quiz")}</Link>}</article>)}</div></section>;
}

