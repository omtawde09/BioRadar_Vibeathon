import React, { useEffect, useRef, useState } from 'react';
import { Database, Fish, Award, MapPin, Dna, Droplets, Leaf, ShieldCheck, Sparkles, Waves, Compass } from 'lucide-react';
import { PopUp, RiseUp, SlideIn } from './MotionReveal';
import { useTranslation } from '../i18n/useTranslation';

export const MetricsBanner: React.FC = () => {
  const { t } = useTranslation();
  const sectionRef = useRef<HTMLElement>(null);
  const [hasAnimated, setHasAnimated] = useState(false);

  // Animated counter state
  const [seqCount, setSeqCount] = useState(0);
  const [speciesCount, setSpeciesCount] = useState(0);
  const [recallCount, setRecallCount] = useState(0);
  const [baselinesCount, setBaselinesCount] = useState(0);

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && !hasAnimated) {
          setHasAnimated(true);
          animateCounters();
        }
      },
      { threshold: 0.15 }
    );

    if (sectionRef.current) {
      observer.observe(sectionRef.current);
    }

    return () => observer.disconnect();
  }, [hasAnimated]);

  const animateCounters = () => {
    const duration = 1800; // 1.8 seconds
    const start = performance.now();

    const frame = (now: number) => {
      const progress = Math.min(1, (now - start) / duration);
      // Ease out cubic
      const ease = 1 - Math.pow(1 - progress, 3);

      setSeqCount(Math.floor(ease * 33611));
      setSpeciesCount(Math.floor(ease * 8020));
      setRecallCount(Math.floor(ease * 100));
      setBaselinesCount(Math.floor(ease * 12));

      if (progress < 1) {
        requestAnimationFrame(frame);
      } else {
        setSeqCount(33611);
        setSpeciesCount(8020);
        setRecallCount(100);
        setBaselinesCount(12);
      }
    };

    requestAnimationFrame(frame);
  };

  return (
    <section
      ref={sectionRef}
      className="relative bg-[#ffffff] bg-bio-neural py-16 sm:py-20 px-4 sm:px-6 lg:px-8 border-b-2 border-[#e2e6d8] font-sans overflow-hidden"
    >
      {/* Decorative Floating Bio-Synapse Vector Accents in Background */}
      <div className="absolute top-6 left-1/4 w-72 h-72 rounded-full bg-[#689660]/8 blur-3xl pointer-events-none" />
      <div className="absolute bottom-6 right-1/4 w-80 h-80 rounded-full bg-[#bd3b67]/8 blur-3xl pointer-events-none" />

      {/* Decorative Wave lines in background */}
      <div className="absolute inset-0 bg-marine-waves opacity-40 pointer-events-none" />

      <div className="relative z-10 max-w-7xl mx-auto">
        {/* Section Header with RiseUp */}
        <RiseUp className="text-center max-w-3xl mx-auto mb-12 sm:mb-16">
          <div className="inline-flex items-center space-x-2 px-4 py-1.5 rounded-full bg-[#f8fef4] border-2 border-[#689660] text-xs font-bold uppercase tracking-wider text-[#1b5e20] shadow-sm mb-3">
            <Sparkles className="w-3.5 h-3.5 text-[#689660]" />
            <span>{t('metrics.badge')}</span>
          </div>
          <h2 className="text-2xl sm:text-4xl font-normal uppercase text-[#020404] tracking-wide font-heading">
            {t('metrics.title')}
          </h2>
          <div className="w-20 h-1.5 bg-[#bd3b67] mx-auto mt-3 rounded-full shadow-sm" />
        </RiseUp>

        {/* ── 3-COLUMN SHOWCASE: Left Column (2 Cards) | Center Kwala Showcase | Right Column (2 Cards) ── */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 lg:gap-6 items-center">
          {/* ══ LEFT COLUMN: 2 Cards (Curated COI & Species Catalogued) ══ */}
          <div className="lg:col-span-4 flex flex-col gap-6 w-full order-2 lg:order-1">
            {/* Card 1: Curated COI Sequences */}
            <SlideIn direction="left" delay={0.1}>
              <div className="w-full relative rounded-3xl bg-[#ffffff] border-2 border-[#d6e4d0] p-6 sm:p-7 shadow-tactile-card shadow-tactile-card-hover transition-all duration-300 overflow-hidden group">
                {/* Large 60% Card-Coverage Marine Graphic */}
                <div className="absolute -right-6 -bottom-8 w-60 h-60 sm:w-72 sm:h-72 opacity-25 pointer-events-none text-[#689660] transition-all duration-500 ease-out group-hover:scale-115 group-hover:opacity-45 group-hover:rotate-3 group-hover:translate-x-1 group-hover:-translate-y-2">
                  <svg viewBox="0 0 200 200" fill="currentColor" className="w-full h-full">
                    <path d="M100 15 C35 15, 5 65, 5 145 A95 95 0 0 0 195 145 C195 65, 165 15, 100 15 Z" fillOpacity="0.10" />
                    <path d="M20 140 C40 100, 80 85, 130 95 C165 102, 185 85, 190 75 C185 105, 155 130, 120 135 C85 140, 55 160, 20 140 Z" />
                    <circle cx="65" cy="115" r="4" />
                    <path d="M145 92 C165 65, 190 70, 198 65 C188 85, 175 98, 155 105 Z" />
                    <circle cx="100" cy="35" r="14" fillOpacity="0.18" />
                    <circle cx="150" cy="50" r="9" fillOpacity="0.15" />
                    <path d="M40 170 C60 155, 90 160, 110 175 Z" fillOpacity="0.25" />
                  </svg>
                </div>

                <div className="flex items-start justify-between mb-4 relative z-10">
                  <div className="w-13 h-13 rounded-2xl bg-[#f4faef] border-2 border-[#689660] flex items-center justify-center text-[#689660] shadow-md group-hover:scale-110 group-hover:bg-[#689660] group-hover:text-white transition-all">
                    <Database className="w-6 h-6" />
                  </div>
                  <span className="inline-flex items-center space-x-1 text-[11px] font-bold px-3 py-1 rounded-full bg-[#f8fef4] border border-[#689660]/40 text-[#1b5e20] uppercase tracking-wider shadow-sm">
                    <Waves className="w-3 h-3 text-[#689660]" />
                    <span>{t('metrics.card1.badge')}</span>
                  </span>
                </div>

                <div className="text-3xl sm:text-4xl font-normal text-[#bd3b67] tracking-wide font-heading mb-1 drop-shadow-sm relative z-10">
                  {seqCount.toLocaleString()}+
                </div>
                <div className="text-xs sm:text-sm font-bold uppercase tracking-wider text-[#020404] mb-2 font-sans relative z-10">
                  {t('metrics.card1.title')}
                </div>
                <p className="text-xs text-[#5a6258] leading-relaxed font-medium font-sans mb-4 relative z-10">
                  {t('metrics.card1.desc')}
                </p>

                {/* Progress Indicator */}
                <div className="pt-3 border-t border-[#e2e6d8] relative z-10">
                  <div className="flex items-center justify-between text-[11px] font-bold text-[#020404] mb-1 font-sans">
                    <span>{t('metrics.card1.progress')}</span>
                    <span className="text-[#1b5e20]">43.2%</span>
                  </div>
                  <div className="w-full h-2 rounded-full bg-[#f0f5ee] border border-[#d6e4d0] overflow-hidden">
                    <div className="h-full rounded-full bg-[#689660] transition-all duration-1000" style={{ width: '43.2%' }} />
                  </div>
                </div>
              </div>
            </SlideIn>

            {/* Card 2: Species Catalogued */}
            <SlideIn direction="left" delay={0.2}>
              <div className="w-full relative rounded-3xl bg-[#ffffff] border-2 border-[#d6e4d0] p-6 sm:p-7 shadow-tactile-card shadow-tactile-card-hover transition-all duration-300 overflow-hidden group">
                {/* Large 60% Card-Coverage Marine Graphic */}
                <div className="absolute -right-6 -bottom-8 w-60 h-60 sm:w-72 sm:h-72 opacity-25 pointer-events-none text-[#2a7b88] transition-all duration-500 ease-out group-hover:scale-115 group-hover:opacity-45 group-hover:rotate-3 group-hover:translate-x-1 group-hover:-translate-y-2">
                  <svg viewBox="0 0 200 200" fill="currentColor" className="w-full h-full">
                    <path d="M100 15 C30 15, 0 65, 0 145 A100 100 0 0 0 200 145 C200 65, 170 15, 100 15 Z" fillOpacity="0.10" />
                    <path d="M100 60 C65 90, 20 105, 10 115 C40 120, 75 115, 100 132 C125 115, 160 120, 190 115 C180 105, 135 90, 100 60 Z" />
                    <path d="M97 132 L97 185 L103 185 L103 132 Z" />
                    <circle cx="100" cy="40" r="16" fillOpacity="0.15" />
                    <path d="M45 155 C52 130, 72 135, 78 155 Z" fillOpacity="0.25" />
                    <path d="M122 155 C128 130, 148 135, 155 155 Z" fillOpacity="0.25" />
                  </svg>
                </div>

                <div className="flex items-start justify-between mb-4 relative z-10">
                  <div className="w-13 h-13 rounded-2xl bg-[#f4faef] border-2 border-[#689660] flex items-center justify-center text-[#689660] shadow-md group-hover:scale-110 group-hover:bg-[#689660] group-hover:text-white transition-all">
                    <Fish className="w-6 h-6" />
                  </div>
                  <span className="inline-flex items-center space-x-1 text-[11px] font-bold px-3 py-1 rounded-full bg-[#f8fef4] border border-[#689660]/40 text-[#1b5e20] uppercase tracking-wider shadow-sm">
                    <Fish className="w-3 h-3 text-[#689660]" />
                    <span>{t('metrics.card2.badge')}</span>
                  </span>
                </div>

                <div className="text-3xl sm:text-4xl font-normal text-[#bd3b67] tracking-wide font-heading mb-1 drop-shadow-sm relative z-10">
                  {speciesCount.toLocaleString()}+
                </div>
                <div className="text-xs sm:text-sm font-bold uppercase tracking-wider text-[#020404] mb-2 font-sans relative z-10">
                  {t('metrics.card2.title')}
                </div>
                <p className="text-xs text-[#5a6258] leading-relaxed font-medium font-sans mb-4 relative z-10">
                  {t('metrics.card2.desc')}
                </p>

                {/* Progress Indicator */}
                <div className="pt-3 border-t border-[#e2e6d8] relative z-10">
                  <div className="flex items-center justify-between text-[11px] font-bold text-[#020404] mb-1 font-sans">
                    <span>{t('metrics.card2.progress')}</span>
                    <span className="text-[#1b5e20]">99.4%</span>
                  </div>
                  <div className="w-full h-2 rounded-full bg-[#f0f5ee] border border-[#d6e4d0] overflow-hidden">
                    <div className="h-full rounded-full bg-[#689660] transition-all duration-1000" style={{ width: '99.4%' }} />
                  </div>
                </div>
              </div>
            </SlideIn>
          </div>

          {/* ══ CENTER COLUMN: Large Kwala Wildlife Showcase ══ */}
          <div className="lg:col-span-4 flex flex-col items-center justify-center relative py-4 sm:py-6 order-1 lg:order-2">
            <PopUp delay={0.25} duration={0.7} className="relative flex items-center justify-center w-72 h-72 sm:w-88 sm:h-88 lg:w-96 lg:h-96">
              {/* Outer Decorative Rotating Orbit Ring */}
              <div className="w-full h-full rounded-full border-2 border-dashed border-[#689660]/50 absolute animate-orbit flex items-center justify-center pointer-events-none">
                <div className="absolute -top-4 sm:-top-5 w-10 h-10 sm:w-12 sm:h-12 rounded-full bg-[#ffffff] border-2 border-[#689660] shadow-md flex items-center justify-center text-[#689660]">
                  <Dna className="w-5 h-5 sm:w-6 sm:h-6 text-[#689660]" />
                </div>
                <div className="absolute -right-4 sm:-right-5 w-10 h-10 sm:w-12 sm:h-12 rounded-full bg-[#ffffff] border-2 border-[#689660] shadow-md flex items-center justify-center text-[#689660]">
                  <Droplets className="w-5 h-5 sm:w-6 sm:h-6 text-[#689660]" />
                </div>
                <div className="absolute -bottom-4 sm:-bottom-5 w-10 h-10 sm:w-12 sm:h-12 rounded-full bg-[#ffffff] border-2 border-[#689660] shadow-md flex items-center justify-center text-[#689660]">
                  <Leaf className="w-5 h-5 sm:w-6 sm:h-6 text-[#689660]" />
                </div>
                <div className="absolute -left-4 sm:-left-5 w-10 h-10 sm:w-12 sm:h-12 rounded-full bg-[#ffffff] border-2 border-[#689660] shadow-md flex items-center justify-center text-[#689660]">
                  <ShieldCheck className="w-5 h-5 sm:w-6 sm:h-6 text-[#689660]" />
                </div>
              </div>

              {/* Inner Pulsing Halo Ring */}
              <div className="absolute inset-4 rounded-full border-2 border-[#bd3b67]/30 animate-halo-pulse pointer-events-none" />

              {/* Central Circular Image Frame */}
              <div className="relative w-56 h-56 sm:w-72 sm:h-72 lg:w-80 lg:h-80 rounded-full border-4 border-[#689660] bg-[#ffffff] shadow-eco-lg p-2 overflow-hidden z-10 group animate-bio-float">
                <img
                  src="/static/assets/kwala.png"
                  alt="Native Wildlife Baseline Surveillance"
                  className="w-full h-full object-cover rounded-full group-hover:scale-105 transition-transform duration-500"
                  onError={(e: any) => {
                    e.target.src = '/static/kwala.png';
                  }}
                />
                <div className="absolute inset-0 rounded-full border border-black/10 pointer-events-none shadow-inner" />
              </div>
            </PopUp>

            {/* Bottom Wildlife Showcase Badge with Depth */}
            <RiseUp delay={0.35} className="mt-5 sm:mt-6 z-10 text-center">
              <span className="inline-flex items-center space-x-2 px-5 py-2 rounded-full bg-[#ffffff] border-2 border-[#689660] text-xs font-bold text-[#1b5e20] uppercase tracking-wider font-sans shadow-md">
                <span className="w-2.5 h-2.5 rounded-full bg-[#689660] animate-pulse" />
                <span>{t('metrics.center.badge')}</span>
              </span>
            </RiseUp>
          </div>

          {/* ══ RIGHT COLUMN: 2 Cards (Benchmark Recall & Coastal Baselines) ══ */}
          <div className="lg:col-span-4 flex flex-col gap-6 w-full order-3 lg:order-3">
            {/* Card 3: Benchmark Recall */}
            <SlideIn direction="right" delay={0.1}>
              <div className="w-full relative rounded-3xl bg-[#ffffff] border-2 border-[#ebd2dc] p-6 sm:p-7 shadow-tactile-card shadow-tactile-card-hover transition-all duration-300 overflow-hidden group">
                <div className="absolute -right-6 -bottom-8 w-60 h-60 sm:w-72 sm:h-72 opacity-25 pointer-events-none text-[#bd3b67] transition-all duration-500 ease-out group-hover:scale-115 group-hover:opacity-45 group-hover:rotate-3 group-hover:translate-x-1 group-hover:-translate-y-2">
                  <svg viewBox="0 0 200 200" fill="currentColor" className="w-full h-full">
                    <path d="M100 15 C35 15, 5 65, 5 145 A95 95 0 0 0 195 145 C195 65, 165 15, 100 15 Z" fillOpacity="0.10" />
                    <ellipse cx="100" cy="110" rx="42" ry="50" />
                    <circle cx="100" cy="50" r="16" />
                    <path d="M62 85 C38 72, 20 85, 12 102 C38 108, 55 102, 68 96 Z" />
                    <path d="M138 85 C162 72, 180 85, 188 102 C162 108, 145 102, 132 96 Z" />
                    <path d="M68 135 C50 148, 42 165, 48 178 C60 172, 72 155, 75 142 Z" />
                    <path d="M132 135 C150 148, 158 165, 152 178 C140 172, 128 155, 125 142 Z" />
                  </svg>
                </div>

                <div className="flex items-start justify-between mb-4 relative z-10">
                  <div className="w-13 h-13 rounded-2xl bg-[#faedf3] border-2 border-[#bd3b67] flex items-center justify-center text-[#bd3b67] shadow-md group-hover:scale-110 group-hover:bg-[#bd3b67] group-hover:text-white transition-all">
                    <Award className="w-6 h-6" />
                  </div>
                  <span className="inline-flex items-center space-x-1 text-[11px] font-bold px-3 py-1 rounded-full bg-[#faedf3] border border-[#bd3b67]/40 text-[#bd3b67] uppercase tracking-wider shadow-sm">
                    <Sparkles className="w-3 h-3 text-[#bd3b67]" />
                    <span>{t('metrics.card3.badge')}</span>
                  </span>
                </div>

                <div className="text-3xl sm:text-4xl font-normal text-[#bd3b67] tracking-wide font-heading mb-1 drop-shadow-sm relative z-10">
                  {recallCount}%
                </div>
                <div className="text-xs sm:text-sm font-bold uppercase tracking-wider text-[#020404] mb-2 font-sans relative z-10">
                  {t('metrics.card3.title')}
                </div>
                <p className="text-xs text-[#5a6258] leading-relaxed font-medium font-sans mb-4 relative z-10">
                  {t('metrics.card3.desc')}
                </p>

                <div className="pt-3 border-t border-[#f4e6ec] relative z-10">
                  <div className="flex items-center justify-between text-[11px] font-bold text-[#020404] mb-1 font-sans">
                    <span>{t('metrics.card3.progress')}</span>
                    <span className="text-[#bd3b67]">100%</span>
                  </div>
                  <div className="w-full h-2 rounded-full bg-[#faedf3] border border-[#ebd2dc] overflow-hidden">
                    <div className="h-full rounded-full bg-[#bd3b67] transition-all duration-1000" style={{ width: '100%' }} />
                  </div>
                </div>
              </div>
            </SlideIn>

            {/* Card 4: Coastal Baselines */}
            <SlideIn direction="right" delay={0.2}>
              <div className="w-full relative rounded-3xl bg-[#ffffff] border-2 border-[#d6e4d0] p-6 sm:p-7 shadow-tactile-card shadow-tactile-card-hover transition-all duration-300 overflow-hidden group">
                <div className="absolute -right-6 -bottom-8 w-60 h-60 sm:w-72 sm:h-72 opacity-25 pointer-events-none text-[#689660] transition-all duration-500 ease-out group-hover:scale-115 group-hover:opacity-45 group-hover:rotate-3 group-hover:translate-x-1 group-hover:-translate-y-2">
                  <svg viewBox="0 0 200 200" fill="currentColor" className="w-full h-full">
                    <path d="M100 15 C35 15, 5 65, 5 145 A95 95 0 0 0 195 145 C195 65, 165 15, 100 15 Z" fillOpacity="0.10" />
                    <path d="M100 70 C75 70, 55 90, 55 115 C55 145, 80 170, 110 170 C145 170, 175 140, 175 105 C175 65, 140 30, 100 30 C55 30, 15 70, 15 120 C15 175, 60 195, 100 195" fill="none" stroke="currentColor" strokeWidth="10" strokeLinecap="round" />
                    <circle cx="100" cy="115" r="12" />
                  </svg>
                </div>

                <div className="flex items-start justify-between mb-4 relative z-10">
                  <div className="w-13 h-13 rounded-2xl bg-[#f4faef] border-2 border-[#689660] flex items-center justify-center text-[#689660] shadow-md group-hover:scale-110 group-hover:bg-[#689660] group-hover:text-white transition-all">
                    <MapPin className="w-6 h-6" />
                  </div>
                  <span className="inline-flex items-center space-x-1 text-[11px] font-bold px-3 py-1 rounded-full bg-[#f8fef4] border border-[#689660]/40 text-[#1b5e20] uppercase tracking-wider shadow-sm">
                    <Compass className="w-3 h-3 text-[#689660]" />
                    <span>{t('metrics.card4.badge')}</span>
                  </span>
                </div>

                <div className="text-3xl sm:text-4xl font-normal text-[#bd3b67] tracking-wide font-heading mb-1 drop-shadow-sm relative z-10">
                  {baselinesCount}+
                </div>
                <div className="text-xs sm:text-sm font-bold uppercase tracking-wider text-[#020404] mb-2 font-sans relative z-10">
                  {t('metrics.card4.title')}
                </div>
                <p className="text-xs text-[#5a6258] leading-relaxed font-medium font-sans mb-4 relative z-10">
                  {t('metrics.card4.desc')}
                </p>

                <div className="pt-3 border-t border-[#e2e6d8] relative z-10">
                  <div className="flex items-center justify-between text-[11px] font-bold text-[#020404] mb-1 font-sans">
                    <span>{t('metrics.card4.progress')}</span>
                    <span className="text-[#1b5e20]">12 / 12</span>
                  </div>
                  <div className="w-full h-2 rounded-full bg-[#f0f5ee] border border-[#d6e4d0] overflow-hidden">
                    <div className="h-full rounded-full bg-[#689660] transition-all duration-1000" style={{ width: '100%' }} />
                  </div>
                </div>
              </div>
            </SlideIn>
          </div>
        </div>
      </div>
    </section>
  );
};
