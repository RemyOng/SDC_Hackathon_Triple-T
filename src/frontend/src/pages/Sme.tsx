import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { IconBuildingBank, IconEye, IconInbox, IconSolarPanel, IconTrash } from "@tabler/icons-react";
import type { SmeListing, SmeRequest } from "../api";
import { date, dateTime, num, rm, years } from "../format";
import { useApi, useSession } from "../session";
import {
  Button,
  Card,
  Chip,
  Disclaimer,
  EmptyState,
  ErrorBox,
  EvidenceBadge,
  Field,
  IconDisc,
  Loading,
  LockedList,
  Modal,
  Notice,
  PageHeader,
  StatusChip,
  UPGRADE_ICON,
} from "../ui";
import { SentDocument } from "./Documents";

export function SmeListingPage() {
  const { role, call, toast, refresh } = useSession();
  const { data, error, loading } = useApi<SmeListing>("/sme/listing");
  const [confirmUnlist, setConfirmUnlist] = useState(false);
  if (loading && !data) return <Loading />;
  if (error) return <ErrorBox message={error} />;
  if (!data) return null;

  const bill = data.bill;
  const spike = Math.round((bill.usage_kwh / bill.average_kwh - 1) * 100);
  const preview = data.partner_preview;
  const pending = data.requests.filter((request) => request.status === "requested").length;

  const unlist = async () => {
    try {
      await call(`/listings/${data.id}/unlist`, { method: "POST" });
      toast(`${data.id} unlisted`, "warning");
      refresh();
    } catch (err) {
      toast((err as Error).message, "danger");
    } finally {
      setConfirmUnlist(false);
    }
  };

  return (
    <>
      <PageHeader
        title={`Listing ${data.id}`}
        subtitle={
          <>
            {String(data.company.name)} · listed {date(data.listed_at)} · expires {date(data.expires_at)}
          </>
        }
        actions={
          <div className="flex items-center gap-2">
            <StatusChip status={data.status} />
            {data.status === "live" && (
              <Button
                variant="danger"
                onClick={() => (role === "sme_owner" ? setConfirmUnlist(true) : toast("Only the company owner can unlist (C05).", "warning"))}
              >
                <IconTrash size={16} /> Unlist
              </Button>
            )}
          </div>
        }
      />

      <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Stat tint="bg-dawn" label="This month's bill" value={rm(bill.amount_myr)} caption={`Due ${date(bill.due)}`} />
        <Stat
          tint="bg-asian-pear"
          label="Usage this month"
          value={`${num(bill.usage_kwh)} kWh`}
          caption={spike > 0 ? `⚠ +${spike}% vs 6-month average` : "In line with average"}
          warn={spike >= 15}
        />
        <Stat tint="bg-sky" label="Bill check" value={`${bill.checks_passed}/${bill.checks_total}`} caption="✓ All checks passed" />
        <Stat tint="bg-moon" label="Views" value={`${data.views.investors + data.views.suppliers}`} caption={`${data.views.investors} investors · ${data.views.suppliers} suppliers`} />
      </div>

      {pending > 0 && (
        <div className="mb-4">
          <Notice>
            {pending} request{pending > 1 ? "s" : ""} waiting for your decision.{" "}
            <Link to="/sme/requests" className="font-semibold text-royal underline">
              Review requests
            </Link>
          </Notice>
        </div>
      )}

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <p className="eyebrow mb-1 text-muted">What you see</p>
          <h2 className="mb-3 text-lg font-semibold">Your listing (private)</h2>
          <dl>
            <Field label="Company" value={String(data.company.name)} />
            <Field label="Real cost per kWh" value={rm(bill.real_cost_per_kwh, 2)} />
            <Field label="Upgrades ticked" value={data.upgrade_labels.join(", ")} />
          </dl>
          <UsageBars history={bill.history} />
          <div className="mt-4 space-y-2">
            {data.upgrades.map((upgrade) => {
              const icon = UPGRADE_ICON[upgrade.type];
              return (
                <div key={upgrade.type} className="flex items-center gap-3 rounded-xl bg-porcelain p-3">
                  <IconDisc icon={icon.icon} tint={icon.tint} size={36} />
                  <div className="tnum min-w-0 flex-1 text-sm">
                    <p className="font-semibold">
                      {upgrade.label} · {upgrade.size} <Chip tone="draft">{upgrade.basis}</Chip>
                    </p>
                    <p className="text-muted">
                      ≈{rm(Math.round(upgrade.capex_myr / 100) * 100)} · saves ≈{rm(Math.round(upgrade.saving_myr_year / 10) * 10)}/yr ·{" "}
                      {years(Math.round((upgrade.payback_years ?? 0) * 10) / 10 || null)} · ≈
                      {num(upgrade.co2e_t_year, 1)} t CO2e
                    </p>
                  </div>
                </div>
              );
            })}
          </div>
        </Card>

        <Card className="bg-white">
          <p className="eyebrow mb-1 text-muted">What partners see</p>
          <h2 className="mb-3 text-lg font-semibold">Anonymous card on the Opportunity Board</h2>
          <div className="rounded-2xl border border-sky p-4">
            <p className="eyebrow text-muted">{preview.id}</p>
            <p className="text-lg font-semibold">{preview.upgrade_labels.join(" + ")}</p>
            <dl className="mt-2">
              <Field label="Business" value={`${preview.size} ${preview.sector.toLowerCase()}, ${preview.state}, ${preview.age_band}`} />
              <Field label="Usage band" value={preview.usage_band} />
              <Field label="Monthly bill band" value={preview.bill_band} />
              <Field label="CapEx band" value={preview.capex_band} />
              <Field label="Estimated saving" value={`About ${rm(preview.saving_approx_myr)}/year`} />
              <Field label="Payback" value={`About ${years(preview.payback_approx_years)}`} />
              <Field label="CO2e avoided" value={`About ${preview.co2e_approx_t} t/year`} />
            </dl>
            <div className="mt-2">
              <EvidenceBadge evidence={preview.evidence} />
            </div>
          </div>
          <div className="mt-4">
            <LockedList items={data.hidden} title="Hidden from partners until you accept" />
          </div>
        </Card>
      </div>
      <div className="mt-4">
        <Disclaimer>{data.disclaimer} You can unlist at any time.</Disclaimer>
      </div>

      {confirmUnlist && (
        <Modal
          title={`Unlist ${data.id}?`}
          onClose={() => setConfirmUnlist(false)}
          footer={
            <>
              <Button variant="tertiary" onClick={() => setConfirmUnlist(false)}>
                Cancel
              </Button>
              <Button variant="danger" onClick={unlist}>
                Unlist
              </Button>
            </>
          }
        >
          <p>Your card is removed from the Opportunity Board straight away. Partners you already accepted keep what you shared with them.</p>
        </Modal>
      )}
    </>
  );
}

function Stat({ label, value, caption, warn, tint }: { label: string; value: string; caption: string; warn?: boolean; tint: string }) {
  return (
    <div className={`rounded-[20px] p-5 ${tint}`}>
      <p className="text-xs font-semibold">{label}</p>
      <p className="tnum mt-2 text-[28px] leading-9 font-bold">{value}</p>
      <p className={`text-xs ${warn ? "font-semibold text-warning" : "text-muted"}`}>{caption}</p>
    </div>
  );
}

export function UsageBars({ history }: { history: Record<string, number> }) {
  const entries = Object.entries(history);
  const max = Math.max(...entries.map(([, kwh]) => kwh));
  const average = entries.reduce((sum, [, kwh]) => sum + kwh, 0) / entries.length;
  const last = entries[entries.length - 1];
  return (
    <figure className="mt-4" aria-label={`${last[0]} usage ${Math.round((last[1] / average - 1) * 100)}% above the 6-month average`}>
      <figcaption className="eyebrow mb-2 text-muted">6-month usage (kWh)</figcaption>
      <div className="flex h-32 items-end gap-2">
        {entries.map(([month, kwh], index) => (
          <div key={month} className="flex flex-1 flex-col items-center gap-1">
            <span className="tnum text-[11px] text-muted">{num(kwh)}</span>
            <div
              className={`w-full rounded-t-md ${index === entries.length - 1 ? "bg-midnight" : "bg-china"}`}
              style={{ height: `${(kwh / max) * 88}px` }}
            />
            <span className="text-xs">{month}</span>
          </div>
        ))}
      </div>
    </figure>
  );
}

// ---------------------------------------------------------------- requests
export function SmeRequestsPage() {
  const { data, error, loading } = useApi<{ requests: SmeRequest[] }>("/requests");
  const [params] = useSearchParams();
  const [openId, setOpenId] = useState<string | null>(params.get("open"));
  useEffect(() => setOpenId(params.get("open")), [params]);

  if (loading && !data) return <Loading />;
  if (error) return <ErrorBox message={error} />;
  if (!data) return null;
  const open = data.requests.find((request) => request.id === openId) ?? data.requests[0];

  return (
    <>
      <PageHeader title="Requests" subtitle="Partners who want to connect. Nothing about your company is shared until you accept." />
      {data.requests.length === 0 ? (
        <EmptyState
          icon={IconInbox}
          text="No requests yet. Investors and suppliers who see your anonymous card can ask to connect — you decide who gets your details."
        />
      ) : (
        <div className="grid gap-4 lg:grid-cols-[340px_1fr]">
          <div className="space-y-3">
            {data.requests.map((request) => (
              <RequestListItem key={request.id} request={request} active={request.id === open?.id} onOpen={() => setOpenId(request.id)} />
            ))}
          </div>
          {open && <RequestDetail request={open} />}
        </div>
      )}
    </>
  );
}

function RequestListItem({ request, active, onOpen }: { request: SmeRequest; active: boolean; onOpen: () => void }) {
  const Icon = request.partner_type === "investor" ? IconBuildingBank : IconSolarPanel;
  const proposal = request.documents.find((doc) => doc.type === "proposal");
  const eoi = request.documents.find((doc) => doc.type === "eoi");
  let preview = request.message || (proposal ? "Outreach proposal attached" : "Wants to connect");
  if (proposal) {
    const values = proposal.values;
    preview = `Proposal · indicative ${rm(Number(values.a_price_min) / 1000)}k–${rm(Number(values.a_price_max) / 1000).replace("RM", "")}k`;
  }
  return (
    <button
      onClick={onOpen}
      className={`flex w-full items-start gap-3 rounded-2xl bg-white p-4 text-left shadow-card transition ${active ? "ring-2 ring-royal" : "hover:ring-1 hover:ring-sky"}`}
    >
      <IconDisc icon={Icon} size={40} />
      <div className="min-w-0 flex-1">
        <p className="font-semibold">{request.partner.name}</p>
        <p className="text-xs text-muted capitalize">
          {request.partner_type} · {dateTime(request.created_at)}
        </p>
        <p className="mt-1 truncate text-sm">{eoi ? `EOI ${eoi.reference} ${eoi.status === "sent" ? "waiting" : eoi.status}` : preview}</p>
      </div>
      <StatusChip status={request.status} />
    </button>
  );
}

function RequestDetail({ request }: { request: SmeRequest }) {
  const { role, call, toast, refresh } = useSession();
  const [modal, setModal] = useState<"accept" | "decline" | null>(null);
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [blocked, setBlocked] = useState<string | null>(null);
  const partner = request.partner;
  const isOwner = role === "sme_owner";

  const openModal = (kind: "accept" | "decline") => {
    if (!isOwner) {
      setBlocked("Only the company owner can accept or decline requests (rule C05). Ask Ahmad (Owner) to review this.");
      return;
    }
    setModal(kind);
  };

  const decide = async () => {
    setBusy(true);
    try {
      await call(`/requests/${request.id}/${modal}`, { method: "POST", body: modal === "decline" ? { reason } : undefined });
      toast(modal === "accept" ? `Accepted ${partner.name}. Your details are now shared with them only.` : `Declined ${partner.name}`, modal === "accept" ? "success" : "warning");
      refresh();
      setModal(null);
    } catch (err) {
      toast((err as Error).message, "danger");
    } finally {
      setBusy(false);
    }
  };

  const respondEoi = async (documentId: string, accept: boolean) => {
    if (!isOwner) {
      setBlocked("Only the company owner can reply to an EOI (rule C05).");
      return;
    }
    try {
      await call(`/documents/${documentId}/${accept ? "accept" : "decline"}`, { method: "POST" });
      toast(accept ? "EOI accepted. The bank will contact you to start its own assessment." : "EOI declined", accept ? "success" : "warning");
      refresh();
    } catch (err) {
      toast((err as Error).message, "danger");
    }
  };

  return (
    <div className="space-y-4">
      <Card>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="eyebrow text-muted capitalize">
              {partner.type} · {request.listing_id}
            </p>
            <h2 className="text-xl font-semibold">{partner.name}</h2>
            <p className="text-sm text-muted">
              {partner.type === "supplier"
                ? `SEDA ${partner.seda_no} (valid until ${date(partner.seda_valid_until!)}) · serves ${partner.service_area?.join(", ")}`
                : partner.unit}
            </p>
          </div>
          <StatusChip status={request.status} />
        </div>
        {request.message && <p className="mt-4 rounded-xl bg-porcelain p-3 text-sm">“{request.message}”</p>}

        {request.status === "requested" && (
          <>
            <div className="mt-4 rounded-xl bg-dawn p-4 text-sm">
              <p className="mb-1 font-semibold">If you accept, {partner.name} receives:</p>
              <ul className="list-disc pl-5">
                {request.will_receive.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
              <p className="mt-2 text-muted">Only this partner. Others still see your anonymous card.</p>
            </div>
            <div className="mt-4 flex flex-wrap gap-2">
              <Button onClick={() => openModal("accept")}>Accept</Button>
              <Button variant="secondary" onClick={() => openModal("decline")}>
                Decline
              </Button>
            </div>
          </>
        )}
        {request.status === "accepted" && (
          <p className="mt-4 flex items-center gap-2 text-sm text-success">
            <IconEye size={16} /> You accepted on {dateTime(request.decided_at!)}. Your details are shared with {partner.name} only.
          </p>
        )}
        {request.status === "declined" && (
          <p className="mt-4 text-sm text-muted">
            Declined {dateTime(request.decided_at!)}
            {request.decline_reason ? ` · “${request.decline_reason}”` : ""}
          </p>
        )}
        {blocked && (
          <div className="mt-4">
            <Notice tone="warning">{blocked}</Notice>
          </div>
        )}
      </Card>

      {request.documents.map((doc) => (
        <Card key={doc.id} className="!p-4">
          <SentDocument doc={doc} />
          {doc.type === "eoi" && doc.status === "sent" && (
            <div className="mx-auto mt-4 flex max-w-[794px] flex-wrap gap-2">
              <Button onClick={() => respondEoi(doc.id, true)}>Accept EOI</Button>
              <Button variant="secondary" onClick={() => respondEoi(doc.id, false)}>
                Decline
              </Button>
              <p className="w-full text-xs text-muted">Accepting is not a loan agreement. The bank still runs its own assessment.</p>
            </div>
          )}
        </Card>
      ))}

      {modal && (
        <Modal
          title={modal === "accept" ? `Share your details with ${partner.name}?` : `Decline ${partner.name}?`}
          onClose={() => setModal(null)}
          footer={
            <>
              <Button variant="tertiary" onClick={() => setModal(null)}>
                Cancel
              </Button>
              <Button variant={modal === "accept" ? "primary" : "danger"} onClick={decide} loading={busy}>
                {modal === "accept" ? "Approve and share" : "Decline"}
              </Button>
            </>
          }
        >
          {modal === "accept" ? (
            <>
              <p className="eyebrow text-muted">Orbyte Connect approval · owner only</p>
              <ul className="list-disc pl-5 text-sm">
                {request.will_receive.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
              <p className="text-sm">
                Who sees it: <strong>{partner.name}</strong> only. You can unlist at any time; this is logged in your Activity.
              </p>
            </>
          ) : (
            <label className="block text-sm font-semibold">
              Reason (optional, shared with the partner)
              <textarea
                className="mt-1 block min-h-20 w-full rounded-lg border border-line p-3 font-normal"
                value={reason}
                onChange={(e) => setReason(e.target.value)}
              />
            </label>
          )}
        </Modal>
      )}
    </div>
  );
}
