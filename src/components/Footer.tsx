import React from 'react';
import { Dna, Shield, ArrowUpRight, Upload, Activity, FileText, BarChart2, Bell, Settings, Home } from 'lucide-react';
import { PopUp, RiseUp, SlideIn } from './MotionReveal';
import { useTranslation } from '../i18n/useTranslation';

interface FooterProps {
  onNavigateView?: (viewId: string) => void;
}

export const Footer: React.FC<FooterProps> = ({ onNavigateView }) => {
  const { t } = useTranslation();

  const handleNav = (viewId: string) => {
    if (onNavigateView) {
      onNavigateView(viewId);
    } else {
      window.location.hash = `#${viewId}`;
    }
  };

  return (
    <footer
      id="bioradar-footer"
      className="relative w-full border-t-2 border-[#1e3320] py-8 sm:py-10 px-4 sm:px-8 lg:px-12 font-sans overflow-hidden bg-cover bg-center sm:bg-bottom bg-no-repeat bg-[#09140c] text-white min-h-[580px] sm:min-h-[640px] flex flex-col justify-between"
      style={{
        backgroundImage: "url('/static/assets/footer-img.png')"
      }}
    >
      <div className="max-w-7xl mx-auto w-full flex-1 flex flex-col justify-between">
        {/* ── Main Side-Flanked Row: Left Side Column | Open Center Whale Window | Right Side Column ── */}
        <div className="flex flex-col lg:flex-row justify-between items-start gap-8 w-full pt-2">
          {/* ══ LEFT SIDE COLUMN (Flanking the Whale to the Left) ══ */}
          <SlideIn direction="left" delay={0.1} className="w-full lg:w-[320px] xl:w-[350px] space-y-4 shrink-0">
            {/* Brand Logo & Mission */}
            <div className="space-y-3">
              <div className="flex items-center space-x-3">
                <div className="w-10 h-10 rounded-2xl bg-[#09140c]/90 border-2 border-[#82b978] flex items-center justify-center text-[#82b978] shadow-xl backdrop-blur-md">
                  <Dna className="w-5 h-5 text-[#82b978]" />
                </div>
                <div>
                  <span className="text-2xl font-normal text-white font-heading tracking-wide drop-shadow-[0_2px_6px_rgba(0,0,0,0.95)]">
                    {t('app.title')}
                  </span>
                  <span className="ml-2 text-xs px-2.5 py-0.5 rounded-full bg-[#142418]/95 border-2 border-[#82b978] text-[#82b978] font-bold shadow-md backdrop-blur-md">
                    {t('app.tag')}
                  </span>
                </div>
              </div>

              <p className="text-xs text-[#e2ecd0] leading-relaxed font-medium drop-shadow-[0_2px_6px_rgba(0,0,0,0.95)]">
                {t('app.footerDesc')}
              </p>

              <div className="flex flex-wrap items-center gap-2 pt-1">
                <span className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full bg-[#09140c]/90 border-2 border-[#82b978] text-[11px] font-bold text-[#82b978] shadow-md backdrop-blur-md">
                  <Shield className="w-3.5 h-3.5 text-[#82b978]" />
                  <span>{t('footer.moesCite')}</span>
                </span>
                <span className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full bg-[#09140c]/90 border-2 border-white/30 text-[11px] font-bold text-white shadow-md backdrop-blur-md">
                  <span>{t('footer.standards')}</span>
                </span>
              </div>
            </div>

            {/* Quick Section Anchors on Left Side */}
            <div className="pt-2">
              <h4 className="text-xs font-bold uppercase tracking-widest text-white mb-2 font-heading border-b-2 border-[#82b978] pb-1 inline-block drop-shadow-[0_2px_4px_rgba(0,0,0,0.9)]">
                {t('footer.quickLinks')}
              </h4>
              <div className="flex flex-col space-y-1.5 text-xs font-bold pt-1">
                <a href="#theory" className="text-white hover:text-[#82b978] transition-colors flex items-center space-x-2 drop-shadow-[0_1px_4px_rgba(0,0,0,0.9)]">
                  <span className="w-1.5 h-1.5 rounded-full bg-[#82b978]" />
                  <span>{t('nav.theory')}</span>
                </a>
                <a href="#pipeline" className="text-white hover:text-[#82b978] transition-colors flex items-center space-x-2 drop-shadow-[0_1px_4px_rgba(0,0,0,0.9)]">
                  <span className="w-1.5 h-1.5 rounded-full bg-[#82b978]" />
                  <span>{t('nav.pipeline')}</span>
                </a>
                <a href="#zones" className="text-white hover:text-[#82b978] transition-colors flex items-center space-x-2 drop-shadow-[0_1px_4px_rgba(0,0,0,0.9)]">
                  <span className="w-1.5 h-1.5 rounded-full bg-[#82b978]" />
                  <span>{t('nav.capabilities')}</span>
                </a>
                <a href="#models" className="text-white hover:text-[#82b978] transition-colors flex items-center space-x-2 drop-shadow-[0_1px_4px_rgba(0,0,0,0.9)]">
                  <span className="w-1.5 h-1.5 rounded-full bg-[#82b978]" />
                  <span>{t('nav.aimath')}</span>
                </a>
                <a href="#sites" className="text-white hover:text-[#82b978] transition-colors flex items-center space-x-2 drop-shadow-[0_1px_4px_rgba(0,0,0,0.9)]">
                  <span className="w-1.5 h-1.5 rounded-full bg-[#82b978]" />
                  <span>{t('nav.baselines')}</span>
                </a>
              </div>
            </div>
          </SlideIn>

          {/* ══ CENTER ISOLATION SPACE: Completely empty and unobstructed so the Killer Whale is 100% visible ══ */}
          <div className="hidden lg:block flex-1 min-h-[340px] pointer-events-none" aria-hidden="true" />

          {/* ══ RIGHT SIDE COLUMN (Flanking the Whale to the Right) ══ */}
          <SlideIn direction="right" delay={0.15} className="w-full lg:w-[320px] xl:w-[350px] space-y-4 shrink-0">
            <div>
              <h4 className="text-xs font-bold uppercase tracking-widest text-white mb-2.5 font-heading border-b-2 border-[#82b978] pb-1 inline-block drop-shadow-[0_2px_4px_rgba(0,0,0,0.9)]">
                {t('footer.platformTools')}
              </h4>

              {/* 6 Platform Tools in a neat 2-column grid pinned to the right */}
              <div className="grid grid-cols-2 gap-2">
                <button
                  type="button"
                  onClick={() => handleNav('analyze')}
                  className="py-2.5 px-3 rounded-xl bg-[#09140c]/90 hover:bg-[#689660] text-white border-2 border-[#2b422a] hover:border-[#82b978] transition-all shadow-lg backdrop-blur-md flex items-center justify-between group"
                >
                  <div className="flex items-center space-x-2">
                    <Upload className="w-3.5 h-3.5 text-[#82b978] group-hover:text-white" />
                    <span className="text-xs font-bold">{t('nav.analyze')}</span>
                  </div>
                  <ArrowUpRight className="w-3.5 h-3.5 text-[#a8c4a4] group-hover:text-white" />
                </button>

                <button
                  type="button"
                  onClick={() => handleNav('monitor')}
                  className="py-2.5 px-3 rounded-xl bg-[#09140c]/90 hover:bg-[#689660] text-white border-2 border-[#2b422a] hover:border-[#82b978] transition-all shadow-lg backdrop-blur-md flex items-center justify-between group"
                >
                  <div className="flex items-center space-x-2">
                    <Activity className="w-3.5 h-3.5 text-[#82b978] group-hover:text-white" />
                    <span className="text-xs font-bold">{t('nav.monitor')}</span>
                  </div>
                  <ArrowUpRight className="w-3.5 h-3.5 text-[#a8c4a4] group-hover:text-white" />
                </button>

                <button
                  type="button"
                  onClick={() => handleNav('results')}
                  className="py-2.5 px-3 rounded-xl bg-[#09140c]/90 hover:bg-[#689660] text-white border-2 border-[#2b422a] hover:border-[#82b978] transition-all shadow-lg backdrop-blur-md flex items-center justify-between group"
                >
                  <div className="flex items-center space-x-2">
                    <FileText className="w-3.5 h-3.5 text-[#82b978] group-hover:text-white" />
                    <span className="text-xs font-bold">{t('nav.results')}</span>
                  </div>
                  <ArrowUpRight className="w-3.5 h-3.5 text-[#a8c4a4] group-hover:text-white" />
                </button>

                <button
                  type="button"
                  onClick={() => handleNav('compare')}
                  className="py-2.5 px-3 rounded-xl bg-[#09140c]/90 hover:bg-[#689660] text-white border-2 border-[#2b422a] hover:border-[#82b978] transition-all shadow-lg backdrop-blur-md flex items-center justify-between group"
                >
                  <div className="flex items-center space-x-2">
                    <BarChart2 className="w-3.5 h-3.5 text-[#82b978] group-hover:text-white" />
                    <span className="text-xs font-bold">{t('nav.compare')}</span>
                  </div>
                  <ArrowUpRight className="w-3.5 h-3.5 text-[#a8c4a4] group-hover:text-white" />
                </button>

                <button
                  type="button"
                  onClick={() => handleNav('alerts')}
                  className="py-2.5 px-3 rounded-xl bg-[#09140c]/90 hover:bg-[#bd3b67] text-white border-2 border-[#2b422a] hover:border-[#bd3b67] transition-all shadow-lg backdrop-blur-md flex items-center justify-between group"
                >
                  <div className="flex items-center space-x-2">
                    <Bell className="w-3.5 h-3.5 text-[#e66a93] group-hover:text-white" />
                    <span className="text-xs font-bold">{t('nav.alerts')}</span>
                  </div>
                  <ArrowUpRight className="w-3.5 h-3.5 text-[#a8c4a4] group-hover:text-white" />
                </button>

                <button
                  type="button"
                  onClick={() => handleNav('settings')}
                  className="py-2.5 px-3 rounded-xl bg-[#09140c]/90 hover:bg-[#689660] text-white border-2 border-[#2b422a] hover:border-[#82b978] transition-all shadow-lg backdrop-blur-md flex items-center justify-between group"
                >
                  <div className="flex items-center space-x-2">
                    <Settings className="w-3.5 h-3.5 text-[#82b978]" />
                    <span className="text-xs font-bold">{t('nav.settings')}</span>
                  </div>
                  <ArrowUpRight className="w-3.5 h-3.5 text-[#a8c4a4] group-hover:text-white" />
                </button>
              </div>
            </div>

            {/* Cryptographic Provenance Badge Pinned to Right Side */}
            <div className="p-3 rounded-xl bg-[#09140c]/90 border-2 border-[#2b422a] flex items-center justify-between shadow-lg backdrop-blur-md">
              <div className="text-[11px] text-white font-medium">
                <span className="font-bold text-[#82b978]">{t('footer.provenance')}</span> {t('footer.provenanceValue')}
              </div>
              <span className="w-2 h-2 rounded-full bg-[#82b978] animate-pulse" />
            </div>
          </SlideIn>
        </div>

        {/* ── Bottom Edge Compliance Bar ── */}
        <div className="w-full pt-8">
          <RiseUp delay={0.2} className="pt-3 border-t border-white/20 flex flex-col sm:flex-row items-center justify-between text-xs text-white font-bold gap-3 drop-shadow-[0_1px_4px_rgba(0,0,0,0.9)]">
            <div>
              {t('footer.copyright')}
            </div>
            <div className="flex items-center space-x-4 text-xs font-bold text-white">
              <span className="flex items-center space-x-1.5">
                <span className="w-2 h-2 rounded-full bg-[#82b978]" />
                <span>{t('footer.gigw')}</span>
              </span>
              <span>&bull;</span>
              <span className="flex items-center space-x-1.5">
                <span className="w-2 h-2 rounded-full bg-[#82b978]" />
                <span>{t('footer.wcag')}</span>
              </span>
            </div>
          </RiseUp>
        </div>
      </div>
    </footer>
  );
};
