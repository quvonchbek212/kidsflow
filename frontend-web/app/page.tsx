"use client";

import Link from "next/link";
import { useState, type ReactNode } from "react";

import { Carousel } from "@/components/Carousel";
import { Reveal } from "@/components/Reveal";
import { CONTENT, type Lang } from "@/lib/landing-content";
import { SHOWCASE } from "@/lib/showcase-content";

const LANGS: Lang[] = ["ru", "en", "uz"];

export default function LandingPage(): ReactNode {
  const [lang, setLang] = useState<Lang>("uz");
  const c = CONTENT[lang];
  const showcase = SHOWCASE[lang];

  return (
    <div className="landing">
      <header className="lp-header">
        <div className="lp-logo">
          <div className="mark">KF</div>
          <div>
            <div className="name">KIDSFLOW</div>
            <div className="sub">Bog&apos;cha platformasi</div>
          </div>
        </div>
        <nav className="lp-nav">
          <a href="#features">{c.nav.features}</a>
          <a href="#roles">{showcase.title}</a>
          <a href="#advantages">{c.nav.advantages}</a>
          <a href="#how">{c.nav.how}</a>
        </nav>
        <span className="spacer" />
        <div className="lang-switch">
          {LANGS.map((l) => (
            <button
              key={l}
              className={l === lang ? "active" : ""}
              onClick={() => setLang(l)}
            >
              {l.toUpperCase()}
            </button>
          ))}
        </div>
        <Link href="/login" className="btn">
          {c.nav.login}
        </Link>
      </header>

      {/* Hero */}
      <section className="lp-container hero">
        <div className="hero-enter">
          <span className="pill">✨ {c.hero.badge}</span>
          <h1>{c.hero.title}</h1>
          <p className="lead">{c.hero.subtitle}</p>
          <div className="hero-actions">
            <Link href="/login" className="btn btn-lg">
              {c.hero.ctaPrimary}
            </Link>
            <a href="#features" className="btn btn-lg btn-ghost">
              {c.hero.ctaSecondary} →
            </a>
          </div>
        </div>
        <div className="mockup-enter">
          <Mockup content={c.mockup} />
        </div>
      </section>

      {/* Features */}
      <section id="features" className="lp-container section">
        <Reveal>
          <div className="section-head">
            <h2>{c.featuresTitle}</h2>
            <p>{c.featuresSubtitle}</p>
          </div>
        </Reveal>
        <div className="feature-grid">
          {c.features.map((f, i) => (
            <Reveal key={f.title} delay={i * 70}>
              <div className="feature-card">
                <div className="ic">{f.icon}</div>
                <h3>{f.title}</h3>
                <p>{f.desc}</p>
              </div>
            </Reveal>
          ))}
        </div>
      </section>

      {/* Roles carousel */}
      <section id="roles" className="lp-container section">
        <Reveal>
          <div className="section-head">
            <h2>{showcase.title}</h2>
            <p>{showcase.subtitle}</p>
          </div>
        </Reveal>
        <Reveal delay={80}>
          <Carousel slides={showcase.slides} />
        </Reveal>
      </section>

      {/* Advantages */}
      <section id="advantages" className="lp-container section">
        <Reveal>
          <div className="section-head">
            <h2>{c.advantagesTitle}</h2>
            <p>{c.advantagesSubtitle}</p>
          </div>
        </Reveal>
        <div className="feature-grid">
          {c.advantages.map((a, i) => (
            <Reveal key={a.title} delay={i * 70}>
              <div className="feature-card">
                <div className="ic">{a.icon}</div>
                <h3>{a.title}</h3>
                <p>{a.desc}</p>
              </div>
            </Reveal>
          ))}
        </div>
      </section>

      {/* How it works */}
      <section id="how" className="lp-container section">
        <Reveal>
          <div className="section-head">
            <h2>{c.howTitle}</h2>
            <p>{c.howSubtitle}</p>
          </div>
        </Reveal>
        <div className="steps">
          {c.steps.map((s, i) => (
            <Reveal key={s.title} delay={i * 90}>
              <div className="step">
                <div className="num">{i + 1}</div>
                <h3>{s.title}</h3>
                <p>{s.desc}</p>
              </div>
            </Reveal>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section className="lp-container">
        <Reveal>
          <div className="cta-band">
            <h2>{c.ctaTitle}</h2>
            <p>{c.ctaSubtitle}</p>
            <Link href="/login" className="btn btn-lg btn-white">
              {c.ctaButton}
            </Link>
          </div>
        </Reveal>
      </section>

      <footer className="lp-footer">
        © {new Date().getFullYear()} {c.footer}
      </footer>
    </div>
  );
}

function Mockup({
  content,
}: {
  content: {
    modules: string;
    realtime: string;
    realtimeSub: string;
    selfService: string;
    selfServiceSub: string;
  };
}): ReactNode {
  return (
    <div className="mockup">
      <div className="browser">
        <div className="chrome">
          <span className="dot" style={{ background: "#ef4444" }} />
          <span className="dot" style={{ background: "#f59e0b" }} />
          <span className="dot" style={{ background: "#22c55e" }} />
          <span className="url">app.kidsflow.uz</span>
        </div>
        <div className="screen">
          <div className="mini-tiles">
            <div className="mini-tile">
              <span />
              <span />
            </div>
            <div className="mini-tile">
              <span />
              <span />
            </div>
            <div className="mini-tile">
              <span />
              <span />
            </div>
          </div>
          <div className="mini-charts">
            <div className="bars">
              {[40, 65, 50, 80, 60, 90, 72].map((h, i) => (
                <i key={i} style={{ height: `${h}%` }} />
              ))}
            </div>
            <div className="donut">
              <div className="ring" />
            </div>
          </div>
        </div>
      </div>

      <div className="float tl">
        <div className="ic">📊</div>
        <div>{content.modules}</div>
      </div>
      <div className="float bl">
        <div className="ic">🔔</div>
        <div>
          {content.realtime}
          <small>{content.realtimeSub}</small>
        </div>
      </div>
      <div className="float br">
        <div className="ic">👨‍👩‍👧</div>
        <div>
          {content.selfService}
          <small>{content.selfServiceSub}</small>
        </div>
      </div>
    </div>
  );
}
