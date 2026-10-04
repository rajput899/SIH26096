'use client';
import {useInterface} from './InterfaceLanguage';
import Link from 'next/link';

const collections = [
  ['manuscripts', 'Manuscripts & Letters'],
  ['photographs', 'Photographs'],
  ['videos', 'Videos'],
];

export default function CollectionNavigation({compact=false,current=''}:{compact?:boolean;current?:string}) {
 const {ui}=useInterface();

  return <nav className="collection-navigation" aria-label={ui("Archive collections")}>
    {!compact&&<Link href="/archive" aria-current={!current?'page':undefined}>{ui("All archive records")}</Link>}
    {collections.map(([key,title])=><Link key={key} href={`/archive?collection=${key}`} aria-current={current===key?'page':undefined}>{ui(title)}</Link>)}
  </nav>;
}
