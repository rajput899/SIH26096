'use client';
import {useInterface} from './InterfaceLanguage';

import Link from 'next/link';
import {FormEvent, useEffect, useState} from 'react';

type Entry = {id:string; title:string; description:string; material_type:string;
  language:string; volume_number:number|null; part_number:number|null};
export default function CollectionExplorer() {
 const {ui}=useInterface();

  const [entries,setEntries]=useState<Entry[]>([]);
  const [message,setMessage]=useState('Loading collection…');
  const [query,setQuery]=useState('');
  const [kind,setKind]=useState('');
  const [volume,setVolume]=useState('');
  const [offset,setOffset]=useState(0);
  async function load(start=0) {
    setMessage('Loading collection…');
    try {
      const params=new URLSearchParams({q:query,material_type:kind,offset:String(start),limit:'24'});
      if(volume) params.set('volume',volume);
      const response=await fetch(`/api/archive/catalog?${params}`,{cache:'no-store'});
      if(!response.ok) throw Error('Collection unavailable. Please retry.');
      setEntries(await response.json());setOffset(start);setMessage('');
    } catch(error) {setMessage(error instanceof Error?error.message:'Collection unavailable.');}
  }
  useEffect(()=>{
    const controller=new AbortController();
    fetch('/api/archive/catalog?limit=24',{cache:'no-store',signal:controller.signal})
      .then(async response=>{if(!response.ok)throw Error('Collection unavailable. Please retry.');
        setEntries(await response.json());setMessage('');})
      .catch(error=>{if(!controller.signal.aborted)setMessage(error.message);});
    return ()=>controller.abort();
  },[]);
  function search(event:FormEvent){event.preventDefault();void load(0);}
  return <section aria-label={ui("Explore the Collection")}><p className="eyebrow">{ui("Read / Listen / Explore")}</p>
    <h2>{ui("Explore the Collection")}</h2>
    <p className="intro">{ui("Discover approved documents and recordings, open their sources, and ask questions grounded in reviewed archival text.")}</p>
    <nav className="staff-stages" aria-label={ui("Collection views")}><Link className="button" href="/archive">{ui("Archive readers")}</Link><Link className="button" href="/speeches">{ui("Audio & video")}</Link><Link className="button" href="/ai">{ui("AI Research Assistant")}</Link></nav>
    <form className="filters" onSubmit={search}>
      <label>{ui("Search collection")}<input type="search" maxLength={200} value={query} onChange={e=>setQuery(e.target.value)}/></label>
      <label>{ui("Volume")}<select value={volume} onChange={e=>setVolume(e.target.value)}><option value="">{ui("All volumes")}</option>{Array.from({length:17},(_,i)=><option key={i+1} value={i+1}>{ui("Volume ")}{i+1}</option>)}</select></label>
      <label>{ui("Material type")}<select value={kind} onChange={e=>setKind(e.target.value)}><option value="">{ui("All materials")}</option>{['document','manuscript','photograph','audio','video','speech'].map(type=><option key={type} value={type}>{ui(type)}</option>)}</select></label>
      <button className="button">{ui("Search collection")}</button>
    </form>
    <p role="status">{ui(message) || ui("{0} approved records on this page", entries.length)}</p>
    {message.startsWith('Collection unavailable')&&<button onClick={()=>void load(offset)}>{ui("Retry")}</button>}
    {!message&&!entries.length&&<section className="empty-state"><h2>{ui("No approved records in this selection")}</h2><p>{ui("Only reviewed material approved for public access appears here. Try another filter or return after curators publish the collection.")}</p></section>}
    {!message&&<div className="record-grid">{entries.map(entry=><article className="record" key={entry.id}>
      <span className="tag">{entry.material_type} {ui(" / ")}{entry.language}</span><h2><Link href={`/archive/${entry.id}`}>{entry.title}</Link></h2>
      {entry.volume_number&&<p>{ui("Volume ")}{entry.volume_number}{entry.part_number&&` · Part ${entry.part_number}`}</p>}<p>{entry.description}</p>
      <Link className="text-link" href={`/archive/${entry.id}`}>{ui("Open source →")}</Link>
      <Link className="text-link" href={`/ai?source=${entry.id}`}>{ui("Research this source →")}</Link>
    </article>)}</div>}
    <nav className="staff-stages" aria-label={ui("Collection pages")}><button disabled={offset===0} onClick={()=>void load(Math.max(0,offset-24))}>{ui("Previous page")}</button><button disabled={entries.length<24} onClick={()=>void load(offset+24)}>{ui("Next page")}</button></nav>
  </section>;
}
