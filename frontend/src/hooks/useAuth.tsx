import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import { api, tokenStore } from '../services/api';
import type { User } from '../types';

interface AuthValue {
  user: User | null;
  ready: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  signUp: (email: string, fullName: string, password: string) => Promise<void>;
  /** Opens an empty lab account under a chosen name and signs in as it. Returns the
   *  generated credentials so the caller can show them once. */
  openLabAccount: (body: {
    full_name: string; upi_handle?: string; opening_balance: number; as_admin: boolean;
  }) => Promise<{ email: string; password: string }>;
  signOut: () => void;
  refresh: () => Promise<void>;
  setUser: (user: User) => void;
}

const AuthContext = createContext<AuthValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const token = tokenStore.get();
    if (!token) {
      setReady(true);
      return;
    }
    api
      .me()
      .then(setUser)
      .catch(() => tokenStore.clear())
      .finally(() => setReady(true));
  }, []);

  const signIn = useCallback(async (email: string, password: string) => {
    const result = await api.login(email, password);
    tokenStore.set(result.access_token);
    setUser(result.user);
  }, []);

  const signUp = useCallback(async (email: string, fullName: string, password: string) => {
    const result = await api.register(email, fullName, password);
    tokenStore.set(result.access_token);
    setUser(result.user);
  }, []);

  const openLabAccount = useCallback(
    async (body: { full_name: string; upi_handle?: string; opening_balance: number; as_admin: boolean }) => {
      const result = await api.createLabAccount(body);
      tokenStore.set(result.access_token);
      setUser(result.user);
      return { email: result.user.email, password: result.password };
    },
    [],
  );

  const signOut = useCallback(() => {
    tokenStore.clear();
    setUser(null);
  }, []);

  const refresh = useCallback(async () => {
    setUser(await api.me());
  }, []);

  const value = useMemo(
    () => ({ user, ready, signIn, signUp, openLabAccount, signOut, refresh, setUser }),
    [user, ready, signIn, signUp, openLabAccount, signOut, refresh],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used inside AuthProvider');
  return context;
}
