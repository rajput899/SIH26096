'use client';
import {useInterface} from '../../components/InterfaceLanguage';

import Link from 'next/link';
import { FormEvent, useEffect, useRef, useState } from 'react';
import { useKiosk } from '../../components/Kiosk';

type Source = { passage_id: string; title: string; page_number: number | null; start_seconds: number | null; end_seconds: number | null; sequence: number; revision: number; excerpt: string; reader_url: string; original_url: string };
type Response = { reason?: string; status: string; message: string; warning: string; paragraphs: { text: string; evidence: { passage_id: string; quote: string }[] }[]; sources: Source[] };
type Turn = { question: string; response: Response };
export default function AI() {
 const {ui}=useInterface();

  const { speak } = useKiosk(); const [question, setQuestion] = useState('');
  const [turns, setTurns] = useState<Turn[]>([]); const [busy, setBusy] = useState(false);
  const [error, setError] = useState(''); const [language, setLanguage] = useState('');
  const [source, setSource] = useState('');
  const [catalog, setCatalog] = useState<{id:string;title:string}[]>([]);
  const [volume,setVolume]=useState(''); const [pageFilter,setPageFilter]=useState('');
  const [type, setType] = useState(''); const abort = useRef<AbortController | null>(null);
  const [provider, setProvider] = useState<{ provider: string; message: string; cloud: boolean; retrieval_message: string } | null>(null);
  useEffect(() => { fetch('/api/archive/research/provider', { cache: 'no-store' }).then(r => r.ok ? r.json() : null).then(setProvider).catch(() => setProvider(null)); }, []);
  const [suggestions,setSuggestions] = useState<string[]>([]);
  useEffect(()=>{fetch('/api/archive/catalog',{cache:'no-store'}).then(r=>r.ok?r.json():[]).then(rows=>{setCatalog(rows);const requested=new URLSearchParams(window.location.search).get('source');if(requested && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(requested)){setSource(requested);if(!rows.some((r:{id:string})=>r.id===requested))setCatalog([...rows,{id:requested,title:'Selected source (availability checked when answering)'}]);}setSuggestions(rows.filter((r:{current_text_revision:number|null})=>r.current_text_revision).slice(0,3).map((r:{title:string})=>`What does ${r.title} say?`));}).catch(()=>setSuggestions([]));},[]);
  const last = useRef(''); const result = useRef<HTMLDivElement>(null);
  useEffect(() => () => abort.current?.abort(), []);
  async function ask(text: string) {
    if (text.trim().length < 2 || busy) return;
    setBusy(true); setError(''); last.current = text;
    const controller = new AbortController(); abort.current = controller;
    try {
      const response = await fetch('/api/archive/research/ask', { method: 'POST', headers: { 'Content-Type': 'application/json' }, signal: controller.signal, body: JSON.stringify({ question: text, history: turns.slice(-4).map(t => t.question), language, material_type: type, item_id: source || null, volume:volume?Number(volume):null, page:pageFilter?Number(pageFilter):null }) });
      if (!response.ok) { const body = await response.json().catch(() => ({ detail: 'The research service is unavailable. Please retry.' })); throw new Error(typeof body.detail === 'string' ? body.detail : 'The research service is unavailable. Please retry.'); }
      const answer = await response.json() as Response;
      setTurns(items => [...items.slice(-9), { question: text, response: answer }]); setQuestion('');
      requestAnimationFrame(() => result.current?.focus());
    } catch (e) { if (!controller.signal.aborted) setError(e instanceof Error ? e.message : 'Unable to reach the assistant.'); }
    finally { if (!controller.signal.aborted) setBusy(false); }
  }
  function submit(e: FormEvent) { e.preventDefault(); void ask(question); }
  function clear() { abort.current?.abort(); setTurns([]); setQuestion(''); setError(''); setBusy(false); setSource(''); }
  return <main className="page"><p className="eyebrow">{ui("01 / Ask with evidence")}</p><h1>{ui("AI Research Assistant")}</h1><p className="intro">{ui("A question is a starting point. Explore answers grounded in curator-verified, published archive text — and read the sources for yourself.")}</p>
    <p role="status" className="publication-notice">{provider ? ui("{0}: {1}", provider.provider, provider.message) : ui("Provider status unavailable.")}{provider && ` ${provider.retrieval_message || ""}`}{provider?.cloud && " Questions and retrieved public excerpts are sent to Google Gemini. Do not enter personal information."}</p><div className="ai-layout"><section className="assistant-panel" aria-label={ui("Research conversation")}><div className="assistant-heading"><span className="tag">{ui("Source-grounded research")}</span><button onClick={clear}>{ui("Clear conversation")}</button></div><div className="conversation">
      {!turns.length && <div><h2>{ui("What would you like to explore?")}</h2><p>{ui("Ask about writings, speeches or debates represented in the archive. An answer depends on the sources currently available.")}</p><div className="suggestions">{suggestions.map(text => <button key={text} onClick={() => setQuestion(text)}>{text}</button>)}</div></div>}
      {turns.map((turn, i) => <article key={i} aria-label={ui("Question {0}", i + 1)}><h2 className="question-bubble">{turn.question}</h2><div className="answer"><p className="tag">{turn.response.status === 'answered' ? ui("AI-generated summary") : ['greeting','scope'].includes(turn.response.status) ? ui("Archive assistant") : turn.response.reason === 'provider_abstained' ? ui("Model abstained") : turn.response.status === 'insufficient_sources' ? ui("Evidence unavailable") : ui("Research service result")}</p><p lang="en" translate="no">{turn.response.message}</p>{turn.response.warning && <p className="alert">{turn.response.warning}</p>}
        {turn.response.paragraphs.map((p, n) => <div key={n}><p lang="en" translate="no">{p.text}</p><div className="button-row">{p.evidence.map((e, j) => { const s = turn.response.sources.find(source => source.passage_id === e.passage_id); return s ? <a className="text-link" key={j} href={`#source-${i}-${e.passage_id}`}>{ui("Source: ")}{s.title}{s.start_seconds != null ? ui(" · {0}–{1} seconds", s.start_seconds, s.end_seconds) : s.page_number ? ui(" · p. {0}", s.page_number) : ui(" · page unspecified")}</a> : null; })}</div></div>)}
        {turn.response.paragraphs.length > 0 && <button onClick={() => speak(turn.response.paragraphs.map(p => p.text).join('\n'))}>{ui("Read answer aloud")}</button>}
        {turn.response.sources.length > 0 && <section aria-label={ui("Original source excerpts")}><h3>{ui("Verified source excerpts")}</h3><p className="subtle">{ui("Transcribed source text, not generated summaries. Page and time locators come from the archive record.")}</p>{turn.response.sources.map(s => <details className="source" id={`source-${i}-${s.passage_id}`} key={s.passage_id}><summary>{s.title} {ui(" · ")}{s.start_seconds != null ? ui("{0}–{1} seconds", s.start_seconds, s.end_seconds) : s.page_number ? ui("Page {0}", s.page_number) : ui("Section {0}, page unspecified", s.sequence)} {ui(" · Revision ")}{s.revision}</summary><blockquote lang="en" translate="no">{s.excerpt}</blockquote><div className="button-row"><Link className="text-link" href={s.reader_url}>{ui("Read verified source")}</Link><a className="text-link" href={s.original_url}>{ui("Open preserved original")}</a><button onClick={() => speak(s.excerpt)}>{ui("Read excerpt aloud")}</button></div></details>)}</section>}
        {turn.response.status === 'model_unavailable' && <button disabled={busy} onClick={() => void ask(turn.question)}>{ui("Retry answer")}</button>}
      </div></article>)}
      <div ref={result} tabIndex={-1} role="status">{busy ? ui("Processing your question…") : turns.length ? ui("Response ready. Supporting excerpts appear when available.") : ''}</div>
      {error && <div role="alert" className="alert">{ui(error)} <button onClick={() => void ask(last.current)}>{ui("Retry question")}</button></div>}
    </div><form className="ask-form" onSubmit={submit}><label htmlFor="question">{ui("Your question")}<textarea id="question" value={question} onChange={e => setQuestion(e.target.value)} minLength={2} maxLength={1200} required placeholder={ui("Ask a question about the archive…")} /></label><label>{ui("Research scope")}<select value={source} onChange={e => { setSource(e.target.value); setTurns([]); }}><option value="">{ui("All eligible archive sources")}</option>{catalog.map(item => <option key={item.id} value={item.id}>{item.title}</option>)}</select></label>{source && <button type="button" disabled={busy} onClick={() => void ask("Summarize this source")}>{ui("Summarize selected source")}</button>}<details><summary>{ui("Filter source documents")}</summary><div className="filters"><label>{ui("Verified volume")}<input type="number" min="1" max="100" value={volume} onChange={e=>setVolume(e.target.value)}/></label><label>{ui("PDF page")}<input type="number" min="1" value={pageFilter} onChange={e=>setPageFilter(e.target.value)}/></label><label>{ui("Document language")}<input value={language} onChange={e => setLanguage(e.target.value)} maxLength={80} placeholder={ui("Any language (exact name)")} /></label><label>{ui("Material type")}<select value={type} onChange={e => setType(e.target.value)}><option value="">{ui("All materials")}</option><option value="document">{ui("Documents")}</option><option value="manuscript">{ui("Manuscripts")}</option><option value="photograph">{ui("Photographs")}</option><option value="speech">{ui("Speeches")}</option><option value="audio">{ui("Audio")}</option><option value="video">{ui("Video")}</option></select></label></div></details><div className="button-row"><span className="subtle">{ui("Questions remain in this visit’s memory.")}</span><button className="button" disabled={busy || question.trim().length < 2}>{busy ? ui("Working…") : ui("Ask the archive →")}</button></div></form></section>
    <aside className="research-note"><div><p className="eyebrow">{ui("Research with care")}</p><h2>{ui("Evidence comes first.")}</h2><p>{ui("Only curator-verified text from public, published documents can support answers. Sources are checked again before a response is returned.")}</p><p>{ui("AI summaries can still misinterpret a source. Always compare the cited excerpt and original.")}</p></div><div><h2>{ui("A source-linked reading companion.")}</h2><p>{ui("Model and search availability depend on this kiosk’s configuration. If a model is unavailable, you can still browse the archive and read retrieved excerpts.")}</p><Link className="text-link" href="/archive">{ui("Browse the archive ↗")}</Link></div></aside></div>
  </main>;
}

