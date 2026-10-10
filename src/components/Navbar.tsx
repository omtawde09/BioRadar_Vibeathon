import React, { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import {
  Home,
  Upload,
  Activity,
  FileText,
  BarChart2,
  Bell,
  Settings,
  Dna,
  Globe,
  Menu,
  X,
  ArrowUpRight
} from 'lucide-react';
import { useTranslation, Language } from '../i18n/useTranslation';

interface NavbarProps {
  onNavigateView?: (viewId: string) => void;
  activeView?: string;
}

export const Navbar: React.FC<NavbarProps> = ({ onNavigateView, activeView = 'home' }) => {
  const { currentLang, setLanguage, t } = useTranslation();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  // Navbar is transparent while the hero section fills the viewport, then turns
  // solid once the user scrolls past it (so the light content below stays
  // readable behind the bar). The mobile menu always forces the solid look.
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const navHeight = 76;

    const compute = () => {
      const hero = document.getElementById('hero');
      // Switch a touch before the hero fully leaves, so the bar is opaque by
      // the time cream-coloured content reaches it.
      const threshold = hero ? hero.offsetHeight - navHeight : 120;
      const lenis = (window as any).bioradarLenis;
      const y =
        lenis && typeof lenis.scroll === 'number'
          ? lenis.scroll
          : window.scrollY || document.documentElement.scrollTop || 0;
      // React bails out when the boolean is unchanged, so calling this on every
      // scroll frame is cheap.
      setScrolled(y > threshold);
    };

    compute();
    // Native scroll covers plain scrolling; Lenis (smooth scroll) suppresses the
    // native event and emits its own instead, so subscribe to that too.
    window.addEventListener('scroll', compute, { passive: true });
    window.addEventListener('resize', compute);

    // Lenis is created by the parent HomePage effect, which runs after this
    // child mounts — so poll briefly until it is available, then subscribe.
    let lenis: any = null;
    const attach = () => {
      const inst = (window as any).bioradarLenis;
      if (inst && typeof inst.on === 'function') {
        lenis = inst;
        lenis.on('scroll', compute);
        compute();
        return true;
      }
      return false;
    };
    let pollId = 0;
    let stopId = 0;
    if (!attach()) {
      pollId = window.setInterval(() => {
        if (attach()) window.clearInterval(pollId);
      }, 100);
      stopId = window.setTimeout(() => window.clearInterval(pollId), 5000);
    }

    return () => {
      window.removeEventListener('scroll', compute);
      window.removeEventListener('resize', compute);
      window.clearInterval(pollId);
      window.clearTimeout(stopId);
      if (lenis && typeof lenis.off === 'function') lenis.off('scroll', compute);
    };
  }, []);

  const solid = scrolled || mobileMenuOpen;

  const handleToggleLang = (lang: Language) => {
    setLanguage(lang);
  };

  const handleNavClick = (hash: string, viewId?: string) => {
    setMobileMenuOpen(false);
    if (viewId && onNavigateView) {
      onNavigateView(viewId);
    } else {
      window.location.hash = hash;
    }
  };

  // Render the fixed bar as a direct child of <body> via a portal. Inside the
  // app shell, `position: fixed` is trapped by an ancestor that establishes a
  // containing block (Lenis/framer-motion interaction), so the bar would scroll
  // away with the page. Portaling to <body> pins it to the viewport reliably.
  // React context (i18n) still flows through the portal from the component tree.
  const bar = (
    <header
      id="bioradar-navbar"
      data-solid={solid}
      className="fixed top-0 left-0 right-0 z-[100] w-full font-sans pointer-events-auto py-1 transition-all duration-500"
      style={
        solid
          ? {
              backgroundColor: 'rgba(9, 20, 12, 0.92)',
              backdropFilter: 'blur(20px)',
              WebkitBackdropFilter: 'blur(20px)',
              borderBottom: '2px solid #1e3320',
              boxShadow: '0 4px 30px rgba(0, 0, 0, 0.6)',
            }
          : {
              backgroundColor: 'transparent',
              backdropFilter: 'blur(0px)',
              WebkitBackdropFilter: 'blur(0px)',
              borderBottom: '2px solid transparent',
              boxShadow: 'none',
            }
      }
    >
      {/* Soft top-down scrim only while transparent, so nav text stays legible
          over the brightest frames of the hero video without a visible bar. */}
      {!solid && (
        <div
          className="absolute inset-0 -z-10 pointer-events-none"
          style={{
            background:
              'linear-gradient(to bottom, rgba(0, 0, 0, 0.45), rgba(0, 0, 0, 0.12) 55%, transparent)',
          }}
        />
      )}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-12 sm:h-14">
          {/* ══ Brand Logo & Name ══ */}
          <div
            className="flex items-center space-x-2.5 sm:space-x-3 cursor-pointer group shrink-0"
            onClick={() => handleNavClick('#home', 'home')}
          >
            <div className="w-9 h-9 rounded-xl bg-[#142418] border-2 border-[#82b978] flex items-center justify-center text-[#82b978] shadow-md group-hover:scale-105 group-hover:border-[#a8d89e] transition-all">
              <Dna className="w-[18px] h-[18px] text-[#82b978] group-hover:text-white transition-colors" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="text-lg sm:text-xl font-normal tracking-wide text-white font-heading group-hover:text-[#82b978] transition-colors drop-shadow-[0_2px_4px_rgba(0,0,0,0.9)]">
                  {t('app.title')}
                </span>
                <span className="text-[10px] sm:text-xs px-2 py-0.5 rounded-full bg-[#142418] border border-[#82b978] text-[#82b978] font-bold shadow-sm">
                  {t('app.tag')}
                </span>
              </div>
              <p className="text-[10px] text-[#c2d6be] font-medium tracking-wider hidden sm:block">
                {t('app.subtitle')}
              </p>
            </div>
          </div>

          {/* ══ DESKTOP TOP NAVBAR (Laptops & Computers: lg & xl) ══ */}
          <nav className="hidden lg:flex items-center space-x-4 xl:space-x-6">
            {/* Section Anchors for Quick Scrolling on Home */}
            <div className="flex items-center space-x-3 xl:space-x-4 text-xs font-bold text-white">
              <a
                href="#theory"
                className="nav-link-underline text-white/90 hover:text-[#82b978]"
              >
                <span>{t('nav.theory')}</span>
              </a>
              <a
                href="#pipeline"
                className="nav-link-underline text-white/90 hover:text-[#82b978]"
              >
                <span>{t('nav.pipeline')}</span>
              </a>
              <a
                href="#zones"
                className="nav-link-underline text-white/90 hover:text-[#82b978]"
              >
                <span>{t('nav.capabilities')}</span>
              </a>
              <a
                href="#models"
                className="nav-link-underline text-white/90 hover:text-[#82b978]"
              >
                <span>{t('nav.aimath')}</span>
              </a>
              <a
                href="#sites"
                className="nav-link-underline text-white/90 hover:text-[#82b978]"
              >
                <span>{t('nav.baselines')}</span>
              </a>
            </div>

            {/* ══ Prominent Hindi / English Language Toggle Pill for Laptops & Computers ══ */}
            <div className="inline-flex p-0.5 rounded-full bg-[#142418] border-2 border-[#82b978] shadow-md items-center space-x-0.5 ml-1">
              <Globe className="w-3.5 h-3.5 text-[#82b978] ml-2 mr-0.5" />
              <button
                type="button"
                onClick={() => handleToggleLang('en')}
                className={`px-3 py-1 rounded-full text-xs font-bold transition-all ${
                  currentLang === 'en'
                    ? 'bg-[#689660] text-white shadow-md scale-105 border border-[#82b978]'
                    : 'text-[#c2d6be] hover:text-white'
                }`}
                aria-pressed={currentLang === 'en'}
                title="Switch interface to English"
              >
                EN
              </button>
              <button
                type="button"
                onClick={() => handleToggleLang('hi')}
                className={`px-3 py-1 rounded-full text-xs font-bold transition-all ${
                  currentLang === 'hi'
                    ? 'bg-[#689660] text-white shadow-md scale-105 border border-[#82b978]'
                    : 'text-[#c2d6be] hover:text-white'
                }`}
                aria-pressed={currentLang === 'hi'}
                title="इंटरफ़ेस को हिन्दी में बदलें"
              >
                हिन्दी
              </button>
            </div>

            {/* Primary CTA into the platform. Individual app views (analyze,
                monitor, results, …) live in the in-app navigation and the mobile
                menu, so the landing bar stays uncluttered. */}
            <button
              type="button"
              onClick={() => handleNavClick('#analyze', 'analyze')}
              className="inline-flex items-center space-x-1.5 bg-[#689660] hover:bg-[#588051] text-white border border-[#82b978] px-4 py-2 rounded-full text-xs font-bold uppercase tracking-wider transition-all shadow-md active:translate-y-0.5"
            >
              <Upload className="w-3.5 h-3.5" />
              <span>{t('nav.launch', 'Launch Platform')}</span>
            </button>
          </nav>

          {/* ══ MOBILE COMPACT HEADER (Only for screens < lg) ══ */}
          <div className="flex lg:hidden items-center space-x-2">
            {/* Language toggle for mobile */}
            <div className="inline-flex p-0.5 rounded-full bg-[#142418] border border-[#82b978] shadow-sm items-center">
              <button
                type="button"
                onClick={() => handleToggleLang(currentLang === 'en' ? 'hi' : 'en')}
                className="px-2.5 py-1 rounded-full text-[11px] font-bold bg-[#689660] text-white shadow-sm flex items-center space-x-1"
                title="Toggle Language"
              >
                <Globe className="w-3 h-3 text-white" />
                <span>{currentLang === 'en' ? 'हिन्दी' : 'EN'}</span>
              </button>
            </div>

            {/* Hamburger button */}
            <button
              type="button"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="p-2 rounded-xl bg-[#142418] border border-[#2b422a] text-white hover:border-[#82b978] shadow-sm"
              aria-label="Toggle navigation menu"
            >
              {mobileMenuOpen ? <X className="w-5 h-5 text-[#e66a93]" /> : <Menu className="w-5 h-5 text-white" />}
            </button>
          </div>
        </div>
      </div>

      {/* ══ MOBILE DROPDOWN MENU (Only shown when user taps hamburger) ══ */}
      {mobileMenuOpen && (
        <div className="lg:hidden border-t-2 border-[#1e3320] bg-[#09140c] px-4 pt-3 pb-5 space-y-3 shadow-2xl max-h-[80vh] overflow-y-auto">
          {/* Section Anchors */}
          <div className="grid grid-cols-2 gap-2 pb-2 border-b border-[#1e3320]">
            <a
              href="#theory"
              onClick={() => setMobileMenuOpen(false)}
              className="text-xs font-bold text-[#e2ecd0] p-2.5 rounded-xl bg-[#142418] border border-[#2b422a] flex items-center justify-between"
            >
              <span>{t('nav.theory')}</span>
              <ArrowUpRight className="w-3.5 h-3.5 text-[#82b978]" />
            </a>
            <a
              href="#pipeline"
              onClick={() => setMobileMenuOpen(false)}
              className="text-xs font-bold text-[#e2ecd0] p-2.5 rounded-xl bg-[#142418] border border-[#2b422a] flex items-center justify-between"
            >
              <span>{t('nav.pipeline')}</span>
              <ArrowUpRight className="w-3.5 h-3.5 text-[#82b978]" />
            </a>
            <a
              href="#zones"
              onClick={() => setMobileMenuOpen(false)}
              className="text-xs font-bold text-[#e2ecd0] p-2.5 rounded-xl bg-[#142418] border border-[#2b422a] flex items-center justify-between"
            >
              <span>{t('nav.capabilities')}</span>
              <ArrowUpRight className="w-3.5 h-3.5 text-[#82b978]" />
            </a>
            <a
              href="#models"
              onClick={() => setMobileMenuOpen(false)}
              className="text-xs font-bold text-[#e2ecd0] p-2.5 rounded-xl bg-[#142418] border border-[#2b422a] flex items-center justify-between"
            >
              <span>{t('nav.aimath')}</span>
              <ArrowUpRight className="w-3.5 h-3.5 text-[#82b978]" />
            </a>
            <a
              href="#sites"
              onClick={() => setMobileMenuOpen(false)}
              className="col-span-2 text-xs font-bold text-[#e2ecd0] p-2.5 rounded-xl bg-[#142418] border border-[#2b422a] flex items-center justify-between"
            >
              <span>{t('nav.baselines')}</span>
              <ArrowUpRight className="w-3.5 h-3.5 text-[#82b978]" />
            </a>
          </div>

          {/* Platform Pages */}
          <div className="space-y-1.5">
            <div className="text-[10px] font-bold uppercase tracking-wider text-[#82b978] px-1">
              {t('nav.tools')}
            </div>
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => handleNavClick('#home', 'home')}
                className="py-2 px-3 rounded-xl bg-[#142418] border border-[#2b422a] text-white flex items-center justify-between font-bold text-xs"
              >
                <div className="flex items-center space-x-2">
                  <Home className="w-3.5 h-3.5 text-[#82b978]" />
                  <span>{t('nav.home')}</span>
                </div>
              </button>

              <button
                type="button"
                onClick={() => handleNavClick('#analyze', 'analyze')}
                className="py-2 px-3 rounded-xl bg-[#142418] border border-[#2b422a] text-white flex items-center justify-between font-bold text-xs"
              >
                <div className="flex items-center space-x-2">
                  <Upload className="w-3.5 h-3.5 text-[#82b978]" />
                  <span>{t('nav.analyze')}</span>
                </div>
              </button>

              <button
                type="button"
                onClick={() => handleNavClick('#monitor', 'monitor')}
                className="py-2 px-3 rounded-xl bg-[#142418] border border-[#2b422a] text-white flex items-center justify-between font-bold text-xs"
              >
                <div className="flex items-center space-x-2">
                  <Activity className="w-3.5 h-3.5 text-[#82b978]" />
                  <span>{t('nav.monitor')}</span>
                </div>
              </button>

              <button
                type="button"
                onClick={() => handleNavClick('#results', 'results')}
                className="py-2 px-3 rounded-xl bg-[#142418] border border-[#2b422a] text-white flex items-center justify-between font-bold text-xs"
              >
                <div className="flex items-center space-x-2">
                  <FileText className="w-3.5 h-3.5 text-[#82b978]" />
                  <span>{t('nav.results')}</span>
                </div>
              </button>

              <button
                type="button"
                onClick={() => handleNavClick('#compare', 'compare')}
                className="py-2 px-3 rounded-xl bg-[#142418] border border-[#2b422a] text-white flex items-center justify-between font-bold text-xs"
              >
                <div className="flex items-center space-x-2">
                  <BarChart2 className="w-3.5 h-3.5 text-[#82b978]" />
                  <span>{t('nav.compare')}</span>
                </div>
              </button>

              <button
                type="button"
                onClick={() => handleNavClick('#alerts', 'alerts')}
                className="py-2 px-3 rounded-xl bg-[#142418] border border-[#2b422a] text-white flex items-center justify-between font-bold text-xs"
              >
                <div className="flex items-center space-x-2">
                  <Bell className="w-3.5 h-3.5 text-[#e66a93]" />
                  <span>{t('nav.alerts')}</span>
                </div>
              </button>

              <button
                type="button"
                onClick={() => handleNavClick('#settings', 'settings')}
                className="col-span-2 py-2 px-3 rounded-xl bg-[#142418] border border-[#2b422a] text-white flex items-center justify-between font-bold text-xs"
              >
                <div className="flex items-center space-x-2">
                  <Settings className="w-3.5 h-3.5 text-[#82b978]" />
                  <span>{t('nav.settings')}</span>
                </div>
              </button>
            </div>
          </div>
        </div>
      )}
    </header>
  );

  return typeof document !== 'undefined' ? createPortal(bar, document.body) : bar;
};
