'use client';
import {useInterface} from '../../components/InterfaceLanguage';

import Link from 'next/link';
import {redirect,useSearchParams} from 'next/navigation';
import CollectionNavigation from '../../components/CollectionNavigation';
import {Suspense} from 'react';
import CollectionBrowser, {collectionDefinitions} from '../../components/CollectionBrowser';
import ArchiveImage from '../../components/ArchiveImage';
import {FormEvent,useEffect,useRef,useState} from 'react';
type RecordEntry={id:string;title:string;description:string;language:string;material_type:string;source_name:string;mime_type:string;date_value:string|null;date_precision:string|null;volume_number:number|null;part_number:number|null};
type Filters={q:string;language:string;material_type:string;sort:string;volume:string};
const initial:Filters={q:'',language:'',material_type:'',sort:'title',volume:''};
const pageSize=24;
export default function Archive(){
 const {ui}=useInterface();

 return <Suspense fallback={<main className="page"><p role="status">{ui("Loading collection…")}</p></main>}><ArchiveRoute/></Suspense>;
}
function ArchiveRoute(){
 const {ui}=useInterface();

 const params=useSearchParams();const collection=params.get("collection")||"";
 if(collection==='audio')redirect('/speeches');
 if(collection==='media')return <main className="page catalogue"><header className="catalogue-heading"><p className="eyebrow">{ui("The Archive / Collection")}</p><h1>{ui("Media")}</h1><p className="intro">{ui("Explore photographs and videos approved for public display. Each collection separates supplied dataset content from other approved archive records.")}</p></header><CollectionNavigation/><section aria-labelledby="media-photos"><h2 id="media-photos">{ui("Photographs")}</h2><p>{ui("Inspect approved images, preserved originals and their provenance.")}</p><Link className="button" href="/archive?collection=photographs">{ui("Browse photographs →")}</Link></section><section aria-labelledby="media-videos"><h2 id="media-videos">{ui("Videos")}</h2><p>{ui("Open approved recordings with protected playback and reviewed transcripts where available.")}</p><Link className="button" href="/archive?collection=videos">{ui("Browse videos →")}</Link></section><p>{ui("Published audio and MP3 recordings remain in ")}<Link href="/speeches">{ui("Speeches & Recordings")}</Link>{ui(".")}</p></main>;
 return Object.hasOwn(collectionDefinitions,collection) ? <CollectionBrowser key={collection} collection={collection as keyof typeof collectionDefinitions}/> : <Catalogue/>;
}
function Catalogue(){
 const {ui}=useInterface();

 const [records,setRecords]=useState<RecordEntry[]>([]);const [busy,setBusy]=useState(true);const [error,setError]=useState('');
 const [draft,setDraft]=useState(initial);const [filters,setFilters]=useState(initial);const [offset,setOffset]=useState(0);const [more,setMore]=useState(false);const [retry,setRetry]=useState(0);
 const results=useRef<HTMLHeadingElement>(null);
 useEffect(()=>{const controller=new AbortController();const params=new URLSearchParams({...filters,offset:String(offset),limit:String(pageSize+1)});if(!filters.volume)params.delete('volume');
   fetch(`/api/archive/catalog?${params}`,{cache:'no-store',signal:controller.signal}).then(async r=>{if(!r.ok)throw Error('The archive is temporarily unavailable. Please try again.');const rows:RecordEntry[]=await r.json();setRecords(rows.slice(0,pageSize));setMore(rows.length>pageSize);setError('');})
   .catch(()=>{if(!controller.signal.aborted)setError('The archive is temporarily unavailable. Please try again.');}).finally(()=>{if(!controller.signal.aborted)setBusy(false);});
   return()=>controller.abort();
 },[filters,offset,retry]);
 function search(e:FormEvent){e.preventDefault();setBusy(true);setError('');setOffset(0);setFilters({...draft});}
 function paginate(start:number){setBusy(true);setOffset(start);results.current?.focus();}
 function field(key:keyof Filters,value:string){setDraft({...draft,[key]:value});}
 return <main className="page catalogue"><header className="catalogue-heading"><p className="eyebrow">{ui("02 / Read the source")}</p><h1>{ui("The Archive")}</h1><p className="intro">{ui("Discover published records. Read reviewed text, inspect preserved originals and follow each source’s provenance.")}</p></header>
 <CollectionNavigation/>
 <form className="filters catalogue-filters" onSubmit={search} aria-label={ui("Search the archive")}>
 <label className="catalogue-search">{ui("Search title or description")}<input type="search" maxLength={200} value={draft.q} onChange={e=>field('q',e.target.value)} placeholder={ui("A title, phrase or subject…")}/></label>
 <label>{ui("Document language")}<input value={draft.language} maxLength={80} onChange={e=>field('language',e.target.value)} placeholder={ui("Any language (exact name)")}/></label>
 <label>{ui("Material type")}<select value={draft.material_type} onChange={e=>field('material_type',e.target.value)}><option value="">{ui("All materials")}</option>{[['document','Documents'],['image','Images (identity unverified)'],['manuscript','Manuscripts'],['photograph','Photographs'],['speech','Speeches'],['audio','Audio'],['video','Video']].map(([value,label])=><option key={value} value={value}>{ui(label)}</option>)}</select></label>
 <label>{ui("Volume")}<input type="number" min="1" max="100" value={draft.volume} onChange={e=>field('volume',e.target.value)} placeholder={ui("All volumes")}/></label>
 <label>{ui("Sort")}<select value={draft.sort} onChange={e=>field('sort',e.target.value)}><option value="title">{ui("Title")}</option><option value="newest">{ui("Recently added")}</option><option value="oldest">{ui("Oldest additions")}</option></select></label>
 <div className="button-row"><button className="button" disabled={busy}>{ui("Search archive")}</button><button type="button" disabled={busy} onClick={()=>{setDraft(initial);setFilters({...initial});setOffset(0);setBusy(true);setError('');}}>{ui("Clear filters")}</button></div></form>
 <div className="catalogue-results"><h2 ref={results} tabIndex={-1}>{ui("Published records")}</h2><p role="status">{busy ? ui("Loading published records…") : error ? '' : records.length ? ui("{0}–{1} shown{2}", offset+1, offset+records.length, more?' · more records available':'') : ui("0 records shown")}</p></div>
 {error&&<div className="alert" role="alert">{ui(error)} <button onClick={()=>{setBusy(true);setError('');setRetry(n=>n+1);}}>{ui("Retry archive")}</button></div>}
 {!busy&&!error&&!records.length&&<section className="empty"><h2>{ui("No published documents found")}</h2><p>{ui("Try fewer filters or another search. Only records approved for public access appear here; unpublished material is not included.")}</p></section>}
 {!busy&&!error&&<div className="record-grid catalogue-grid">{records.map(record=><article className="record catalogue-record" key={record.id}>
 <div className="catalogue-visual">{record.mime_type.startsWith('image/') ? <Link href={`/archive/${record.id}`} aria-label={ui("Open {0}",record.title)}><ArchiveImage id={record.id} title={record.title}/></Link> : <div className="record-mark" aria-hidden="true"><span>{record.material_type}</span><div/><div/><div/></div>}</div>
 <div><p className="tag">{record.material_type} {ui(" / ")}{record.language}</p><h2><Link href={`/archive/${record.id}`}>{record.title}</Link></h2><p>{record.description}</p>
 <dl className="catalogue-metadata"><div><dt>{ui("Source")}</dt><dd>{record.source_name}</dd></div>{record.date_value&&<div><dt>{ui("Recorded date")}</dt><dd>{record.date_value}{record.date_precision&&` (${record.date_precision})`}</dd></div>}{record.volume_number!=null&&<div><dt>{ui("Collection reference")}</dt><dd>{ui("Volume ")}{record.volume_number}{record.part_number!=null&&` · Part ${record.part_number}`}</dd></div>}<div><dt>{ui("Access")}</dt><dd>{ui("Published for public access · text review shown in reader")}</dd></div></dl>
 <Link className="text-link" href={`/archive/${record.id}`}>{ui("Read record & original ↗")}</Link></div></article>)}</div>}
 <nav className="catalogue-pagination" aria-label={ui("Archive pages")}><button disabled={busy||offset===0} onClick={()=>paginate(Math.max(0,offset-pageSize))}>{ui("Previous page")}</button><span>{ui("Page ")}{Math.floor(offset/pageSize)+1}</span><button disabled={busy||!!error||!more} onClick={()=>paginate(offset+pageSize)}>{ui("Next page")}</button></nav>
 </main>;
}

