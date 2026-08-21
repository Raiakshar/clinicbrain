import { createContext, useContext, useState, type ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "./api";
import type { User } from "./types";

interface AuthCtx {
  user: User | null;
  login: (phone: string, password: string) => Promise<void>;
  signup: (data: {
    clinic_name: string;
    name: string;
    phone: string;
    password: string;
  }) => Promise<void>;
  logout: () => void;
}

const Ctx = createContext<AuthCtx>(null as unknown as AuthCtx);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(() => {
    const raw = localStorage.getItem("cb_user");
    return raw ? (JSON.parse(raw) as User) : null;
  });
  const navigate = useNavigate();

  const finish = (token: string, u: User) => {
    localStorage.setItem("cb_token", token);
    localStorage.setItem("cb_user", JSON.stringify(u));
    setUser(u);
    navigate("/patients");
  };

  const login = async (phone: string, password: string) => {
    const resp = await api.post("/auth/login", { phone, password });
    finish(resp.data.token, resp.data.user);
  };

  const signup = async (data: {
    clinic_name: string;
    name: string;
    phone: string;
    password: string;
  }) => {
    const resp = await api.post("/auth/signup", data);
    finish(resp.data.token, resp.data.user);
  };

  const logout = () => {
    localStorage.removeItem("cb_token");
    localStorage.removeItem("cb_user");
    setUser(null);
    navigate("/login");
  };

  return <Ctx.Provider value={{ user, login, signup, logout }}>{children}</Ctx.Provider>;
}

export const useAuth = () => useContext(Ctx);
