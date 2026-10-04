'use client';
import {useInterface} from './InterfaceLanguage';

import Image from 'next/image';
import { useEffect, useRef, useState } from 'react';
export default function StaffOriginal({ id, api }: { id: string; api: (path: string, options?: RequestInit) => Promise<Response> }) {
 const {ui}=useInterface();

  const [url, setUrl] = useState(''); const [mime, setMime] = useState(''); const [text, setText] = useState(''); const [message, setMessage] = useState('');
  const blob = useRef('');
  useEffect(() => () => { if (blob.current) URL.revokeObjectURL(blob.current); }, []);
  async function open() {
    setMessage('Opening preserved original…');
    try {
      const response = await api(`staff/documents/${id}/original`); const bytes = await response.arrayBuffer();
      const first = new Uint8Array(bytes); const kind = first[0] === 137 ? 'image/png' : first[0] === 255 ? 'image/jpeg' : first[0] === 37 ? 'application/pdf' : 'text/plain';
      if (blob.current) URL.revokeObjectURL(blob.current);
      if (kind === 'text/plain') setText(new TextDecoder().decode(bytes));
      else { blob.current = URL.createObjectURL(new Blob([bytes], { type: kind })); setUrl(blob.current); }
      setMime(kind); setMessage('Original preview. Compare the text below against this source.');
    } catch { setMessage('Unable to preview original. Use Download original to inspect it.'); }
  }
  return <details className="source"><summary onClick={() => { if (!url && !text) void open(); }}>{ui("Review preserved original")}</summary><p role="status">{ui(message)}</p>{url && (mime === 'application/pdf' ? <iframe className="reader-preview" src={url} title={ui("Preserved original for curator review")} /> : <Image unoptimized width={800} height={900} className="reader-image" src={url} alt={ui("Original scan for curator comparison")} />)}{text && <pre className="original-text">{text}</pre>}</details>;
}
