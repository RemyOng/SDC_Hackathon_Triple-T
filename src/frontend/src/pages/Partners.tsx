import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { IconCheck, IconDownload, IconPlugConnected, IconRefresh, IconSend, IconUserCheck } from "@tabler/icons-react";
import type { AuditEvent, GrDocument, Identity, InvestorCard, RequestSummary, SupplierCard } from "../api";
import { date, dateTime, rm } from "../format";
import { useApi, useSession } from "../session";
import { Button, Card, Chip, EmptyState, ErrorBox, Field, Loading, Notice, PageHeader, StatusChip } from "../ui";
import { SentDocument } from "./Documents";

type PartnerRequest<C> = RequestSummary & { listing_id: string; message: string; listing: C; documents: GrDocument[] };

// ------------------------------------------------------------ investor
export function InvestorConnectionsPage() {
  const navigate = useNavigate();
  const { data, error, loading } = useApi<{ requests: PartnerRequest<InvestorCard>[] }>("/requests");
  const [viewing, setViewing] = useState<string | null>(null);
  if (loading && !data) return <Loading />;
  if (error) return <ErrorBox message={error} />;
  if (!data) return null;
  return (
    <>
      <PageHeader title="Connections" subtitle="Requested · Accepted · Declined · Expired. Company details unlock only after the owner accepts." />
      {data.requests.length === 0 ? (
        <EmptyState
          icon={IconPlugConnected}
          text="You haven't requested any connections yet."
          action={<Link to="/investor/board" className="font-semibold text-royal">Browse the Opportunity Board</Link>}
        />
      ) : (
        <div className="space-y-3">
          {data.requests.map((request) => {
            const eoi = request.documents.find((doc) => doc.type === "eoi");
            return (
              <Card key={request.id} className="!p-5">
                <div className="flex flex-wrap items-center gap-4">
                  <div className="min-w-0 flex-1">
                    <p className="eyebrow text-muted">
                      {request.listing_id} · requested {dateTime(request.created_at)}
                    </p>
                    <p className="text-lg font-semibold">
                      {request.listing.identity ? request.listing.identity.company_name : `Anonymous ${request.listing.sector.toLowerCase()} business`}
                    </p>
                    <p className="text-sm text-muted">
                      {request.listing.upgrade_labels.join(" + ")} · {request.listing.state} · CapEx {request.listing.capex_band}
                    </p>
                  </div>
                  <StatusChip status={request.status} />
                  {request.status === "accepted" && !eoi && (
                    <Button onClick={() => navigate(`/investor/eoi/${request.id}`)}>
                      <IconSend size={16} /> Send EOI
                    </Button>
                  )}
                  {eoi && (
                    <Button variant="secondary" onClick={() => setViewing(viewing === eoi.id ? null : eoi.id)}>
                      EOI {eoi.reference} · {eoi.status === "sent" ? "waiting" : eoi.status}
                    </Button>
                  )}
                  <Link to={`/investor/listing/${request.listing_id}`} className="text-sm font-semibold text-royal">
                    Open listing
                  </Link>
                </div>
                {request.status === "accepted" && request.listing.identity && <Unlocked identity={request.listing.identity} />}
                {eoi && viewing === eoi.id && (
                  <div className="mt-4">
                    <SentDocument doc={eoi} />
                  </div>
                )}
              </Card>
            );
          })}
        </div>
      )}
    </>
  );
}

function Unlocked({ identity }: { identity: Identity }) {
  return (
    <dl className="mt-4 grid gap-x-6 rounded-xl bg-[#E6F2EC] px-4 py-2 sm:grid-cols-2">
      <Field label="Registration no." value={identity.reg_no} />
      <Field label="Contact" value={identity.contact_person} />
      <Field label="Phone" value={identity.contact_phone} />
      <Field label="Email" value={identity.contact_email} />
    </dl>
  );
}

// ------------------------------------------------------------ supplier
export function SupplierRequestsPage() {
  const { data, error, loading } = useApi<{ requests: PartnerRequest<SupplierCard>[] }>("/requests");
  const [viewing, setViewing] = useState<string | null>(null);
  if (loading && !data) return <Loading />;
  if (error) return <ErrorBox message={error} />;
  if (!data) return null;
  return (
    <>
      <PageHeader title="My requests" subtitle="Proposals you've sent. You pay RM200 only for the ones owners accept." />
      {data.requests.length === 0 ? (
        <EmptyState
          icon={IconSend}
          text="You haven't sent any proposals yet."
          action={<Link to="/supplier/board" className="font-semibold text-royal">Browse the Opportunity Board</Link>}
        />
      ) : (
        <div className="space-y-3">
          {data.requests.map((request) => {
            const proposal = request.documents.find((doc) => doc.type === "proposal");
            return (
              <Card key={request.id} className="!p-5">
                <div className="flex flex-wrap items-center gap-4">
                  <div className="min-w-0 flex-1">
                    <p className="eyebrow text-muted">
                      {request.listing_id} · sent {dateTime(request.created_at)}
                    </p>
                    <p className="text-lg font-semibold">{request.listing.upgrade_labels.join(" + ")}</p>
                    <p className="text-sm text-muted">
                      {request.listing.sector} · {request.listing.state}
                    </p>
                  </div>
                  <StatusChip status={request.status} />
                  {proposal && (
                    <Button variant="secondary" onClick={() => setViewing(viewing === proposal.id ? null : proposal.id)}>
                      {viewing === proposal.id ? "Hide" : "View"} {proposal.reference}
                    </Button>
                  )}
                </div>
                {proposal && viewing === proposal.id && (
                  <div className="mt-4">
                    <SentDocument doc={proposal} />
                  </div>
                )}
              </Card>
            );
          })}
        </div>
      )}
    </>
  );
}

export function SupplierLeadsPage() {
  const { data, error, loading } = useApi<{ requests: PartnerRequest<SupplierCard>[] }>("/requests");
  if (loading && !data) return <Loading />;
  if (error) return <ErrorBox message={error} />;
  if (!data) return null;
  const leads = data.requests.filter((request) => request.status === "accepted");
  return (
    <>
      <PageHeader title="Accepted leads" subtitle="Owners who accepted your proposal. Arrange the free site survey, then send a firm quotation." />
      {leads.length === 0 ? (
        <EmptyState icon={IconUserCheck} text="No accepted leads yet. When an owner accepts, their contact details appear here." />
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {leads.map((request) => {
            const identity = request.listing.identity!;
            return (
              <Card key={request.id}>
                <p className="eyebrow text-muted">
                  {request.listing_id} · accepted {dateTime(request.decided_at!)}
                </p>
                <h2 className="text-lg font-semibold">{identity.company_name}</h2>
                <dl className="mt-2">
                  <Field label="Contact person" value={identity.contact_person} />
                  <Field label="Phone" value={identity.contact_phone} />
                  <Field label="Email" value={identity.contact_email} />
                  <Field label="Site address" value={identity.address} />
                </dl>
                <div className="mt-4 flex flex-wrap items-center gap-3">
                  <Link to={`/supplier/listing/${request.listing_id}`} className="font-semibold text-royal">
                    Bill summary for sizing
                  </Link>
                  <Chip tone="draft">Firm quotation (V14–V15 checks) · next step</Chip>
                </div>
              </Card>
            );
          })}
        </div>
      )}
    </>
  );
}

// ------------------------------------------------------------- billing
type InvestorBilling = { plan: string; monthly_fee_myr: number; next_invoice: string; invoices: { number: string; period: string; amount_myr: number; status: string }[] };
type SupplierBilling = {
  plan: string;
  fee_per_connection_myr: number;
  next_invoice: string;
  accepted_connections: { listing_id: string; amount_myr: number; at: string; request_id: string }[];
  pending_requests: { request_id: string; listing_id: string; sent_at: string }[];
  requests_left: number;
  requests_per_week: number;
  month_to_date_myr: number;
};

function Tile({ label, value, caption, tint }: { label: string; value: string; caption: string; tint: string }) {
  return (
    <div className={`rounded-[20px] p-5 ${tint}`}>
      <p className="text-xs font-semibold">{label}</p>
      <p className="tnum mt-2 text-[28px] leading-9 font-bold">{value}</p>
      <p className="text-xs text-muted">{caption}</p>
    </div>
  );
}

function PlanCard({ title, price, unit, points }: { title: string; price: string; unit: string; points: string[] }) {
  return (
    <div className="relative overflow-hidden rounded-[20px] bg-midnight p-6 text-white">
      <div className="pointer-events-none absolute -top-16 -right-16 h-48 w-48 rounded-full bg-royal/60 blur-2xl" />
      <p className="relative text-sm font-semibold text-sky">{title}</p>
      <p className="tnum relative mt-2 text-[32px] leading-10 font-bold">
        {price} <span className="text-base font-medium text-sky">{unit}</span>
      </p>
      <ul className="relative mt-4 space-y-2 text-sm">
        {points.map((point) => (
          <li key={point} className="flex items-start gap-2">
            <IconCheck size={16} className="mt-0.5 shrink-0 text-sky" /> {point}
          </li>
        ))}
      </ul>
    </div>
  );
}

function BillingTable({ head, rows, empty }: { head: string[]; rows: React.ReactNode[][]; empty: string }) {
  return (
    <Card className="!p-0">
      <table className="w-full text-left text-sm">
        <thead>
          <tr className="text-xs text-muted">
            {head.map((cell, index) => (
              <th key={cell} className={`px-6 pt-5 pb-2 font-medium ${index === head.length - 1 ? "text-right" : ""}`}>
                {cell}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr key={index} className="border-t border-porcelain">
              {row.map((cell, cellIndex) => (
                <td key={cellIndex} className={`tnum px-6 py-4 ${cellIndex === row.length - 1 ? "text-right font-semibold" : ""}`}>
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {rows.length === 0 && <p className="px-6 pt-2 pb-6 text-sm text-muted">{empty}</p>}
    </Card>
  );
}

export function BillingPage() {
  const { role } = useSession();
  const { data, error, loading } = useApi<InvestorBilling & SupplierBilling>("/billing");
  if (loading && !data) return <Loading />;
  if (error) return <ErrorBox message={error} />;
  if (!data) return null;

  if (role === "investor") {
    return (
      <>
        <PageHeader title="Billing" subtitle={`Billed monthly by Orbyte · next invoice ${date(data.next_invoice)} (mock)`} />
        <div className="grid gap-6 xl:grid-cols-[1fr_340px]">
          <div className="space-y-6">
            <div className="grid gap-4 sm:grid-cols-3">
              <Tile tint="bg-dawn" label="This month" value={rm(data.monthly_fee_myr)} caption="Flat subscription" />
              <Tile tint="bg-sky" label="Next invoice" value={date(data.next_invoice)} caption="Orbyte monthly invoice" />
              <Tile tint="bg-moon" label="Per-connection fees" value="RM0" caption="Included in your plan" />
            </div>
            <div>
              <h2 className="mb-3 text-lg font-semibold">Invoices</h2>
              <BillingTable
                head={["Invoice", "Period", "Status", "Amount"]}
                rows={data.invoices.map((invoice) => [invoice.number, invoice.period, <Chip tone="success">✓ {invoice.status}</Chip>, rm(invoice.amount_myr)])}
                empty="No invoices yet."
              />
            </div>
          </div>
          <PlanCard
            title="Bank / investor plan"
            price={rm(data.monthly_fee_myr)}
            unit="/ month"
            points={[
              "Browse every live listing, filtered by your own criteria",
              "Repayment check on your own terms",
              "Unlimited connection requests and EOIs",
              "No scores or rankings — your credit decision stays yours",
            ]}
          />
        </div>
      </>
    );
  }

  const accepted = data.accepted_connections;
  return (
    <>
      <PageHeader title="Billing" subtitle={`You pay only when an owner accepts · next Orbyte invoice ${date(data.next_invoice)} (mock)`} />
      <div className="grid gap-6 xl:grid-cols-[1fr_340px]">
        <div className="space-y-6">
          <div className="grid gap-4 sm:grid-cols-3">
            <Tile tint="bg-dawn" label="This month" value={rm(data.month_to_date_myr)} caption={`${accepted.length} accepted × ${rm(data.fee_per_connection_myr)}`} />
            <Tile tint="bg-asian-pear" label="Waiting for owners" value={String(data.pending_requests.length)} caption="Not charged unless accepted" />
            <Tile
              tint="bg-sky"
              label="Requests left this week"
              value={`${data.requests_left} of ${data.requests_per_week}`}
              caption="Resets every Monday (M04)"
            />
          </div>
          <div>
            <h2 className="mb-3 text-lg font-semibold">Accepted connections</h2>
            <BillingTable
              head={["Listing", "Accepted", "Status", "Fee"]}
              rows={accepted.map((fee) => [
                <Link to={`/supplier/listing/${fee.listing_id}`} className="font-semibold text-royal hover:underline">{fee.listing_id}</Link>,
                dateTime(fee.at),
                <Chip tone="info">On next invoice</Chip>,
                rm(fee.amount_myr),
              ])}
              empty="Nothing to pay yet. You're charged only after an owner accepts your proposal."
            />
          </div>
          {data.pending_requests.length > 0 && (
            <div>
              <h2 className="mb-3 text-lg font-semibold">Waiting for owners</h2>
              <BillingTable
                head={["Listing", "Sent", "Status", "Fee"]}
                rows={data.pending_requests.map((request) => [request.listing_id, dateTime(request.sent_at), <Chip>Waiting</Chip>, "RM0"])}
                empty=""
              />
            </div>
          )}
        </div>
        <PlanCard
          title="Supplier plan"
          price={rm(data.fee_per_connection_myr)}
          unit="per accepted connection"
          points={[
            "No monthly fee — browse and send proposals for free",
            `Up to ${data.requests_per_week} proposals a week`,
            "Charged only after the owner accepts",
            "Billed on your monthly Orbyte invoice",
          ]}
        />
      </div>
    </>
  );
}

// ------------------------------------------------------- activity / ops
export function ActivityPage({ title = "Activity" }: { title?: string }) {
  const { role, call, toast, refresh } = useSession();
  const [filter, setFilter] = useState("");
  const { data, error, loading } = useApi<{ events: AuditEvent[] }>(`/audit${filter ? `?object=${encodeURIComponent(filter)}` : ""}`);
  const all = useApi<{ events: AuditEvent[] }>("/audit");

  const reset = async () => {
    try {
      await call("/ops/reset", { method: "POST" });
      toast("Demo data reset");
      refresh();
    } catch (err) {
      toast((err as Error).message, "danger");
    }
  };

  const exportCsv = () => {
    const rows = [["Time", "User", "Role", "Action", "Object"], ...(data?.events ?? []).map((e) => [e.at, e.user, e.role, e.action, e.object])];
    const csv = rows.map((row) => row.map((cell) => `"${cell.replace(/"/g, '""')}"`).join(",")).join("\n");
    const link = document.createElement("a");
    link.href = URL.createObjectURL(new Blob([csv], { type: "text/csv" }));
    link.download = "greenready-activity.csv";
    link.click();
    URL.revokeObjectURL(link.href);
  };

  const events = all.data?.events ?? [];
  const tiles = [
    { label: "Events logged", value: events.length, caption: "Every step, newest first", tint: "bg-dawn" },
    { label: "People and systems", value: new Set(events.map((e) => e.user)).size, caption: "Who acted", tint: "bg-sky" },
    {
      label: "Owner approvals",
      value: events.filter((e) => e.role === "SME Owner").length,
      caption: "Human control points",
      tint: "bg-moon",
    },
  ];

  return (
    <>
      <PageHeader
        title={title}
        subtitle="Every step with who, role and time, from the Orbyte audit log."
        actions={
          <>
            <Button variant="secondary" onClick={exportCsv} disabled={!data?.events.length}>
              <IconDownload size={16} /> Export CSV
            </Button>
            {role === "ops" && (
              <Button variant="danger" onClick={reset}>
                <IconRefresh size={16} /> Reset demo
              </Button>
            )}
          </>
        }
      />

      <div className="mb-6 grid gap-4 sm:grid-cols-3">
        {tiles.map((tile) => (
          <div key={tile.label} className={`rounded-[20px] p-5 ${tile.tint}`}>
            <p className="text-xs font-semibold">{tile.label}</p>
            <p className="tnum mt-2 text-[32px] leading-10 font-bold">{tile.value}</p>
            <p className="text-xs text-muted">{tile.caption}</p>
          </div>
        ))}
      </div>

      <Card className="!p-0">
        <div className="flex flex-col gap-3 border-b border-porcelain px-6 py-5 sm:flex-row sm:items-center sm:justify-between">
          <h2 className="text-lg font-semibold">Timeline</h2>
          <div role="tablist" aria-label="Filter by object" className="flex flex-wrap gap-1 rounded-xl bg-porcelain p-1">
            {AUDIT_FILTERS.map(([value, label]) => (
              <button
                key={label}
                role="tab"
                aria-selected={filter === value}
                onClick={() => setFilter(value)}
                className={`rounded-lg px-3 py-1.5 text-sm font-medium ${
                  filter === value ? "bg-white text-midnight shadow-card" : "text-muted hover:text-midnight"
                }`}
              >
                {label}
              </button>
            ))}
          </div>
        </div>
        {loading && !data && <div className="px-6"><Loading /></div>}
        {error && <div className="p-6"><ErrorBox message={error} /></div>}
        {data && data.events.length === 0 && <p className="px-6 py-12 text-center text-muted">No activity for this filter yet.</p>}
        {data && data.events.length > 0 && (
          <table className="w-full text-left text-sm">
            <thead className="hidden sm:table-header-group">
              <tr className="text-xs text-muted">
                <th className="px-6 pt-4 pb-2 font-medium">Time</th>
                <th className="px-3 pt-4 pb-2 font-medium">Who</th>
                <th className="px-3 pt-4 pb-2 font-medium">Action</th>
                <th className="px-6 pt-4 pb-2 text-right font-medium">Object</th>
              </tr>
            </thead>
            <tbody>
              {data.events.map((event, index) => (
                <tr key={index} className="flex flex-col gap-1 border-t border-porcelain px-6 py-4 sm:table-row sm:px-0 sm:py-0">
                  <td className="tnum text-xs whitespace-nowrap text-muted sm:px-6 sm:py-4">{dateTime(event.at)}</td>
                  <td className="sm:px-3 sm:py-4">
                    <span className="flex items-center gap-3">
                      <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-dawn text-xs font-bold text-royal" aria-hidden>
                        {initials(event.user)}
                      </span>
                      <span className="min-w-0">
                        <span className="block font-semibold">{event.user}</span>
                        <span className="block text-xs text-muted">{event.role}</span>
                      </span>
                    </span>
                  </td>
                  <td className="sm:px-3 sm:py-4">{event.action}</td>
                  <td className="sm:px-6 sm:py-4 sm:text-right">
                    <Chip>{event.object}</Chip>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </>
  );
}

const AUDIT_FILTERS: [string, string][] = [
  ["", "All"],
  ["Bill", "Bills"],
  ["Listing", "Listings"],
  ["Request", "Requests"],
  ["Pack", "Packs"],
];

function initials(name: string) {
  return name
    .split(/\s+/)
    .filter((word) => /^[A-Za-z]/.test(word))
    .slice(0, 2)
    .map((word) => word[0].toUpperCase())
    .join("");
}

type Wallet = { data: { walletId: number; balance: number; lowBalance: boolean } };
type Transactions = { data: { id: number; amount: number; type: string; reason: string; at: string }[] };

export function WalletPage() {
  const wallet = useApi<Wallet>("/wallet");
  const transactions = useApi<Transactions>("/wallet/transactions");
  if (wallet.loading && !wallet.data) return <Loading />;
  if (wallet.error) return <ErrorBox message={wallet.error} />;
  if (!wallet.data) return null;
  const balance = wallet.data.data.balance;
  return (
    <>
      <PageHeader title="Wallet" subtitle="Your Orbyte credit wallet — one wallet for every Orbyte module." />
      <div className="grid gap-4 lg:grid-cols-3">
        <section className="relative overflow-hidden rounded-[20px] bg-midnight p-6 text-white shadow-card">
          <div className="pointer-events-none absolute -top-16 -right-16 h-48 w-48 rounded-full bg-royal/60 blur-2xl" />
          <p className="eyebrow relative text-sky">Balance</p>
          <p className="tnum relative mt-1 text-[32px] leading-10 font-bold">{rm(balance, 2)}</p>
          <p className="relative text-sm text-sky">Enough for {Math.floor(balance / 2)} bill analyses at RM2</p>
          <a
            href="https://orbyte-xyz.alphareds.com/wallet"
            target="_blank"
            rel="noopener noreferrer"
            className="relative mt-6 inline-flex min-h-10 items-center rounded-full bg-white px-5 text-sm font-semibold text-midnight hover:bg-dawn"
          >
            Top up in Orbyte Wallet
          </a>
          <p className="relative mt-2 text-xs text-sky">Top-ups are mocked in the demo</p>
        </section>
        <Card className="lg:col-span-2">
          <h2 className="mb-2 font-semibold">Transactions</h2>
          {transactions.error && <Notice tone="warning">{transactions.error}</Notice>}
          <dl>
            {(transactions.data?.data ?? []).map((entry) => (
              <Field
                key={entry.id}
                label={`${dateTime(entry.at)} · ${entry.reason}`}
                value={<span className={entry.amount < 0 ? "" : "text-success"}>{entry.amount < 0 ? "−" : "+"}{rm(Math.abs(entry.amount), 2)}</span>}
              />
            ))}
          </dl>
        </Card>
      </div>
    </>
  );
}
