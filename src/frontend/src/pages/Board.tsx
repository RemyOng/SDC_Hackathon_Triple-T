import { useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { IconArrowUpRight, IconCheck, IconFilter, IconLayoutGrid, IconMapPin, IconSend } from "@tabler/icons-react";
import type { Criteria, Filters, InvestorCard, SupplierCard } from "../api";
import { date, rm, years } from "../format";
import { useApi, useSession } from "../session";
import {
  Button,
  Card,
  Chip,
  EmptyState,
  ErrorBox,
  EvidenceBadge,
  IconDisc,
  Loading,
  Notice,
  PageHeader,
  UPGRADE_ICON,
} from "../ui";
import { RequestModal } from "./ListingDetail";

type InvestorBoard = { listings: InvestorCard[]; note: string; criteria: Criteria };
type SupplierBoard = {
  listings: SupplierCard[];
  note: string;
  requests_left: number;
  requests_per_week: number;
  categories: string[];
  service_area: string[];
};

export function InvestorBoardPage() {
  const { data, error, loading, reload } = useApi<InvestorBoard>("/board");
  const filters = useApi<Filters>("/board/filters");
  const [onlyMatches, setOnlyMatches] = useState(false);
  const [requesting, setRequesting] = useState<InvestorCard | null>(null);

  const listings = useMemo(() => {
    const all = data?.listings ?? [];
    return onlyMatches ? all.filter((card) => card.criteria.total > 0 && card.criteria.passed === card.criteria.total) : all;
  }, [data, onlyMatches]);

  if (loading && !data) return <Loading />;
  if (error) return <ErrorBox message={error} />;
  if (!data) return null;

  return (
    <>
      <PageHeader title="Opportunity Board" subtitle={`${data.note} Every figure is a band or an estimate until an owner accepts.`} />
      {filters.data && (
        <CriteriaBar filters={filters.data} criteria={data.criteria} onSaved={reload} onlyMatches={onlyMatches} setOnlyMatches={setOnlyMatches} />
      )}
      {listings.length === 0 ? (
        <EmptyState icon={IconLayoutGrid} text="No live listings meet all of your criteria right now. Loosen a filter to see more." />
      ) : (
        <Grid>
          {listings.map((card) => (
            <InvestorListingCard key={card.id} card={card} onRequest={() => setRequesting(card)} />
          ))}
        </Grid>
      )}
      {requesting && (
        <RequestModal
          listingId={requesting.id}
          onClose={() => setRequesting(null)}
          onSent={() => {
            setRequesting(null);
            reload();
          }}
        />
      )}
    </>
  );
}

export function SupplierBoardPage() {
  const { data, error, loading } = useApi<SupplierBoard>("/board");
  if (loading && !data) return <Loading />;
  if (error) return <ErrorBox message={error} />;
  if (!data) return null;
  return (
    <>
      <PageHeader
        title="Opportunity Board"
        subtitle={data.note}
        actions={
          <Chip tone={data.requests_left > 0 ? "info" : "warning"} className="tnum px-3 py-1 text-sm">
            Requests left this week: {data.requests_left} of {data.requests_per_week}
          </Chip>
        }
      />
      <div className="mb-6">
        <Notice>
          Showing listings inside your service area ({data.service_area.join(", ")}) that want your categories (
          {data.categories.join(", ")}). You pay RM200 only when an owner accepts your proposal.
        </Notice>
      </div>
      {data.listings.length === 0 ? (
        <EmptyState icon={IconMapPin} text="No live listings match your categories and service area yet." />
      ) : (
        <Grid>
          {data.listings.map((card) => (
            <SupplierListingCard key={card.id} card={card} requestsLeft={data.requests_left} />
          ))}
        </Grid>
      )}
    </>
  );
}

function Grid({ children }: { children: React.ReactNode }) {
  return <div className="stagger grid grid-cols-1 gap-5 md:grid-cols-2 xl:grid-cols-3">{children}</div>;
}

// ------------------------------------------------------------------ cards
function CardShell({
  card,
  to,
  title,
  description,
  children,
  button,
}: {
  card: InvestorCard | SupplierCard;
  to: string;
  title: string;
  description: string;
  children: React.ReactNode;
  button: React.ReactNode;
}) {
  const primary = UPGRADE_ICON[card.upgrades[0]] ?? UPGRADE_ICON.solar;
  return (
    <article className="lift flex flex-col rounded-[20px] bg-white p-5 shadow-card hover:shadow-modal">
      <div className="flex items-start justify-between">
        <IconDisc icon={primary.icon} tint={primary.tint} />
        <Link
          to={to}
          className="flex h-9 w-9 items-center justify-center rounded-full bg-porcelain text-midnight hover:bg-dawn"
          aria-label={`Open listing ${card.id}`}
        >
          <IconArrowUpRight size={18} stroke={1.75} />
        </Link>
      </div>
      <p className="eyebrow mt-4 text-muted">
        {card.id} · {date(card.listed_at)}
      </p>
      <h3 className="mt-1 text-xl leading-7 font-semibold">
        <Link to={to} className="hover:text-royal">
          {title}
        </Link>
      </h3>
      <p className="mt-2 line-clamp-4 text-[13px] leading-5 text-muted">{description}</p>
      <div className="mt-4 flex-1 space-y-3">{children}</div>
      <div className="mt-5">{button}</div>
    </article>
  );
}

function MiniStats({ items }: { items: [string, string][] }) {
  return (
    <dl className="grid grid-cols-3 gap-2 rounded-xl bg-porcelain px-3 py-2.5">
      {items.map(([label, value]) => (
        <div key={label}>
          <dt className="text-[11px] leading-4 text-muted">{label}</dt>
          <dd className="tnum text-sm font-semibold">{value}</dd>
        </div>
      ))}
    </dl>
  );
}

function InvestorListingCard({ card, onRequest }: { card: InvestorCard; onRequest: () => void }) {
  const to = `/investor/listing/${card.id}`;
  const allMatch = card.criteria.total > 0 && card.criteria.passed === card.criteria.total;
  const request = card.my_request;
  return (
    <CardShell
      card={card}
      to={to}
      title={card.upgrade_labels.join(" + ")}
      description={`${card.size} ${card.sector.toLowerCase()} · ${card.state} · ${card.age_band}. Uses ${card.usage_band.replace("/month", "")} a month; bill ${card.bill_band}.`}
      button={
        request && request.status !== "declined" && request.status !== "expired" ? (
          <Link
            to={request.status === "accepted" ? "/investor/connections" : to}
            className={`flex min-h-10 w-full items-center justify-center gap-1.5 rounded-full text-sm font-semibold ${
              request.status === "accepted" ? "bg-[#E6F2EC] text-success" : "bg-dawn text-royal"
            }`}
          >
            {request.status === "accepted" ? (
              <>
                <IconCheck size={16} /> Connected · Send EOI
              </>
            ) : (
              "Requested · waiting for owner"
            )}
          </Link>
        ) : (
          <Button variant="soft" block onClick={onRequest}>
            Request to connect
          </Button>
        )
      }
    >
      <MiniStats
        items={[
          ["Saving / yr", `~${rm(card.saving_approx_myr)}`],
          ["Payback", `~${years(card.payback_approx_years)}`],
          ["CO2e / yr", `~${card.co2e_approx_t} t`],
        ]}
      />
      <div className="flex flex-wrap gap-1.5">
        {card.criteria.total > 0 && (
          <Chip tone={allMatch ? "success" : "neutral"}>
            {allMatch && <IconCheck size={12} />} Meets {card.criteria.passed} of {card.criteria.total}
          </Chip>
        )}
        <Chip tone="info">CapEx {card.capex_band}</Chip>
      </div>
      <EvidenceBadge evidence={card.evidence} />
    </CardShell>
  );
}

function SupplierListingCard({ card, requestsLeft }: { card: SupplierCard; requestsLeft: number }) {
  const navigate = useNavigate();
  const to = `/supplier/listing/${card.id}`;
  const request = card.my_request;
  const solar = card.match.matching_categories.includes("solar");
  const details = [`${card.size} ${card.sector.toLowerCase()} · ${card.state}.`, `Uses ${card.usage_band.replace("/month", "")} a month.`];
  details.push(card.daytime_operation ? "Runs in the daytime." : "Not a daytime operation.");
  if (card.upgrades.includes("led")) details.push(`Lighting: ${card.lighting}.`);
  return (
    <CardShell
      card={card}
      to={to}
      title={card.upgrade_labels.join(" + ")}
      description={details.join(" ")}
      button={
        request && request.status !== "declined" && request.status !== "expired" ? (
          <Link
            to={request.status === "accepted" ? "/supplier/leads" : "/supplier/requests"}
            className={`flex min-h-10 w-full items-center justify-center gap-1.5 rounded-full text-sm font-semibold ${
              request.status === "accepted" ? "bg-[#E6F2EC] text-success" : "bg-dawn text-royal"
            }`}
          >
            {request.status === "accepted" ? "✓ Accepted · view lead" : "Proposal sent · waiting"}
          </Link>
        ) : (
          <Button
            variant="soft"
            block
            disabled={requestsLeft === 0 || !solar}
            title={!solar ? "Proposal drafts cover rooftop solar listings" : requestsLeft === 0 ? "Weekly limit reached" : undefined}
            onClick={() => navigate(`/supplier/proposal/${card.id}`)}
          >
            <IconSend size={16} /> {requestsLeft === 0 ? "Weekly limit reached" : solar ? "Send proposal" : "Solar proposals only for now"}
          </Button>
        )
      }
    >
      <MiniStats
        items={[
          ["Suggested size", card.suggested_solar_size ? `~${card.suggested_solar_size}` : "—"],
          ["CapEx band", card.capex_band.replace("RM", "")],
          ["Quote", card.existing_quote ? "Yes" : "None yet"],
        ]}
      />
      <div className="flex flex-wrap gap-1.5">
        {card.match.in_service_area && (
          <Chip tone="success">
            <IconCheck size={12} /> In your area
          </Chip>
        )}
        <Chip tone="success">
          <IconCheck size={12} /> Matches {card.match.matching_categories.map((kind) => UPGRADE_ICON[kind]?.label ?? kind).join(", ")}
        </Chip>
      </div>
      <EvidenceBadge evidence={card.evidence} />
    </CardShell>
  );
}

// ------------------------------------------------------ investor criteria
function CriteriaBar({
  filters,
  criteria,
  onSaved,
  onlyMatches,
  setOnlyMatches,
}: {
  filters: Filters;
  criteria: Criteria;
  onSaved: () => void;
  onlyMatches: boolean;
  setOnlyMatches: (value: boolean) => void;
}) {
  const { call, toast } = useSession();
  const [draft, setDraft] = useState<Criteria>(criteria);
  const [saving, setSaving] = useState(false);
  const set = (key: keyof Criteria, value: string, numeric = false) =>
    setDraft((current) => ({ ...current, [key]: value === "" ? undefined : numeric ? Number(value) : value }));

  const save = async () => {
    setSaving(true);
    try {
      await call("/criteria", { method: "PUT", body: draft });
      toast("My criteria saved");
      onSaved();
    } catch (err) {
      toast((err as Error).message, "danger");
    } finally {
      setSaving(false);
    }
  };

  const select = "h-10 w-full rounded-lg border border-line bg-white px-3 text-sm";
  return (
    <Card className="mb-6 !p-5">
      <div className="mb-3 flex flex-wrap items-center gap-x-2 gap-y-1">
        <IconFilter size={18} className="text-royal" aria-hidden />
        <h2 className="font-semibold">My criteria</h2>
        <span className="text-xs text-muted">Your own lending rules (M02). GreenReady applies them; it never scores listings.</span>
      </div>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4 xl:grid-cols-7">
        <label className="text-xs text-muted">
          Upgrade
          <select className={select} value={draft.upgrade ?? ""} onChange={(e) => set("upgrade", e.target.value)}>
            <option value="">Any</option>
            {filters.upgrades.map((item) => (
              <option key={item.id} value={item.id}>
                {item.label}
              </option>
            ))}
          </select>
        </label>
        <label className="text-xs text-muted">
          State
          <select className={select} value={draft.state ?? ""} onChange={(e) => set("state", e.target.value)}>
            <option value="">Any</option>
            {filters.states.map((item) => (
              <option key={item}>{item}</option>
            ))}
          </select>
        </label>
        <label className="text-xs text-muted">
          Sector
          <select className={select} value={draft.sector ?? ""} onChange={(e) => set("sector", e.target.value)}>
            <option value="">Any</option>
            {filters.sectors.map((item) => (
              <option key={item}>{item}</option>
            ))}
          </select>
        </label>
        <label className="text-xs text-muted">
          CapEx band
          <select className={select} value={draft.capex_band ?? ""} onChange={(e) => set("capex_band", e.target.value)}>
            <option value="">Any</option>
            {filters.capex_bands.map((item) => (
              <option key={item}>{item}</option>
            ))}
          </select>
        </label>
        <label className="text-xs text-muted">
          Company age
          <select className={select} value={draft.min_age_years ?? ""} onChange={(e) => set("min_age_years", e.target.value, true)}>
            <option value="">Any</option>
            <option value="2">2+ years</option>
            <option value="5">5+ years</option>
            <option value="10">10+ years</option>
          </select>
        </label>
        <label className="text-xs text-muted">
          Min. saving / year (RM)
          <input
            className={select}
            inputMode="numeric"
            value={draft.min_saving_myr ?? ""}
            onChange={(e) => set("min_saving_myr", e.target.value.replace(/\D/g, ""), true)}
            placeholder="Any"
          />
        </label>
        <label className="text-xs text-muted">
          Payback under
          <select className={select} value={draft.max_payback_years ?? ""} onChange={(e) => set("max_payback_years", e.target.value, true)}>
            <option value="">Any</option>
            {[2, 3, 5, 7].map((value) => (
              <option key={value} value={value}>
                {value} years
              </option>
            ))}
          </select>
        </label>
      </div>
      <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" className="h-4 w-4 accent-royal" checked={onlyMatches} onChange={(e) => setOnlyMatches(e.target.checked)} />
          Only show listings that meet all my criteria
        </label>
        <Button variant="secondary" onClick={save} loading={saving}>
          Save as My criteria
        </Button>
      </div>
    </Card>
  );
}
