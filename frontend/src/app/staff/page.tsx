'use client';
import {useInterface} from '../../components/InterfaceLanguage';


import Link from 'next/link';
import UploadSteps from '../../components/UploadSteps';
import { FormEvent, useEffect, useState } from 'react';
import ProcessingReview from '../archive/ProcessingReview';
import LearningEditor from '../../components/LearningEditor';
import RecordingReview from '../../components/RecordingReview';
import StaffOriginal from '../../components/StaffOriginal';
import CorpusStatus from '../../components/CorpusStatus';

type Document = {
  dataset_authorization?:string|null; id: string; title: string; description: string; language: string; material_type: string;
  source_name: string; source_record_locator: string; rights_statement: string;
  review_status: string; access_level: string; original_filename: string; byte_size: number;
  source_status:string; corpus_state:string|null; mime_type: string; checksum: string; created_at: string; job_status: string | null; text_status: string | null;
};

export default function Archive() {
 const {ui}=useInterface();

  const [documents, setDocuments] = useState<Document[]>([]);
  const [auth, setAuth] = useState('');
  const [role, setRole] = useState('');
  const [message, setMessage] = useState('Loading archive…');
  const [busy, setBusy] = useState(false);
  const [filter, setFilter] = useState('all');const [offset,setOffset]=useState(0);

  async function api(path: string, options: RequestInit = {}, token = auth) {
    const response = await fetch(`/api/archive/${path}`, {
      ...options, cache: 'no-store', headers: { ...options.headers, ...(token ? { Authorization: token } : {}) },
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(typeof error.detail === 'string' ? error.detail : 'Request failed');
    }
    return response;
  }

  async function refresh(token = auth,start=offset) {
    const response = await api(`${token ? 'staff/' : ''}documents${token ? `?offset=${start}&limit=25` : ''}`, {}, token);
    setDocuments(await response.json());setOffset(start);
  }

  useEffect(() => {
    fetch('/api/archive/documents', { cache: 'no-store' }).then(async response => {
      if (!response.ok) throw new Error('Archive unavailable');
      setDocuments(await response.json()); setMessage('');
    }).catch(error => setMessage(error.message));
  }, []);

  async function run(work: () => Promise<void>) {
    setBusy(true); setMessage('');
    try { await work(); } catch (error) { setMessage(error instanceof Error ? error.message : 'Request failed'); }
    finally { setBusy(false); }
  }

  async function login(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const token = `Basic ${btoa(`${form.get('login')}:${form.get('password')}`)}`;
    await run(async () => {
      const user = await (await api('staff/me', {}, token)).json();
      await refresh(token); setAuth(token); setRole(user.role); setMessage(`Signed in as ${user.login}`);
    });
  }

  async function upload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const element = event.currentTarget;
    const form = new FormData(element);
    const file = form.get('file') as File;
    const metadata = Object.fromEntries(['title', 'source_name', 'source_locator', 'source_record_locator', 'language', 'rights_statement', 'description', 'access_level', 'material_type'].map(key => [key, form.get(key)]));
    await run(async () => {
      await (await api(`staff/documents?metadata=${encodeURIComponent(JSON.stringify({ ...metadata, original_filename: file.name, provenance_confirmed: true }))}`, {
        method: 'POST', headers: { 'Content-Type': file.type || 'application/octet-stream' }, body: file,
      })).json();
      element.reset(); await refresh(); setMessage('Original preserved. Document awaits staff verification.');
    });
  }

  async function transition(id: string, action: string) {
    await run(async () => {
      await api(`staff/documents/${id}/transition`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ action, metadata_reviewed: action === 'verify' }) });
      await refresh(); setMessage(`Document ${action === 'verify' ? 'verified; publication is a separate action' : action === 'publish' ? 'published' : 'withdrawn'}.`);
    });
  }

  async function download(document: Document) {
    await run(async () => {
      const response = await api(`${auth ? 'staff/' : ''}documents/${document.id}/original`);
      const url = URL.createObjectURL(await response.blob());
      const link = window.document.createElement('a'); link.href = url; link.download = document.original_filename; link.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    });
  }

  const inputStyle = 'block w-full rounded border border-slate-300 bg-white p-2 mt-1';
  const buttonStyle = 'rounded bg-slate-900 px-4 py-2 text-white disabled:opacity-40';
  return <main className="mx-auto max-w-5xl p-6 sm:p-12">
    <Link href="/system" className="underline">{ui("Service health")}</Link>
    <p className="mt-8 text-sm tracking-widest">{ui("SIH26096")}</p>
    <h1 className="text-4xl font-semibold mt-2">{ui("Curator workspace")}</h1>
    <p className="mt-4 text-slate-600">{ui("Preserved originals and their source metadata. Staff can extract, review and verify page-level text separately from publication.")}</p>
    <section className="my-8 border rounded-xl p-5" aria-label={ui("Staff access")}>
      {!auth ? <form onSubmit={login} className="flex flex-wrap gap-4 items-end">
        <label>{ui("Staff login")}<input name="login" autoComplete="username" required className={inputStyle} /></label>
        <label>{ui("Password")}<input name="password" type="password" autoComplete="current-password" required className={inputStyle} /></label>
        <button disabled={busy} className={buttonStyle}>{ui("Sign in")}</button>
      </form> : <div className="flex justify-between"><p>{ui("Staff view · ")}{role} {ui(" · Credentials kept only in this page’s memory")}</p><button className="underline" disabled={busy} onClick={() => void run(async () => { setAuth(''); setRole(''); setDocuments([]); await refresh(''); })}>{ui("Sign out")}</button></div>}
    </section>
    {auth && <nav className="staff-stages" aria-label={ui("Staff tasks")}>{[['all', 'All material'], ['review', 'Needs Review'], ['published', 'Published'], ['withdrawn', 'Withdrawn'], ['failed', 'Processing Issues']].map(([value, title]) => <button key={value} aria-pressed={filter === value} onClick={() => setFilter(value)}>{ui(title)}</button>)}</nav>}
    {role === 'admin' && <details open className="staff-add"><summary>{ui("Add Material")}</summary><section className="border rounded-xl p-6 mb-8">
      <h2 className="text-2xl font-semibold">{ui("Upload original")}</h2>
      <UploadSteps onSubmit={upload} busy={busy}/>
    </section></details>}
    <p role="status" className="my-4">{busy ? ui("Working…") : ui(message)}</p>
    {auth && <CorpusStatus api={api} canReview={role==='admin'}/>}
    {auth && <LearningEditor api={api} documents={documents}/>}
    <h2 className="text-2xl font-semibold">{auth ? ui("Staff documents") : ui("Published documents")}</h2>
    <p className="text-sm text-slate-500 mt-2">{ui("Records on this page; review filters apply to the current page.")}</p>
    {!documents.length && <p className="py-8">{ui("No ")}{auth ? '' : ui("published public ")}{ui("documents to display.")}</p>}
    <nav className="button-row" aria-label={ui("Staff record pages")}><button disabled={busy||offset===0} onClick={()=>void run(()=>refresh(auth,Math.max(0,offset-25)))}>{ui("Previous records")}</button><span>{ui("Page ")}{Math.floor(offset/25)+1}</span><button disabled={busy||documents.length<25} onClick={()=>void run(()=>refresh(auth,offset+25))}>{ui("Next records")}</button></nav><div className="space-y-5 mt-5">{documents.filter(d => filter === 'all' || (filter === 'review' ? ['uploaded', 'verified'].includes(d.review_status) : filter === 'failed' ? d.job_status === 'failed' : d.review_status === filter)).map(document => <article key={document.id} className="rounded-xl border p-6 bg-white">
      <h3 className="text-xl font-semibold">{document.title}</h3>
      <p className="text-sm my-2">{document.review_status} {ui(" · ")}{document.access_level} {ui(" · ")}{document.material_type} {ui(" · ")}{document.language}</p>
      <p>{document.description}</p><p className="publication-notice">{document.review_status === "published" && document.access_level === "public" ? ui("Visible in the public Archive.") : document.review_status === "verified" ? ui("Verified, but not published. Review the summary below before publishing.") : document.access_level === "staff" ? ui("Staff-only access. Publication will not expose this original publicly.") : ui("Not visible publicly until explicitly published.")}</p>
      <p className="mt-3">{ui("Source: ")}<a className="underline" href={document.source_record_locator} target="_blank" rel="noreferrer">{document.source_name}</a></p>
      <p>{ui("Recorded item rights: ")}{document.rights_statement}</p>{document.dataset_authorization&&<p className="publication-notice">{document.dataset_authorization} {ui(" Metadata and text review remain separate; withdrawal still restricts this record.")}</p>}{!document.dataset_authorization&&["allowed","unknown","not verified"].includes(document.rights_statement.trim().toLowerCase())&&<p className="alert">{ui("Public-display permission is not established by this rights statement. Keep this record unpublished; staff access only.")}</p>}{!document.dataset_authorization&&document.source_status!=="verified"&&<p className="alert">{ui("Source authenticity, provenance and rights: Not verified. Use Dataset ingestion and page checkpoints to record an explicit source review.")}</p>}{document.corpus_state&&<p>{ui("Local import: ")}{document.corpus_state}{ui(". Machine extraction is not curator verification.")}</p>}
      <details><summary>{ui("Technical details")}</summary><p className="text-sm mt-2">{document.original_filename} {ui(" · ")}{document.byte_size} {ui(" bytes · Added ")}{new Date(document.created_at).toLocaleString()}</p>
      <p className="text-xs break-all mt-2">{ui("SHA-256: ")}{document.checksum}</p>
      <p className="text-xs break-all">{ui("Record: ")}{document.id}</p></details>
      <h4 className="review-stage">{ui("Review → Verify → Publish")}</h4><p className="subtle">{ui("Verification confirms review; publication is a separate decision. Access: ")}{document.access_level}{ui(". Text: ")}{document.text_status || ui("No extraction requested")}{ui(". ")}{document.job_status && `Processing: ${document.job_status}.`}</p><div className="flex flex-wrap gap-3 mt-4">
        <button className={buttonStyle} disabled={busy} onClick={() => void download(document)}>{ui("Download original")}</button>
        {auth && ['uploaded', 'withdrawn'].includes(document.review_status) && <button className={buttonStyle} disabled={busy} onClick={() => void transition(document.id, 'verify')}>{ui("Confirm original, metadata, provenance and rights reviewed")}</button>}
        {auth && document.review_status === 'verified' && <button className={buttonStyle} disabled={busy || ["allowed","unknown","not verified"].includes(document.rights_statement.trim().toLowerCase()) || Boolean(document.job_status && (document.job_status !== 'succeeded' || document.text_status !== 'verified'))} onClick={() => void transition(document.id, 'publish')}>{ui("Publish record and original")}</button>}
        {auth && ['verified', 'published'].includes(document.review_status) && <button className={buttonStyle} disabled={busy} onClick={() => void transition(document.id, 'withdraw')}>{ui("Withdraw")}</button>}
      </div>
      {auth && document.job_status && (document.job_status !== "succeeded" || document.text_status !== "verified") && <p className="alert">{ui("Publication requires successful processing and verification of the current text.")}</p>}{auth && !document.mime_type.startsWith("audio/") && !document.mime_type.startsWith("video/") && <StaffOriginal id={document.id} api={api} />}{auth && !document.mime_type.startsWith("audio/") && !document.mime_type.startsWith("video/") && <ProcessingReview id={document.id} api={api} onChanged={() => refresh()} />}
    {auth && (document.mime_type.startsWith('audio/') || document.mime_type.startsWith('video/')) && <RecordingReview id={document.id} mime={document.mime_type} api={api} onChanged={()=>refresh()}/>}
    </article>)}</div>
  </main>;
}

