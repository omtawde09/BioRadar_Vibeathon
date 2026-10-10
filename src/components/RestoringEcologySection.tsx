import React from 'react';
import { ArrowRight, Dna, Droplets, Leaf, Microscope, Trees, ShieldCheck, Share2, Activity, Users } from 'lucide-react';
import { PopUp, RiseUp, SlideIn, StaggerContainer, StaggerItem } from './MotionReveal';
import { useTranslation } from '../i18n/useTranslation';

export const RestoringEcologySection: React.FC = () => {
  const { t } = useTranslation();

  return (
    <section
      id="theory"
      className="relative py-16 sm:py-20 px-4 sm:px-6 lg:px-8 border-b-2 border-[#547c4d] font-sans overflow-hidden text-white"
      style={{
        background: 'linear-gradient(to right, #689660 0%, #689660 100%)'
      }}
    >
      {/* Decorative ambient background glows */}
      <div className="absolute top-10 right-1/4 w-96 h-96 rounded-full bg-white/10 blur-3xl pointer-events-none" />
      <div className="absolute bottom-10 left-1/4 w-96 h-96 rounded-full bg-[#2d4d27]/25 blur-3xl pointer-events-none" />

      {/* Wavy Marine Bathymetric Background Pattern */}
      <div className="absolute inset-0 bg-marine-waves opacity-40 pointer-events-none" />

      {/* ── Rich Multi-Layered Aquatic Wavy Illustrations ── */}
      <div className="absolute inset-0 pointer-events-none opacity-50 overflow-hidden">
        <svg className="w-full h-full" xmlns="http://www.w3.org/2000/svg" preserveAspectRatio="none" viewBox="0 0 1440 600">
          <path d="M0,80 C320,220 440,20 720,160 C1000,300 1140,80 1440,200 L1440,600 L0,600 Z" fill="none" stroke="#ffffff" strokeWidth="2" strokeOpacity="0.45" />
          <path d="M0,180 C360,340 500,100 820,260 C1140,420 1260,160 1440,300 L1440,600 L0,600 Z" fill="none" stroke="#e8f5e5" strokeWidth="1.8" strokeOpacity="0.4" />
          <path d="M0,280 C380,440 560,180 900,340 C1240,500 1340,240 1440,380 L1440,600 L0,600 Z" fill="none" stroke="#ffffff" strokeWidth="1.5" strokeOpacity="0.3" />
          <path d="M0,380 C420,520 620,260 980,420 C1340,580 1380,320 1440,460 L1440,600 L0,600 Z" fill="none" stroke="#e8f5e5" strokeWidth="1.2" strokeOpacity="0.25" />
          <path d="M0,480 C460,580 700,360 1060,500 C1380,620 1410,400 1440,540 L1440,600 L0,600 Z" fill="none" stroke="#ffffff" strokeWidth="1" strokeOpacity="0.2" />
        </svg>
      </div>

      <div className="relative z-10 max-w-7xl mx-auto space-y-12 sm:space-y-16">
        {/* ── TOP HERO ROW: Narrative Left + Orbiting Satellite eDNA Visual on Right ── */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 lg:gap-12 items-center">
          {/* Left Column: Theory & Narrative */}
          <SlideIn direction="left" delay={0.1} className="lg:col-span-7 space-y-5">
            <div>
              <div className="flex items-center space-x-3 mb-2">
                <span className="text-xs font-bold uppercase tracking-widest text-[#f8fef4] bg-black/25 border border-white/40 px-3 py-1 rounded-full font-sans shadow-sm">
                  {t('eco.badge')}
                </span>
                <div className="h-0.5 bg-white/40 flex-1 max-w-[140px]" />
              </div>
              <h2 className="text-2xl sm:text-4xl lg:text-5xl font-normal uppercase tracking-wide font-heading leading-tight text-white drop-shadow-[0_2px_4px_rgba(0,0,0,0.3)]">
                {t('eco.title')}
              </h2>
            </div>

            <p className="text-xs sm:text-base text-[#f0f9ee] leading-relaxed font-medium font-sans">
              {t('eco.subtitle')}
            </p>

            {/* Highlight Callout Box with Leaf Icon & Tactile Border */}
            <div className="p-4 sm:p-5 rounded-2xl bg-[#4d7346] border-2 border-white/30 flex items-start space-x-4 shadow-tactile-card">
              <div className="w-11 h-11 rounded-2xl bg-white border-2 border-white flex items-center justify-center text-[#689660] shrink-0 mt-0.5 shadow-sm">
                <Leaf className="w-5 h-5 text-[#689660]" />
              </div>
              <p className="text-xs sm:text-sm text-white leading-relaxed font-sans italic font-medium">
                {t('eco.quote')}
              </p>
            </div>

            {/* Action CTA Button */}
            <div className="pt-1">
              <a
                href="#pipeline"
                className="inline-flex items-center space-x-2 bg-white text-[#1b5e20] hover:bg-[#f0f9ee] border-2 border-white px-7 py-3.5 rounded-full text-xs font-bold uppercase tracking-wider transition-all font-sans shadow-tactile-btn transform active:translate-y-0.5"
              >
                <span>{t('hero.btn.explore')}</span>
                <ArrowRight className="w-4 h-4" />
              </a>
            </div>
          </SlideIn>

          {/* Right Column: Circular eDNA Image with Dark Orbit Rings & Nodes */}
          <div className="lg:col-span-5 flex flex-col items-center justify-center relative py-4">
            <PopUp delay={0.2} duration={0.7} className="relative flex items-center justify-center w-72 h-72 sm:w-88 sm:h-88">
              {/* Continuously Rotating Dashed Dark Orbit Ring with Dark Satellite Nodes */}
              <div className="w-full h-full rounded-full border-2 border-dashed border-[#09140c] absolute animate-orbit flex items-center justify-center pointer-events-none">
                <div className="absolute -top-5 w-11 h-11 rounded-full bg-[#09140c] border-2 border-[#1e3320] shadow-lg flex items-center justify-center text-[#82b978]">
                  <Microscope className="w-5 h-5 text-[#82b978]" />
                </div>
                <div className="absolute -right-5 w-11 h-11 rounded-full bg-[#09140c] border-2 border-[#1e3320] shadow-lg flex items-center justify-center text-[#82b978]">
                  <Dna className="w-5 h-5 text-[#82b978]" />
                </div>
                <div className="absolute -bottom-5 w-11 h-11 rounded-full bg-[#09140c] border-2 border-[#1e3320] shadow-lg flex items-center justify-center text-[#82b978]">
                  <Leaf className="w-5 h-5 text-[#82b978]" />
                </div>
                <div className="absolute -left-5 w-11 h-11 rounded-full bg-[#09140c] border-2 border-[#1e3320] shadow-lg flex items-center justify-center text-[#82b978]">
                  <Droplets className="w-5 h-5 text-[#82b978]" />
                </div>
              </div>

              {/* Central Fixed Circular Image Frame with Dark Ring */}
              <div className="relative w-52 h-52 sm:w-64 sm:h-64 rounded-full border-4 border-[#09140c] bg-[#09140c] shadow-[0_0_30px_rgba(0,0,0,0.6)] p-1.5 overflow-hidden z-10 animate-bio-float">
                <img
                  src="/static/assets/circular-image.png"
                  alt="Environmental DNA Double Helix"
                  className="w-full h-full object-cover rounded-full"
                  onError={(e: any) => {
                    e.target.src = '/static/circular-image.png';
                  }}
                />
              </div>
            </PopUp>

            {/* Bottom Label Badge with Dark Border & Background */}
            <RiseUp delay={0.3} className="mt-6 z-10">
              <span className="inline-flex items-center space-x-2 px-4 py-1.5 rounded-full bg-[#09140c] border-2 border-[#1e3320] text-xs font-bold text-[#82b978] uppercase tracking-wider font-sans shadow-lg">
                <span className="w-2 h-2 rounded-full bg-[#82b978] animate-pulse" />
                <span>ENVIRONMENTAL DNA (eDNA)</span>
              </span>
            </RiseUp>
          </div>
        </div>

        {/* ── MIDDLE ROW: 3 Distinct Feature Metric Cards in Crisp White Theme ── */}
        <StaggerContainer className="grid grid-cols-1 md:grid-cols-3 gap-6" staggerDelay={0.12}>
          {/* Card 1: 3,500+ Native Taxa */}
          <StaggerItem className="relative rounded-3xl bg-white border-2 border-[#d2dcc8] hover:border-[#4d7346] p-6 shadow-tactile-card shadow-tactile-card-hover transition-all duration-300 flex flex-col justify-between overflow-hidden group">
            <div className="absolute right-0 bottom-0 w-32 h-32 opacity-10 pointer-events-none text-[#689660]">
              <Trees className="w-full h-full" />
            </div>

            <div>
              <div className="w-12 h-12 rounded-2xl bg-[#689660] border-2 border-[#4d7346] flex items-center justify-center text-white mb-4 shadow-md group-hover:scale-105 transition-transform">
                <Trees className="w-6 h-6" />
              </div>
              <div className="text-3xl sm:text-4xl font-normal text-[#020404] tracking-wide font-heading mb-1 drop-shadow-sm">
                3,500+
              </div>
              <div className="text-xs font-bold uppercase tracking-wider text-[#1b5e20] mb-2 font-sans">
                {t('eco.card1.title')}
              </div>
              <p className="text-xs text-[#5a6258] leading-relaxed font-sans font-medium mb-6">
                {t('eco.card1.desc')}
              </p>
            </div>

            <div className="pt-4 border-t border-[#e2e6d8]">
              <div className="flex items-center justify-between text-[11px] font-bold text-[#020404] mb-1.5 font-sans">
                <span>{t('metrics.card1.progress')}</span>
                <span className="text-[#1b5e20]">98%</span>
              </div>
              <div className="w-full h-2.5 rounded-full bg-[#f0f9ee] border border-[#d2dcc8] overflow-hidden">
                <div className="h-full rounded-full bg-[#689660] transition-all duration-1000" style={{ width: '98%' }} />
              </div>
            </div>
          </StaggerItem>

          {/* Card 2: 6 Baselines Cataloged Systems */}
          <StaggerItem className="relative rounded-3xl bg-white border-2 border-[#d2dcc8] hover:border-[#2a7b88] p-6 shadow-tactile-card shadow-tactile-card-hover transition-all duration-300 flex flex-col justify-between overflow-hidden group">
            <div className="absolute right-0 bottom-0 w-32 h-32 opacity-10 pointer-events-none text-[#2a7b88]">
              <Droplets className="w-full h-full" />
            </div>

            <div>
              <div className="w-12 h-12 rounded-2xl bg-[#2a7b88] border-2 border-[#1f5c66] flex items-center justify-center text-white mb-4 shadow-md group-hover:scale-105 transition-transform">
                <Droplets className="w-6 h-6" />
              </div>
              <div className="text-3xl sm:text-4xl font-normal text-[#2a7b88] tracking-wide font-heading mb-1 drop-shadow-sm">
                6 BASELINES
              </div>
              <div className="text-xs font-bold uppercase tracking-wider text-[#1d606a] mb-2 font-sans">
                {t('eco.card2.title')}
              </div>
              <p className="text-xs text-[#5a6258] leading-relaxed font-sans font-medium mb-6">
                {t('eco.card2.desc')}
              </p>
            </div>

            <div className="pt-4 border-t border-[#e2e6d8]">
              <div className="flex items-center justify-between text-[11px] font-bold text-[#020404] mb-1.5 font-sans">
                <span>{t('metrics.card4.progress')}</span>
                <span className="text-[#2a7b88]">92%</span>
              </div>
              <div className="w-full h-2.5 rounded-full bg-[#eef7f8] border border-[#d2dcc8] overflow-hidden">
                <div className="h-full rounded-full bg-[#2a7b88] transition-all duration-1000" style={{ width: '92%' }} />
              </div>
            </div>
          </StaggerItem>

          {/* Card 3: 1.9X Surveillance Density */}
          <StaggerItem className="relative rounded-3xl bg-white border-2 border-[#d2dcc8] hover:border-[#bd3b67] p-6 shadow-tactile-card shadow-tactile-card-hover transition-all duration-300 flex flex-col justify-between overflow-hidden group">
            <div className="absolute right-0 bottom-0 w-32 h-32 opacity-10 pointer-events-none text-[#bd3b67]">
              <Activity className="w-full h-full" />
            </div>

            <div>
              <div className="w-12 h-12 rounded-2xl bg-[#bd3b67] border-2 border-[#8f2549] flex items-center justify-center text-white mb-4 shadow-md group-hover:scale-105 transition-transform">
                <Activity className="w-6 h-6" />
              </div>
              <div className="text-3xl sm:text-4xl font-normal text-[#bd3b67] tracking-wide font-heading mb-1 drop-shadow-sm">
                1.9X
              </div>
              <div className="text-xs font-bold uppercase tracking-wider text-[#9c284e] mb-2 font-sans">
                {t('eco.card3.title')}
              </div>
              <p className="text-xs text-[#5a6258] leading-relaxed font-sans font-medium mb-6">
                {t('eco.card3.desc')}
              </p>
            </div>

            <div className="pt-4 border-t border-[#e2e6d8]">
              <div className="flex items-center justify-between text-[11px] font-bold text-[#020404] mb-1.5 font-sans">
                <span>{t('metrics.card2.progress')}</span>
                <span className="text-[#bd3b67]">89%</span>
              </div>
              <div className="w-full h-2.5 rounded-full bg-[#fcf2f5] border border-[#d2dcc8] overflow-hidden">
                <div className="h-full rounded-full bg-[#bd3b67] transition-all duration-1000" style={{ width: '89%' }} />
              </div>
            </div>
          </StaggerItem>
        </StaggerContainer>

        {/* ── BOTTOM ROW: 5-Pill Value Highlights Ribbon with RiseUp ── */}
        <RiseUp delay={0.15}>
          <div className="rounded-3xl bg-[#4d7346] border-2 border-white/30 p-5 sm:p-6 shadow-tactile-card">
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4 lg:gap-6 divide-y sm:divide-y-0 sm:divide-x divide-white/20">
              {/* Pill 1 */}
              <div className="flex items-center space-x-3 pt-3 sm:pt-0 sm:px-2">
                <div className="w-10 h-10 rounded-2xl bg-white border-2 border-white flex items-center justify-center text-[#689660] shrink-0 shadow-sm">
                  <Leaf className="w-5 h-5 text-[#689660]" />
                </div>
                <div>
                  <div className="text-[11px] font-bold uppercase tracking-wider text-white font-sans">
                    {t('eco.card1.title')}
                  </div>
                  <div className="text-[10px] text-[#e2ecd0] leading-tight font-sans font-medium">
                    {t('eco.card1.desc')}
                  </div>
                </div>
              </div>

              {/* Pill 2 */}
              <div className="flex items-center space-x-3 pt-3 sm:pt-0 sm:px-3">
                <div className="w-10 h-10 rounded-2xl bg-white border-2 border-white flex items-center justify-center text-[#689660] shrink-0 shadow-sm">
                  <ShieldCheck className="w-5 h-5 text-[#689660]" />
                </div>
                <div>
                  <div className="text-[11px] font-bold uppercase tracking-wider text-white font-sans">
                    {t('eco.card2.title')}
                  </div>
                  <div className="text-[10px] text-[#e2ecd0] leading-tight font-sans font-medium">
                    {t('eco.card2.desc')}
                  </div>
                </div>
              </div>

              {/* Pill 3 */}
              <div className="flex items-center space-x-3 pt-3 sm:pt-0 sm:px-3">
                <div className="w-10 h-10 rounded-2xl bg-white border-2 border-white flex items-center justify-center text-[#689660] shrink-0 shadow-sm">
                  <Share2 className="w-5 h-5 text-[#689660]" />
                </div>
                <div>
                  <div className="text-[11px] font-bold uppercase tracking-wider text-white font-sans">
                    {t('eco.card3.title')}
                  </div>
                  <div className="text-[10px] text-[#e2ecd0] leading-tight font-sans font-medium">
                    {t('eco.card3.desc')}
                  </div>
                </div>
              </div>

              {/* Pill 4 */}
              <div className="flex items-center space-x-3 pt-3 sm:pt-0 sm:px-3">
                <div className="w-10 h-10 rounded-2xl bg-white border-2 border-white flex items-center justify-center text-[#689660] shrink-0 shadow-sm">
                  <Activity className="w-5 h-5 text-[#689660]" />
                </div>
                <div>
                  <div className="text-[11px] font-bold uppercase tracking-wider text-white font-sans">
                    {t('eco.card4.title')}
                  </div>
                  <div className="text-[10px] text-[#e2ecd0] leading-tight font-sans font-medium">
                    {t('eco.card4.desc')}
                  </div>
                </div>
              </div>

              {/* Pill 5 */}
              <div className="flex items-center space-x-3 pt-3 sm:pt-0 sm:px-3">
                <div className="w-10 h-10 rounded-2xl bg-white border-2 border-white flex items-center justify-center text-[#689660] shrink-0 shadow-sm">
                  <Users className="w-5 h-5 text-[#689660]" />
                </div>
                <div>
                  <div className="text-[11px] font-bold uppercase tracking-wider text-white font-sans">
                    {t('footer.quickLinks')}
                  </div>
                  <div className="text-[10px] text-[#e2ecd0] leading-tight font-sans font-medium">
                    {t('footer.standards')}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </RiseUp>
      </div>
    </section>
  );
};
