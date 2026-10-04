'use client';
import {useInterface} from './InterfaceLanguage';

import { FormEvent, useRef, useState } from 'react';

export default function UploadSteps({onSubmit,busy}:{onSubmit:(event:FormEvent<HTMLFormElement>)=>Promise<void>;busy:boolean}) {
 const {ui}=useInterface();

  const [step,setStep]=useState(1); const [fileInfo,setFileInfo]=useState('');
  const form=useRef<HTMLFormElement>(null);
  const input='block w-full rounded border border-slate-300 bg-white p-2 mt-1';
  function next(){
    const fields=form.current?.querySelectorAll<HTMLInputElement|HTMLSelectElement|HTMLTextAreaElement>(`[data-step="${step}"] input, [data-step="${step}"] select, [data-step="${step}"] textarea`);
    if(fields && [...fields].every(field=>field.reportValidity()))setStep(n=>n+1);
  }
  return <form ref={form} onSubmit={onSubmit} onReset={()=>{setStep(1);setFileInfo('');}} className="mt-4">
    <p role="status">{ui("Step ")}{step} {ui(" of 3 · ")}{ui(['Upload','Basic details','Source and rights'][step-1])}</p>
    <fieldset data-step="1" hidden={step!==1}><legend>{ui("1. Choose an original")}</legend>
      <label>{ui("Original file · PDF, image, text, WAV, MP3 or H.264/AAC MP4 · 10 MiB maximum")}<input name="file" type="file" accept="application/pdf,image/png,image/jpeg,text/plain,audio/wav,audio/mpeg,video/mp4" required className={input} onChange={e=>{const file=e.target.files?.[0];e.target.setCustomValidity(file && file.size>10*1024*1024?'This file exceeds the current 10 MiB limit. Keep the original; do not split or compress it to bypass preservation safeguards.':'');setFileInfo(file?`${file.name} · ${(file.size/1024/1024).toFixed(2)} MiB · ${file.type || 'Type checked by server'}`:'');const type=form.current?.elements.namedItem('material_type') as HTMLSelectElement|null;if(file&&type)type.value=file.type.startsWith('image/')?'photograph':file.type.startsWith('audio/')?'speech':file.type.startsWith('video/')?'video':'document';}} /></label>
      <p>{fileInfo}</p><p className="subtle">{ui("PDF processing currently supports up to 50 pages. Large-volume ingestion needs a separately validated workflow.")}</p>
    </fieldset>
    <fieldset data-step="2" hidden={step!==2}><legend>{ui("2. Describe the material")}</legend>
      {[['title','Title'],['language','Language']].map(([name,label])=><label key={name}>{ui(label)}<input name={name} maxLength={200} required className={input}/></label>)}
      <label>{ui("Material type")}<select name="material_type" className={input}><option value="document">{ui("Document")}</option><option value="manuscript">{ui("Manuscript / letter")}</option><option value="photograph">{ui("Photograph")}</option><option value="speech">{ui("Speech / audio")}</option><option value="video">{ui("Video")}</option></select></label>
      <label>{ui("Description")}<textarea name="description" maxLength={2000} className={input}/></label>
    </fieldset>
    <fieldset data-step="3" hidden={step!==3}><legend>{ui("3. Record source and rights")}</legend>
      <p>{ui("Use verified source details. Access to a file does not establish permission. Keep uncertain material outside the public archive pending review.")}</p>
      {[['source_name','Source name'],['source_locator','Verified source URL'],['source_record_locator','Source record URL'],['rights_statement','Rights / permission statement']].map(([name,label])=><label key={name}>{ui(label)}<input name={name} type={name.includes('locator')?'url':'text'} maxLength={name==='rights_statement'?1000:200} required className={input}/></label>)}
      <label>{ui("Access after publication")}<select name="access_level" className={input}><option value="staff">{ui("Staff only")}</option><option value="public">{ui("Public")}</option></select></label>
      <label><input type="checkbox" required/> {ui(" I checked the source locator and permission to preserve this file under the stated rights.")}</label>
      <p>{ui("Preserving the original does not publish it. Next: processing → review and correction → verification → separate publication decision.")}</p>
    </fieldset>
    <div className="button-row">{step>1&&<button type="button" disabled={busy} onClick={()=>setStep(n=>n-1)}>{ui("Back")}</button>}{step<3 ? <button type="button" className="button" onClick={next}>{ui("Continue")}</button> : <button className="button" disabled={busy}>{busy?ui("Preserving original…"):ui("Preserve original")}</button>}</div>
  </form>;
}
