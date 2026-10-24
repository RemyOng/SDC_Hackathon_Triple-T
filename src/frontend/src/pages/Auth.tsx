import { useState, type FormEvent, type ReactNode } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  IconArrowLeft,
  IconArrowRight,
  IconBrandWhatsapp,
  IconBuildingBank,
  IconCheck,
  IconFileInvoice,
  IconReceipt,
  IconScale,
  IconSearch,
  IconUpload,
  IconX,
} from "@tabler/icons-react";
import { api, ApiError, ROLE_HOME, type Role } from "../api";
import { useSession } from "../session";
import { Button, Notice } from "../ui";

const DEMO_ACCOUNTS: { role: Role; label: string; who: string; email: string }[] = [
  { role: "sme_owner", label: "SME Owner", who: "Ahmad · Kilang Contoh", email: "ahmad@kilangcontoh.example" },
  { role: "sme_staff", label: "SME Staff", who: "Siti · Kilang Contoh", email: "siti@kilangcontoh.example" },
  { role: "investor", label: "Investor", who: "Bank Hijau Berhad", email: "green.sme@bankhijau.example" },
  { role: "supplier", label: "Supplier", who: "Suria Hijau Solar", email: "sales@suriahijau.example" },
  { role: "ops", label: "Orbyte Ops", who: "Orbyte staff", email: "ops@orbyte.example" },
];

const input =
  "mt-1.5 block h-11 w-full rounded-xl border border-line bg-white px-3.5 text-sm font-normal transition-colors focus:border-royal";

function AuthShell({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-screen bg-white">
      <aside className="relative hidden w-[44%] max-w-[620px] flex-col justify-between overflow-hidden bg-midnight p-12 text-white lg:flex">
        <div className="pointer-events-none absolute -top-40 -right-40 h-[520px] w-[520px] rounded-full bg-royal/50 blur-3xl" />
        <div className="pointer-events-none absolute -bottom-48 -left-24 h-[420px] w-[420px] rounded-full bg-china/30 blur-3xl" />
        <div className="relative flex items-center gap-3">
          <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-white">
            <img src={`${import.meta.env.BASE_URL}greenready-mark.png`} alt="" className="h-9 w-9" />
          </span>
          <span>
            <span className="block text-xl font-bold">Orbyte GreenReady</span>
            <span className="block text-sm text-sky">From Bills to Better Business</span>
          </span>
        </div>
        <div className="relative space-y-6">
          <h2 className="max-w-md text-[32px] leading-10 font-bold">Turn every TNB bill into a decision you control.</h2>
          {[
            { icon: IconReceipt, title: "Check every bill", text: "AI reads it, rules check it — 8 checks in under a minute." },
            { icon: IconScale, title: "Compare upgrades fairly", text: "Same formulas for every option. No supplier pays for the ranking." },
            { icon: IconBuildingBank, title: "Meet banks and suppliers on your terms", text: "Anonymous until you approve. You can unlist any time." },
          ].map(({ icon: Icon, title, text }) => (
            <div key={title} className="flex gap-4">
              <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-white/10">
                <Icon size={22} stroke={1.75} />
              </span>
              <span>
                <span className="block font-semibold">{title}</span>
                <span className="block text-sm text-sky">{text}</span>
              </span>
            </div>
          ))}
        </div>
        <p className="relative text-xs text-sky">A module inside Orbyte · Demo — synthetic data</p>
      </aside>
      <main className="flex flex-1 items-start justify-center overflow-y-auto px-4 py-10 sm:items-center sm:px-8">
        <div className="page-enter w-full max-w-[480px]">{children}</div>
      </main>
    </div>
  );
}

function MobileBrand() {
  return (
    <div className="mb-8 flex items-center gap-2.5 lg:hidden">
      <img src={`${import.meta.env.BASE_URL}greenready-mark.png`} alt="" className="h-9 w-9" />
      <span className="text-lg font-bold">Orbyte GreenReady</span>
    </div>
  );
}

// ------------------------------------------------------------------ sign in
export function LoginPage() {
  const { signIn } = useSession();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const enter = (role: Role) => {
    signIn(role);
    navigate(ROLE_HOME[role]);
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const result = await api<{ role: Role }>("sme_owner", "/auth/login", { method: "POST", body: { email, password } });
      enter(result.role);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthShell>
      <MobileBrand />
      <h1 className="text-[28px] leading-9 font-bold">Sign in</h1>
      <p className="mt-1 text-muted">Use your Orbyte account. GreenReady uses the same login and roles (Orbyte Connect).</p>

      <form onSubmit={submit} className="mt-8 space-y-4">
        <label className="block text-sm font-semibold">
          Work email
          <input className={input} type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        </label>
        <label className="block text-sm font-semibold">
          Password
          <input className={input} type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} required />
        </label>
        {error && <Notice tone="danger">{error}</Notice>}
        <Button type="submit" block loading={busy} className="h-11">
          Sign in with Orbyte
        </Button>
      </form>

      <div className="my-8 flex items-center gap-3 text-xs text-muted">
        <span className="h-px flex-1 bg-line" /> or use a demo account <span className="h-px flex-1 bg-line" />
      </div>
      <div className="grid gap-2 sm:grid-cols-2">
        {DEMO_ACCOUNTS.map((account) => (
          <button
            key={account.role}
            onClick={() => enter(account.role)}
            className="lift group flex items-center justify-between rounded-xl border border-line px-4 py-3 text-left hover:border-royal hover:bg-dawn/40"
          >
            <span>
              <span className="block text-sm font-semibold">{account.label}</span>
              <span className="block text-xs text-muted">{account.who}</span>
            </span>
            <IconArrowRight size={16} className="text-muted transition-transform group-hover:translate-x-0.5 group-hover:text-royal" />
          </button>
        ))}
      </div>
      <p className="mt-3 text-xs text-muted">Demo password for any account above: <span className="font-semibold text-midnight">demo</span></p>

      <p className="mt-10 text-sm">
        New to GreenReady?{" "}
        <Link to="/signup" className="font-semibold text-royal hover:underline">
          Create a business account
        </Link>
      </p>
    </AuthShell>
  );
}

// ------------------------------------------------------------------ sign up
type Check = { rule: string; passed: boolean; label: string };
type Company = {
  ssm_no: string;
  name: string;
  type: string;
  status: string;
  incorporated: string;
  msic: string;
  nature: string;
  state: string;
  directors: string[];
  sector: string;
  region: string;
  checks: Record<string, Check>;
  blocked: string | null;
};

const QUESTIONS: { key: string; title: string; options: [string, string][] }[] = [
  { key: "lighting", title: "What lighting do you mostly use?", options: [["fluorescent", "Fluorescent"], ["led", "LED"], ["not_sure", "Not sure"]] },
  {
    key: "aircon",
    title: "What kind of aircon do you have?",
    options: [["non_inverter", "Non-inverter"], ["inverter", "Inverter"], ["mixed", "Mixed"], ["none", "None"], ["not_sure", "Not sure"]],
  },
  { key: "roof_access", title: "Can you use your roof for solar?", options: [["yes", "Yes"], ["no", "No"], ["not_sure", "Not sure"]] },
  { key: "daytime", title: "Do you mostly operate in the daytime?", options: [["yes", "Yes"], ["no", "No"]] },
];

const STEPS = ["Account", "Company", "Quick questions", "Done"];
const SAMPLE_SSM = ["201901023456", "202101045678", "201801034567", "202301012345"];

export function SignupPage() {
  const { signIn } = useSession();
  const navigate = useNavigate();
  const [step, setStep] = useState(0);
  const [account, setAccount] = useState({ name: "", email: "", phone: "", password: "" });
  const [ssm, setSsm] = useState("");
  const [company, setCompany] = useState<Company | null>(null);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [units, setUnits] = useState("");
  const [consent, setConsent] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [credit, setCredit] = useState<{ free_credit_myr: number; free_analyses: number } | null>(null);

  const lookup = async (value = ssm) => {
    setBusy(true);
    setError(null);
    setCompany(null);
    try {
      setCompany(await api<Company>("sme_owner", `/onboarding/ssm/${encodeURIComponent(value.trim())}`));
    } catch (err) {
      setError((err as ApiError).message);
    } finally {
      setBusy(false);
    }
  };

  const register = async () => {
    setBusy(true);
    setError(null);
    try {
      const result = await api<{ free_credit_myr: number; free_analyses: number }>("sme_owner", "/onboarding/register", {
        method: "POST",
        body: {
          ssm_no: company!.ssm_no,
          owner_name: account.name,
          email: account.email,
          phone: account.phone,
          pdpa_consent: consent,
          answers,
          aircon_units: Number(units) || 0,
        },
      });
      setCredit(result);
      setStep(3);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const answered = QUESTIONS.filter((q) => answers[q.key]).length;
  const accountValid = account.name.trim() && /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(account.email) && account.password.length >= 6;

  return (
    <AuthShell>
      <MobileBrand />
      {step < 3 && (
        <Link to="/login" className="mb-6 inline-flex items-center gap-1 text-sm font-medium text-royal hover:underline">
          <IconArrowLeft size={16} /> Back to sign in
        </Link>
      )}
      <ol className="mb-8 flex items-center gap-2" aria-label="Sign-up progress">
        {STEPS.map((label, index) => (
          <li key={label} className="flex flex-1 flex-col gap-1.5">
            <span className={`h-1.5 rounded-full transition-colors duration-300 ${index <= step ? "bg-royal" : "bg-porcelain"}`} />
            <span className={`text-[11px] font-semibold ${index === step ? "text-royal" : "text-muted"}`}>{label}</span>
          </li>
        ))}
      </ol>

      {step === 0 && (
        <div key="s0" className="page-enter">
          <h1 className="text-[28px] leading-9 font-bold">Create your business account</h1>
          <p className="mt-1 text-muted">You become the owner — the person who approves listings and connections (rule C05).</p>
          <div className="mt-8 space-y-4">
            <label className="block text-sm font-semibold">
              Full name
              <input className={input} value={account.name} onChange={(e) => setAccount({ ...account, name: e.target.value })} autoComplete="name" />
            </label>
            <label className="block text-sm font-semibold">
              Work email
              <input className={input} type="email" value={account.email} onChange={(e) => setAccount({ ...account, email: e.target.value })} autoComplete="email" />
            </label>
            <label className="block text-sm font-semibold">
              Mobile (for WhatsApp bill forwarding)
              <input className={input} inputMode="tel" placeholder="+60 12-345 6789" value={account.phone} onChange={(e) => setAccount({ ...account, phone: e.target.value })} />
            </label>
            <label className="block text-sm font-semibold">
              Password
              <input className={input} type="password" value={account.password} onChange={(e) => setAccount({ ...account, password: e.target.value })} autoComplete="new-password" />
              <span className="mt-1 block text-xs font-normal text-muted">At least 6 characters. This becomes your Orbyte Connect login.</span>
            </label>
          </div>
          <Button block className="mt-8 h-11" disabled={!accountValid} onClick={() => setStep(1)}>
            Continue <IconArrowRight size={16} />
          </Button>
        </div>
      )}

      {step === 1 && (
        <div key="s1" className="page-enter">
          <h1 className="text-[28px] leading-9 font-bold">Your company</h1>
          <p className="mt-1 text-muted">Enter your SSM number. We fill in the rest from the SSM register.</p>
          <form
            className="mt-6 flex gap-2"
            onSubmit={(event) => {
              event.preventDefault();
              lookup();
            }}
          >
            <input
              className={`${input} mt-0 tnum`}
              inputMode="numeric"
              maxLength={12}
              placeholder="12-digit SSM number"
              aria-label="SSM registration number"
              value={ssm}
              onChange={(e) => setSsm(e.target.value.replace(/\D/g, ""))}
            />
            <Button type="submit" variant="secondary" loading={busy} className="h-11 shrink-0">
              <IconSearch size={16} /> Look up
            </Button>
          </form>
          <p className="mt-2 flex flex-wrap items-center gap-1.5 text-xs text-muted">
            Try:
            {SAMPLE_SSM.map((value) => (
              <button
                key={value}
                className="tnum rounded-full bg-porcelain px-2 py-0.5 font-medium text-midnight hover:bg-dawn"
                onClick={() => {
                  setSsm(value);
                  lookup(value);
                }}
              >
                {value}
              </button>
            ))}
          </p>
          {error && <div className="mt-4"><Notice tone="danger">{error}</Notice></div>}
          {company && (
            <div className="page-enter mt-6 rounded-2xl border border-line p-5">
              <p className="text-lg font-semibold">{company.name}</p>
              <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
                {[
                  ["Registration no.", company.ssm_no],
                  ["Incorporated", new Date(company.incorporated).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" })],
                  ["Type", company.type],
                  ["Status", company.status],
                  ["Business (MSIC)", `${company.nature} (${company.msic})`],
                  ["Directors", company.directors.join(", ")],
                  ["State", company.state],
                ].map(([label, value]) => (
                  <div key={label} className={label === "Business (MSIC)" ? "col-span-2" : ""}>
                    <dt className="text-xs text-muted">{label}</dt>
                    <dd className="font-medium">{value}</dd>
                  </div>
                ))}
              </dl>
              <div className="mt-4 flex flex-wrap gap-1.5">
                {Object.values(company.checks).map((check) => (
                  <span
                    key={check.rule}
                    title={`Rule ${check.rule}`}
                    className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-semibold ${
                      check.passed ? "bg-[#E6F2EC] text-success" : "bg-[#FBEAE8] text-danger"
                    }`}
                  >
                    {check.passed ? <IconCheck size={12} /> : <IconX size={12} />} {check.label}
                  </span>
                ))}
              </div>
              <p className="mt-2 text-xs text-muted">Read-only, from SSM. Contact SSM if anything is wrong.</p>
              {company.blocked && <div className="mt-4"><Notice tone="danger">{company.blocked}</Notice></div>}
            </div>
          )}
          <div className="mt-8 flex gap-2">
            <Button variant="secondary" className="h-11" onClick={() => setStep(0)}>
              Back
            </Button>
            <Button className="h-11 flex-1" disabled={!company || !!company.blocked} onClick={() => setStep(2)}>
              Continue <IconArrowRight size={16} />
            </Button>
          </div>
        </div>
      )}

      {step === 2 && (
        <div key="s2" className="page-enter">
          <div className="flex items-baseline justify-between">
            <h1 className="text-[28px] leading-9 font-bold">Four quick questions</h1>
            <span className="tnum text-sm font-semibold text-royal">{answered} of 4</span>
          </div>
          <p className="mt-1 text-muted">These decide which upgrades we compare for you.</p>
          <div className="mt-6 space-y-6">
            {QUESTIONS.map((question) => (
              <fieldset key={question.key}>
                <legend className="mb-2 text-sm font-semibold">{question.title}</legend>
                <div className="flex flex-wrap gap-2">
                  {question.options.map(([value, label]) => {
                    const selected = answers[question.key] === value;
                    return (
                      <label
                        key={value}
                        className={`flex min-h-11 cursor-pointer items-center gap-2 rounded-xl border px-4 text-sm font-medium transition-colors ${
                          selected ? "border-royal bg-dawn text-midnight" : "border-line hover:border-china"
                        }`}
                      >
                        <input
                          type="radio"
                          name={question.key}
                          value={value}
                          checked={selected}
                          onChange={() => setAnswers({ ...answers, [question.key]: value })}
                          className="sr-only"
                        />
                        {selected && <IconCheck size={16} className="text-royal" />}
                        {label}
                      </label>
                    );
                  })}
                </div>
                {question.key === "aircon" && ["non_inverter", "inverter", "mixed"].includes(answers.aircon) && (
                  <label className="mt-3 block text-sm font-semibold">
                    Number of aircon units
                    <input className={`${input} tnum w-32`} inputMode="numeric" value={units} onChange={(e) => setUnits(e.target.value.replace(/\D/g, ""))} />
                  </label>
                )}
              </fieldset>
            ))}
          </div>
          <label className="mt-8 flex items-start gap-3 rounded-xl bg-moon p-4 text-sm">
            <input type="checkbox" className="mt-0.5 h-4 w-4 accent-royal" checked={consent} onChange={(e) => setConsent(e.target.checked)} />
            <span>
              I agree that GreenReady may process my company's bills to check them and prepare estimates, as described in the PDPA notice
              (version PDPA-2026-1). Nothing is shared with banks or suppliers unless I approve it.
            </span>
          </label>
          {error && <div className="mt-4"><Notice tone="danger">{error}</Notice></div>}
          <div className="mt-8 flex gap-2">
            <Button variant="secondary" className="h-11" onClick={() => setStep(1)}>
              Back
            </Button>
            <Button className="h-11 flex-1" disabled={answered < 4 || !consent} loading={busy} onClick={register}>
              Create account
            </Button>
          </div>
        </div>
      )}

      {step === 3 && credit && company && (
        <div key="s3" className="page-enter">
          <span className="flex h-14 w-14 items-center justify-center rounded-2xl bg-[#E6F2EC] text-success">
            <IconCheck size={28} />
          </span>
          <h1 className="mt-5 text-[28px] leading-9 font-bold">Welcome, {account.name.split(" ")[0]}</h1>
          <p className="mt-2 text-lg">
            <span className="tnum font-bold text-royal">RM{credit.free_credit_myr.toFixed(0)}</span> free credit added to your Orbyte wallet — enough
            for {credit.free_analyses} bill analyses.
          </p>
          <p className="mt-1 text-sm text-muted">{company.name} is ready. Send your first TNB bill to see your check in about 3 minutes.</p>
          <div className="mt-6 grid gap-3">
            {[
              { icon: IconFileInvoice, title: "Claim it in eClaim", text: "Use the “TNB bill” claim type — analysis starts automatically." },
              { icon: IconBrandWhatsapp, title: "Forward on WhatsApp", text: "Send the bill photo or PDF to the GreenReady number." },
              { icon: IconUpload, title: "Upload here", text: "PDF, JPG, PNG or a screenshot." },
            ].map(({ icon: Icon, title, text }) => (
              <div key={title} className="flex items-center gap-4 rounded-2xl border border-line p-4">
                <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-dawn">
                  <Icon size={22} stroke={1.75} className="text-royal" />
                </span>
                <span>
                  <span className="block font-semibold">{title}</span>
                  <span className="block text-sm text-muted">{text}</span>
                </span>
              </div>
            ))}
          </div>
          <Button
            block
            className="mt-8 h-11"
            onClick={() => {
              signIn("sme_owner");
              navigate(ROLE_HOME.sme_owner);
            }}
          >
            Go to GreenReady <IconArrowRight size={16} />
          </Button>
          <p className="mt-3 text-xs text-muted">Demo: the dashboard continues with the sample company Kilang Contoh, which already has 6 months of bills.</p>
        </div>
      )}
    </AuthShell>
  );
}
