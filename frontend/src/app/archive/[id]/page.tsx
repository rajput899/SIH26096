'use client';
import {useInterface} from '../../../components/InterfaceLanguage';

import Image from 'next/image';
import ContentTranslation from '../../../components/ContentTranslation';
import Link from 'next/link';
import RelatedExhibitions from '../../../components/RelatedExhibitions';
import SourceResearch from '../../../components/SourceResearch';
import RecordingPlayer from '../../../components/RecordingPlayer';
import ArchiveImage from '../../../components/ArchiveImage';
import { use, useEffect, useRef, useState } from 'react';
import { useKiosk } from '../../../components/Kiosk';

type Document = { dataset_authorization?: string | null; dataset_path?: string | null; dataset_collection?: string | null; provenance_status?: string; id: string; title: string; description: string; language: string; material_type: string; source_name: string; source_record_locator: string; rights_statement: string; original_filename: string; checksum: string; mime_type: string; date_value?: string | null; date_precision?: string | null; volume_number?: number | null; part_number?: number | null };
type Page = { sequence: number; page_number: number | null; start_seconds: number | null; end_seconds: number | null; text: string; confidence?: number | null };
type Detail = { document: Document; pages: Page[]; text_revision: number | null };
export default function Reader({ params }: { params: Promise<{ id: string }> }) {
 const {ui}=useInterface();

  const { id } = use(params); const { speak } = useKiosk();
  const [data, setData] = useState<Detail | null>(null); const [error, setError] = useState('');
  const [preview, setPreview] = useState(''); const [previewText, setPreviewText] = useState('');
  const [opening, setOpening] = useState(false); const [retry, setRetry] = useState(0);
  const [selected, setSelected] = useState(0); const [zoom, setZoom] = useState(100);
  const blob = useRef('');
  const [readingMode,setReadingMode]=useState<'text'|'summary'>('text');
  useEffect(() => {
    function followCitation() {
      const sequence = Number(window.location.hash.replace('#page-', ''));
      const index = data?.pages.findIndex(page => page.sequence === sequence) ?? -1;
      if (index >= 0) setSelected(index);
    }
    window.addEventListener('hashchange', followCitation);
    return () => window.removeEventListener('hashchange', followCitation);
  }, [data]);
  useEffect(() => {
    const controller = new AbortController();
    const rev = new URLSearchParams(window.location.search).get('revision');
    fetch(`/api/archive/catalog/${id}${rev ? `?revision=${encodeURIComponent(rev)}` : ''}`, { cache: 'no-store', signal: controller.signal }).then(async response => {
      if (!response.ok) { const e = await response.json().catch(() => null); throw new Error(typeof e?.detail === 'string' ? e.detail : 'Document unavailable. Check the record link or retry.'); }
      const detail = await response.json() as Detail; setData(detail); setError('');
      const sequence = Number(window.location.hash.replace('#page-', ''));
      const index = detail.pages.findIndex(page => page.sequence === sequence); if(index >= 0) setSelected(index);
      requestAnimationFrame(() => { const target = window.location.hash.slice(1); if (target) document.getElementById(target)?.scrollIntoView(); });
    }).catch(e => { if (!controller.signal.aborted) setError(e.message); });
    return () => { controller.abort(); if (blob.current) URL.revokeObjectURL(blob.current); };
  }, [id, retry]);
  async function original() {
    if (!data) return; setOpening(true);
    try {
      const response = await fetch(`/api/archive/documents/${id}/original`, { cache: 'no-store' });
      if (!response.ok) throw new Error('The original is no longer available for public access.');
      const bytes = await response.arrayBuffer();
      if (blob.current) URL.revokeObjectURL(blob.current);
      if (data.document.mime_type === 'text/plain') setPreviewText(new TextDecoder().decode(bytes));
      else { blob.current = URL.createObjectURL(new Blob([bytes], { type: data.document.mime_type })); setPreview(blob.current); }
    } catch (e) { setError(e instanceof Error ? e.message : 'Unable to open original'); }
    finally { setOpening(false); }
  }
  if (!data) return <main className="page"><h1>{ui("Document reader")}</h1>{error ? <div role="alert" className="alert">{ui(error)} <button onClick={() => setRetry(v => v + 1)}>{ui("Retry document")}</button></div> : <p role="status">{ui("Loading document…")}</p>}</main>;
  const d = data.document;
  const recording = d.mime_type.startsWith('audio/') || d.mime_type.startsWith('video/');
  const sourceDetails = <aside className="metadata"><h2>{ui("Source & provenance")}</h2><dl><dt>{ui("Title")}</dt><dd>{d.title || ui("Unknown")}</dd><dt>{ui("Source")}</dt><dd>{/^https?:\/\//.test(d.source_record_locator) ? <a href={d.source_record_locator} target="_blank" rel="noreferrer">{d.source_name} {ui(" ↗")}</a> : <span>{d.source_name} {ui(" · ")}{d.dataset_path || d.source_record_locator}</span>}</dd><dt>{ui("Recorded date")}</dt><dd>{d.date_value ? ui("{0} ({1})", d.date_value, d.date_precision || "precision not recorded") : ui("Unknown")}</dd><dt>{ui("Language")}</dt><dd>{d.language}</dd><dt>{ui("Material")}</dt><dd>{d.material_type}</dd>{d.volume_number!=null&&<><dt>{ui("Collection reference")}</dt><dd>{ui("Volume ")}{d.volume_number}{d.part_number!=null&&` · Part ${d.part_number}`}</dd></>}<dt>{ui("OCR confidence")}</dt><dd>{data.pages[selected]?.confidence != null ? ui("{0}% (machine estimate)", (data.pages[selected].confidence! * 100).toFixed(1)) : ui("Unknown — not supplied by the reviewed-text response")}</dd><dt>{ui("Text review")}</dt><dd>{data.pages.length ? ui("Curator-verified") : ui("No approved text available")}</dd><dt>{ui("Publication")}</dt><dd>{ui("Published for public access")}</dd>{d.dataset_authorization&&<><dt>{ui("Prototype display authorization")}</dt><dd>{d.dataset_authorization}</dd><dt>{ui("Supplied grouping")}</dt><dd>{d.dataset_collection} {ui(" · grouping is not historical authentication")}</dd><dt>{ui("Historical provenance")}</dt><dd>{d.provenance_status || ui("Unverified")}</dd></>}<dt>{ui("Recorded item rights")}</dt><dd>{d.rights_statement}</dd><dt>{ui("Original filename")}</dt><dd>{d.original_filename}</dd><dt>{ui("SHA-256 integrity record")}</dt><dd>{d.checksum}</dd><dt>{ui("Verified text revision")}</dt><dd>{data.text_revision ?? ui("Not available")}</dd></dl></aside>;
  const assistance = data.pages.length ? <SourceResearch key={id} id={id}/> : <section className="source" aria-label={ui("Source-specific AI unavailable")}><h2>{ui("AI-assisted reading unavailable")}</h2><p>{recording ? ui("No reviewed transcript or approved source text is available for this recording.") : ui("No reviewed text is available for this document.")} {ui(" Questions cannot be answered from unreviewed OCR, images or unsupported assumptions.")}</p></section>;
  return <main className="page source-reader"><Link className="text-link" href="/archive">{ui("← Back to Archive")}</Link><p className="eyebrow">{ui("Preserved source / Document reader")}</p><h1 tabIndex={-1} lang="en" translate="no">{d.title}</h1><p className="intro">{d.description}</p>{d.dataset_authorization&&<p className="publication-notice">{ui("Published under organizer-dataset authorization for this SIH prototype. Identity, dates, authorship and source provenance may remain unverified. Public display does not certify metadata, OCR or transcripts.")}</p>}{error && <p role="alert" className="alert">{ui(error)}</p>}
    <div className="button-row">{!recording && <button className="button" disabled={opening} onClick={() => void original()}>{opening ? ui("Opening original…") : ui("Open original scan / file")}</button>}<a className="text-link" href={`/api/archive/documents/${id}/original`}>{ui("Download preserved original")}</a></div>
    {recording && <RecordingPlayer record={d}/>}
    {!recording && <section className="archival-reader" aria-label={ui("Original and verified transcription")}>
      <div className="original-panel"><h2>{ui("Preserved original")}</h2>{d.mime_type.startsWith("image/") && !preview && <ArchiveImage id={id} title={d.title}/> }{!preview && !previewText && <p>{ui("Open the original scan to compare it with the verified text.")}</p>}
      {preview && <><label>{ui("Scan zoom")}<select value={zoom} onChange={e=>setZoom(Number(e.target.value))}><option value={100}>{ui("Fit width")}</option><option value={150}>{ui("150%")}</option><option value={200}>{ui("200%")}</option></select></label><div className="scan-viewport">{d.mime_type === 'application/pdf' ? <iframe className="reader-preview" src={`${preview}#page=${data.pages[selected]?.page_number || 1}&zoom=${zoom === 100 ? 'page-width' : zoom}`} title={ui("Original PDF: {0}", d.title)} /> : <Image unoptimized width={1200} height={1600} style={{width:`${zoom}%`,maxWidth:'none',height:'auto'}} src={preview} alt={ui("Preserved original scan: {0}", d.title)} />}</div></>}
      {previewText && <section className="text-page"><h3>{ui("Original plain-text file")}</h3><pre lang="en" translate="no">{previewText}</pre></section>}
      <p className="subtle">{ui("The preserved file is unchanged. Scan pages and printed page labels may differ.")}</p></div>
      <section className="verified-panel" aria-label={ui("Verified text")}><h2>{ui("Curator-verified text")}</h2><p>{ui("Curator-reviewed transcription, which may originate from OCR; not raw OCR or an AI summary. OCR confidence is not a guarantee of historical accuracy.")}</p>
      {!data.pages.length ? <p>{ui("No verified transcription is available. Unreviewed OCR is not shown publicly.")}</p> : <><nav className="button-row" aria-label={ui("Text pages")}><button disabled={selected === 0} onClick={()=>setSelected(n=>n-1)}>{ui("Previous page")}</button><label>{ui("Page or section")}<select value={selected} onChange={e=>setSelected(Number(e.target.value))}>{data.pages.map((p,i)=><option key={p.sequence} value={i}>{p.page_number ? ui("PDF page {0}", p.page_number) : ui("Section {0}", p.sequence)}</option>)}</select></label><button disabled={selected === data.pages.length-1} onClick={()=>setSelected(n=>n+1)}>{ui("Next page")}</button></nav>
      {data.pages.filter((_,i)=>i===selected).map(page=><article className="text-page" id={`page-${page.sequence}`} key={page.sequence}><h3>{page.page_number ? ui("Page {0}", page.page_number) : ui("Section {0}", page.sequence)}</h3><button onClick={()=>speak(page.text,d.language.toLowerCase().startsWith("hi")?"hi":"en")}>{ui("Read page aloud")}</button><pre lang={d.language.toLowerCase().startsWith("hi")?"hi":"en"} translate="no">{page.text}</pre><ContentTranslation key={`${id}:${data.text_revision}:${page.sequence}`} id={id} revision={data.text_revision!} sequence={page.sequence} sourceLanguage={d.language}/><a href={`?revision=${data.text_revision}#page-${page.sequence}`}>{ui("Link to this verified page")}</a></article>)}</>}
      {sourceDetails}{assistance}</section></section>}
    <nav className="staff-stages" aria-label={ui("Reading mode")}><button aria-pressed={readingMode==="text"} onClick={()=>setReadingMode("text")}>{ui("Full reviewed text")}</button><button aria-pressed={readingMode==="summary"} disabled={!data.pages.length} onClick={()=>setReadingMode("summary")}>{ui("AI summary & questions")}</button></nav> {readingMode==="text" && !recording && data.pages.length>0 && <section aria-label={ui("Full reviewed text")} className="full-source-text"><h2>{ui("Full reviewed text")}</h2><p className="subtle">{ui("All available verified sections in source order. The original remains accessible above; unreviewed extraction is not displayed.")}</p>{data.pages.map(page=><article className="text-page" key={page.sequence}><h3>{page.page_number ? ui("Page {0}", page.page_number) : ui("Section {0}", page.sequence)}</h3><pre lang={d.language.toLowerCase().startsWith("hi")?"hi":"en"} translate="no">{page.text}</pre><ContentTranslation key={`${id}:${data.text_revision}:${page.sequence}`} id={id} revision={data.text_revision!} sequence={page.sequence} sourceLanguage={d.language}/></article>)}</section>}
    <div className="reader-layout">{recording && sourceDetails}
      {recording && <section className="verified-panel" aria-label={ui("Verified text")}><h2>{ui("Curator-verified text")}</h2><p className="subtle">{ui("Transcription of the source, not an AI summary. Compare with the original for layout and context.")}</p>{!data.pages.length && <div className="empty"><p>{ui("No verified text is available for this document.")}</p></div>}{data.pages.map(page => <article className="text-page" id={`page-${page.sequence}`} key={page.sequence}><div className="section-heading"><h2>{page.start_seconds != null ? ui("{0}–{1} seconds", page.start_seconds, page.end_seconds) : page.page_number ? ui("Page {0}", page.page_number) : ui("Text section {0} · page unspecified", page.sequence)}</h2><button onClick={() => speak(page.text,d.language.toLowerCase().startsWith("hi")?"hi":"en")}>{ui("Read page aloud")}</button></div><pre lang={d.language.toLowerCase().startsWith("hi")?"hi":"en"} translate="no">{page.text}</pre><ContentTranslation key={`${id}:${data.text_revision}:${page.sequence}`} id={id} revision={data.text_revision!} sequence={page.sequence} sourceLanguage={d.language}/></article>)}</section>}</div>
    {recording && assistance}<RelatedExhibitions id={id}/>
  </main>;
}


