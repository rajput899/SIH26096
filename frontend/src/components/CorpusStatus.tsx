'use client';
import {useInterface} from './InterfaceLanguage';

import {FormEvent,useState} from 'react';
type Row={checksum:string;relative_path:string;item_id:string|null;page_count:number|null;
  state:string;extracted_pages:number;ocr_pending_pages:number;failed_pages:number;index_status:string|null;
  metadata:{candidate_volume?:number;candidate_part?:number;transcript_status?:string;playback_status?:string}};
type Page={page_number:number;status:string;error:string|null;result:{text:string;warning:string;confidence?:number|null;extraction_method?:string}|null};
export default function CorpusStatus({api,canReview=false}:{canReview?:boolean;api:(path:string,options?:RequestInit)=>Promise<Response>}){
 const {ui}=useInterface();

  const [reviewId,setReviewId]=useState('');const [reviewBusy,setReviewBusy]=useState(false);
  const [rows,setRows]=useState<Row[]>([]);const [message,setMessage]=useState('');
  const [pages,setPages]=useState<Page[]>([]);const [selected,setSelected]=useState('');const [offset,setOffset]=useState(0);
  async function refresh(){try{setRows(await (await api('staff/corpus')).json());setMessage('Inventory refreshed.');}catch(e){setMessage(e instanceof Error?e.message:'Inventory unavailable');}}
  async function view(id:string,start=0){try{setPages(await (await api(`staff/corpus/${id}/pages?offset=${start}`)).json());setSelected(id);setOffset(start);}catch(e){setMessage(e instanceof Error?e.message:'Pages unavailable');}}
  async function review(event:FormEvent<HTMLFormElement>){event.preventDefault();const form=new FormData(event.currentTarget);setReviewBusy(true);try{await api(`staff/corpus/${reviewId}/source-review`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({source_locator:form.get('source'),rights_statement:form.get('rights'),public_display_approved:form.get('public')==='on',volume_number:form.get('volume')?Number(form.get('volume')):null,part_number:form.get('part')?Number(form.get('part')):null,language:form.get('language')})});setReviewId('');await refresh();setMessage('Source review recorded. Content verification and publication remain separate. Refresh staff records to see the change.');}catch(e){setMessage(e instanceof Error?e.message:'Review failed');}finally{setReviewBusy(false);}}
  return <details className="source" onToggle={e=>{if(e.currentTarget.open&&!rows.length)void refresh();}}>
    <summary>{ui("Dataset ingestion and page checkpoints")}</summary>
    <p>{ui("Machine extraction remains unverified. Organizer authorization permits public originals from the frozen dataset, except explicit holds. Other uploads still require source and rights review. Volume numbers below are filename candidates awaiting edition review.")}</p>
    <button onClick={()=>void refresh()}>{ui("Refresh ingestion progress")}</button><p role="status">{ui(message)}</p>
    {rows.map(row=><section className="source" key={row.checksum}><h3>{row.relative_path}</h3>
      <p>{row.state} {ui(" · ")}{row.page_count ? ui("{0}/{1} pages extracted · {2} OCR pending · {3} failed", row.extracted_pages, row.page_count, row.ocr_pending_pages, row.failed_pages) : ui("Media/reference item")} {ui(" · Research index: ")}{row.index_status || ui("not eligible")}</p>
      {row.metadata.candidate_volume&&<p>{ui("Candidate volume ")}{row.metadata.candidate_volume}{row.metadata.candidate_part&&` · Part ${row.metadata.candidate_part}`}</p>}
      {row.metadata.transcript_status&&<p>{ui("Transcript: ")}{row.metadata.transcript_status}</p>}
      {row.metadata.playback_status&&<p>{row.metadata.playback_status}</p>}
      {canReview&&row.item_id&&<button onClick={()=>setReviewId(row.item_id!)}>{ui("Review source and rights for ")}{row.relative_path}</button>}{row.item_id&&row.page_count&&<button onClick={()=>void view(row.item_id!)}>{ui("Inspect extracted pages")}</button>}
    </section>)}
    {reviewId&&<form onSubmit={review} className="source"><h3>{ui("Explicit source and rights review")}</h3><p>{ui("Record independently checked evidence. This action does not publish anything.")}</p><label>{ui("Verified acquisition or source URL")}<input name="source" type="url" required/></label><label>{ui("Evidence and permission statement")}<textarea name="rights" minLength={10} maxLength={1000} required/></label><label>{ui("Verified language")}<input name="language" required maxLength={80}/></label><label>{ui("Verified volume (optional)")}<input name="volume" type="number" min="1" max="100"/></label><label>{ui("Verified part (optional)")}<input name="part" type="number" min="1"/></label><label><input name="public" type="checkbox"/> {ui(" The reviewed rights permit public display")}</label><label><input type="checkbox" required/> {ui(" I independently checked provenance and the stated permission")}</label><button disabled={reviewBusy}>{ui("Record source review")}</button><button type="button" onClick={()=>setReviewId('')}>{ui("Cancel review")}</button></form>}
    {selected&&<section aria-label={ui("Checkpoint pages")}><h3>{ui("Machine-extracted page preview")}</h3>{pages.map(page=><article key={page.page_number}><h4>{ui("Physical page ")}{page.page_number} {ui(" · ")}{page.status}</h4><p>{page.error || page.result?.warning}</p><p className="subtle">{ui("Method: ")}{page.result?.extraction_method || ui("Not recorded")} {ui(" · OCR confidence: ")}{page.result?.confidence!=null ? ui("{0}% (machine estimate, not verification)", (page.result.confidence*100).toFixed(1)) : ui("Not available")}</p><pre className="original-text whitespace-pre-wrap">{page.result?.text}</pre></article>)}<button disabled={offset===0} onClick={()=>void view(selected,Math.max(0,offset-25))}>{ui("Previous 25 pages")}</button><button disabled={pages.length<25} onClick={()=>void view(selected,offset+25)}>{ui("Next 25 pages")}</button></section>}
  </details>;
}

