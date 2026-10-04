"use client";
import {useInterface} from '../../components/InterfaceLanguage';


import { useEffect, useState } from "react";
import Link from "next/link";

type HealthReport = {
  status: "ready" | "degraded" | "unavailable";
  checks?: Record<string, { status: "ok" | "error"; detail: string }>;
};

async function getHealth(): Promise<HealthReport> {
  try {
    const response = await fetch("/api/health", { cache: "no-store" });
    if (response.status !== 200 && response.status !== 503) throw new Error("Health request failed");
    return await response.json();
  } catch {
    return { status: "unavailable" };
  }
}

export default function Home() {
 const {ui}=useInterface();

  const [report, setReport] = useState<HealthReport | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    void getHealth().then((next) => {
      if (active) { setReport(next); setLoading(false); }
    });
    return () => { active = false; };
  }, []);

  async function refresh() {
    setLoading(true);
    setReport(await getHealth());
    setLoading(false);
  }

  return (
    <main className="mx-auto max-w-3xl px-6 py-16 sm:py-24">
      <p className="text-sm font-semibold tracking-widest text-slate-500">{ui("SIH26096 / OPERATIONS")}</p>
      <h1 className="mt-4 text-4xl font-semibold tracking-tight">{ui("Service Status")}</h1>
      <p className="mt-4 max-w-xl leading-7 text-slate-600">
        {ui("These checks report service connectivity and basic dependency responses. Reachability does not establish that a feature is implemented or has passed acceptance tests.")}</p>
      <section aria-label={ui("Service health")} className="mt-10 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <h2 className="text-xl font-semibold">{ui("Service health")}</h2>
          <button onClick={() => void refresh()} disabled={loading} className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-50">
            {loading ? ui("Checking…") : ui("Check again")}
          </button>
        </div>
        <p role="status" className="mt-4 font-medium">
          {loading ? ui("Checking local services…") : report?.status === "ready" ? ui("All checked services reachable") : report?.status === "degraded" ? ui("One or more dependencies unavailable") : ui("Backend unavailable")}
        </p>
        {!loading && report?.checks && (
          <ul className="mt-4 divide-y divide-slate-100">
            {Object.entries(report.checks).map(([name, check]) => (
              <li key={name} className="py-4" data-testid={`service-${name}`}>
                <div className="flex justify-between gap-4">
                  <span className="font-medium capitalize">{name}</span>
                  <span className={check.status === "ok" ? "text-emerald-700" : "text-red-700"}>{check.status === "ok" ? ui("Connected") : ui("Unavailable")}</span>
                </div>
                <p className="mt-1 text-sm text-slate-500">{check.detail}</p>
              </li>
            ))}
          </ul>
        )}
      </section>
      <Link href="/archive" className="block mt-6 underline">{ui("Open ARCHIVE")}</Link>
      <p className="mt-6 text-sm leading-6 text-slate-500">{ui("Ollama connectivity does not prove successful inference. Gemini, OCR accuracy, transcript alignment, email delivery and kiosk hardware are not tested by this page.")}</p>
    </main>
  );
}
