import { ReactNode } from "react";
import { Link, useLocation } from "react-router-dom";
import { useAuth } from "../auth";

const NAV = [
  { to: "/patients", label: "Patients" },
  { to: "/review", label: "Review" },
  { to: "/queue", label: "Queue" },
];

export function Logo({ size = "md" }: { size?: "md" | "lg" }) {
  const dim = size === "lg" ? "h-11 w-11 text-xl" : "h-8 w-8 text-sm";
  return (
    <span className="flex items-center gap-2.5">
      <span
        className={`${dim} grid place-items-center rounded-xl bg-gradient-to-br from-teal-400 to-blue-600 font-black text-slate-950 shadow-glow animate-pulseGlow`}
      >
        C
      </span>
      <span className={`font-extrabold tracking-tight ${size === "lg" ? "text-2xl" : "text-lg"}`}>
        Clinic<span className="text-gradient">Brain</span>
      </span>
    </span>
  );
}

export default function AppShell({ children }: { children: ReactNode }) {
  const { user, logout } = useAuth();
  const { pathname } = useLocation();

  return (
    <div className="min-h-screen relative overflow-x-clip">
      <div className="pointer-events-none fixed inset-0 -z-10">
        <div className="absolute -top-40 -left-32 h-[480px] w-[480px] rounded-full bg-teal-500/15 blur-[130px] animate-orb" />
        <div className="absolute top-1/3 -right-40 h-[520px] w-[520px] rounded-full bg-violet-600/15 blur-[140px] animate-orb [animation-delay:-6s]" />
        <div className="absolute bottom-0 left-1/4 h-[380px] w-[380px] rounded-full bg-blue-600/10 blur-[120px] animate-orb [animation-delay:-12s]" />
        <div className="absolute inset-0 bg-grid [mask-image:radial-gradient(ellipse_70%_60%_at_50%_0%,black,transparent)]" />
      </div>

      <header className="sticky top-0 z-40 border-b border-white/10 bg-slate-950/60 backdrop-blur-xl">
        <div className="max-w-6xl mx-auto px-4 h-16 flex items-center justify-between">
          <Link to="/patients">
            <Logo />
          </Link>
          <nav className="flex items-center gap-1 p-1 rounded-full border border-white/10 bg-white/[0.04]">
            {NAV.map((n) => {
              const active = pathname.startsWith(n.to);
              return (
                <Link
                  key={n.to}
                  to={n.to}
                  className={`px-4 py-1.5 rounded-full text-sm font-medium transition duration-300 ${
                    active
                      ? "bg-gradient-to-r from-teal-400/90 to-blue-500/90 text-slate-950 shadow-glow"
                      : "text-slate-300 hover:text-white hover:bg-white/[0.06]"
                  }`}
                >
                  {n.label}
                </Link>
              );
            })}
          </nav>
          <div className="flex items-center gap-3">
            <div className="hidden sm:flex items-center gap-2.5 pl-3 border-l border-white/10">
              <span className="grid place-items-center h-8 w-8 rounded-full bg-gradient-to-br from-teal-400/30 to-blue-500/30 border border-teal-300/30 text-xs font-bold text-teal-200">
                {user?.name?.slice(0, 2).toUpperCase() ?? "DR"}
              </span>
              <span className="text-sm text-slate-300">{user?.name}</span>
            </div>
            <button
              onClick={logout}
              className="text-xs font-medium text-slate-400 hover:text-red-400 transition"
            >
              Logout
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 py-8">{children}</main>

      <footer className="border-t border-white/[0.06] py-6 text-center text-xs text-slate-600">
        ClinicBrain — the AI memory of your clinic
      </footer>
    </div>
  );
}
