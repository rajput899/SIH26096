'use client';
import {useState} from 'react';
import {useInterface} from './InterfaceLanguage';
type Translation={translation:string;source:{reader_url:string;text_sha256:string;revision:number;sequence:number};provider:string;machine_generated:boolean};
export default function ContentTranslation({id,revision,sequence,sourceLanguage}:{id:string;revision:number;sequence:number;sourceLanguage:string}){
 const {ui,languages}=useInterface();const [result,setResult]=useState<Translation|null>(null);const [error,setError]=useState('');const [busy,setBusy]=useState(false);
 const supported=['english','en'].includes(sourceLanguage.toLowerCase())&&languages.some(l=>l.code==='hi'&&l.enabled);
 async function translate(){setBusy(true);setError('');setResult(null);try{const response=await fetch(`/api/archive/documents/${id}/translation`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({revision,sequence,target_language:'hi',fallback:'none'})});if(!response.ok)throw Error();setResult(await response.json());}catch{setError('Translation unavailable. Original verified text remains available.');}finally{setBusy(false);}}
 return <section aria-label={ui('Optional content translation')} className="source" data-testid="content-translation">
  <h3>{ui('Optional content translation')}</h3><p>{ui('Only this public, verified section will be sent to Bhashini when you request translation. The original and citations stay unchanged.')}</p>
  <button disabled={!supported||busy} onClick={()=>void translate()}>{ui(busy?'Translating…':'Translate this verified section into Hindi')}</button>
  {!supported&&<p>{ui('Only verified English → Hindi translation is currently available. This source or service is not eligible.')}</p>}
  {error&&<p role="alert">{ui(error)}</p>}
  {result&&<><p>{ui('Machine translation · unreviewed. Compare with the original.')}</p><pre lang="hi" translate="no">{result.translation}</pre><a href={result.source.reader_url}>{ui('Open exact source section')}</a><p>{ui('Source text SHA-256: ')}<code>{result.source.text_sha256}</code></p><button onClick={()=>setResult(null)}>{ui('Hide translation')}</button></>}
 </section>;
}
