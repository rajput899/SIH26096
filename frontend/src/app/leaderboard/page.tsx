'use client';
import {useInterface} from '../../components/InterfaceLanguage';

import {useEffect,useState} from 'react';
export default function Leaderboard(){
 const {ui}=useInterface();
const [rows,setRows]=useState<{alias:string;activity:string;score:number;total:number}[]>([]);const [message,setMessage]=useState('Loading…');useEffect(()=>{fetch('/api/archive/leaderboard',{cache:'no-store'}).then(async r=>{if(!r.ok)throw Error('Leaderboard unavailable');setRows(await r.json());setMessage('');}).catch(e=>setMessage(e.message));},[]);return <main className="page"><h1>{ui("Shared learning")}</h1><p>{ui("Voluntary scores, using generated pseudonyms. Each entry represents one completed attempt; this is not a ranking of individual people.")}</p><p role="status">{ui(message)}</p>{!message&&!rows.length&&<p>{ui("No participants have opted to share a score yet.")}</p>}<ol>{rows.map((r,i)=><li className="source" key={i}><strong>{r.alias}</strong> {ui(" · ")}{r.activity} {ui(" · ")}{r.score} {ui(" / ")}{r.total}</li>)}</ol></main>;}
