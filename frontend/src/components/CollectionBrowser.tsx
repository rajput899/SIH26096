'use client';
import {useInterface} from './InterfaceLanguage';

import Link from 'next/link';
import {FormEvent, useEffect, useState} from 'react';
import ArchiveImage from './ArchiveImage';
import CollectionNavigation from './CollectionNavigation';

export const collectionDefinitions = {
  manuscripts: {title: 'Manuscripts & Letters', types: ['manuscript'], split: false},
  photographs: {title: 'Photographs', types: ['photograph'], split: true},
  videos: {title: 'Videos', types: ['video'], split: true},
};
type Entry = {id:string;title:string;description:string;mime_type:string;material_type:string;source_name:string};

function CollectionPart({title, types, origin, query}: {title:string;types:string[];origin:string;query:string}) {
 const {ui}=useInterface();

  const [rows,setRows]=useState<Entry[]>([]);
  const [busy,setBusy]=useState(true);
  const [error,setError]=useState(false);
  const [offset,setOffset]=useState(0);
  const [more,setMore]=useState(false);
  const [retry,setRetry]=useState(0);
  useEffect(()=>{
    const controller=new AbortController();
    Promise.all(types.map(async material_type=>{
      const params=new URLSearchParams({collection: material_type==='manuscript'?'manuscripts':material_type==='photograph'?'photographs':'videos',origin,q:query,offset:String(offset),limit:'13'});
      const response=await fetch(`/api/archive/catalog?${params}`,{cache:'no-store',signal:controller.signal});
      if(!response.ok)throw Error();
      return await response.json() as Entry[];
    })).then(groups=>{if(controller.signal.aborted)return;setRows(groups.flatMap(group=>group.slice(0,12)));setMore(groups.some(group=>group.length>12));setError(false);})
      .catch(()=>{if(!controller.signal.aborted)setError(true);})
      .finally(()=>{if(!controller.signal.aborted)setBusy(false);});
    return()=>controller.abort();
  },[types,origin,query,offset,retry]);
  function page(start:number){setBusy(true);setOffset(start);}
  return <section aria-label={ui(title)} className="collection-part"><h2>{ui(title)}</h2>
    <p role="status">{busy ? ui("Loading published records…") : error ? '' : ui("{0} published records on this page", rows.length)}</p>
    {error&&<p role="alert">{ui("This collection is temporarily unavailable. ")}<button onClick={()=>{setBusy(true);setError(false);setRetry(n=>n+1);}}>{ui("Retry collection")}</button></p>}
    {!busy&&!error&&!rows.length&&<div className="empty"><h3>{query ? ui("No published records match this search") : ui("No approved records available")}</h3><p>{origin==='dataset' ? ui("No supplied records are currently published for this selection. Explicitly held material and unreviewed OCR remain private.") : ui("Only existing records reviewed and approved for public display appear here.")}</p></div>}
    {!busy&&!error&&<div className="record-grid">{rows.map(row=><article className="record" key={row.id}>
      {row.mime_type.startsWith('image/')&&<Link href={`/archive/${row.id}`} aria-label={ui("Open {0}", row.title)}><ArchiveImage id={row.id} title={row.title}/></Link>}
      <span className="tag">{row.material_type}</span><h3><Link href={`/archive/${row.id}`}>{row.title}</Link></h3><p>{row.description}</p><p>{ui("Source: ")}{row.source_name}</p><Link className="text-link" href={`/archive/${row.id}`}>{ui("Open record & original ↗")}</Link>
    </article>)}</div>}
    <nav className="catalogue-pagination" aria-label={ui("{0} pages", title)}><button disabled={busy||offset===0} onClick={()=>page(Math.max(0,offset-12))}>{ui("Previous page")}</button><span>{ui("Page ")}{Math.floor(offset/12)+1}</span><button disabled={busy||error||!more} onClick={()=>page(offset+12)}>{ui("Next page")}</button></nav>
  </section>;
}

export default function CollectionBrowser({collection}:{collection:keyof typeof collectionDefinitions}) {
 const {ui}=useInterface();

  const definition=collectionDefinitions[collection];
  const [draft,setDraft]=useState('');const [query,setQuery]=useState('');
  function search(event:FormEvent){event.preventDefault();setQuery(draft);}
  return <main className="page catalogue"><header className="catalogue-heading"><p className="eyebrow">{ui("The Archive / Collection")}</p><h1 tabIndex={-1}>{ui(definition.title)}</h1><p className="intro">{ui("Published, authorized sources. Open each record to inspect its original, metadata and curator-reviewed text where available.")}</p></header>
    <CollectionNavigation current={collection}/>
    {collection==='manuscripts'&&<p>{ui("Supplied images are grouped here according to the organizer dataset. This grouping does not authenticate an image as a letter or manuscript. Unknown identities and machine OCR remain unverified. ")}<Link href="/staff">{ui("Curator workspace: review identities, metadata and text.")}</Link></p>}
    <form className="filters" onSubmit={search}><label>{ui("Search this collection")}<input type="search" maxLength={200} value={draft} onChange={e=>setDraft(e.target.value)}/></label><button className="button">{ui("Search collection")}</button><button type="button" onClick={()=>{setDraft('');setQuery('');}}>{ui("Clear search")}</button></form>
    {definition.split ? <><CollectionPart key={`dataset-${query}`} title={ui("From the supplied dataset")} types={definition.types} origin="dataset" query={query}/><CollectionPart key={`other-${query}`} title={ui("Other archive content")} types={definition.types} origin="other" query={query}/></> : <CollectionPart key={query} title={ui("Published collection records")} types={definition.types} origin="" query={query}/>}
  </main>;
}
