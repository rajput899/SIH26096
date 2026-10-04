'use client';
import {useInterface} from '../../components/InterfaceLanguage';


import { useState } from 'react';

type Revision = { revision: number; status: string; review_note: string; verified_at: string | null };
type Segment = { sequence: number; page_number: number | null; text: string; extraction_method: string; warning: string | null; confidence: number | null };
type TextRecord = { current_revision: number | null; snapshot: Revision | null; revisions: Revision[]; segments: Segment[]; total_segments: number };
type Job = { status: string; attempts: number; error: string | null; mode: string };

export default function ProcessingReview({ id, api, onChanged }: {
  id: string; api: (path: string, options?: RequestInit) => Promise<Response>; onChanged: () => Promise<void>;
}) {
 const {ui}=useInterface();

  const [job, setJob] = useState<Job | null>(null);
  const [text, setText] = useState<TextRecord | null>(null);
  const [pages, setPages] = useState<Segment[]>([]);
  const [note, setNote] = useState('');
  const [compared, setCompared] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const [mode, setMode] = useState('auto');
  const [offset, setOffset] = useState(0);
  const base = `staff/documents/${id}`;

  async function load(revision?: number, start = offset) {
    const [jobResponse, textResponse] = await Promise.all([
      api(`${base}/processing`), api(`${base}/text?offset=${start}${revision ? `&revision=${revision}` : ''}`),
    ]);
    const record = await textResponse.json() as TextRecord;
    setOffset(start); setJob(await jobResponse.json()); setText(record); setPages(record.segments); setCompared(false);
  }

  async function run(work: () => Promise<void>) {
    setBusy(true); setMessage('');
    try { await work(); } catch (error) { setMessage(error instanceof Error ? error.message : 'Processing request failed'); }
    finally { setBusy(false); }
  }

  async function post(path: string, body: unknown) {
    await api(`${base}/${path}`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
    await load(); await onChanged();
  }

  const current = text?.snapshot?.revision === text?.current_revision;
  const dirty = pages.some((page, index) => page.text !== text?.segments[index]?.text);
  const button = 'rounded border border-slate-400 px-3 py-2 disabled:opacity-40';
  return <details className="mt-5 border-t pt-4" onToggle={event => {
    if (event.currentTarget.open && !text && !busy) void run(() => load());
  }}>
    <summary className="cursor-pointer font-semibold">{ui("Document processing and text review")}</summary>
    <p className="text-sm my-3">{ui("Extraction never changes the original. Page numbers are physical PDF/image pages; plain text has no page number. OCR can be wrong and must be compared with the original.")}</p>
    <button className={button} disabled={busy} onClick={() => void run(() => load())}>{ui("Refresh processing status")}</button>
    {text && !job && <div className="flex flex-wrap gap-3 mt-3">
      <label>{ui("Extraction mode ")}<select value={mode} onChange={e => setMode(e.target.value)} className="border p-2">
        <option value="auto">{ui("Embedded text, OCR for pages without text")}</option><option value="ocr">{ui("Force OCR of every page")}</option>
      </select></label>
      <button className={button} disabled={busy} onClick={() => void run(() => post('processing', { mode }))}>{ui("Queue extraction")}</button>
    </div>}
    {job && <p className="my-3">{ui("Processing: ")}<strong>{job.status}</strong> {ui(" · attempts ")}{job.attempts}{ui("/3 · ")}{job.mode}{job.error && ` · ${job.error}`}</p>}
    {job?.status === 'failed' && job.attempts < 3 && <button className={button} disabled={busy} onClick={() => void run(() => post('processing/retry', {}))}>{ui("Retry failed extraction")}</button>}
    {text?.snapshot && <div className="mt-4">
      <label>{ui("Text history ")}<select className="border p-2" disabled={busy} value={text.snapshot.revision} onChange={e => void run(() => load(Number(e.target.value)))}>
        {text.revisions.map(revision => <option key={revision.revision} value={revision.revision}>{ui("Revision ")}{revision.revision} {ui(" · ")}{revision.status}</option>)}
      </select></label>
      <p className="my-3">{ui("Text revision ")}{text.snapshot.revision}{ui(": ")}<strong>{text.snapshot.status}</strong>{ui(". ")}{current ? ui("Current snapshot.") : ui("Historical snapshot; read only.")} {ui(" Text verification does not publish the document.")}</p>
      {text.snapshot.review_note && <p>{ui("Review note: ")}{text.snapshot.review_note}</p>}
      <p>{ui("Showing pages ")}{offset + 1}{ui("–")}{offset + pages.length} {ui(" of ")}{text.total_segments}{ui(". Save changes before changing pages.")}</p><button className={button} disabled={busy || dirty || offset === 0} onClick={() => void run(() => load(text.snapshot!.revision, Math.max(0, offset-50)))}>{ui("Previous 50 pages")}</button><button className={button} disabled={busy || dirty || offset + 50 >= text.total_segments} onClick={() => void run(() => load(text.snapshot!.revision, offset+50))}>{ui("Next 50 pages")}</button>
      {pages.map((page, index) => <section key={page.sequence} className="my-4 rounded border p-4">
        <label className="block font-medium">{page.page_number ? ui("Page {0}", page.page_number) : ui("Whole document (unpaginated)")}
          <textarea aria-label={ui("Text segment {0}", page.sequence)} value={page.text} disabled={busy || !current} rows={9}
            className="mt-2 block w-full border p-3 font-mono text-sm" maxLength={100000}
            onChange={e => setPages(previous => previous.map((value, i) => i === index ? { ...value, text: e.target.value } : value))} />
        </label>
        <p className="text-sm mt-2">{ui("Extraction: ")}{page.extraction_method}{page.confidence !== null && ` · original OCR minimum confidence ${(page.confidence * 100).toFixed(1)}%`}</p>
        <p className="text-sm text-amber-800">{page.warning}</p>
      </section>)}
      {current && <>
        <label className="block">{ui("Review/correction note")}<input value={note} maxLength={1000} onChange={e => setNote(e.target.value)} className="block border p-2 w-full mt-1" /></label>
        <button className={`${button} my-3`} disabled={busy || !note.trim()} onClick={() => void run(async () => {
          await post('text/revisions', { base_revision: text.snapshot!.revision, partial: true, pages: pages.map(page => ({ sequence: page.sequence, text: page.text })), note }); setNote('');
        })}>{ui("Save reviewed text as new revision")}</button>
        {text.snapshot.status === 'reviewed' && <div>
          <label><input type="checkbox" checked={compared} onChange={e => setCompared(e.target.checked)} /> {ui(" I compared every page with the original and checked corrections.")}</label>
          <button className={`${button} block mt-3`} disabled={busy || !compared || dirty} onClick={() => void run(() => post('text/verify', { revision: text.snapshot!.revision, original_compared: true }))}>{ui("Verify current text")}</button>
          {dirty && <p>{ui("Save your edits as a new revision before verifying.")}</p>}
        </div>}
      </>}
    </div>}
    <p role="status" className="my-2">{busy ? ui("Working…") : ui(message)}</p>
  </details>;
}
