"use client";

import React, { createContext, useContext, useEffect, useState, useCallback } from "react";
import { User, api, getToken, setToken, removeToken } from "./api";
import { useRouter } from "next/navigation";

interface AuthContextType {
  user: User | null;
  role: "USER" | "ADMIN" | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (credentials: { username_or_email: string; password: string }) => Promise<User>;
  register: (data: { username: string; email: string; password: string; full_name?: string }) => Promise<User>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();

  const refreshUser = useCallback(async () => {
    const token = getToken();
    if (!token) {
      setUser(null);
      setIsLoading(false);
      return;
    }
    try {
      const currentUser = await api.auth.me();
      setUser(currentUser);
    } catch (err) {
      console.warn("Failed to restore session:", err);
      removeToken();
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    let ignore = false;
    const run = async () => {
      const token = getToken();
      if (!token) {
        if (!ignore) {
          setUser(null);
          setIsLoading(false);
        }
        return;
      }
      try {
        const currentUser = await api.auth.me();
        if (!ignore) setUser(currentUser);
      } catch (err) {
        console.warn("Failed to restore session:", err);
        removeToken();
        if (!ignore) setUser(null);
      } finally {
        if (!ignore) setIsLoading(false);
      }
    };
    run();
    return () => {
      ignore = true;
    };
  }, []);

  const login = async (credentials: { username_or_email: string; password: string }) => {
    setIsLoading(true);
    try {
      const res = await api.auth.login(credentials);
      setToken(res.access_token);
      const currentUser: User = {
        id: res.user_id,
        username: res.username,
        email: res.email,
        role: res.role,
        full_name: res.full_name,
        is_active: true,
        created_at: new Date().toISOString(),
      };
      setUser(currentUser);
      return currentUser;
    } finally {
      setIsLoading(false);
    }
  };

  const register = async (data: { username: string; email: string; password: string; full_name?: string }) => {
    setIsLoading(true);
    try {
      const newUser = await api.auth.register(data);
      return newUser;
    } finally {
      setIsLoading(false);
    }
  };

  const logout = async () => {
    try {
      if (getToken()) {
        await api.auth.logout();
      }
    } catch {
      // Ignore network errors on logout
    } finally {
      removeToken();
      setUser(null);
      router.push("/login");
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        role: user?.role || null,
        isAuthenticated: !!user,
        isLoading,
        login,
        register,
        logout,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
