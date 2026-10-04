'use client';
import {useInterface} from './InterfaceLanguage';

import Link from 'next/link';
import {useEffect,useState} from 'react';
export default function RelatedExhibitions({id}:{id:string}) {
 const {ui}=useInterface();

 const [topics,setTopics]=useState<string[]>([]);
 useEffect(()=>{const c=new AbortController();
  Promise.all(['timeline','story','quiz'].map(async kind=>{const r=await fetch(`/api/archive/learning?kind=${kind}`,{cache:'no-store',signal:c.signal});if(!r.ok)throw Error();return r.json() as Promise<{topic:string;evidence:{item_id:string}[]}[]>;}))
   .then(groups=>setTopics([...new Set(groups.flat().filter(e=>e.evidence.some(s=>s.item_id===id)).map(e=>e.topic||'Reviewed activities'))]))
   .catch(()=>{});return()=>c.abort();
 },[id]);
 return topics.length>0&&<aside className="source"><h2>{ui("Explore this source in context")}</h2><p>{ui("Curator-authored exhibitions referencing this record:")}</p>{topics.map(t=><Link className="text-link" key={t} href={`/experience/${encodeURIComponent(t)}`}>{t} {ui(" →")}</Link>)}</aside>;
}
