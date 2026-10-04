'use client';
import {useInterface} from './InterfaceLanguage';

import Link from 'next/link';
import {useEffect,useState} from 'react';
import KnowledgeMap from './KnowledgeMap';
type Entry={id:string;kind:string;title:string;topic:string;description:string;date_label:string;question_count:number;evidence:{item_id:string;title:string;revision:number|null;quote:string}[]};
export default function Exhibition({topic}:{topic?:string}) {
 const {ui}=useInterface();

 const [entries,setEntries]=useState<Entry[]>([]);
 const [message,setMessage]=useState('Loading reviewed exhibitions…');
 const [failed,setFailed]=useState(false);const [retry,setRetry]=useState(0);
 const [map,setMap]=useState(false);
 useEffect(()=>{const controller=new AbortController();
   Promise.all(['timeline','story','quiz'].map(async kind=>{
     const r=await fetch(`/api/archive/learning?kind=${kind}`,{cache:'no-store',signal:controller.signal});
     if(!r.ok)throw Error('Exhibitions are temporarily unavailable. Please retry.');
     return r.json() as Promise<Entry[]>;
   })).then(groups=>{setEntries(groups.flat());setMessage('');setFailed(false);})
   .catch(()=>{if(!controller.signal.aborted){setMessage('Exhibitions are temporarily unavailable. Please retry.');setFailed(true);}});
   return()=>controller.abort();
 },[retry]);
 const topics=[...new Set(entries.map(e=>e.topic||'Reviewed activities'))].sort();
 const selected=entries.filter(e=>(e.topic||'Reviewed activities')===topic);
 function sources(entry:Entry){return <details className="exhibit-evidence"><summary>{ui("Supporting sources · ")}{entry.evidence.length}</summary>{entry.evidence.map((s,i)=><div key={`${s.item_id}-${i}`}><Link href={`/archive/${s.item_id}${s.revision?`?revision=${s.revision}`:''}`}>{s.title} {ui(" →")}</Link>{s.quote&&<blockquote lang="en" translate="no">{s.quote}</blockquote>}</div>)}</details>;}
 return <main className="page exhibition">
   {topic&&<Link className="text-link" href="/experience">{ui("← All exhibitions")}</Link>}
   <header className="exhibition-heading"><p className="eyebrow">{ui("03 / Read · Connect · Reflect")}</p><h1>{topic || ui("Explore the legacy")}</h1>
   <p className="intro">{topic ? ui("A curated path through published learning activities. Read the introductions, compare the supporting sources and reflect on what you discover.") : ui("Choose a topic and follow its stories, milestones and learning activities back to the sources that support them.")}</p></header>
   {message&&<p role={failed?'alert':'status'}>{ui(message)}</p>}{failed&&<button onClick={()=>{setMessage('Loading reviewed exhibitions…');setFailed(false);setRetry(n=>n+1);}}>{ui("Retry exhibitions")}</button>}
   {!message&&!topic&&<><div className="exhibition-grid">{topics.map((t,i)=>{
     const rows=entries.filter(e=>(e.topic||'Reviewed activities')===t);
     const introduction=rows.find(e=>e.kind==='story')||rows[0];
     return <Link className="exhibition-plaque" href={`/experience/${encodeURIComponent(t)}`} key={t}>
       <div className="plaque-art" aria-hidden="true"><span>{String(i+1).padStart(2,'0')}</span><div className="plaque-lines"/></div>
       <div className="plaque-copy"><p className="eyebrow">{ui("Curator-authored exhibition")}</p><h2>{t}</h2><p>{introduction.description.split(/\n\s*\n|\\n\\n/)[0]}</p><p className="subtle">{rows.filter(e=>e.kind==='timeline').length} {ui(" milestones · ")}{rows.filter(e=>e.kind==='story').length} {ui(" stories · ")}{rows.filter(e=>e.kind==='quiz').length} {ui(" quizzes")}</p><span className="card-action">{ui("Enter exhibition →")}</span></div>
     </Link>;
   })}</div>{!topics.length&&<section className="empty"><h2>{ui("No published exhibitions yet")}</h2><p>{ui("Exhibitions appear after curators review their content and supporting sources.")}</p></section>}
   <section className="trust-strip"><h2>{ui("Follow the evidence")}</h2><div><p>{ui("Exhibition text is curator-authored. Supporting records retain their own provenance: a modern account is not an original historical document.")}</p><button aria-expanded={map} onClick={()=>setMap(v=>!v)}>{ui("Knowledge map")}</button>{map&&<KnowledgeMap/>}</div></section></>}
   {!message&&topic&&<>{!selected.length ? <section className="empty"><h2>{ui("Exhibition unavailable")}</h2><p>{ui("No currently published activities support this topic. It may have been withdrawn or renamed.")}</p></section> : <>
     <nav className="staff-stages" aria-label={ui("In this exhibition")}>{[['story','Stories'],['timeline','Timeline'],['quiz','Quizzes']].filter(([kind])=>selected.some(e=>e.kind===kind)).map(([kind,label])=><a className="button" href={`#${kind}`} key={kind}>{label}</a>)}<a className="text-link" href="#connections">{ui("Source connections")}</a></nav>
     {(['story','timeline','quiz'] as const).map(kind=>{const rows=selected.filter(e=>e.kind===kind);return rows.length>0&&<section className={`exhibit-section exhibit-${kind}`} id={kind} key={kind}><p className="eyebrow">{kind==='story'?ui("Read the context"):kind==='timeline'?ui("Trace the milestones"):ui("Reflect and learn")}</p><h2>{kind==='story'?ui("Stories"):kind==='timeline'?ui("Timeline"):ui("Quizzes")}</h2>{rows.map(e=><article className="exhibit-entry" id={`activity-${e.id}`} key={e.id}>
       {e.date_label&&<p className="exhibit-date">{e.date_label}</p>}<div><p className="tag">{ui("Curator-authored ")}{kind}</p><h3>{e.title}</h3>{e.description.split(/\n\s*\n|\\n\\n/).map((p,i)=><p className="original-text" key={i}>{p}</p>)}{sources(e)}{kind==='quiz'&&<Link className="button" href={`/quiz/${e.id}`}>{ui("Begin quiz · ")}{e.question_count} {ui(" questions")}</Link>}</div>
     </article>)}</section>;})}
     <section id="connections"><KnowledgeMap initialTopic={topic}/></section>
   </>}</>}
 </main>;
}
