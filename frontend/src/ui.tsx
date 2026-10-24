import { useEffect, useRef, type ButtonHTMLAttributes, type ReactNode } from "react";
import {
  IconAirConditioning,
  IconAlertTriangle,
  IconBulb,
  IconCheck,
  IconCircleCheck,
  IconInfoCircle,
  IconLoader2,
  IconLock,
  IconSun,
  IconX,
  type Icon,
} from "@tabler/icons-react";
import type { Evidence } from "./api";
import { useSession } from "./session";

export const UPGRADE_ICON: Record<string, { icon: Icon; tint: string; label: string }> = {
  solar: { icon: IconSun, tint: "bg-tint-solar", label: "Rooftop solar" },
  led: { icon: IconBulb, tint: "bg-tint-led", label: "LED lighting" },
  aircon: { icon: IconAirConditioning, tint: "bg-tint-aircon", label: "Inverter aircon" },
};

// ---------------------------------------------------------------- buttons
type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "soft" | "tertiary" | "danger";
  loading?: boolean;
  block?: boolean;
};

export function Button({ variant = "primary", loading, block, className = "", children, disabled, ...rest }: ButtonProps) {
  const styles = {
    primary: "bg-royal text-white hover:bg-midnight",
    secondary: "bg-white text-royal border border-royal hover:bg-dawn",
    soft: "bg-porcelain text-midnight hover:bg-dawn",
    tertiary: "text-royal hover:underline px-1",
    danger: "bg-white text-danger border border-line hover:border-danger",
  }[variant];
  return (
    <button
      {...rest}
      disabled={disabled || loading}
      className={`inline-flex min-h-10 items-center justify-center gap-2 rounded-full px-5 text-sm font-semibold transition-colors disabled:cursor-not-allowed disabled:opacity-40 ${styles} ${block ? "w-full" : ""} ${className}`}
    >
      {loading && <IconLoader2 size={16} className="animate-spin" aria-hidden />}
      {children}
    </button>
  );
}

// ------------------------------------------------------------------ chips
type Tone = "neutral" | "info" | "success" | "warning" | "danger" | "draft";

export function Chip({ tone = "neutral", children, className = "" }: { tone?: Tone; children: ReactNode; className?: string }) {
  const styles = {
    neutral: "bg-porcelain text-midnight",
    info: "bg-dawn text-royal",
    success: "bg-[#E6F2EC] text-success",
    warning: "bg-asian-pear text-warning",
    danger: "bg-[#FBEAE8] text-danger",
    draft: "bg-asian-pear text-midnight",
  }[tone];
  return (
    <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-semibold ${styles} ${className}`}>
      {children}
    </span>
  );
}

const STATUS: Record<string, { tone: Tone; label: string }> = {
  requested: { tone: "info", label: "Requested" },
  accepted: { tone: "success", label: "✓ Accepted" },
  declined: { tone: "danger", label: "✗ Declined" },
  expired: { tone: "neutral", label: "Expired" },
  sent: { tone: "info", label: "Waiting for owner" },
  live: { tone: "success", label: "● Live" },
  unlisted: { tone: "neutral", label: "Unlisted" },
};

export function StatusChip({ status }: { status: string }) {
  const item = STATUS[status] ?? { tone: "neutral" as Tone, label: status };
  return <Chip tone={item.tone}>{item.label}</Chip>;
}

export function IconDisc({ icon: IconComponent, tint = "bg-dawn", size = 44 }: { icon: Icon; tint?: string; size?: number }) {
  return (
    <span className={`inline-flex shrink-0 items-center justify-center rounded-xl ${tint}`} style={{ width: size, height: size }}>
      <IconComponent size={size * 0.5} stroke={1.75} className="text-midnight" aria-hidden />
    </span>
  );
}

export function EvidenceBadge({ evidence }: { evidence: Evidence }) {
  const parts = [
    `${evidence.months_of_bills} months of bills`,
    `${evidence.reading_type} readings`,
    `${evidence.checks_passed}/${evidence.checks_total} checks ✓`,
  ];
  if (evidence.quote_attached !== undefined) parts.push(`quote ${evidence.quote_attached ? "✓" : "✗"}`);
  return (
    <p className="flex items-start gap-1.5 text-xs leading-[18px] text-muted">
      <IconCircleCheck size={14} className="mt-0.5 shrink-0 text-success" aria-hidden />
      <span>{parts.join(" · ")}</span>
    </p>
  );
}

// --------------------------------------------------------------- surfaces
export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <section className={`rounded-[20px] bg-white p-6 shadow-card ${className}`}>{children}</section>;
}

export function PageHeader({ title, subtitle, actions }: { title: string; subtitle?: ReactNode; actions?: ReactNode }) {
  return (
    <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
      <div className="min-w-0">
        <h1 className="text-2xl leading-8 font-bold">{title}</h1>
        {subtitle && <p className="mt-1 max-w-2xl text-muted">{subtitle}</p>}
      </div>
      {actions && <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div>}
    </div>
  );
}

export function Disclaimer({ children = "Estimates for preparation only. Not financial advice." }: { children?: ReactNode }) {
  return (
    <p className="flex items-start gap-2 rounded-xl bg-moon px-4 py-3 text-xs leading-[18px] text-midnight">
      <IconInfoCircle size={16} className="mt-px shrink-0" aria-hidden />
      <span>{children}</span>
    </p>
  );
}

export function Notice({ tone = "info", children }: { tone?: "info" | "warning" | "danger" | "success"; children: ReactNode }) {
  const styles = {
    info: "bg-dawn text-midnight",
    warning: "bg-asian-pear text-warning",
    danger: "bg-[#FBEAE8] text-danger",
    success: "bg-[#E6F2EC] text-success",
  }[tone];
  const IconComponent = tone === "info" ? IconInfoCircle : tone === "success" ? IconCheck : IconAlertTriangle;
  return (
    <div className={`flex items-start gap-2 rounded-xl px-4 py-3 text-sm ${styles}`} role={tone === "danger" ? "alert" : undefined}>
      <IconComponent size={18} className="mt-0.5 shrink-0" aria-hidden />
      <div>{children}</div>
    </div>
  );
}

export function LockedList({ items, title = "Hidden until the owner accepts" }: { items: string[]; title?: string }) {
  return (
    <div>
      <p className="eyebrow mb-2 text-muted">{title}</p>
      <ul className="space-y-1.5">
        {items.map((item) => (
          <li key={item} className="flex items-start gap-2 text-sm">
            <IconLock size={16} className="mt-0.5 shrink-0 text-muted" aria-hidden />
            {item}
          </li>
        ))}
      </ul>
    </div>
  );
}

export function Field({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="flex justify-between gap-4 border-b border-porcelain py-2 last:border-0">
      <dt className="text-muted">{label}</dt>
      <dd className="tnum text-right font-medium">{value}</dd>
    </div>
  );
}

export function EmptyState({ icon, text, action }: { icon: Icon; text: string; action?: ReactNode }) {
  return (
    <Card className="flex flex-col items-center gap-3 py-12 text-center">
      <IconDisc icon={icon} />
      <p className="max-w-sm text-muted">{text}</p>
      {action}
    </Card>
  );
}

export function Loading() {
  return (
    <div className="flex items-center gap-2 py-16 text-muted" role="status">
      <IconLoader2 size={18} className="animate-spin" aria-hidden /> Loading…
    </div>
  );
}

export function ErrorBox({ message }: { message: string }) {
  return <Notice tone="danger">{message}</Notice>;
}

// ------------------------------------------------------------------ modal
export function Modal({
  title,
  onClose,
  children,
  footer,
}: {
  title: string;
  onClose: () => void;
  children: ReactNode;
  footer: ReactNode;
}) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => event.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    ref.current?.querySelector<HTMLElement>("textarea, input, button")?.focus();
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);
  return (
    <div className="fade-in fixed inset-0 z-50 flex items-end justify-center bg-midnight/40 p-4 sm:items-center" onClick={onClose}>
      <div
        ref={ref}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        className="pop-in w-full max-w-lg rounded-2xl bg-white p-6 shadow-modal"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="mb-4 flex items-start justify-between gap-4">
          <h2 className="text-xl leading-7 font-semibold">{title}</h2>
          <button onClick={onClose} className="rounded-full p-1 text-muted hover:bg-porcelain" aria-label="Close">
            <IconX size={20} />
          </button>
        </div>
        <div className="space-y-4">{children}</div>
        <div className="mt-6 flex flex-wrap justify-end gap-2">{footer}</div>
      </div>
    </div>
  );
}

export function Toasts() {
  const { toasts } = useSession();
  return (
    <div className="pointer-events-none fixed right-4 bottom-4 z-[60] flex flex-col gap-2" aria-live="polite">
      {toasts.map((item) => (
        <div
          key={item.id}
          className={`pointer-events-auto flex items-center gap-2 rounded-xl px-4 py-3 text-sm font-medium text-white shadow-modal ${
            { success: "bg-success", warning: "bg-warning", danger: "bg-danger" }[item.tone]
          }`}
        >
          {item.tone === "success" ? <IconCheck size={16} /> : <IconAlertTriangle size={16} />}
          {item.text}
        </div>
      ))}
    </div>
  );
}
