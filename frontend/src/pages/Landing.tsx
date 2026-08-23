import { Link } from "react-router-dom";
import { Logo } from "../components/AppShell";

const HERO_IMG =
  "https://images.unsplash.com/photo-1631217868264-e5b90bb7e133?q=80&w=1400&auto=format&fit=crop";
const IMG_DOCTOR =
  "https://images.unsplash.com/photo-1612349317150-e413f6a5b16d?q=80&w=800&auto=format&fit=crop";
const IMG_LAB =
  "https://images.unsplash.com/photo-1579154204601-01588f351e67?q=80&w=800&auto=format&fit=crop";
const IMG_CORRIDOR =
  "https://images.unsplash.com/photo-1519494026892-80bbd2d6fd0d?q=80&w=800&auto=format&fit=crop";
const IMG_PHARMA =
  "https://images.unsplash.com/photo-1471864190281-a93a3070b6de?q=80&w=800&auto=format&fit=crop";
const IMG_TEAM =
  "https://images.unsplash.com/photo-1551076805-e1869033e561?q=80&w=800&auto=format&fit=crop";
const IMG_RECORDS =
  "https://images.unsplash.com/photo-1576091160399-112ba8d25d1f?q=80&w=800&auto=format&fit=crop";

const FEATURES = [
  {
    title: "Digitize any record",
    body: "Snap a photo of any paper — prescriptions, letters, discharge summaries. GPT reads it into a clean, searchable draft your team confirms in one tap.",
    img: IMG_RECORDS,
    tag: "OCR + LLM",
  },
  {
    title: "Lab reports that think",
    body: "Photos of lab panels become structured rows with flags for every out-of-range value, then beautiful trend charts per test over time.",
    img: IMG_LAB,
    tag: "Trends",
  },
  {
    title: "WhatsApp follow-ups",
    body: "Token confirmations, your-turn alerts and follow-up reminders sent automatically. Retries handled, failures surfaced on a staff dashboard.",
    img: IMG_TEAM,
    tag: "Cloud API",
  },
  {
    title: "Queue without the crowd",
    body: "Patients check in and get a token number instantly. One tap calls the next patient — nobody hovers at the door.",
    img: IMG_CORRIDOR,
    tag: "Live queue",
  },
  {
    title: "Rx safety net",
    body: "Allergy hard-stops, interaction warnings against existing meds, max-dose checks — inline while you prescribe.",
    img: IMG_PHARMA,
    tag: "Guardrails",
  },
  {
    title: "Built for trust",
    body: "AI only drafts — humans confirm. Every action lands in an append-only audit log. Consent-gated messaging by design (DPDP).",
    img: IMG_DOCTOR,
    tag: "Audit trail",
  },
];

const STEPS = [
  {
    n: "01",
    title: "Capture",
    body: "Upload or snap documents at the desk. The pipeline extracts, structures and drafts everything in seconds.",
  },
  {
    n: "02",
    title: "Confirm",
    body: "Your staff reviews AI drafts in one focused queue. Nothing enters the record without a human yes.",
  },
  {
    n: "03",
    title: "Follow up",
    body: "Labs trend over time, the queue moves itself, WhatsApp keeps patients coming back on schedule.",
  },
];

export default function Landing() {
  return (
    <div className="min-h-screen relative overflow-x-clip">
      <div className="pointer-events-none absolute inset-0 -z-10">
        <div className="absolute -top-48 left-1/2 -translate-x-1/2 h-[600px] w-[900px] rounded-full bg-teal-500/10 blur-[150px]" />
        <div className="absolute top-[40%] -left-40 h-[480px] w-[480px] rounded-full bg-violet-600/10 blur-[130px] animate-orb" />
        <div className="absolute bottom-0 -right-32 h-[420px] w-[420px] rounded-full bg-blue-600/15 blur-[130px] animate-orb [animation-delay:-8s]" />
        <div className="absolute inset-0 bg-grid [mask-image:radial-gradient(ellipse_75%_55%_at_50%_0%,black,transparent)]" />
      </div>

      <header className="sticky top-0 z-50 border-b border-white/[0.06] bg-slate-950/50 backdrop-blur-xl">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
          <Logo />
          <nav className="hidden md:flex items-center gap-8 text-sm text-slate-300">
            <a href="#features" className="hover:text-white transition">Features</a>
            <a href="#how" className="hover:text-white transition">How it works</a>
          </nav>
          <div className="flex items-center gap-3">
            <Link to="/login" className="text-sm font-medium text-slate-300 hover:text-white transition">
              Log in
            </Link>
            <Link to="/signup" className="cb-btn !py-2">
              Get started
            </Link>
          </div>
        </div>
      </header>

      <section className="max-w-7xl mx-auto px-4 sm:px-6 pt-16 pb-20 lg:pt-24 grid lg:grid-cols-2 gap-14 items-center">
        <div className="perspective-1200">
          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-black leading-[1.05] tracking-tight">
            The <span className="text-gradient">AI memory</span>
            <br />
            of your clinic
          </h1>
          <p className="mt-6 text-lg text-slate-400 max-w-xl leading-relaxed">
            ClinicBrain turns paper records, lab reports and missed follow-ups into a living digital
            brain — built for small clinics in India. Snap it, confirm it, never lose it.
          </p>
          <div className="mt-8 flex flex-wrap items-center gap-4">
            <Link to="/signup" className="cb-btn !px-7 !py-3 text-base">
              Start free →
            </Link>
            <Link to="/login" className="cb-btn-ghost !px-6 !py-3 text-base">
              Try the demo clinic
            </Link>
          </div>
          <div className="mt-10 flex flex-wrap gap-2.5">
            {["21+ lab tests tracked", "×3 auto-retry delivery", "Zero lost records", "DPDP consent"].map(
              (chip) => (
                <span key={chip} className="cb-chip">
                  <span className="h-1.5 w-1.5 rounded-full bg-teal-300 shadow-glow" />
                  {chip}
                </span>
              )
            )}
          </div>
        </div>

        <div className="relative perspective-1200">
          <div className="preserve-3d relative tilt-hero">
            <img
              src={HERO_IMG}
              alt="Doctor checking patient records"
              className="rounded-3xl border border-white/10 shadow-glass w-full object-cover aspect-[4/3]"
              loading="eager"
            />
            <img
              src={IMG_LAB}
              alt="Lab analysis"
              className="absolute -bottom-8 -left-6 sm:-left-12 w-36 sm:w-44 rounded-2xl border border-white/15 shadow-glass animate-floaty"
              loading="lazy"
            />
            <div className="absolute -top-5 -right-3 sm:-right-8 cb-card px-4 py-3 animate-floaty [animation-delay:-2s]">
              <p className="text-[11px] uppercase tracking-wider text-slate-400">HbA1c trend</p>
              <p className="text-xl font-extrabold text-teal-300">8.2 ↓ 6.4</p>
            </div>
            <div className="absolute top-1/2 -right-4 sm:-right-10 cb-card px-4 py-2.5 animate-floaty [animation-delay:-4s]">
              <p className="text-sm font-semibold text-emerald-300">✓ Token #4 called</p>
            </div>
          </div>
        </div>
      </section>

      <section id="features" className="max-w-7xl mx-auto px-4 sm:px-6 py-20">
        <div className="max-w-2xl mb-12">
          <p className="cb-label text-teal-300">Everything in one place</p>
          <h2 className="mt-3 text-3xl sm:text-4xl font-extrabold tracking-tight">
            Six superpowers for small clinics
          </h2>
        </div>
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {FEATURES.map((f) => (
            <article
              key={f.title}
              className="cb-card cb-card-hover overflow-hidden group perspective-1200"
            >
              <div className="relative h-44 overflow-hidden">
                <img
                  src={f.img}
                  alt={f.title}
                  loading="lazy"
                  className="w-full h-full object-cover opacity-70 group-hover:opacity-100 group-hover:scale-105 transition duration-700"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-slate-950 via-slate-950/30 to-transparent" />
                <span className="absolute top-3 left-3 cb-chip !bg-slate-950/60">{f.tag}</span>
              </div>
              <div className="p-5">
                <h3 className="font-bold text-lg">{f.title}</h3>
                <p className="mt-2 text-sm text-slate-400 leading-relaxed">{f.body}</p>
              </div>
            </article>
          ))}
        </div>
      </section>

      <section id="how" className="max-w-7xl mx-auto px-4 sm:px-6 py-20">
        <div className="text-center max-w-2xl mx-auto mb-16">
          <p className="cb-label text-violet-300">How it works</p>
          <h2 className="mt-3 text-3xl sm:text-4xl font-extrabold tracking-tight">
            From paper to follow-up in three steps
          </h2>
        </div>
        <div className="relative grid md:grid-cols-3 gap-6">
          <div className="hidden md:block absolute top-10 left-[16%] right-[16%] h-px bg-gradient-to-r from-teal-400/60 via-blue-500/60 to-violet-500/60" />
          {STEPS.map((s) => (
            <div key={s.n} className="relative text-center px-4">
              <span className="inline-grid place-items-center h-20 w-20 rounded-full cb-card font-black text-2xl text-gradient bg-slate-950">
                {s.n}
              </span>
              <h3 className="mt-5 text-xl font-bold">{s.title}</h3>
              <p className="mt-2 text-sm text-slate-400 leading-relaxed max-w-xs mx-auto">{s.body}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="max-w-5xl mx-auto px-4 sm:px-6 py-16">
        <div className="cb-card relative overflow-hidden p-10 sm:p-14 text-center">
          <img
            src={IMG_CORRIDOR}
            alt=""
            aria-hidden
            className="absolute inset-0 w-full h-full object-cover opacity-15"
            loading="lazy"
          />
          <div className="absolute inset-0 bg-gradient-to-r from-slate-950/80 via-slate-950/60 to-slate-950/90" />
          <div className="relative">
            <h2 className="text-3xl sm:text-4xl font-extrabold tracking-tight">
              Your clinic already has the data.
              <br />
              <span className="text-gradient">Start remembering it.</span>
            </h2>
            <div className="mt-8 flex justify-center gap-4 flex-wrap">
              <Link to="/signup" className="cb-btn !px-8 !py-3 text-base">
                Create your clinic
              </Link>
              <Link to="/login" className="cb-btn-ghost !px-7 !py-3 text-base">
                Log in
              </Link>
            </div>
          </div>
        </div>
      </section>

      <footer className="border-t border-white/[0.06] mt-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-10 flex flex-col sm:flex-row items-center justify-between gap-4 text-sm text-slate-500">
          <Logo />
          <p>© 2026 ClinicBrain · Built for Indian small clinics</p>
        </div>
      </footer>
    </div>
  );
}
