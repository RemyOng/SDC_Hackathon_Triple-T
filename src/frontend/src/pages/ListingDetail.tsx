import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { IconArrowLeft, IconCheck, IconLockOpen, IconSend, IconX } from "@tabler/icons-react";
import type { Identity, InvestorCard, SupplierCard } from "../api";
import { date, num, rm, years } from "../format";
import { useApi, useSession } from "../session";
import {
  Button,
  Card,
  Chip,
  Disclaimer,
  ErrorBox,
  EvidenceBadge,
  Field,
  IconDisc,
  Loading,
  LockedList,
  Modal,
  Notice,
  StatusChip,
  UPGRADE_ICON,
} from "../ui";

export function RequestModal({ listingId, onClose, onSent }: { listingId: string; onClose: () => void; onSent: () => void }) {
  const { call, toast, refresh } = useSession();
  const [message, setMessage] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const send = async () => {
    setSending(true);
    setError(null);
    try {
      await call("/requests", { method: "POST", body: { listing_id: listingId, message } });
      toast(`Request sent for ${listingId}`);
      refresh();
      onSent();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSending(false);
    }
  };
  return (
    <Modal
      title={`Request to connect · ${listingId}`}
      onClose={onClose}
      footer={
        <>
          <Button variant="tertiary" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={send} loading={sending}>
            Send request
          </Button>
        </>
      }
    >
      <p className="text-sm">
        The owner sees <strong>Bank Hijau Berhad</strong> and your message. They decide whether to share their company name, contacts
        and full Preparation Pack with you.
      </p>
      <label className="block text-sm font-semibold">
        Message (optional)
        <textarea
          className="mt-1 block min-h-24 w-full rounded-lg border border-line p-3 font-normal"
          maxLength={1000}
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          placeholder="e.g. We finance rooftop solar for Selangor manufacturers under our green SME programme."
        />
      </label>
      {error && <ErrorBox message={error} />}
    </Modal>
  );
}

function Back({ to, label }: { to: string; label: string }) {
  return (
    <Link to={to} className="mb-4 inline-flex items-center gap-1 text-sm font-medium text-royal hover:underline">
      <IconArrowLeft size={16} /> {label}
    </Link>
  );
}

function Header({ card }: { card: InvestorCard | SupplierCard }) {
  const primary = UPGRADE_ICON[card.upgrades[0]] ?? UPGRADE_ICON.solar;
  return (
    <div className="mb-6 flex flex-wrap items-start gap-4">
      <IconDisc icon={primary.icon} tint={primary.tint} size={56} />
      <div className="min-w-0 flex-1">
        <p className="eyebrow text-muted">
          {card.id} · Listed {date(card.listed_at)}
        </p>
        <h1 className="text-2xl leading-8 font-bold">{card.upgrade_labels.join(" + ")}</h1>
        <p className="text-muted">
          {card.size} {card.sector.toLowerCase()} business · {card.state} · {card.age_band}
        </p>
      </div>
      {card.my_request && <StatusChip status={card.my_request.status} />}
    </div>
  );
}

function IdentityCard({ identity }: { identity: Identity }) {
  return (
    <Card className="border border-[#BFE0CD]">
      <div className="mb-3 flex items-center gap-2 text-success">
        <IconLockOpen size={20} aria-hidden />
        <h2 className="font-semibold">Shared with you by the owner</h2>
      </div>
      <dl>
        <Field label="Company" value={identity.company_name} />
        <Field label="Registration no." value={identity.reg_no} />
        <Field label="Site address" value={identity.address} />
        <Field label="Contact person" value={identity.contact_person} />
        <Field label="Phone" value={identity.contact_phone} />
        <Field label="Email" value={identity.contact_email} />
      </dl>
    </Card>
  );
}

// ---------------------------------------------------------------- investor
export function InvestorListingPage() {
  const { id = "" } = useParams();
  const navigate = useNavigate();
  const { data: card, error, loading, reload } = useApi<InvestorCard>(`/listings/${id}`);
  const [requesting, setRequesting] = useState(false);
  if (loading && !card) return <Loading />;
  if (error) return <ErrorBox message={error} />;
  if (!card) return null;
  const request = card.my_request;
  const canRequest = !request || request.status === "declined" || request.status === "expired";

  return (
    <>
      <Back to="/investor/board" label="Opportunity Board" />
      <Header card={card} />
      <div className="grid gap-4 lg:grid-cols-3">
        <div className="space-y-4 lg:col-span-2">
          <Card>
            <h2 className="mb-3 text-lg font-semibold">Listing facts</h2>
            <dl>
              <Field label="Company status" value={<span className="text-success">✓ {card.company_status}</span>} />
              <Field label="Upgrade wanted" value={card.upgrade_labels.join(", ")} />
              <Field label="Usage band" value={card.usage_band} />
              <Field label="Monthly bill band" value={card.bill_band} />
              <Field label="Estimated cost (CapEx band)" value={card.capex_band} />
              <Field label="Estimated saving" value={`About ${rm(card.saving_approx_myr)}/year`} />
              <Field label="Payback" value={`About ${years(card.payback_approx_years)}`} />
              <Field label="CO2e avoided" value={`About ${card.co2e_approx_t} t/year`} />
              <Field label="Evidence" value={<EvidenceBadge evidence={card.evidence} />} />
            </dl>
          </Card>
          <RepaymentCheck listingId={card.id} saving={card.saving_approx_myr} />
          {card.identity && card.unlocked && (
            <Card>
              <h2 className="mb-3 text-lg font-semibold">Preparation Pack (unlocked)</h2>
              <dl>
                <Field label={`Bill · ${card.unlocked.bill.month}`} value={`${rm(card.unlocked.bill.amount_myr)} · ${num(card.unlocked.bill.usage_kwh)} kWh`} />
                <Field label="6-month average" value={`${num(card.unlocked.bill.average_kwh)} kWh`} />
                <Field label="Checks" value={`${card.unlocked.bill.checks_passed}/${card.unlocked.bill.checks_total} passed ✓`} />
                {card.unlocked.upgrades.map((upgrade) => (
                  <Field
                    key={upgrade.type}
                    label={`${upgrade.label} (${upgrade.size})`}
                    value={`${rm(upgrade.capex_myr)} · saves ${rm(upgrade.saving_myr_year)}/yr · ${years(upgrade.payback_years)}`}
                  />
                ))}
              </dl>
            </Card>
          )}
        </div>
        <div className="space-y-4">
          {card.identity ? (
            <>
              <IdentityCard identity={card.identity} />
              <Button block onClick={() => navigate(`/investor/eoi/${request!.id}`)}>
                <IconSend size={16} /> Send EOI
              </Button>
            </>
          ) : (
            <Card>
              <LockedList items={card.hidden ?? []} />
              <p className="eyebrow mt-5 mb-2 text-muted">Unlocked after acceptance</p>
              <ul className="space-y-1 text-sm">
                {(card.unlocks ?? []).map((item) => (
                  <li key={item}>• {item}</li>
                ))}
              </ul>
              <div className="mt-5">
                {canRequest ? (
                  <Button block onClick={() => setRequesting(true)}>
                    Request to connect
                  </Button>
                ) : (
                  <Notice>Request sent {date(request!.created_at)}. The owner decides whether to accept.</Notice>
                )}
              </div>
            </Card>
          )}
          {card.criteria.total > 0 && (
            <Card>
              <h2 className="mb-2 font-semibold">
                Meets your criteria · {card.criteria.passed} of {card.criteria.total}
              </h2>
              <ul className="space-y-1.5 text-sm">
                {card.criteria.checks.map((check) => (
                  <li key={check.label} className="flex items-center gap-2">
                    {check.passed ? <IconCheck size={16} className="text-success" /> : <IconX size={16} className="text-danger" />}
                    {check.label}
                  </li>
                ))}
              </ul>
            </Card>
          )}
          <Disclaimer>{card.disclaimer}</Disclaimer>
        </div>
      </div>
      {requesting && <RequestModal listingId={card.id} onClose={() => setRequesting(false)} onSent={() => { setRequesting(false); reload(); }} />}
    </>
  );
}

type Repayment = { monthly_instalment_myr: number; yearly_instalment_myr: number; saving_used_myr_year: number; coverage: number; note: string };

function RepaymentCheck({ listingId, saving }: { listingId: string; saving: number }) {
  const { call } = useSession();
  const [loan, setLoan] = useState("45000");
  const [tenor, setTenor] = useState("5");
  const [rate, setRate] = useState("");
  const [result, setResult] = useState<Repayment | null>(null);
  const [error, setError] = useState<string | null>(null);

  const run = async () => {
    setError(null);
    try {
      setResult(
        await call<Repayment>(`/listings/${listingId}/repayment-check`, {
          method: "POST",
          body: { loan_myr: Number(loan), tenor_years: Number(tenor), rate_percent: Number(rate) },
        }),
      );
    } catch (err) {
      setError((err as Error).message);
      setResult(null);
    }
  };
  const input = "mt-1 h-10 w-full rounded-lg border border-line px-3 font-normal tnum";
  return (
    <Card>
      <h2 className="text-lg font-semibold">Repayment check on your own terms</h2>
      <p className="mb-4 text-sm text-muted">Uses the estimated saving of about {rm(saving)}/year. You type the terms.</p>
      <div className="grid gap-3 sm:grid-cols-4">
        <label className="text-sm font-semibold">
          Loan amount (RM)
          <input className={input} inputMode="numeric" value={loan} onChange={(e) => setLoan(e.target.value.replace(/[^\d.]/g, ""))} />
        </label>
        <label className="text-sm font-semibold">
          Tenor (years)
          <input className={input} inputMode="numeric" value={tenor} onChange={(e) => setTenor(e.target.value.replace(/[^\d.]/g, ""))} />
        </label>
        <label className="text-sm font-semibold">
          Your rate (% a year)
          <input className={input} inputMode="decimal" value={rate} placeholder="e.g. 6.5" onChange={(e) => setRate(e.target.value.replace(/[^\d.]/g, ""))} />
        </label>
        <div className="flex items-end">
          <Button variant="secondary" block onClick={run} disabled={!loan || !tenor || !rate}>
            Check
          </Button>
        </div>
      </div>
      {error && <div className="mt-3"><ErrorBox message={error} /></div>}
      {result && (
        <div className="mt-4 flex flex-wrap items-center gap-6 rounded-xl bg-dawn px-5 py-4">
          <div>
            <p className="eyebrow text-royal">Savings coverage</p>
            <p className="tnum text-[32px] leading-10 font-bold">about {num(result.coverage, 1)}×</p>
          </div>
          <p className="tnum text-sm">
            Instalment {rm(result.monthly_instalment_myr)}/month ({rm(result.yearly_instalment_myr)}/year)
            <br />
            vs saving about {rm(result.saving_used_myr_year)}/year
          </p>
        </div>
      )}
      <p className="mt-3 text-xs text-muted">Your terms, your decision. GreenReady does not assess credit.</p>
    </Card>
  );
}

// ---------------------------------------------------------------- supplier
export function SupplierListingPage() {
  const { id = "" } = useParams();
  const navigate = useNavigate();
  const { data: card, error, loading } = useApi<SupplierCard>(`/listings/${id}`);
  if (loading && !card) return <Loading />;
  if (error) return <ErrorBox message={error} />;
  if (!card) return null;
  const request = card.my_request;
  const canSend = (!request || request.status === "declined" || request.status === "expired") && (card.requests_left ?? 0) > 0;
  return (
    <>
      <Back to="/supplier/board" label="Opportunity Board" />
      <Header card={card} />
      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <h2 className="mb-3 text-lg font-semibold">Listing facts</h2>
          <dl>
            <Field label="State" value={<>{card.state} {card.match.in_service_area && <Chip tone="success">✓ inside your service area</Chip>}</>} />
            <Field label="Upgrade wanted" value={<>{card.upgrade_labels.join(", ")} <Chip tone="success">✓ matches your category</Chip></>} />
            <Field label="Usage band" value={card.usage_band} />
            <Field label="Daytime operation" value={card.daytime_operation ? "Yes" : "No"} />
            {card.suggested_solar_size && <Field label="Suggested size" value={`About ${card.suggested_solar_size} (for solar)`} />}
            {card.upgrades.includes("led") && <Field label="Lighting" value={`${card.lighting} (for LED)`} />}
            <Field label="Estimated cost (CapEx band)" value={card.capex_band} />
            <Field label="Existing quote" value={card.existing_quote ? "Yes" : "None yet (you'd be the first)"} />
            <Field label="Evidence" value={<EvidenceBadge evidence={card.evidence} />} />
          </dl>
          {card.unlocked && (
            <>
              <h2 className="mt-6 mb-3 text-lg font-semibold">Bill summary for sizing (unlocked)</h2>
              <dl>
                <Field label="6-month average" value={`${num(card.unlocked.average_kwh)} kWh/month`} />
                {Object.entries(card.unlocked.history).map(([month, kwh]) => (
                  <Field key={month} label={month} value={`${num(kwh)} kWh`} />
                ))}
              </dl>
            </>
          )}
        </Card>
        <div className="space-y-4">
          {card.identity ? (
            <IdentityCard identity={card.identity} />
          ) : (
            <Card>
              <LockedList items={card.hidden ?? []} />
              <div className="mt-5 space-y-3">
                <p className="tnum text-sm">Requests left this week: <strong>{card.requests_left} of 5</strong></p>
                {request && !canSend ? (
                  <Notice>Proposal sent {date(request.created_at)}. Waiting for the owner.</Notice>
                ) : (
                  <Button block disabled={!canSend} onClick={() => navigate(`/supplier/proposal/${card.id}`)}>
                    <IconSend size={16} /> Send proposal
                  </Button>
                )}
              </div>
            </Card>
          )}
          <Disclaimer>{card.disclaimer}</Disclaimer>
        </div>
      </div>
    </>
  );
}
