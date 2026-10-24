import { useEffect, useRef, useState, type DragEvent, type ReactNode } from "react";
import { Link, useSearchParams } from "react-router-dom";
import {
  IconAlertTriangle,
  IconBrandWhatsapp,
  IconCamera,
  IconCheck,
  IconChevronDown,
  IconCloudUpload,
  IconFileInvoice,
  IconInfoCircle,
  IconKeyboard,
  IconLoader2,
  IconReceipt,
  IconSparkles,
  IconX,
} from "@tabler/icons-react";
import { apiUpload, type Upgrade } from "../api";
import { dateTime, num, rm, years } from "../format";
import { useApi, useSession } from "../session";
import { Button, Card, Chip, Disclaimer, EmptyState, ErrorBox, IconDisc, Loading, Modal, Notice, PageHeader, UPGRADE_ICON } from "../ui";
import { UsageBars } from "./Sme";

type BillSummary = {
  id: string;
  month: string;
  source: string;
  status: Status;
  total_myr: number | null;
  usage_kwh: number | null;
  checks: string | null;
  charged_myr: number;
  uploaded_at: string;
};
type Status = "needs_review" | "ready" | "check_failed" | "processing";
type FieldRow = {
  key: string;
  label: string;
  kind: "text" | "number";
  value: string | number | null;
  source: "AI" | "Manual" | "Corrected";
  confidence: number | null;
  flagged: boolean;
};
type CheckRow = { rule: string; label: string; unit: string; expected: number; found: number; passed: boolean; note?: string };
type Insight = { rule: string; value: number | null; label: string; unit?: string; note?: string | null; alert?: boolean };
type Bill = {
  id: string;
  month: string;
  source: string;
  mode: "ai" | "demo" | "manual";
  filename: string | null;
  uploaded_at: string;
  fields: FieldRow[];
  history: Record<string, number>;
  notice: string | null;
  charged_myr: number;
  processing_ms: number;
  checks: CheckRow[];
  insights: Record<string, Insight> | null;
  status: Status;
  values: Record<string, string | number | null>;
  charges: { key: string; label: string; help: string; value: number | null }[];
  threshold: number;
  disclaimer: string;
};
type Option = Upgrade & { rule: string; basis_rules: string };
type Recommendations = {
  options: Option[];
  skipped: string[];
  monitor_only: boolean;
  explanation: { source: "ai" | "rules"; model: string | null; text: string };
  parameters: { label: string; value: string; source: string }[];
  formulas: string[];
  note: string;
  disclaimer: string;
  pack: { listing_id: string; status: string } | null;
};
type BillList = { bills: BillSummary[]; price_myr: number; balance_myr: number; ai_reader: "runpod" | "demo" };

const STATUS: Record<Status, { label: string; tone: string }> = {
  ready: { label: "✓ Ready", tone: "bg-[#E6F2EC] text-success" },
  needs_review: { label: "⚠ Needs review", tone: "bg-asian-pear text-warning" },
  check_failed: { label: "✗ Check failed", tone: "bg-[#FBEAE8] text-danger" },
  processing: { label: "Processing", tone: "bg-dawn text-royal" },
};
const STEPS = ["Reading bill (AI)", "Checking against tariff (rules)", "Building insights"];
// Grid placement inside the page grid: right of the upload column, or across both columns.
const RIGHT = "min-w-0 space-y-6 lg:col-start-2 lg:row-start-1";
const FULL = "min-w-0 space-y-6 lg:col-span-2";

function StatusPill({ status }: { status: Status }) {
  const item = STATUS[status];
  return <span className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-semibold whitespace-nowrap ${item.tone}`}>{item.label}</span>;
}

export function BillsPage() {
  const { role, call, toast, refresh } = useSession();
  const [params, setParams] = useSearchParams();
  const list = useApi<BillList>("/bills");
  const selectedId = params.get("bill") ?? list.data?.bills[0]?.id ?? null;
  const [manual, setManual] = useState(false);
  const [pending, setPending] = useState<{ kind: "file"; file: File } | { kind: "manual"; values: Record<string, unknown> } | null>(null);
  const [processing, setProcessing] = useState<{ step: number; started: number; name: string } | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);

  const select = (id: string) => {
    setManual(false);
    setParams({ bill: id }, { replace: true });
  };

  const run = async () => {
    if (!pending) return;
    const job = pending;
    setPending(null);
    setUploadError(null);
    const started = Date.now();
    setProcessing({ step: 0, started, name: job.kind === "file" ? job.file.name : "Manual entry" });
    const timers = [700, 1400].map((delay, index) => window.setTimeout(() => setProcessing((p) => p && { ...p, step: index + 1 }), delay));
    try {
      const bill =
        job.kind === "file"
          ? await apiUpload<Bill>(role, "/bills/upload", job.file)
          : await call<Bill>("/bills/manual", { method: "POST", body: job.values });
      timers.forEach(window.clearTimeout);
      setProcessing((p) => p && { ...p, step: 3 });
      await new Promise((resolve) => window.setTimeout(resolve, 350));
      toast(bill.status === "needs_review" ? "Bill read — please check the flagged fields" : `${bill.month} bill checked`);
      refresh();
      list.reload();
      select(bill.id);
    } catch (err) {
      timers.forEach(window.clearTimeout);
      setUploadError((err as Error).message);
    } finally {
      setProcessing(null);
    }
  };

  if (list.loading && !list.data) return <Loading />;
  if (list.error) return <ErrorBox message={list.error} />;
  if (!list.data) return null;
  const { price_myr: price, balance_myr: balance } = list.data;

  return (
    <>
      <PageHeader title="Bills" subtitle="Send a TNB bill. AI reads it, rules check it, and you see what to do next." />
      {/* Row 1: upload + history (left) beside the bill summary (right). Row 2: full-width details. */}
      <div className="grid gap-6 lg:grid-cols-[360px_minmax(0,1fr)]">
        <div className="space-y-6 lg:col-start-1 lg:row-start-1">

          <UploadCard
            price={price}
            balance={balance}
            reader={list.data.ai_reader}
            busy={!!processing}
            onFile={(file) => setPending({ kind: "file", file })}
            onManual={() => setManual(true)}
          />
          {processing && <ProcessingCard step={processing.step} started={processing.started} name={processing.name} />}
          {uploadError && (
            <Notice tone="danger">
              {uploadError}{" "}
              <button className="font-semibold underline" onClick={() => setManual(true)}>
                Enter it manually
              </button>
            </Notice>
          )}
          <BillHistory bills={list.data.bills} selected={manual ? null : selectedId} onSelect={select} />
        </div>
        {manual ? (
          <div className={RIGHT}>
            <ManualEntry onCancel={() => setManual(false)} onSubmit={(values) => setPending({ kind: "manual", values })} />
          </div>
        ) : selectedId ? (
          <BillResult key={selectedId} billId={selectedId} onChanged={list.reload} />
        ) : (
          <div className={RIGHT}>
            <EmptyState icon={IconReceipt} text="Send your first TNB bill to see your check in about 3 minutes." />
          </div>
        )}
      </div>

      {pending && (
        <Modal
          title="Analyse this bill?"
          onClose={() => setPending(null)}
          footer={
            balance >= price ? (
              <>
                <Button variant="tertiary" onClick={() => setPending(null)}>
                  Cancel
                </Button>
                <Button onClick={run}>Confirm · {rm(price, 2)}</Button>
              </>
            ) : (
              <Button variant="secondary" onClick={() => setPending(null)}>
                Close
              </Button>
            )
          }
        >
          {balance >= price ? (
            <p className="tnum">
              This uses <strong>{rm(price, 2)}</strong> from your Orbyte credit wallet. Balance after:{" "}
              <strong>{rm(balance - price, 2)}</strong>.
            </p>
          ) : (
            <Notice tone="warning">
              Your wallet has {rm(balance, 2)} — not enough for an analysis ({rm(price, 2)}).{" "}
              {role === "sme_owner" ? (
                <Link to="/sme/wallet" className="font-semibold underline">
                  Top up your wallet
                </Link>
              ) : (
                "Ask the owner to top up the wallet."
              )}
            </Notice>
          )}
          {pending.kind === "file" && <p className="text-sm text-muted">File: {pending.file.name}</p>}
        </Modal>
      )}
    </>
  );
}

// ---------------------------------------------------------------- upload
function UploadCard({
  price,
  balance,
  reader,
  busy,
  onFile,
  onManual,
}: {
  price: number;
  balance: number;
  reader: "runpod" | "demo";
  busy: boolean;
  onFile: (file: File) => void;
  onManual: () => void;
}) {
  const input = useRef<HTMLInputElement>(null);
  const camera = useRef<HTMLInputElement>(null);
  const [over, setOver] = useState(false);
  const accept = ".pdf,.png,.jpg,.jpeg,.webp,application/pdf,image/*";

  const pick = (files: FileList | null) => {
    const file = files?.[0];
    if (file) onFile(file);
  };
  const drop = (event: DragEvent) => {
    event.preventDefault();
    setOver(false);
    if (!busy) pick(event.dataTransfer.files);
  };

  return (
    <Card className="!p-5">
      <h2 className="mb-3 font-semibold">Add a bill</h2>
      <div
        onDragOver={(event) => {
          event.preventDefault();
          setOver(true);
        }}
        onDragLeave={() => setOver(false)}
        onDrop={drop}
        className={`flex flex-col items-center rounded-2xl border-2 border-dashed px-4 py-8 text-center transition-colors ${
          over ? "border-royal bg-dawn" : "border-sky bg-canvas"
        }`}
      >
        <IconDisc icon={IconCloudUpload} size={52} />
        <p className="mt-3 font-semibold">Drop your TNB bill here</p>
        <p className="text-xs text-muted">PDF, JPG, PNG or screenshot · up to 10 MB</p>
        <div className="mt-4 flex flex-wrap justify-center gap-2">
          <Button onClick={() => input.current?.click()} disabled={busy}>
            Choose file
          </Button>
          <Button variant="secondary" className="sm:hidden" onClick={() => camera.current?.click()} disabled={busy}>
            <IconCamera size={16} /> Take photo
          </Button>
        </div>
        <input ref={input} type="file" accept={accept} className="hidden" onChange={(e) => (pick(e.target.files), (e.target.value = ""))} />
        <input ref={camera} type="file" accept="image/*" capture="environment" className="hidden" onChange={(e) => (pick(e.target.files), (e.target.value = ""))} />
      </div>
      <p className="tnum mt-3 text-xs text-muted">
        {rm(price, 2)} per analysis from your Orbyte wallet · balance <strong className="text-midnight">{rm(balance, 2)}</strong>
      </p>
      <button onClick={onManual} disabled={busy} className="mt-3 inline-flex items-center gap-1.5 text-sm font-semibold text-royal hover:underline">
        <IconKeyboard size={16} /> Enter a bill manually
      </button>
      <div className="mt-4 rounded-xl bg-porcelain p-3 text-xs leading-[18px] text-muted">
        <p className="mb-1 font-semibold text-midnight">Other ways to send a bill</p>
        <p className="flex items-center gap-1.5">
          <IconFileInvoice size={14} /> Claim it in Orbyte eClaim (“TNB bill” type)
        </p>
        <p className="flex items-center gap-1.5">
          <IconBrandWhatsapp size={14} /> Forward it on WhatsApp
        </p>
        <p className="mt-2 flex items-center gap-1.5">
          <IconSparkles size={14} /> AI reader: {reader === "runpod" ? "RunPod vision model" : "demo (RunPod not connected)"}
        </p>
      </div>
    </Card>
  );
}

function ProcessingCard({ step, started, name }: { step: number; started: number; name: string }) {
  const [elapsed, setElapsed] = useState(0);
  useEffect(() => {
    const timer = window.setInterval(() => setElapsed((Date.now() - started) / 1000), 100);
    return () => window.clearInterval(timer);
  }, [started]);
  return (
    <Card className="page-enter !p-5" aria-live="polite">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="truncate font-semibold">{name}</h2>
        <span className="tnum text-xs text-muted">{elapsed.toFixed(1)} s</span>
      </div>
      <ol className="space-y-2.5">
        {STEPS.map((label, index) => (
          <li key={label} className={`flex items-center gap-2.5 text-sm ${index > step ? "text-muted" : ""}`}>
            {index < step ? (
              <span className="flex h-5 w-5 items-center justify-center rounded-full bg-success text-white">
                <IconCheck size={12} />
              </span>
            ) : index === step ? (
              <IconLoader2 size={20} className="animate-spin text-royal" />
            ) : (
              <span className="h-5 w-5 rounded-full border-2 border-line" />
            )}
            {label}
          </li>
        ))}
      </ol>
      <div className="mt-4 h-1.5 overflow-hidden rounded-full bg-porcelain">
        <div className="h-full rounded-full bg-royal transition-all duration-500" style={{ width: `${Math.min(step / 3, 1) * 100}%` }} />
      </div>
    </Card>
  );
}

function BillHistory({ bills, selected, onSelect }: { bills: BillSummary[]; selected: string | null; onSelect: (id: string) => void }) {
  return (
    <Card className="!p-0">
      <h2 className="px-5 pt-5 pb-3 font-semibold">Your bills</h2>
      {bills.length === 0 && <p className="px-5 pb-5 text-sm text-muted">No bills yet.</p>}
      <ul>
        {bills.map((bill) => (
          <li key={bill.id}>
            <button
              onClick={() => onSelect(bill.id)}
              className={`flex w-full items-center gap-3 border-t border-porcelain px-5 py-3.5 text-left transition-colors ${
                bill.id === selected ? "bg-dawn/60" : "hover:bg-canvas"
              }`}
            >
              <span className="min-w-0 flex-1">
                <span className="flex items-center gap-2">
                  <span className="font-semibold">{bill.month}</span>
                  {bill.source === "eClaim" && <Chip tone="info">From eClaim</Chip>}
                  {bill.source !== "eClaim" && <span className="text-xs text-muted">{bill.source}</span>}
                </span>
                <span className="tnum block text-xs text-muted">
                  {bill.total_myr != null ? rm(bill.total_myr, 2) : "—"} · {bill.usage_kwh != null ? `${num(bill.usage_kwh)} kWh` : "—"}
                  {bill.checks ? ` · ${bill.checks} checks` : ""}
                </span>
              </span>
              <StatusPill status={bill.status} />
            </button>
          </li>
        ))}
      </ul>
    </Card>
  );
}

// ---------------------------------------------------------------- result
function BillResult({ billId, onChanged }: { billId: string; onChanged: () => void }) {
  const { data: bill, error, loading, reload } = useApi<Bill>(`/bills/${billId}`);
  const [reviewing, setReviewing] = useState(false);
  if (loading && !bill) return <div className={RIGHT}><Loading /></div>;
  if (error) return <div className={RIGHT}><ErrorBox message={error} /></div>;
  if (!bill) return null;

  const done = () => {
    setReviewing(false);
    reload();
    onChanged();
  };
  const v = bill.values;
  const insights = bill.insights;
  const passed = bill.checks.filter((check) => check.passed).length;

  const ready = bill.status !== "needs_review" && insights;

  return (
    <>
    <div className={RIGHT}>
      <Card className="!p-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="eyebrow text-muted">
              {bill.source} · {dateTime(bill.uploaded_at)}
            </p>
            <h2 className="text-2xl leading-8 font-bold">{bill.month} bill</h2>
            <p className="text-sm text-muted">
              {String(v.tariff ?? "")} · account ••{String(v.account_last4 ?? "")} · {String(v.billing_period ?? "")}
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Chip tone={String(v.reading_type).toLowerCase().startsWith("a") ? "neutral" : "warning"}>{String(v.reading_type ?? "—")} reading</Chip>
            <StatusPill status={bill.status} />
          </div>
        </div>
        {bill.notice && <div className="mt-4"><Notice>{bill.notice}</Notice></div>}
      </Card>

      {(bill.status === "needs_review" || reviewing) && <ReviewPanel bill={bill} onDone={done} onCancel={bill.status === "needs_review" ? undefined : () => setReviewing(false)} />}

      {ready && (
        <>
          <div className="stagger grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <Tile tint="bg-dawn" label="Total due" value={rm(Number(v.total_payable_myr), 2)} caption={`Due ${String(v.due_date ?? "")}`} />
            <Tile
              tint="bg-asian-pear"
              label="Usage"
              value={`${num(Number(v.current_month_usage_kwh))} kWh`}
              caption={
                insights.spike_pct.value == null
                  ? insights.spike_pct.note ?? ""
                  : `${insights.spike_pct.alert ? "⚠ " : ""}${insights.spike_pct.value > 0 ? "+" : ""}${insights.spike_pct.value}% vs 6-month average`
              }
              warn={insights.spike_pct.alert}
            />
            <Tile tint="bg-sky" label="Bill check" value={`${passed}/${bill.checks.length}`} caption={passed === bill.checks.length ? "✓ All checks passed" : "✗ Some checks failed"} warn={passed < bill.checks.length} />
            <Tile tint="bg-moon" label="Real cost per kWh" value={rm(insights.real_cost_per_kwh.value ?? 0, 2)} caption="Before one-off rebates (B04)" />
          </div>

          <div className="grid gap-6 xl:grid-cols-2">
            <ChecksPanel checks={bill.checks} onReview={() => setReviewing(true)} />
            <Card>
              <h3 className="mb-1 font-semibold">What changed</h3>
              <UsageBars history={bill.history} />
              <dl className="mt-5 grid grid-cols-2 gap-3">
                {(["daily_kwh", "trend_pct", "variable_share", "marginal_saving", "rebate", "baseline_kwh"] as const).map((key) => {
                  const item = insights[key];
                  return (
                    <div key={key} className="rounded-xl bg-canvas p-3" title={`Rule ${item.rule}`}>
                      <dt className="text-xs text-muted">{item.label}</dt>
                      <dd className="tnum font-semibold">
                        {key === "rebate" || key === "marginal_saving" ? rm(item.value ?? 0, key === "marginal_saving" ? 3 : 2) : num(item.value ?? 0, key === "daily_kwh" ? 1 : 0)}
                        {item.unit && !item.unit.startsWith("RM") ? ` ${item.unit}` : ""}
                      </dd>
                      {item.note && <p className="mt-0.5 text-[11px] leading-4 text-muted">{item.note}</p>}
                    </div>
                  );
                })}
              </dl>
            </Card>
          </div>
        </>
      )}
    </div>

    {ready && (
      <div className={FULL}>
        <ChargeBreakdown bill={bill} />
        <Recommendations billId={bill.id} status={bill.status} />
        <Disclaimer>{bill.disclaimer}</Disclaimer>
      </div>
    )}
    </>
  );
}

function Tile({ label, value, caption, tint, warn }: { label: string; value: string; caption: string; tint: string; warn?: boolean }) {
  return (
    <div className={`rounded-[20px] p-5 ${tint}`}>
      <p className="text-xs font-semibold">{label}</p>
      <p className="tnum mt-2 text-[26px] leading-9 font-bold">{value}</p>
      <p className={`text-xs ${warn ? "font-semibold text-warning" : "text-muted"}`}>{caption}</p>
    </div>
  );
}

function ChecksPanel({ checks, onReview }: { checks: CheckRow[]; onReview: () => void }) {
  const failed = checks.some((check) => !check.passed);
  return (
    <Card className="!p-0">
      <div className="flex items-center justify-between px-6 pt-5 pb-3">
        <h3 className="font-semibold">8 checks against the TNB tariff</h3>
        {failed && (
          <Button variant="secondary" className="!min-h-8 !px-3 text-xs" onClick={onReview}>
            Review fields
          </Button>
        )}
      </div>
      <ul>
        {checks.map((check) => (
          <li key={check.rule} className="flex items-center gap-3 border-t border-porcelain px-6 py-2.5">
            <span className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full ${check.passed ? "bg-[#E6F2EC] text-success" : "bg-[#FBEAE8] text-danger"}`}>
              {check.passed ? <IconCheck size={14} /> : <IconX size={14} />}
            </span>
            <span className="min-w-0 flex-1 text-sm">
              <span className="font-medium">{check.label}</span> <span className="text-xs text-muted">{check.rule}</span>
              {check.note && <span className="block text-[11px] text-muted">{check.note}</span>}
            </span>
            <span className="tnum text-right text-xs">
              <span className="block text-muted">expected {check.unit === "RM" ? rm(check.expected, 2) : `${num(check.expected)} kWh`}</span>
              <span className={`block font-semibold ${check.passed ? "" : "text-danger"}`}>
                found {check.unit === "RM" ? rm(check.found, 2) : `${num(check.found)} kWh`}
              </span>
            </span>
          </li>
        ))}
      </ul>
    </Card>
  );
}

function ChargeBreakdown({ bill }: { bill: Bill }) {
  const [open, setOpen] = useState<string | null>(null);
  return (
    <Card className="!p-0">
      <h3 className="px-6 pt-5 pb-3 font-semibold">Charge breakdown</h3>
      {/* One list on phones; two columns of four lines on wide screens */}
      <dl className="grid border-t border-porcelain text-sm lg:grid-flow-col lg:grid-cols-2 lg:grid-rows-4 lg:gap-x-10 lg:px-6">
        {bill.charges.map((row) => (
          <div key={row.key} className="flex items-start justify-between gap-4 border-b border-porcelain px-6 py-3 lg:px-0">
            <dt>
              <button className="inline-flex items-center gap-1.5 font-medium hover:text-royal" onClick={() => setOpen(open === row.key ? null : row.key)} aria-expanded={open === row.key}>
                {row.label} <IconInfoCircle size={14} className="text-muted" />
              </button>
              {open === row.key && <p className="fade-in mt-1 max-w-sm text-xs text-muted">{row.help}</p>}
            </dt>
            <dd className={`tnum font-semibold ${Number(row.value) < 0 ? "text-success" : ""}`}>{rm(Number(row.value ?? 0), 2)}</dd>
          </div>
        ))}
      </dl>
      <div className="mx-6 mt-1 flex items-center justify-between border-t-2 border-midnight py-3">
        <span className="font-bold">Total due</span>
        <span className="tnum text-lg font-bold">{rm(Number(bill.values.total_payable_myr), 2)}</span>
      </div>
      <p className="px-6 pb-5 text-xs text-muted">Charged for this analysis: {rm(bill.charged_myr, 2)} · processed in {(bill.processing_ms / 1000).toFixed(1)} s</p>
    </Card>
  );
}

// ---------------------------------------------------------------- review
function ReviewPanel({ bill, onDone, onCancel }: { bill: Bill; onDone: () => void; onCancel?: () => void }) {
  const { call, toast } = useSession();
  const [values, setValues] = useState<Record<string, string>>(() =>
    Object.fromEntries(bill.fields.map((row) => [row.key, row.value == null ? "" : String(row.value)])),
  );
  const [showAll, setShowAll] = useState(!bill.fields.some((row) => row.flagged));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const flagged = bill.fields.filter((row) => row.flagged);
  const rows = showAll ? bill.fields : flagged;

  const save = async () => {
    setBusy(true);
    setError(null);
    const changed = Object.fromEntries(
      bill.fields.filter((row) => values[row.key] !== (row.value == null ? "" : String(row.value))).map((row) => [row.key, values[row.key]]),
    );
    try {
      const result = await call<Bill>(`/bills/${bill.id}/fields`, { method: "PATCH", body: { values: changed, confirm_all: true } });
      toast(result.status === "ready" ? "All checks passed" : result.status === "check_failed" ? "Saved — a check still fails" : "Saved");
      onDone();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card className="page-enter">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-lg font-semibold">Check what the AI read</h3>
          <p className="text-sm text-muted">
            {flagged.length > 0
              ? `${flagged.length} field${flagged.length > 1 ? "s are" : " is"} under ${bill.threshold}% confidence. No numbers run until you confirm them (V12). Every change is logged.`
              : "Correct any field, then save to re-run the checks."}
          </p>
        </div>
        <button className="text-sm font-semibold text-royal hover:underline" onClick={() => setShowAll((value) => !value)}>
          {showAll ? "Show flagged only" : `Show all ${bill.fields.length} fields`}
        </button>
      </div>
      <div className="grid gap-3 md:grid-cols-2">
        {rows.map((row) => (
          <label key={row.key} className={`block rounded-xl border p-3 ${row.flagged ? "border-warning/40 bg-asian-pear/60" : "border-line"}`}>
            <span className="flex items-center justify-between gap-2 text-xs font-semibold">
              <span>{row.label}</span>
              <ConfidenceTag row={row} threshold={bill.threshold} />
            </span>
            <input
              className="tnum mt-1.5 h-10 w-full rounded-lg border border-line bg-white px-3 text-sm"
              inputMode={row.kind === "number" ? "decimal" : undefined}
              value={values[row.key]}
              onChange={(e) => setValues({ ...values, [row.key]: e.target.value })}
            />
            {row.flagged && <span className="mt-1 flex items-center gap-1 text-[11px] font-semibold text-warning"><IconAlertTriangle size={12} /> Check this against the bill</span>}
          </label>
        ))}
      </div>
      {error && <div className="mt-4"><ErrorBox message={error} /></div>}
      <div className="mt-5 flex flex-wrap gap-2">
        <Button onClick={save} loading={busy}>
          {flagged.length ? "Confirm and run checks" : "Save and re-run checks"}
        </Button>
        {onCancel && (
          <Button variant="tertiary" onClick={onCancel}>
            Cancel
          </Button>
        )}
      </div>
    </Card>
  );
}

function ConfidenceTag({ row, threshold }: { row: FieldRow; threshold: number }) {
  if (row.source !== "AI" || row.confidence == null) {
    return <span className="rounded bg-porcelain px-1.5 py-0.5 text-[10px] text-muted">{row.source}</span>;
  }
  const low = row.confidence < threshold;
  return (
    <span className="flex items-center gap-1.5">
      <span className="rounded bg-dawn px-1.5 py-0.5 text-[10px] font-bold text-royal">AI</span>
      <span className="h-1.5 w-12 overflow-hidden rounded-full bg-porcelain">
        <span className={`block h-full ${low ? "bg-warning" : "bg-china"}`} style={{ width: `${row.confidence}%` }} />
      </span>
      <span className={`tnum text-[11px] ${low ? "text-warning" : "text-muted"}`}>{Math.round(row.confidence)}%</span>
    </span>
  );
}

// -------------------------------------------------------- recommendations
function Recommendations({ billId, status }: { billId: string; status: Status }) {
  const { role, toast } = useSession();
  const { data, error, loading } = useApi<Recommendations>(`/bills/${billId}/recommendations`);
  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-2 pt-2">
        <div>
          <h2 className="text-xl font-semibold">Upgrade recommendations</h2>
          <p className="text-sm text-muted">Same formulas for every option. No supplier is paying for this ranking.</p>
        </div>
        {status === "check_failed" && <Chip tone="warning">⚠ Based on a bill with a failed check</Chip>}
      </div>
      {loading && !data && (
        <Card className="flex items-center gap-2 text-muted">
          <IconSparkles size={18} className="animate-pulse text-royal" /> Preparing your recommendations…
        </Card>
      )}
      {error && <ErrorBox message={error} />}
      {data && (
        <>
          <div className="relative overflow-hidden rounded-[20px] bg-midnight p-6 text-white">
            <div className="pointer-events-none absolute -top-20 -right-10 h-56 w-56 rounded-full bg-royal/60 blur-3xl" />
            <p className="relative flex items-center gap-2 text-sm font-semibold text-sky">
              <IconSparkles size={18} />
              {data.explanation.source === "ai" ? `AI summary · ${data.explanation.model}` : "Summary · rules engine"}
            </p>
            <p className="relative mt-3 whitespace-pre-line text-[15px] leading-6">{data.explanation.text}</p>
            <p className="relative mt-3 text-xs text-sky">
              {data.explanation.source === "ai"
                ? "AI wrote the words; every number comes from GreenReady's rules."
                : "Every number comes from GreenReady's rules engine, using the same formulas for every option."}
            </p>
          </div>

          {data.monitor_only ? (
            <Notice>No upgrade passes the eligibility rules right now (S04: monitor only). We'll keep checking each bill.</Notice>
          ) : (
            <div className="stagger grid gap-4 md:grid-cols-3">
              {data.options.map((option) => (
                <OptionCard
                  key={option.type}
                  option={option}
                  fastest={option.payback_years === Math.min(...data.options.map((o) => o.payback_years ?? 99))}
                  action={
                    role === "sme_owner" ? (
                      data.pack ? (
                        <Link to="/sme/listing" className="flex min-h-10 w-full items-center justify-center rounded-full bg-dawn text-sm font-semibold text-royal">
                          ✓ In Preparation Pack · {data.pack.listing_id}
                        </Link>
                      ) : (
                        <Button block variant="soft">Prepare pack · RM79</Button>
                      )
                    ) : (
                      <Button block variant="soft" onClick={() => toast("Sent to Ahmad (Owner) for approval")}>
                        Ask owner
                      </Button>
                    )
                  }
                />
              ))}
            </div>
          )}

          {!data.monitor_only && <SavingVsCost options={data.options} />}

          <details className="group rounded-[20px] bg-white p-5 shadow-card">
            <summary className="flex cursor-pointer list-none items-center justify-between font-semibold">
              How we calculated this
              <IconChevronDown size={18} className="transition-transform group-open:rotate-180" />
            </summary>
            <div className="mt-4 grid gap-6 md:grid-cols-2">
              <ul className="space-y-1.5 text-sm">
                {data.formulas.map((formula) => (
                  <li key={formula} className="tnum">• {formula}</li>
                ))}
              </ul>
              <dl className="space-y-2 text-sm">
                {data.parameters.map((parameter) => (
                  <div key={parameter.label} className="flex justify-between gap-4 border-b border-porcelain pb-2">
                    <dt className="text-muted">{parameter.label}</dt>
                    <dd className="tnum text-right font-medium">
                      {parameter.value}
                      <span className="block text-[11px] font-normal text-muted">{parameter.source}</span>
                    </dd>
                  </div>
                ))}
              </dl>
            </div>
            {data.skipped.length > 0 && (
              <p className="mt-4 text-xs text-muted">Not shown: {data.skipped.join(" · ")}</p>
            )}
          </details>
        </>
      )}
    </section>
  );
}

function OptionCard({ option, fastest, action }: { option: Option; fastest: boolean; action: ReactNode }) {
  const icon = UPGRADE_ICON[option.type];
  const rows: [string, string][] = [
    ["Cost", `≈${rm(Math.round(option.capex_myr / 100) * 100)}`],
    ["Saving / year", `≈${rm(Math.round(option.saving_myr_year / 10) * 10)}`],
    ["Payback", `≈${years(Math.round((option.payback_years ?? 0) * 10) / 10 || null)}`],
    ["CO2e / year", `≈${num(option.co2e_t_year, 1)} t`],
  ];
  return (
    <article className="lift flex flex-col rounded-[20px] bg-white p-5 shadow-card hover:shadow-modal">
      <div className="flex items-start justify-between">
        <IconDisc icon={icon.icon} tint={icon.tint} />
        <div className="flex flex-col items-end gap-1">
          <Chip tone={option.basis === "exact" ? "success" : "draft"}>{option.basis}</Chip>
          {fastest && <Chip tone="info">Fastest payback</Chip>}
        </div>
      </div>
      <h3 className="mt-4 text-lg font-semibold">{option.label}</h3>
      <p className="text-sm text-muted">{option.size}</p>
      <dl className="mt-4 flex-1 space-y-2">
        {rows.map(([label, value]) => (
          <div key={label} className="flex justify-between border-b border-porcelain pb-2 text-sm last:border-0">
            <dt className="text-muted">{label}</dt>
            <dd className="tnum font-semibold">{value}</dd>
          </div>
        ))}
      </dl>
      <p className="mt-2 text-[11px] text-muted" title="Rule IDs from the GreenReady Rules Engine">
        Rule {option.rule} · basis {option.basis_rules}
      </p>
      <div className="mt-4">{action}</div>
    </article>
  );
}

function SavingVsCost({ options }: { options: Option[] }) {
  const max = Math.max(...options.map((option) => Math.max(option.capex_myr, option.saving_myr_year)));
  return (
    <Card>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
        <h3 className="font-semibold">Yearly saving vs cost</h3>
        <span className="flex items-center gap-4 text-xs text-muted">
          <span className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-sm bg-midnight" /> Saving / year</span>
          <span className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-sm bg-china" /> Cost</span>
        </span>
      </div>
      <div className="space-y-4" role="img" aria-label={options.map((o) => `${o.label}: cost ${rm(o.capex_myr)}, saves ${rm(o.saving_myr_year)} a year`).join("; ")}>
        {options.map((option) => (
          <div key={option.type} className="grid grid-cols-[110px_1fr] items-center gap-3 text-sm">
            <span className="font-medium">{option.label}</span>
            <span className="space-y-1">
              {(
                [
                  ["bg-midnight", option.saving_myr_year],
                  ["bg-china", option.capex_myr],
                ] as const
              ).map(([color, value]) => (
                <span key={color} className="flex items-center gap-2">
                  <span className={`block h-3 rounded-r-md ${color} transition-all duration-700`} style={{ width: `${Math.max((value / max) * 100, 1.5)}%` }} />
                  <span className="tnum text-xs text-muted">≈{rm(Math.round(value / 10) * 10)}</span>
                </span>
              ))}
            </span>
          </div>
        ))}
      </div>
    </Card>
  );
}

// ----------------------------------------------------------------- manual
const MANUAL_GROUPS: { title: string; fields: [string, string, string?][] }[] = [
  {
    title: "Bill details",
    fields: [
      ["month", "Bill month", "e.g. Sep 2026"],
      ["account_last4", "Account (last 4)"],
      ["tariff", "Tariff", "e.g. B — Low voltage commercial"],
      ["billing_period", "Billing period", "01.09.2026 – 30.09.2026"],
      ["due_date", "Due date", "10.11.2026"],
      ["reading_type", "Reading type", "Actual or Estimated"],
    ],
  },
  {
    title: "Meter",
    fields: [
      ["meter_reading_previous", "Previous reading (kWh)"],
      ["meter_reading_current", "Current reading (kWh)"],
      ["current_month_usage_kwh", "Usage (kWh)"],
    ],
  },
  {
    title: "Charges (RM — use a minus sign for discounts)",
    fields: [
      ["energy_charge_myr", "Energy"],
      ["capacity_charge_myr", "Capacity"],
      ["network_charge_myr", "Network"],
      ["afa_charge_myr", "AFA"],
      ["retail_charge_myr", "Retail"],
      ["ee_incentive_myr", "Rebate / EE incentive"],
      ["kwtbb_myr", "KWTBB"],
      ["service_tax_myr", "Service tax"],
      ["current_charges_myr", "Current charges"],
      ["previous_balance_myr", "Previous balance"],
      ["total_payable_myr", "Total due"],
    ],
  },
];
const SAMPLE: Record<string, string> = {
  month: "Sep 2026", account_last4: "0871", tariff: "B — Low voltage commercial", billing_period: "01.09.2026 – 30.09.2026",
  due_date: "10.11.2026", reading_type: "Actual", meter_reading_previous: "128560", meter_reading_current: "132980",
  current_month_usage_kwh: "4420", energy_charge_myr: "1458.60", capacity_charge_myr: "201.11", network_charge_myr: "580.36",
  afa_charge_myr: "-203.31", retail_charge_myr: "20.00", ee_incentive_myr: "-104.20", kwtbb_myr: "31.24", service_tax_myr: "156.20",
  current_charges_myr: "2140.00", previous_balance_myr: "0", total_payable_myr: "2140.00",
};
const HISTORY_MONTHS = ["Apr", "May", "Jun", "Jul", "Aug", "Sep"];
const SAMPLE_HISTORY = ["3520", "3610", "3480", "3650", "3610", "4420"];

function ManualEntry({ onCancel, onSubmit }: { onCancel: () => void; onSubmit: (values: Record<string, unknown>) => void }) {
  const [values, setValues] = useState<Record<string, string>>({});
  const [history, setHistory] = useState<string[]>(Array(6).fill(""));
  const input = "tnum mt-1 h-10 w-full rounded-lg border border-line bg-white px-3 text-sm font-normal";
  return (
    <Card className="page-enter">
      <div className="mb-5 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold">Enter a bill manually</h2>
          <p className="text-sm text-muted">For bills the AI can't read. The same 8 checks run on what you type.</p>
        </div>
        <Button
          variant="secondary"
          onClick={() => {
            setValues(SAMPLE);
            setHistory(SAMPLE_HISTORY);
          }}
        >
          Fill with sample bill
        </Button>
      </div>
      <div className="space-y-6">
        {MANUAL_GROUPS.map((group) => (
          <fieldset key={group.title}>
            <legend className="eyebrow mb-2 text-muted">{group.title}</legend>
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
              {group.fields.map(([key, label, placeholder]) => (
                <label key={key} className="block text-xs font-semibold">
                  {label}
                  <input className={input} placeholder={placeholder} value={values[key] ?? ""} onChange={(e) => setValues({ ...values, [key]: e.target.value })} />
                </label>
              ))}
            </div>
          </fieldset>
        ))}
        <fieldset>
          <legend className="eyebrow mb-2 text-muted">6-month usage from the bill's chart (kWh, optional)</legend>
          <div className="grid grid-cols-3 gap-3 sm:grid-cols-6">
            {HISTORY_MONTHS.map((month, index) => (
              <label key={month} className="block text-xs font-semibold">
                {month}
                <input
                  className={input}
                  inputMode="numeric"
                  value={history[index]}
                  onChange={(e) => setHistory(history.map((value, i) => (i === index ? e.target.value.replace(/[^\d.]/g, "") : value)))}
                />
              </label>
            ))}
          </div>
        </fieldset>
      </div>
      <div className="mt-6 flex flex-wrap gap-2">
        <Button
          onClick={() =>
            onSubmit({
              ...values,
              history: Object.fromEntries(HISTORY_MONTHS.map((month, index) => [month, history[index]]).filter(([, value]) => value)),
            })
          }
        >
          Run checks
        </Button>
        <Button variant="tertiary" onClick={onCancel}>
          Cancel
        </Button>
      </div>
      <p className="mt-3 text-xs text-muted">The 6-month history powers the spike and trend insights. Without it we compare against this month only.</p>
    </Card>
  );
}
