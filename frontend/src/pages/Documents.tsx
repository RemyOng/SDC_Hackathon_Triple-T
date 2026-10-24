import { useEffect, useState, type ReactNode } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { IconArrowLeft, IconSend } from "@tabler/icons-react";
import type { DocField, Evidence, GrDocument } from "../api";
import { date, num, rm } from "../format";
import { useApi, useSession } from "../session";
import { Button, Card, Disclaimer, ErrorBox, Loading, Modal, Notice, StatusChip } from "../ui";

type Values = Record<string, string>;
type Edit = { editable: boolean; values: Values; onChange: (key: string, value: string) => void };

/** Inline bracketed field: an input while drafting, plain text once sent. */
function F({ k, edit, width = 12, numeric }: { k: string; edit: Edit; width?: number; numeric?: boolean }) {
  const value = edit.values[k] ?? "";
  if (!edit.editable) return <span className="font-medium">{value}</span>;
  return (
    <input
      aria-label={k.replace(/_/g, " ")}
      className={`doc-field ${value.trim() ? "" : "empty"} ${numeric ? "tnum" : ""}`}
      style={{ width: `${Math.max(width, value.length + 2)}ch` }}
      inputMode={numeric ? "numeric" : undefined}
      value={value}
      placeholder="…"
      onChange={(event) => edit.onChange(k, event.target.value)}
    />
  );
}

function Paper({ children }: { children: ReactNode }) {
  return (
    <article className="mx-auto w-full max-w-[794px] rounded-lg border border-line bg-jicama px-6 py-8 text-[13px] leading-[21px] shadow-card sm:px-12 sm:py-12">
      {children}
    </article>
  );
}

function DocTable({ head, rows }: { head?: ReactNode[]; rows: ReactNode[][] }) {
  return (
    <div className="my-3 overflow-x-auto">
      <table className="w-full border-collapse text-left">
        {head && (
          <thead>
            <tr className="border-b-2 border-midnight">
              {head.map((cell, index) => (
                <th key={index} className="py-1.5 pr-3 font-semibold">
                  {cell}
                </th>
              ))}
            </tr>
          </thead>
        )}
        <tbody>
          {rows.map((row, index) => (
            <tr key={index} className="border-b border-line align-top">
              {row.map((cell, cellIndex) => (
                <td key={cellIndex} className={`py-1.5 pr-3 ${cellIndex === 0 ? "w-[38%] font-semibold" : ""}`}>
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

const H = ({ children }: { children: ReactNode }) => <h3 className="mt-6 mb-1 text-sm font-bold">{children}</h3>;

function evidenceText(evidence: Evidence) {
  return [
    `${evidence.months_of_bills} months of TNB bills`,
    `${evidence.reading_type} meter readings`,
    `${evidence.checks_passed}/${evidence.checks_total} checks passed`,
    evidence.quote_attached ? "quote attached" : "no quote yet",
  ].join(" · ");
}

function useDraftValues(fields: DocField[] | undefined) {
  const [values, setValues] = useState<Values>({});
  useEffect(() => {
    if (fields) setValues(Object.fromEntries(fields.map((field) => [field.key, field.suggested])));
  }, [fields]);
  const missing = (fields ?? []).filter((field) => !(values[field.key] ?? "").trim()).map((field) => field.label);
  return { values, setValue: (key: string, value: string) => setValues((v) => ({ ...v, [key]: value })), missing };
}

// =================================================================== EOI
type EoiDoc = {
  type: "eoi";
  request_id: string;
  listing_id: string;
  date: string;
  valid_until: string;
  reference?: string;
  status?: string;
  from: { name: string; unit: string; address: string; contact_phone: string; contact_email: string; contact_title: string };
  to: { company_name: string; reg_no: string; address: string };
  subject: string;
  summary: {
    business: string;
    upgrade: string;
    capex_myr: number;
    saving_myr_year: number;
    co2e_t_year: number;
    basis: string;
    evidence: Evidence;
  };
  documents_requested: string[];
  fields: DocField[];
  disclaimer: string;
  values?: Values;
};

export function EoiPaper({ doc, edit }: { doc: EoiDoc; edit: Edit }) {
  const s = doc.summary;
  return (
    <Paper>
      <header className="border-b-2 border-midnight pb-3">
        <p className="text-lg font-bold tracking-wide uppercase">{doc.from.name}</p>
        <p className="text-xs text-muted">
          (fictional) · {doc.from.unit} · {doc.from.address} · {doc.from.contact_phone} / {doc.from.contact_email}
        </p>
      </header>
      <h2 className="mt-6 text-center text-base font-bold tracking-wide">EXPRESSION OF INTEREST — GREEN FINANCING</h2>
      <p className="text-center text-xs">(Non-binding)</p>
      <DocTable
        rows={[
          ["Reference", <span className="tnum">{doc.reference ?? "Assigned when sent"}</span>],
          ["Date", date(doc.date)],
          ["Valid until", date(doc.valid_until)],
        ]}
      />
      <p className="mt-4">To:</p>
      <p>The Directors</p>
      <p>
        <strong>{doc.to.company_name}</strong> (synthetic) · Registration No. {doc.to.reg_no}
      </p>
      <p>{doc.to.address}</p>
      <p className="mt-4 font-semibold">Re: {doc.subject}</p>
      <p className="mt-3">Dear Sirs,</p>
      <p className="mt-2">
        We refer to your Green Financing Preparation Pack shared with us through Orbyte GreenReady. Based on the information provided, we
        are pleased to express our interest in exploring financing for the above project.
      </p>

      <H>1. Project summary (from the Preparation Pack)</H>
      <DocTable
        head={["Item", "Details"]}
        rows={[
          ["Business", s.business],
          ["Upgrade", s.upgrade],
          ["Estimated cost", `≈ ${rm(Math.round(s.capex_myr / 100) * 100)} (${s.basis === "exact" ? "supplier quotation attached" : "GreenReady benchmark estimate"})`],
          ["Estimated electricity savings", `≈ ${rm(Math.round(s.saving_myr_year / 10) * 10)} per year (estimate)`],
          ["Estimated CO2e avoided", `≈ ${num(s.co2e_t_year, 1)} tonnes per year (estimate)`],
          ["Evidence", evidenceText(s.evidence)],
        ]}
      />

      <H>2. Indicative terms (for discussion only)</H>
      <DocTable
        head={["Term", "Indicative position"]}
        rows={[
          ["Purpose", `Purchase and installation of ${s.upgrade.split(",")[0].toLowerCase()}`],
          [
            "Indicative amount",
            <>
              <F k="amount_range" edit={edit} width={20} /> (up to <F k="max_percent" edit={edit} width={3} numeric />% of final supplier
              quotation)
            </>,
          ],
          [
            "Indicative tenure",
            <>
              Up to <F k="tenure_years" edit={edit} width={3} numeric /> years
            </>,
          ],
          ["Facility type", <F k="facility_type" edit={edit} width={30} />],
          ["Pricing", "To be advised after credit evaluation"],
          ["Security / guarantee", <F k="security" edit={edit} width={30} />],
        ]}
      />

      <H>3. Documents requested</H>
      <ul className="list-disc pl-5">
        {doc.documents_requested.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>

      <H>4. Next steps</H>
      <p>
        Our relationship manager, <F k="rm_name" edit={edit} width={14} />, will contact you within{" "}
        <F k="contact_days" edit={edit} width={3} numeric /> working days to arrange a meeting and a site visit if required.
      </p>

      <H>5. Important notice</H>
      <p>
        This letter is an expression of interest only. It is not an offer of financing and creates no legal obligation on either party.
        Any financing is subject to our credit assessment and approval, and to the issue of a formal Letter of Offer by the Bank. Figures
        in Section 1 are estimates prepared by the customer through Orbyte GreenReady and have not been verified by the Bank.
      </p>

      <p className="mt-6">Yours faithfully,</p>
      <p className="mt-8 w-56 border-t border-midnight pt-1">
        <F k="rm_name" edit={edit} width={14} />
      </p>
      <p>
        {doc.from.contact_title} · {doc.from.name} (fictional)
      </p>
      <p>
        {doc.from.contact_phone} · {doc.from.contact_email}
      </p>
    </Paper>
  );
}

export function EoiDraftPage() {
  const { requestId = "" } = useParams();
  const navigate = useNavigate();
  const { call, toast, refresh } = useSession();
  const { data: draft, error, loading } = useApi<EoiDoc>(`/documents/eoi/draft?request_id=${requestId}`);
  const { values, setValue, missing } = useDraftValues(draft?.fields);
  const [confirming, setConfirming] = useState(false);
  const [sending, setSending] = useState(false);
  const [sendError, setSendError] = useState<string | null>(null);

  if (loading && !draft) return <Loading />;
  if (error) return <ErrorBox message={error} />;
  if (!draft) return null;

  const send = async () => {
    setSending(true);
    setSendError(null);
    try {
      const sent = await call<GrDocument>("/documents/eoi", { method: "POST", body: { request_id: requestId, values } });
      toast(`EOI ${sent.reference} sent to ${draft.to.company_name}`);
      refresh();
      navigate("/investor/connections");
    } catch (err) {
      setSendError((err as Error).message);
      setConfirming(false);
    } finally {
      setSending(false);
    }
  };

  return (
    <>
      <BackLink to="/investor/connections" label="Connections" />
      <DraftHeader
        title="Expression of Interest"
        note={`Draft generated by Orbyte GreenReady from listing ${draft.listing_id}. Edit the highlighted fields; everything else comes from the Preparation Pack.`}
        missing={missing}
        onSend={() => setConfirming(true)}
        sendLabel="Send EOI"
      />
      {sendError && <div className="mb-4"><ErrorBox message={sendError} /></div>}
      <EoiPaper doc={draft} edit={{ editable: true, values, onChange: setValue }} />
      <div className="mx-auto mt-4 max-w-[794px]">
        <Disclaimer>{draft.disclaimer}</Disclaimer>
      </div>
      {confirming && (
        <Modal
          title="Send this EOI?"
          onClose={() => setConfirming(false)}
          footer={
            <>
              <Button variant="tertiary" onClick={() => setConfirming(false)}>
                Cancel
              </Button>
              <Button onClick={send} loading={sending}>
                Send EOI
              </Button>
            </>
          }
        >
          <p>
            <strong>{draft.to.company_name}</strong> will see this letter in their GreenReady Requests. It is non-binding and is not an
            offer of financing.
          </p>
        </Modal>
      )}
    </>
  );
}

// ============================================================== proposal
type ProposalDoc = {
  type: "proposal";
  listing_id: string;
  date: string;
  valid_until: string;
  reference?: string;
  status?: string;
  from: { name: string; ssm_no: string; seda_no: string; seda_valid_until: string; address: string; contact_phone: string; contact_email: string };
  listing: {
    upgrades: string[];
    state: string;
    in_service_area: boolean;
    business: string;
    usage_band: string;
    daytime_operation: boolean;
    suggested_size: string;
    existing_quote: boolean;
  };
  system_kwp: number;
  estimate: { generation_kwh_year: number; saving_myr_year: number; co2e_t_year: number };
  parameters: { solar_yield_kwh_per_kwp: number; tariff_myr_kwh: number; grid_factor_kg_kwh: number };
  fee_myr: number;
  requests_left: number;
  fields: DocField[];
  disclaimer: string;
  values?: Values;
};

function paybackRange(values: Values, option: "a" | "b", saving: number): string {
  const low = Number((values[`${option}_price_min`] ?? "").replace(/[^\d.]/g, ""));
  const high = Number((values[`${option}_price_max`] ?? "").replace(/[^\d.]/g, ""));
  if (!low || !high || !saving) return "—";
  return `≈ ${num(low / saving, 1)}–${num(high / saving, 1)} years`;
}

function priceRange(values: Values, option: "a" | "b", edit: Edit) {
  if (!edit.editable) {
    const low = Number(values[`${option}_price_min`]);
    const high = Number(values[`${option}_price_max`]);
    return `${rm(low)} – ${rm(high)}`;
  }
  return (
    <>
      RM <F k={`${option}_price_min`} edit={edit} width={7} numeric /> – RM <F k={`${option}_price_max`} edit={edit} width={7} numeric />
    </>
  );
}

export function ProposalPaper({ doc, edit }: { doc: ProposalDoc; edit: Edit }) {
  const l = doc.listing;
  const p = doc.parameters;
  const saving = doc.estimate.saving_myr_year;
  return (
    <Paper>
      <header className="border-b-2 border-midnight pb-3">
        <p className="text-lg font-bold tracking-wide uppercase">{doc.from.name}</p>
        <p className="text-xs text-muted">
          (fictional) · SSM {doc.from.ssm_no} · SEDA RPVSP No. {doc.from.seda_no} · {doc.from.address} · {doc.from.contact_phone} /{" "}
          {doc.from.contact_email}
        </p>
      </header>
      <h2 className="mt-6 text-center text-base font-bold tracking-wide">PROPOSAL: ROOFTOP SOLAR FOR YOUR BUSINESS</h2>
      <p className="text-center text-xs">Introductory proposal with indicative pricing (non-binding)</p>
      <DocTable
        rows={[
          ["Proposal No.", <span className="tnum">{doc.reference ?? "Assigned when sent"}</span>],
          ["Date", date(doc.date)],
          ["Valid until", date(doc.valid_until)],
          ["GreenReady listing", doc.listing_id],
        ]}
      />
      <p className="mt-4">
        <strong>To:</strong> Business owner, GreenReady listing {doc.listing_id}
      </p>
      <p className="text-xs text-muted">Your company name and contact details are shared with us only if you accept this request.</p>
      <p className="mt-3">Dear Business Owner,</p>
      <p className="mt-2">
        We saw your listing on the Orbyte GreenReady Opportunity Board and believe rooftop solar could cut your electricity costs
        significantly. Your listing matches the projects we install every month: a {l.daytime_operation ? "daytime " : ""}business in{" "}
        {l.state} with steady usage and a roof you can use. This short proposal explains what we would offer and what it could save you.
      </p>

      <H>1. What we understood from your listing</H>
      <DocTable
        head={["Listing detail", "What it tells us"]}
        rows={[
          ["Upgrade wanted", l.upgrades.join(", ")],
          ["Location", `${l.state}${l.in_service_area ? " — inside our service area" : ""}`],
          ["Business type", l.business],
          ["Electricity use", `${l.usage_band}${l.daytime_operation ? ", mainly daytime" : ""}`],
          ["Suggested system size", `About ${l.suggested_size} (GreenReady estimate from your bills)`],
          ["Current quote", l.existing_quote ? "A quote is attached — this would be a comparison quote" : "None attached — this would be your first or a comparison quote"],
        ]}
      />

      <H>2. Our proposed solution</H>
      <ul className="list-disc pl-5">
        <li>A grid-connected rooftop solar system of about {l.suggested_size}, sized to cover your daytime use</li>
        <li>Tier-1 mono PV modules and a 3-phase string inverter, with online monitoring</li>
        <li>We handle the full TNB Solar ATAP application and meter change</li>
        <li>Final size confirmed after a free site survey of your roof and wiring</li>
      </ul>

      <H>3. Indicative investment (two options)</H>
      <DocTable
        head={["", "Option A — Standard", "Option B — Premium", "Basis"]}
        rows={[
          ["System size", `${doc.system_kwp} kWp`, `${doc.system_kwp} kWp`, "Site survey"],
          ["Equipment", <F k="a_equipment" edit={edit} width={18} />, <F k="b_equipment" edit={edit} width={18} />, "Supplier"],
          ["Indicative price", priceRange(edit.values, "a", edit), priceRange(edit.values, "b", edit), "Supplier"],
          [
            "Inverter warranty",
            <><F k="a_inverter_warranty" edit={edit} width={3} numeric /> years</>,
            <><F k="b_inverter_warranty" edit={edit} width={3} numeric /> years</>,
            "Supplier",
          ],
          [
            "Panel performance warranty",
            <><F k="a_panel_warranty" edit={edit} width={3} numeric /> years</>,
            <><F k="b_panel_warranty" edit={edit} width={3} numeric /> years</>,
            "Supplier",
          ],
        ]}
      />
      <p className="text-xs">Prices are indicative ranges before a site survey and exclude service tax if applicable. A firm quotation follows the survey.</p>

      <H>4. What it could save you (estimates)</H>
      <DocTable
        head={["Item", "Estimate"]}
        rows={[
          ["Solar generation", `≈ ${num(Math.round(doc.estimate.generation_kwh_year / 100) * 100)} kWh per year (${doc.system_kwp} kWp × ${num(p.solar_yield_kwh_per_kwp)} kWh/kWp)`],
          ["Electricity savings", `≈ ${rm(Math.round(saving / 10) * 10)} per year at RM${p.tariff_myr_kwh}/kWh (TNB energy + capacity + network)`],
          ["Simple payback", `Option A ${paybackRange(edit.values, "a", saving)} · Option B ${paybackRange(edit.values, "b", saving)}`],
          ["CO2e avoided", `≈ ${num(doc.estimate.co2e_t_year, 1)} tonnes per year (Energy Commission factor ${p.grid_factor_kg_kwh.toFixed(3)} kg/kWh)`],
        ]}
      />
      <p className="text-xs">
        Savings use GreenReady's standard formulas so you can compare our proposal fairly with others. Actual results depend on weather,
        shading and your usage; this is not a guarantee.
      </p>

      <H>5. Why work with us</H>
      <ul className="list-disc pl-5">
        <li>
          SEDA Registered PV Service Provider — {doc.from.seda_no}, active until {date(doc.from.seda_valid_until)}
        </li>
        <li>
          <F k="installations" edit={edit} width={5} /> commercial rooftop installations in the Klang Valley since{" "}
          <F k="since_year" edit={edit} width={5} numeric />
        </li>
        <li>In-house licensed electrical team — no subcontracting of electrical works</li>
        <li>Staged payments (no full payment upfront) and a named after-sales contact</li>
        <li>Experienced with bank green-financing paperwork if you choose to finance the system</li>
      </ul>

      <H>6. Indicative timeline</H>
      <DocTable
        head={["Step", "Typical time"]}
        rows={[
          ["Free site survey after you accept", <>Within <F k="survey_days" edit={edit} width={3} numeric /> working days</>],
          ["Firm quotation and design", <>Within <F k="quote_days" edit={edit} width={3} numeric /> working days after survey</>],
          ["TNB Solar ATAP application", <>About <F k="atap_weeks" edit={edit} width={4} /> weeks</>],
          ["Installation and commissioning", <>About <F k="install_weeks" edit={edit} width={4} /> weeks</>],
        ]}
      />

      <H>7. Next steps</H>
      <ol className="list-decimal pl-5">
        <li>Accept our request on GreenReady to share your contact details.</li>
        <li>We arrange a free site survey at a time that suits you.</li>
        <li>We send a firm quotation with exact models, prices, warranties and payment terms.</li>
        <li>You compare it on GreenReady with any other quotes before deciding.</li>
      </ol>

      <H>8. Important notes</H>
      <p>
        This is an introductory proposal with indicative pricing only. It is not a binding offer or contract. Final price, system size and
        terms depend on a site survey and are set out in a formal quotation. Savings and payback are estimates. Any financing is arranged
        separately with a licensed bank and is subject to its own approval.
      </p>

      <p className="mt-6">Yours sincerely,</p>
      <p className="mt-8 w-56 border-t border-midnight pt-1">
        <F k="signer_name" edit={edit} width={14} />
      </p>
      <p>
        <F k="signer_designation" edit={edit} width={16} /> · {doc.from.name} (fictional)
      </p>
      <p>
        {doc.from.contact_phone} · {doc.from.contact_email}
      </p>
    </Paper>
  );
}

export function ProposalDraftPage() {
  const { listingId = "" } = useParams();
  const navigate = useNavigate();
  const { call, toast, refresh } = useSession();
  const { data: draft, error, loading } = useApi<ProposalDoc>(`/documents/proposal/draft?listing_id=${listingId}`);
  const { values, setValue, missing } = useDraftValues(draft?.fields);
  const [confirming, setConfirming] = useState(false);
  const [sending, setSending] = useState(false);
  const [sendError, setSendError] = useState<string | null>(null);

  if (loading && !draft) return <Loading />;
  if (error) return <ErrorBox message={error} />;
  if (!draft) return null;

  const send = async () => {
    setSending(true);
    setSendError(null);
    try {
      const sent = await call<{ document: GrDocument }>("/documents/proposal", { method: "POST", body: { listing_id: listingId, values } });
      toast(`Proposal ${sent.document.reference} sent`);
      refresh();
      navigate("/supplier/requests");
    } catch (err) {
      setSendError((err as Error).message);
      setConfirming(false);
    } finally {
      setSending(false);
    }
  };

  return (
    <>
      <BackLink to={`/supplier/listing/${listingId}`} label={`Listing ${listingId}`} />
      <DraftHeader
        title="Outreach proposal"
        note="Draft generated by Orbyte GreenReady from the listing facts and the GreenReady estimate. Edit the highlighted fields. The owner's identity stays hidden until they accept."
        missing={missing}
        onSend={() => setConfirming(true)}
        sendLabel="Send proposal"
        extra={
          <Notice>
            You pay <strong>{rm(draft.fee_myr)}</strong> only if the owner accepts. Requests left this week:{" "}
            <strong className="tnum">{draft.requests_left} of 5</strong>.
          </Notice>
        }
      />
      {sendError && <div className="mb-4"><ErrorBox message={sendError} /></div>}
      <ProposalPaper doc={draft} edit={{ editable: true, values, onChange: setValue }} />
      <div className="mx-auto mt-4 max-w-[794px]">
        <Disclaimer>{draft.disclaimer}</Disclaimer>
      </div>
      {confirming && (
        <Modal
          title="Send this proposal?"
          onClose={() => setConfirming(false)}
          footer={
            <>
              <Button variant="tertiary" onClick={() => setConfirming(false)}>
                Cancel
              </Button>
              <Button onClick={send} loading={sending}>
                Send proposal
              </Button>
            </>
          }
        >
          <p>This uses 1 of your {draft.requests_left} remaining requests this week.</p>
          <p>
            If the owner accepts, <strong>{rm(draft.fee_myr)}</strong> is added to your monthly Orbyte invoice and you receive their company
            name, contact person, site address and exact usage.
          </p>
        </Modal>
      )}
    </>
  );
}

// ================================================================ shared
function BackLink({ to, label }: { to: string; label: string }) {
  return (
    <Link to={to} className="mb-4 inline-flex items-center gap-1 text-sm font-medium text-royal hover:underline">
      <IconArrowLeft size={16} /> {label}
    </Link>
  );
}

function DraftHeader({
  title,
  note,
  missing,
  onSend,
  sendLabel,
  extra,
}: {
  title: string;
  note: string;
  missing: string[];
  onSend: () => void;
  sendLabel: string;
  extra?: ReactNode;
}) {
  return (
    <div className="mx-auto mb-6 max-w-[794px] space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl leading-8 font-bold">{title}</h1>
        <Button onClick={onSend} disabled={missing.length > 0} title={missing.length ? `Still to fill: ${missing.join(", ")}` : undefined}>
          <IconSend size={16} /> {sendLabel}
        </Button>
      </div>
      <p className="rounded-xl bg-asian-pear px-4 py-3 text-sm">{note}</p>
      {missing.length > 0 && (
        <p className="text-sm text-danger">
          ⚠ Still to fill: {missing.join(", ")}
        </p>
      )}
      {extra}
    </div>
  );
}

/** Read-only view of a sent EOI or proposal, used in request inboxes. */
export function SentDocument({ doc }: { doc: GrDocument }) {
  const edit: Edit = { editable: false, values: doc.values, onChange: () => undefined };
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2 text-sm">
        <span className="font-semibold">{doc.type === "eoi" ? "Expression of Interest" : "Outreach proposal"}</span>
        <span className="tnum text-muted">{doc.reference}</span>
        <StatusChip status={doc.status} />
      </div>
      {doc.type === "eoi" ? (
        <EoiPaper doc={doc as unknown as EoiDoc} edit={edit} />
      ) : (
        <ProposalPaper doc={doc as unknown as ProposalDoc} edit={edit} />
      )}
    </div>
  );
}

export function DocumentCard({ doc, children }: { doc: GrDocument; children?: ReactNode }) {
  return (
    <Card className="!p-4">
      <SentDocument doc={doc} />
      {children}
    </Card>
  );
}
