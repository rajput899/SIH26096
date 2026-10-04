'use client';
import {useInterface} from './InterfaceLanguage';

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react';

const Context = createContext<{ speak: (text: string, voiceLanguage?: string) => void; language: string; session: number }>({ speak: () => {}, language: 'en', session: 0 });
export const useKiosk = () => useContext(Context);
const guides: Record<string, string> = {
  '/': 'Welcome to the Dr. B. R. Ambedkar Digital Heritage Archive. Choose AI to ask questions with sources, Archive to read published documents, or Experience for the collection introduction. Accessibility and audio controls are below.',
  '/ai': 'Enter a question and select Ask the archive. Answers require verified published sources. Read source excerpts and open original documents below each response. Clear conversation removes the questions in this session.',
  '/archive': 'Search titles or descriptions and choose filters. Select a document title to open metadata, the preserved original and curator-verified text.',
  '/speeches': 'Browse published recordings and reviewed transcripts. If none are published, the page explains the review requirement. Playback is available only for approved recordings.',
  '/experience': 'Explore curator-reviewed timeline events, stories and quizzes. Published activities link to archival sources. Content appears after review and publication.',
};
export default function Kiosk({ children }: { children: React.ReactNode }) {
 const {ui,language,setLanguage,languages,notice:languageNotice,retry:retryLanguage}=useInterface();

  const path = usePathname(); const router = useRouter();
  const [size, setSize] = useState('100');
  const [contrast, setContrast] = useState(false); const [motion, setMotion] = useState(false);
  const [full, setFull] = useState(false); const [notice, setNotice] = useState('');
  const [playback, setPlayback] = useState({ path: '', status: 'stopped' }); const [session, setSession] = useState(0);
  const audio = playback.path === path ? playback.status : 'stopped';
  const setAudio = useCallback((status: string) => setPlayback({ path, status }), [path]);
  const utterance = useRef<SpeechSynthesisUtterance | null>(null);
  const [idle, setIdle] = useState(false); const activity = useRef(0); const run = useRef(0);
  const stop = useCallback(() => { run.current++; window.speechSynthesis?.cancel(); utterance.current = null; setAudio('stopped'); }, [setAudio]);
  const reset = useCallback(() => { stop(); setSession(v => v + 1); setIdle(false); activity.current = Date.now(); router.push('/'); setNotice('Session cleared. Welcome to the archive.'); }, [router, stop]);
  useEffect(() => {
    document.documentElement.style.fontSize = `${size}%`;
    document.documentElement.dataset.contrast = String(contrast);
    document.documentElement.dataset.motion = motion ? 'reduced' : 'system';
  }, [language, size, contrast, motion]);
  useEffect(() => { const change = () => setFull(Boolean(document.fullscreenElement)); document.addEventListener('fullscreenchange', change); return () => document.removeEventListener('fullscreenchange', change); }, []);
  useEffect(() => {
    window.speechSynthesis?.cancel(); run.current++;
    const h = document.querySelector<HTMLElement>('main h1'); h?.setAttribute('tabindex', '-1'); h?.focus({ preventScroll: true });
    return () => { window.speechSynthesis?.cancel(); };
  }, [path]);
  useEffect(() => {
    if (!full) return;
    activity.current = Date.now();
    const active = () => { activity.current = Date.now(); setIdle(false); };
    window.addEventListener('pointerdown', active); window.addEventListener('keydown', active); window.addEventListener('scroll', active, {passive:true});
    const timer = setInterval(() => { const elapsed = Date.now() - activity.current; if (elapsed > 360000) reset(); else if (elapsed > 300000) setIdle(true); }, 5000);
    return () => { clearInterval(timer); window.removeEventListener('pointerdown', active); window.removeEventListener('keydown', active); window.removeEventListener('scroll', active); };
  }, [reset, full]);
  useEffect(() => {
    if (!notice) return;
    const timer = setTimeout(() => setNotice(''), 10000);
    return () => clearTimeout(timer);
  }, [notice]);
  function speak(text: string, voiceLanguage = 'en') {
    stop();
    if (!('speechSynthesis' in window)) { setNotice('Read aloud is unsupported in this browser. Screen-reader navigation remains available.'); return; }
    const voice = window.speechSynthesis.getVoices().find(v => v.localService && v.lang.startsWith(voiceLanguage));
    if (!voice) { setNotice('No local voice is available for the selected language. Install a system voice and reopen this page.'); return; }
    const parts = text.match(/[\s\S]{1,650}(?:\s|$)|[\s\S]{1,650}/g) || []; const token = run.current;
    function next(i: number) {
      if (token !== run.current) return;
      if (i >= parts.length) { setAudio('stopped'); return; }
      const item = new SpeechSynthesisUtterance(parts[i]); item.voice = voice!; item.lang = voice!.lang;
      item.onend = () => next(i + 1);
      item.onerror = () => { if (token === run.current) { setAudio('stopped'); setNotice('Read aloud stopped. Please try again.'); } };
      utterance.current = item; window.speechSynthesis.speak(item);
    }
    setAudio('playing'); setNotice('Reading aloud using a local system voice.'); next(0);
  }
  function speakGuide(text:string){const translated=ui(text);speak(translated,translated===text?'en':language);}
  async function fullscreen() {
    try { if (document.fullscreenElement) await document.exitFullscreen(); else await document.documentElement.requestFullscreen(); setNotice('Fullscreen changed. Escape or Exit Kiosk Mode returns to the browser.'); }
    catch { setNotice('Fullscreen is unavailable or was declined. Archive features remain available.'); }
  }
  function backWithinApp() {
    // Cross-origin history (including another local port) must not leave this app.
    const navigation = (window as Window & {navigation?: {
      currentEntry: {index:number} | null;
      entries: () => {url:string | null}[];
    }}).navigation;
    const previous = navigation?.entries()[(navigation.currentEntry?.index ?? 0)-1]?.url;
    if(previous && new URL(previous).origin === window.location.origin) router.back();
    else router.push(path.startsWith('/archive') && (path !== '/archive' || window.location.search) ? '/archive' : '/');
  }
  return <Context.Provider value={{ speak, language, session }}>
    <a className="skip-link" href="#main-content">{ui("Skip to main content")}</a>
    <header className="site-header"><Link href="/" className="brand" aria-label={ui("Dr. B. R. Ambedkar Digital Heritage Archive home")}><span className="brand-mark" aria-hidden="true">{ui("A")}</span><span>{ui("DR. B. R. AMBEDKAR")}{' '}<small>{ui("DIGITAL HERITAGE ARCHIVE")}</small></span></Link>
      <nav lang={language} aria-label={ui("Main navigation")}>{[['/ai', 'AI'], ['/archive', 'ARCHIVE'], ['/experience', 'EXPERIENCE']].map(([href, text]) => <Link key={href} href={href} aria-current={path.startsWith(href) ? 'page' : undefined}>{ui(text)}</Link>)}</nav>
      <button className="button compact" onClick={() => void fullscreen()}>{full ? ui("Exit Kiosk Mode") : ui("Enter Kiosk Mode")}</button></header>
    <div className="utility-bar"><div className="button-row"><button lang={language} className="quiet" onClick={backWithinApp}>{ui("← ")}{ui("Back")}</button><Link lang={language} className="quiet" href="/">{ui("Home")}</Link></div><span>{ui("Explore. Read. Ask with sources.")}</span>{full && <button className="quiet" onClick={reset}>{ui("End session")}</button>}</div>
    <div id="main-content" key={session}>{children}</div>
    {full && idle && <aside role="alert" className="idle-warning">{ui("This session will clear after one more minute of inactivity. ")}<button onClick={() => { activity.current = Date.now(); setIdle(false); }}>{ui("Continue my visit")}</button></aside>}
    <footer className="access-bar" aria-label={ui("Accessibility and audio controls")}><div className="access-primary">
      <button lang={language} className="button" onClick={() => speakGuide(guides[path] || 'Document reader. Read metadata and verified page text. Open the preserved original to compare the source. Use Read page aloud for audio. Staff tools are available through the Staff link.')}>{ui("◉ ")}{ui("Audio guide")}</button>
      <button disabled={audio === 'stopped'} onClick={() => { if (audio === 'paused') { window.speechSynthesis.resume(); setAudio('playing'); } else { window.speechSynthesis.pause(); setAudio('paused'); } }}>{audio === 'paused' ? ui("Resume audio") : ui("Pause audio")}</button><button disabled={audio === 'stopped'} onClick={stop}>{ui("Stop audio")}</button>
      <details><summary>{ui("Accessibility & language")}</summary><div className="settings-panel">
        <label>{ui("Interface language")}<select data-testid="interface-language" value={language} onChange={e => {stop();setLanguage(e.target.value);}}>{languages.map(option=><option key={option.code} value={option.code} disabled={!option.enabled}>{option.label}</option>)}</select></label>
        <p role="status" lang="en">{languageNotice}</p><button type="button" onClick={retryLanguage}>{ui("Retry language service")}</button>
        <p>{ui("Interface language does not translate documents, quotations, research answers or entered data. Use the separate translation button for eligible verified text. Machine translations may contain errors.")}</p>
        <p>{ui("Read aloud uses local system voices, not Bhashini TTS. Voice commands are not implemented.")}</p>
        <label>{ui("Text size")}<select value={size} onChange={e => setSize(e.target.value)}><option value="100">{ui("Standard")}</option><option value="120">{ui("Large")}</option><option value="140">{ui("Extra large")}</option></select></label>
        <label className="check"><input type="checkbox" checked={contrast} onChange={e => setContrast(e.target.checked)} /> {ui(" High contrast")}</label><label className="check"><input type="checkbox" checked={motion} onChange={e => setMotion(e.target.checked)} /> {ui(" Reduce motion")}</label>
        <p>{ui("Read aloud requires an installed local system voice. Screen readers use page semantics independently. Browser fullscreen does not lock Windows.")}</p>
      </div></details></div><p role="status" className="notice" aria-live="polite">{notice.startsWith("Session cleared") && path !== "/" ? "" : ui(notice)}</p><div className="footer-meta"><span>{ui("Preserved originals · Curator-reviewed text · Traceable sources")}</span><div><Link href="/staff">{ui("Staff")}</Link><Link href="/system">{ui("Service status")}</Link></div></div></footer>
  </Context.Provider>;
}



