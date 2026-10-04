'use client';
import {useInterface} from './InterfaceLanguage';

import Image from 'next/image';
import { useState } from 'react';
export default function ArchiveImage({ id, title }: { id: string; title: string }) {
 const {ui}=useInterface();

  const [failed, setFailed] = useState(false);
  return failed ? <div className="image-missing">{ui("Preview unavailable. Open the record for its original.")}</div> : <Image unoptimized src={`/api/archive/documents/${id}/thumbnail`} width={800} height={600} className="archive-thumbnail" alt={title} onError={() => setFailed(true)} />;
}
