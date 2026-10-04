'use client';
import {useInterface} from './InterfaceLanguage';

import Link from 'next/link';
import {useEffect,useRef,useState} from 'react';
type Recording={id:string;title:string;description:string;mime_type:string;language:string;rights_statement:string;source_name?:string;source_record_locator?:string};
type Cue={start:number;end:number;text:string};
export default function RecordingPlayer({record}:{record:Recording}){
 const {ui}=useInterface();

 const ref=useRef<HTMLMediaElement|null>(null);const track=useRef<TextTrack|null>(null);
 const [cues,setCues]=useState<Cue[]>([]);const [message,setMessage]=useState('Loading reviewed transcript…');const [time,setTime]=useState(0);const [search,setSearch]=useState('');
 useEffect(()=>{const c=new AbortController();fetch(`/api/archive/documents/${record.id}/recording`,{cache:'no-store',signal:c.signal}).then(async r=>{if(!r.ok)throw Error();const d=await r.json();setCues(d?.transcript||[]);setMessage('');}).catch(()=>{if(!c.signal.aborted)setMessage('Transcript unavailable. Reload to retry.');});return()=>c.abort();},[record.id]);
 useEffect(()=>{const media=ref.current;if(!media||!record.mime_type.startsWith('video/')||!cues.length||typeof VTTCue==='undefined')return;
  const captions=track.current||media.addTextTrack('captions','Reviewed transcript');track.current=captions;
  if(captions.cues)Array.from(captions.cues).forEach(c=>captions.removeCue(c));
  cues.forEach(c=>captions.addCue(new VTTCue(c.start,c.end,c.text)));captions.mode='showing';
  return()=>{if(captions.cues)Array.from(captions.cues).forEach(c=>captions.removeCue(c));};
 },[cues,record.mime_type]);
 const src=`/api/archive/documents/${record.id}/playback`;
 const filtered=cues.filter(c=>c.text.toLocaleLowerCase().includes(search.toLocaleLowerCase()));
 return <article className="source recording-reader"><h2>{record.title}</h2><p>{record.description}</p><p>{record.language} {ui(" · Rights: ")}{record.rights_statement}</p><p>{ui("Source: ")}{record.source_record_locator ? <a href={record.source_record_locator} target="_blank" rel="noreferrer">{record.source_name||ui("Source record")}</a> : ui("Not recorded")}</p>
 {record.mime_type.startsWith('video/') ? <video ref={e=>{ref.current=e;}} controls preload="metadata" src={src} aria-label={record.title} onTimeUpdate={e=>setTime(e.currentTarget.currentTime)} onError={()=>setMessage('Playback unavailable. This browser may not support the recording format.')}/> : <audio ref={e=>{ref.current=e;}} controls preload="metadata" src={src} aria-label={record.title} onTimeUpdate={e=>setTime(e.currentTarget.currentTime)} onError={()=>setMessage('Playback unavailable. Please try again.')}/>}
 <label>{ui("Playback speed")}<select defaultValue="1" onChange={e=>{if(ref.current)ref.current.playbackRate=Number(e.target.value);}}>{[0.75,1,1.25,1.5,2].map(n=><option key={n} value={n}>{n}{ui("×")}</option>)}</select></label><p role="status">{ui(message)}</p>
 <h3>{ui("Curator-verified transcript")}</h3>{cues.length>0&&<><p className="subtle">{ui("Read independently, or select a timestamp to listen. Highlighting follows the reviewed cue timings.")}</p><label>{ui("Search this transcript")}<input value={search} onChange={e=>setSearch(e.target.value)}/></label></>}
 {!cues.length&&!message&&<p>{ui("No verified transcript available. Transcript-based AI assistance is unavailable for this recording.")}</p>}
 <div className="transcript-cues">{filtered.map((c,i)=><div className="transcript-cue" data-active={time>=c.start&&time<c.end} key={`${c.start}-${i}`}><button aria-label={ui("Play from {0} seconds", c.start.toFixed(1))} onClick={()=>{if(ref.current){ref.current.currentTime=c.start;setTime(c.start);void ref.current.play().catch(()=>setMessage('Press Play to begin playback.'));}}}>{c.start.toFixed(1)}{ui("–")}{c.end.toFixed(1)} {ui(" seconds")}</button><p>{c.text}</p></div>)}</div>
 {cues.length>0&&<p><Link href={`/ai?source=${record.id}`}>{ui("Ask about this verified transcript")}</Link></p>}{cues.length>0&&!filtered.length&&<p>{ui("No matching transcript segments.")}</p>}</article>;
}
