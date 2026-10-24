export type Role = "sme_owner" | "sme_staff" | "investor" | "supplier" | "ops";

export const ROLE_HOME: Record<Role, string> = {
  sme_owner: "/sme/bills",
  sme_staff: "/sme/bills",
  investor: "/investor/board",
  supplier: "/supplier/board",
  ops: "/ops/audit",
};

const ROLE_KEY = "greenready.demoRole";

export function storedRole(): Role {
  // ?role=investor opens the demo straight into a role (handy for shared demo links).
  const fromUrl = new URLSearchParams(window.location.search).get("role") as Role | null;
  if (fromUrl && fromUrl in ROLE_HOME) {
    storeRole(fromUrl);
    return fromUrl;
  }
  try {
    const value = localStorage.getItem(ROLE_KEY) as Role | null;
    if (value && value in ROLE_HOME) return value;
  } catch {
    /* storage unavailable: fall back to the owner */
  }
  return "sme_owner";
}

export function storeRole(role: Role) {
  try {
    localStorage.setItem(ROLE_KEY, role);
  } catch {
    /* ignore */
  }
}

const SIGNED_IN_KEY = "greenready.signedIn";

export function storedSignedIn(): boolean {
  if (new URLSearchParams(window.location.search).get("role")) return true;
  try {
    return localStorage.getItem(SIGNED_IN_KEY) === "1";
  } catch {
    return false;
  }
}

export function storeSignedIn(value: boolean) {
  try {
    if (value) localStorage.setItem(SIGNED_IN_KEY, "1");
    else localStorage.removeItem(SIGNED_IN_KEY);
  } catch {
    /* ignore */
  }
}

export class ApiError extends Error {
  status: number;
  rule?: string;
  constructor(message: string, status: number, rule?: string) {
    super(message);
    this.status = status;
    this.rule = rule;
  }
}

export async function api<T>(role: Role, path: string, init: { method?: string; body?: unknown } = {}): Promise<T> {
  const response = await fetch(`/api/greenready${path}`, {
    method: init.method ?? "GET",
    headers: { "Content-Type": "application/json", "X-Demo-Role": role },
    body: init.body === undefined ? undefined : JSON.stringify(init.body),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = typeof data.detail === "string" ? data.detail : "Something went wrong. Please try again.";
    throw new ApiError(detail, response.status, data.rule ?? undefined);
  }
  return data as T;
}

export async function apiUpload<T>(role: Role, path: string, file: File): Promise<T> {
  const body = new FormData();
  body.append("file", file);
  const response = await fetch(`/api/greenready${path}`, { method: "POST", headers: { "X-Demo-Role": role }, body });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = typeof data.detail === "string" ? data.detail : "Upload failed. Please try again.";
    throw new ApiError(detail, response.status, data.rule ?? undefined);
  }
  return data as T;
}

// ---------------------------------------------------------------- types
export type Evidence = {
  months_of_bills: number;
  reading_type: string;
  checks_passed: number;
  checks_total: number;
  quote_attached?: boolean;
};

export type RequestSummary = {
  id: string;
  status: "requested" | "accepted" | "declined" | "expired";
  created_at: string;
  decided_at: string | null;
  document_ids: string[];
};

export type Identity = {
  company_name: string;
  reg_no: string;
  address: string;
  contact_person: string;
  contact_phone: string;
  contact_email: string;
  directors: string[];
};

export type Upgrade = {
  type: string;
  label: string;
  size: string;
  capex_myr: number;
  saving_myr_year: number;
  payback_years: number | null;
  co2e_t_year: number;
  basis: "estimate" | "exact";
};

type BaseCard = {
  id: string;
  sector: string;
  state: string;
  size: string;
  age_band: string;
  company_status: string;
  upgrades: string[];
  upgrade_labels: string[];
  usage_band: string;
  capex_band: string;
  listed_at: string;
  disclaimer: string;
  my_request: RequestSummary | null;
  identity?: Identity;
  hidden?: string[];
  unlocks?: string[];
};

export type InvestorCard = BaseCard & {
  bill_band: string;
  saving_approx_myr: number;
  payback_approx_years: number | null;
  co2e_approx_t: number;
  evidence: Evidence;
  criteria: { checks: { label: string; passed: boolean }[]; passed: number; total: number };
  unlocked?: {
    bill: Bill;
    upgrades: Upgrade[];
    ssm_profile: Record<string, string | number>;
    quote_attached: boolean;
  };
};

export type SupplierCard = BaseCard & {
  match: { in_service_area: boolean; matching_categories: string[]; visible: boolean };
  daytime_operation: boolean;
  lighting: string;
  existing_quote: boolean;
  evidence: Evidence;
  suggested_solar_size?: string;
  requests_left?: number;
  unlocked?: {
    average_kwh: number;
    usage_kwh: number;
    history: Record<string, number>;
    operations: Record<string, string | boolean>;
  };
};

export type Bill = {
  month: string;
  amount_myr: number;
  due: string;
  usage_kwh: number;
  average_kwh: number;
  history: Record<string, number>;
  months_of_bills: number;
  reading_type: string;
  checks_passed: number;
  checks_total: number;
  real_cost_per_kwh: number;
};

export type Partner = {
  id: string;
  type: "investor" | "supplier";
  name: string;
  contact_name: string;
  contact_title: string;
  address: string;
  unit?: string;
  seda_no?: string;
  seda_valid_until?: string;
  categories?: string[];
  service_area?: string[];
};

export type DocField = { key: string; label: string; suggested: string };

export type GrDocument = {
  id: string;
  type: "eoi" | "proposal";
  reference: string;
  status: "sent" | "accepted" | "declined";
  sent_at: string;
  listing_id: string;
  values: Record<string, string>;
  [key: string]: unknown;
};

export type SmeRequest = {
  id: string;
  listing_id: string;
  partner_id: string;
  partner_type: "investor" | "supplier";
  message: string;
  status: RequestSummary["status"];
  created_at: string;
  decided_at: string | null;
  decline_reason: string | null;
  document_ids: string[];
  partner: Partner;
  documents: GrDocument[];
  will_receive: string[];
};

export type SmeListing = {
  id: string;
  status: "live" | "unlisted" | "expired";
  listed_at: string;
  expires_at: string;
  company: Record<string, string | number | string[]>;
  bill: Bill;
  operations: Record<string, string | boolean>;
  upgrades: Upgrade[];
  upgrade_labels: string[];
  quote_attached: boolean;
  views: { investors: number; suppliers: number };
  evidence: Evidence;
  requests: SmeRequest[];
  partner_preview: InvestorCard;
  hidden: string[];
  disclaimer: string;
};

export type Criteria = {
  upgrade?: string;
  state?: string;
  sector?: string;
  capex_band?: string;
  min_age_years?: number;
  min_saving_myr?: number;
  max_payback_years?: number;
};

export type Filters = {
  sectors: string[];
  states: string[];
  upgrades: { id: string; label: string }[];
  capex_bands: string[];
  age_bands: string[];
};

export type AuditEvent = { at: string; user: string; role: string; action: string; object: string };

export type MenuItem = {
  id: number;
  parentId: number;
  menuType: "Category" | "Menu";
  menuName: string;
  icon: string;
  url: string;
};
