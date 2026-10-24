import { useEffect, useMemo, useState } from "react";
import { IconBrandWhatsapp, IconMail, IconRefresh, IconFile, IconAlertCircle, IconSearch, IconInbox } from "@tabler/icons-react";
import { dateTime } from "../format";
import { useApi } from "../session";
import { Button, Card, Chip, EmptyState, ErrorBox, Loading, PageHeader, StatusChip } from "../ui";

type IngestedDocument = {
  id: string;
  channel: "GMAIL" | "WHATSAPP" | string;
  type: string;
  status: string;
  filename: string;
  sender?: string;
  subject?: string;
  message_id?: string;
  created_at: string;
  extracted: Record<string, unknown>;
  file_url?: string;
};

export function IngestionPage() {
  const { data, error, loading, reload } = useApi<{ documents: IngestedDocument[] }>("/ingestion-feed");
  const [query, setQuery] = useState("");
  const [channel, setChannel] = useState("ALL");
  const [status, setStatus] = useState("ALL");

  useEffect(() => {
    const refreshWhenVisible = () => {
      if (document.visibilityState === "visible") reload();
    };
    const timer = window.setInterval(refreshWhenVisible, 5000);
    document.addEventListener("visibilitychange", refreshWhenVisible);
    window.addEventListener("focus", refreshWhenVisible);
    return () => {
      window.clearInterval(timer);
      document.removeEventListener("visibilitychange", refreshWhenVisible);
      window.removeEventListener("focus", refreshWhenVisible);
    };
  }, [reload]);

  const documents = data?.documents ?? [];
  const channels = useMemo(() => [...new Set(documents.map((document) => document.channel))].sort(), [documents]);
  const statuses = useMemo(() => [...new Set(documents.map((document) => document.status))].sort(), [documents]);
  const filteredDocuments = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    return documents.filter((document) => {
      const searchable = [document.filename, document.sender, document.subject, document.type]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();
      return (
        (channel === "ALL" || document.channel === channel) &&
        (status === "ALL" || document.status === status) &&
        (!normalizedQuery || searchable.includes(normalizedQuery))
      );
    });
  }, [channel, documents, query, status]);

  if (loading && !data) return <Loading />;
  if (error) return <ErrorBox message={error} />;

  return (
    <>
      <PageHeader
        title="Ingestion inbox"
        subtitle="Documents received through connected channels. This inbox reads the latest records from Supabase."
        actions={<Button variant="tertiary" onClick={reload} disabled={loading}><IconRefresh size={16} className={loading ? "animate-spin" : ""} /> Refresh</Button>}
      />
      {documents.length === 0 ? (
        <EmptyState icon={IconFile} text="No ingested documents yet. New Gmail attachments and WhatsApp uploads will appear here." />
      ) : (
        <>
          <div className="mb-5 grid gap-3 sm:grid-cols-3">
            <Card className="flex items-center gap-3 !p-4"><IconInbox className="text-royal" size={22} /><div><p className="text-xs text-muted">Total documents</p><p className="text-xl font-bold">{documents.length}</p></div></Card>
            <Card className="flex items-center gap-3 !p-4"><IconMail className="text-royal" size={22} /><div><p className="text-xs text-muted">Channels</p><p className="text-xl font-bold">{channels.length}</p></div></Card>
            <Card className="flex items-center gap-3 !p-4"><IconAlertCircle className="text-warning" size={22} /><div><p className="text-xs text-muted">Needs review</p><p className="text-xl font-bold">{documents.filter((document) => document.status.toUpperCase() === "NEEDS_HUMAN").length}</p></div></Card>
          </div>
          <Card className="mb-5 !p-4">
            <div className="flex flex-col gap-3 md:flex-row">
              <label className="relative min-w-0 flex-1">
                <IconSearch size={17} className="absolute left-3 top-3 text-muted" aria-hidden />
                <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search filename, sender, subject…" className="h-10 w-full rounded-full border border-line bg-white pl-9 pr-4 text-sm outline-none focus:border-royal" />
              </label>
              <select value={channel} onChange={(event) => setChannel(event.target.value)} className="h-10 rounded-full border border-line bg-white px-4 text-sm">
                <option value="ALL">All channels</option>
                {channels.map((value) => <option key={value} value={value}>{value}</option>)}
              </select>
              <select value={status} onChange={(event) => setStatus(event.target.value)} className="h-10 rounded-full border border-line bg-white px-4 text-sm">
                <option value="ALL">All statuses</option>
                {statuses.map((value) => <option key={value} value={value}>{value}</option>)}
              </select>
            </div>
            <p className="mt-3 text-xs text-muted">Showing {filteredDocuments.length} of {documents.length} documents</p>
          </Card>
          {filteredDocuments.length === 0 ? (
            <EmptyState icon={IconSearch} text="No documents match these filters." />
          ) : <div className="space-y-3">
          {filteredDocuments.map((document) => {
            const isGmail = document.channel === "GMAIL";
            return (
              <Card key={document.id} className="flex flex-wrap items-start gap-4 transition-shadow hover:shadow-modal">
                <span className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-xl ${isGmail ? "bg-dawn text-royal" : "bg-asian-pear text-success"}`}>
                  {isGmail ? <IconMail size={22} /> : <IconBrandWhatsapp size={22} />}
                </span>
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <h2 className="font-semibold">{isGmail ? document.subject || "Gmail message" : "WhatsApp upload"}</h2>
                    <StatusChip status={document.status.toLowerCase()} />
                  </div>
                  <p className="mt-1 truncate text-sm text-muted">{document.filename}</p>
                  <p className="mt-2 text-xs text-muted">
                    {isGmail ? `From ${document.sender || "unknown sender"}` : `From ${document.sender || "unknown number"}`} · {document.created_at ? dateTime(document.created_at) : "Date unavailable"}
                  </p>
                  <div className="mt-2 flex flex-wrap gap-2"><Chip tone="neutral">{document.channel}</Chip><Chip tone="info">{document.type}</Chip></div>
                  {document.file_url && (
                    <a href={document.file_url} target="_blank" rel="noreferrer" className="mt-3 inline-flex text-sm font-semibold text-royal hover:underline">
                      Open ingested file
                    </a>
                  )}
                  {Object.entries(document.extracted ?? {}).filter(([key, value]) => !key.startsWith("_") && value != null).length > 0 && (
                    <details className="mt-3 text-sm">
                      <summary className="cursor-pointer font-semibold text-royal">View extracted data</summary>
                      <dl className="mt-2 grid gap-x-4 gap-y-1 sm:grid-cols-2">
                        {Object.entries(document.extracted)
                          .filter(([key, value]) => !key.startsWith("_") && value != null)
                          .slice(0, 12)
                          .map(([key, value]) => (
                            <div key={key} className="flex min-w-0 justify-between gap-2 border-b border-porcelain py-1">
                              <dt className="truncate text-muted">{key.replace(/_/g, " ")}</dt>
                              <dd className="truncate text-right font-medium">{typeof value === "object" ? JSON.stringify(value) : String(value)}</dd>
                            </div>
                          ))}
                      </dl>
                    </details>
                  )}
                </div>
                {document.status.toUpperCase() === "NEEDS_HUMAN" && <IconAlertCircle className="text-warning" size={20} aria-label="Needs review" />}
              </Card>
            );
          })}
          </div>}
        </>
      )}
    </>
  );
}
