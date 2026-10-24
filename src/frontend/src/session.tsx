import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { api, storeRole, storeSignedIn, storedRole, storedSignedIn, type Role } from "./api";

type Toast = { id: number; tone: "success" | "warning" | "danger"; text: string };

type Session = {
  role: Role;
  setRole: (role: Role) => void;
  signedIn: boolean;
  signIn: (role: Role) => void;
  signOut: () => void;
  /** Bumped after any change so shell counters (wallet, requests) refresh. */
  version: number;
  refresh: () => void;
  call: <T>(path: string, init?: { method?: string; body?: unknown }) => Promise<T>;
  toasts: Toast[];
  toast: (text: string, tone?: Toast["tone"]) => void;
};

const SessionContext = createContext<Session | null>(null);

export function SessionProvider({ children }: { children: ReactNode }) {
  const [role, setRoleState] = useState<Role>(storedRole);
  const [signedIn, setSignedIn] = useState<boolean>(storedSignedIn);
  const [version, setVersion] = useState(0);
  const [toasts, setToasts] = useState<Toast[]>([]);

  const setRole = useCallback((next: Role) => {
    storeRole(next);
    setRoleState(next);
  }, []);
  const signIn = useCallback(
    (next: Role) => {
      setRole(next);
      storeSignedIn(true);
      setSignedIn(true);
    },
    [setRole],
  );
  const signOut = useCallback(() => {
    storeSignedIn(false);
    setSignedIn(false);
  }, []);
  useEffect(() => {
    if (signedIn) storeSignedIn(true);
  }, [signedIn]);
  const refresh = useCallback(() => setVersion((value) => value + 1), []);
  const call = useCallback(
    <T,>(path: string, init?: { method?: string; body?: unknown }) => api<T>(role, path, init),
    [role],
  );
  const toast = useCallback((text: string, tone: Toast["tone"] = "success") => {
    const id = Date.now() + Math.random();
    setToasts((items) => [...items, { id, tone, text }]);
    window.setTimeout(() => setToasts((items) => items.filter((item) => item.id !== id)), 4000);
  }, []);

  return (
    <SessionContext.Provider value={{ role, setRole, signedIn, signIn, signOut, version, refresh, call, toasts, toast }}>
      {children}
    </SessionContext.Provider>
  );
}

export function useSession(): Session {
  const session = useContext(SessionContext);
  if (!session) throw new Error("useSession outside SessionProvider");
  return session;
}

/** Fetch `path` for the current role; reloads when the role or session version changes. */
export function useApi<T>(path: string | null) {
  const { call, version } = useSession();
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    if (!path) return;
    let live = true;
    setLoading(true);
    call<T>(path)
      .then((result) => {
        if (!live) return;
        setData(result);
        setError(null);
      })
      .catch((err: Error) => live && setError(err.message))
      .finally(() => live && setLoading(false));
    return () => {
      live = false;
    };
  }, [path, call, version, tick]);

  const reload = useCallback(() => setTick((value) => value + 1), []);
  return { data, error, loading, reload };
}
