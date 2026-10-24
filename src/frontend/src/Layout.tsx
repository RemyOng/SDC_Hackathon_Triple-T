import { useCallback, useEffect, useRef, useState } from "react";
import { Link, NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import {
  IconBell,
  IconBriefcase,
  IconExternalLink,
  IconFileInvoice,
  IconFileText,
  IconLogout,
  IconReceipt,
  IconHistory,
  IconInbox,
  IconLayoutBoard,
  IconLayoutGrid,
  IconListSearch,
  IconMenu2,
  IconPlugConnected,
  IconSelector,
  IconSend,
  IconUserCheck,
  IconUsers,
  IconWallet,
  IconX,
  type Icon,
} from "@tabler/icons-react";
import { ROLE_HOME, type MenuItem, type Role } from "./api";
import { rm } from "./format";
import { useApi, useSession } from "./session";
import { Toasts } from "./ui";

// Orbyte menus name icons as "tabler-<name>"; map the ones GreenReady uses.
const MENU_ICONS: Record<string, Icon> = {
  "tabler-layout-board": IconLayoutBoard,
  "tabler-receipt": IconReceipt,
  "tabler-layout-grid": IconLayoutGrid,
  "tabler-inbox": IconInbox,
  "tabler-history": IconHistory,
  "tabler-wallet": IconWallet,
  "tabler-plug-connected": IconPlugConnected,
  "tabler-file-invoice": IconFileInvoice,
  "tabler-send": IconSend,
  "tabler-user-check": IconUserCheck,
  "tabler-list-search": IconListSearch,
};

const ROLE_OPTIONS: { role: Role; label: string; name: string; org: string; initials: string }[] = [
  { role: "sme_owner", label: "SME Owner", name: "Ahmad", org: "Kilang Contoh Sdn Bhd", initials: "AH" },
  { role: "sme_staff", label: "SME Staff", name: "Siti", org: "Kilang Contoh Sdn Bhd", initials: "SI" },
  { role: "investor", label: "Investor", name: "Nurul", org: "Bank Hijau Berhad", initials: "BH" },
  { role: "supplier", label: "Supplier", name: "Daniel", org: "Suria Hijau Solar", initials: "SH" },
  { role: "ops", label: "Orbyte Ops", name: "Orbyte Ops", org: "Alpha Red Pro", initials: "OR" },
];

// The rest of Orbyte: these open the real Orbyte pages (same menu URLs as Orbyte's /api/menus).
const ORBYTE_URL = "https://orbyte-xyz.alphareds.com";
const ORBYTE_MODULES: { name: string; icon: Icon; href: string }[] = [
  { name: "eClaims", icon: IconReceipt, href: `${ORBYTE_URL}/eclaims/my-claims` },
  { name: "Wallet", icon: IconWallet, href: `${ORBYTE_URL}/wallet` },
  { name: "People", icon: IconUsers, href: `${ORBYTE_URL}/resources` },
  { name: "Work", icon: IconBriefcase, href: `${ORBYTE_URL}/mytasksv2` },
  { name: "eSign", icon: IconFileText, href: "https://documenso.alphareds.com/t/ars" },
];

const TODAY = new Date().toLocaleDateString("en-GB", { weekday: "long", day: "numeric", month: "long", year: "numeric" });

type ActionItems = { data: { counts: { pendingApproval: number; pendingReview: number }; items: { id: string; title: string; webPath: string }[] } };

function greeting() {
  const hour = new Date().getHours();
  return hour < 12 ? "Good morning" : hour < 18 ? "Good afternoon" : "Good evening";
}

export default function Layout() {
  const { role, setRole } = useSession();
  const menus = useApi<{ data: MenuItem[] }>("/menus");
  const isSme = role === "sme_owner" || role === "sme_staff";
  const wallet = useApi<{ data: { balance: number; lowBalance: boolean } }>(isSme ? "/wallet" : null);
  const actions = useApi<ActionItems>("/action-items");
  const navigate = useNavigate();
  const location = useLocation();
  const [drawer, setDrawer] = useState(false);
  const current = ROLE_OPTIONS.find((option) => option.role === role)!;

  useEffect(() => setDrawer(false), [location.pathname]);

  const links = (menus.data?.data ?? []).filter((item) => item.menuType === "Menu");
  const counts = actions.data?.data.counts;
  const pending = counts ? counts.pendingApproval + counts.pendingReview : 0;

  const switchRole = (next: Role) => {
    setRole(next);
    navigate(ROLE_HOME[next]);
  };

  const sidebar = (
    <Sidebar links={links} pending={isSme ? pending : 0} current={current} onSwitch={switchRole} onClose={() => setDrawer(false)} />
  );

  return (
    <div className="min-h-screen bg-[linear-gradient(135deg,#BAD6EB_0%,#D0E3FF_45%,#BAD6EB_100%)] lg:p-4">
      <div className="mx-auto flex min-h-screen max-w-[1480px] bg-white lg:min-h-[calc(100vh-2rem)] lg:overflow-hidden lg:rounded-[28px] lg:shadow-modal">
        {/* Desktop sidebar */}
        <aside className="hidden w-64 shrink-0 lg:flex">{sidebar}</aside>

        {/* Mobile drawer */}
        {drawer && (
          <div className="fixed inset-0 z-50 flex lg:hidden">
            <div className="fade-in absolute inset-0 bg-midnight/40" onClick={() => setDrawer(false)} />
            <aside className="drawer-in relative flex w-72 max-w-[85vw] bg-white shadow-modal">{sidebar}</aside>
          </div>
        )}

        <div className="flex min-w-0 flex-1 flex-col bg-canvas lg:rounded-l-[28px] lg:border-l lg:border-[#E4EAF3]">
          {/* Top bar */}
          <header className="flex items-center gap-3 px-4 pt-5 pb-2 sm:px-8 sm:pt-7">
            <button
              onClick={() => setDrawer(true)}
              className="flex h-10 w-10 items-center justify-center rounded-xl bg-white shadow-card lg:hidden"
              aria-label="Open menu"
            >
              <IconMenu2 size={20} />
            </button>
            <div className="min-w-0 flex-1">
              <p className="truncate text-lg leading-7 font-semibold">
                {greeting()}, {current.name}
              </p>
              <p className="truncate text-xs text-muted">{TODAY}</p>
            </div>
            {isSme && wallet.data && (
              <Link
                to={role === "sme_owner" ? "/sme/wallet" : location.pathname}
                className={`tnum hidden h-10 items-center gap-2 rounded-xl px-3.5 text-sm font-semibold shadow-card sm:flex ${
                  wallet.data.data.lowBalance ? "bg-asian-pear text-warning" : "bg-white text-midnight"
                }`}
              >
                <IconWallet size={18} stroke={1.75} className="text-royal" aria-hidden />
                Credit {rm(wallet.data.data.balance, 2)}
              </Link>
            )}
            <Notifications items={actions.data?.data.items ?? []} count={pending} />
            <span className="hidden h-10 items-center rounded-xl bg-asian-pear px-3 text-xs font-semibold md:flex">Demo mode</span>
          </header>

          <main className="flex-1 px-4 pt-6 pb-10 sm:px-8">
            <div key={location.pathname} className="page-enter">
              <Outlet />
            </div>
          </main>

          <footer className="px-4 pb-6 text-xs leading-[18px] text-muted sm:px-8">
            Demo — synthetic data. All companies, banks and suppliers are fictional. Loans and upgrade payments are agreed directly with
            the bank or supplier and never pass through Orbyte.
          </footer>
        </div>
      </div>
      <Toasts />
    </div>
  );
}

function Sidebar({
  links,
  pending,
  current,
  onSwitch,
  onClose,
}: {
  links: MenuItem[];
  pending: number;
  current: (typeof ROLE_OPTIONS)[number];
  onSwitch: (role: Role) => void;
  onClose: () => void;
}) {
  return (
    <div className="flex w-full flex-col px-5 py-7">
      <div className="flex items-center justify-between px-2">
        <Link to={ROLE_HOME[current.role]} className="flex items-center gap-2.5" aria-label="GreenReady home">
          <img src={`${import.meta.env.BASE_URL}greenready-mark.png`} alt="" className="h-9 w-9" />
          <span className="leading-tight">
            <span className="block text-[17px] font-bold">GreenReady</span>
            <span className="block text-[11px] text-muted">by Orbyte</span>
          </span>
        </Link>
        <button onClick={onClose} className="rounded-lg p-1 text-muted hover:bg-porcelain lg:hidden" aria-label="Close menu">
          <IconX size={20} />
        </button>
      </div>

      <p className="eyebrow mt-10 mb-2 px-3 text-muted">GreenReady</p>
      <nav aria-label="GreenReady" className="space-y-1">
        {links.map((item) => {
          const IconComponent = MENU_ICONS[item.icon] ?? IconLayoutGrid;
          const badge = item.url === "/sme/requests" && pending > 0 ? pending : null;
          return (
            <NavLink
              key={item.id}
              to={item.url}
              className={({ isActive }) =>
                `flex min-h-11 items-center gap-3 rounded-xl px-3 text-sm font-medium transition-colors ${
                  isActive ? "bg-dawn font-semibold text-midnight" : "text-muted hover:bg-porcelain hover:text-midnight"
                }`
              }
            >
              {({ isActive }) => (
                <>
                  <IconComponent size={20} stroke={1.75} className={isActive ? "text-royal" : ""} aria-hidden />
                  <span className="flex-1">{item.menuName}</span>
                  {badge && <span className="tnum rounded-full bg-royal px-2 text-[11px] leading-5 font-bold text-white">{badge}</span>}
                </>
              )}
            </NavLink>
          );
        })}
      </nav>

      <p className="eyebrow mt-8 mb-2 px-3 text-muted">Orbyte</p>
      <ul className="space-y-1">
        {ORBYTE_MODULES.map(({ name, icon: IconComponent, href }) => (
          <li key={name}>
            <a
              href={href}
              target="_blank"
              rel="noopener noreferrer"
              className="group flex min-h-11 items-center gap-3 rounded-xl px-3 text-sm font-medium text-muted transition-colors hover:bg-porcelain hover:text-midnight"
            >
              <IconComponent size={20} stroke={1.75} aria-hidden />
              <span className="flex-1">{name}</span>
              <IconExternalLink size={14} className="opacity-0 transition-opacity group-hover:opacity-100" aria-label="opens Orbyte" />
            </a>
          </li>
        ))}
      </ul>

      <div className="mt-auto pt-8">
        <RoleSwitcher current={current} onSwitch={onSwitch} />
      </div>
    </div>
  );
}

function useOutside(onOutside: () => void) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const handler = (event: MouseEvent) => ref.current && !ref.current.contains(event.target as Node) && onOutside();
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [onOutside]);
  return ref;
}

function RoleSwitcher({ current, onSwitch }: { current: (typeof ROLE_OPTIONS)[number]; onSwitch: (role: Role) => void }) {
  const { signOut } = useSession();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const close = useCallback(() => setOpen(false), []);
  const ref = useOutside(close);
  return (
    <div ref={ref} className="relative">
      {open && (
        <div className="pop-in absolute right-0 bottom-full left-0 z-40 mb-2 rounded-2xl bg-white p-2 shadow-modal">
          <p className="eyebrow px-3 py-2 text-muted">Demo mode · switch role</p>
          {ROLE_OPTIONS.map((option) => (
            <button
              key={option.role}
              onClick={() => {
                setOpen(false);
                onSwitch(option.role);
              }}
              className={`flex w-full items-center gap-3 rounded-xl px-3 py-2 text-left text-sm hover:bg-porcelain ${
                option.role === current.role ? "bg-dawn" : ""
              }`}
            >
              <Avatar initials={option.initials} size={32} />
              <span className="min-w-0">
                <span className="block font-semibold">{option.label}</span>
                <span className="block truncate text-xs text-muted">{option.org}</span>
              </span>
            </button>
          ))}
          <div className="my-1 h-px bg-porcelain" />
          <button
            onClick={() => {
              setOpen(false);
              signOut();
              navigate("/login");
            }}
            className="flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left text-sm font-medium text-danger hover:bg-porcelain"
          >
            <IconLogout size={18} /> Sign out
          </button>
        </div>
      )}
      <button
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
        className="flex w-full items-center gap-3 rounded-2xl bg-porcelain p-3 text-left hover:bg-dawn"
      >
        <Avatar initials={current.initials} size={40} />
        <span className="min-w-0 flex-1">
          <span className="block truncate text-sm font-semibold">{current.name}</span>
          <span className="block truncate text-xs text-muted">
            {current.label}
          </span>
        </span>
        <IconSelector size={18} className="shrink-0 text-muted" aria-hidden />
      </button>
    </div>
  );
}

function Avatar({ initials, size }: { initials: string; size: number }) {
  return (
    <span
      className="flex shrink-0 items-center justify-center rounded-full bg-midnight text-[12px] font-bold text-white"
      style={{ width: size, height: size }}
      aria-hidden
    >
      {initials}
    </span>
  );
}

function Notifications({ items, count }: { items: { id: string; title: string; webPath: string }[]; count: number }) {
  const [open, setOpen] = useState(false);
  const close = useCallback(() => setOpen(false), []);
  const ref = useOutside(close);
  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen((value) => !value)}
        className="relative flex h-10 w-10 items-center justify-center rounded-xl bg-white shadow-card hover:bg-dawn"
        aria-label={`Notifications${count ? `, ${count} waiting` : ""}`}
        aria-expanded={open}
      >
        <IconBell size={20} stroke={1.75} />
        {count > 0 && (
          <span className="absolute -top-1 -right-1 flex h-5 min-w-5 items-center justify-center rounded-full bg-royal px-1 text-[11px] font-bold text-white">
            {count}
          </span>
        )}
      </button>
      {open && (
        <div className="pop-in absolute right-0 z-40 mt-2 w-80 max-w-[calc(100vw-2rem)] rounded-2xl bg-white p-2 shadow-modal">
          <p className="eyebrow px-3 py-2 text-muted">Orbyte approvals</p>
          {items.length === 0 && <p className="px-3 pb-3 text-sm text-muted">Nothing waiting for you.</p>}
          {items.map((item) => (
            <Link key={item.id} to={item.webPath} onClick={close} className="block rounded-xl px-3 py-2 text-sm hover:bg-porcelain">
              {item.title}
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
