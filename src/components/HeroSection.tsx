import React, { useRef, useEffect } from 'react';
import { ArrowUpRight, Sparkles, Waves, ShieldCheck } from 'lucide-react';
import { PopUp, RiseUp, StaggerContainer, StaggerItem } from './MotionReveal';
import { useTranslation } from '../i18n/useTranslation';

interface HeroSectionProps {
  onExplorePipeline?: () => void;
  onLaunchDemo?: () => void;
}

export const HeroSection: React.FC<HeroSectionProps> = ({ onExplorePipeline, onLaunchDemo }) => {
  const { t } = useTranslation();
  const videoRef = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    // Force immediate video playback directly on mount with zero delay or color flash
    if (videoRef.current) {
      const playPromise = videoRef.current.play();
      if (playPromise !== undefined) {
        playPromise.catch(() => {
          // Autoplay policy fallback (video is muted and playsinline)
        });
      }
    }
  }, []);

  return (
    <section
      id="hero"
      className="relative w-full min-h-[100dvh] sm:min-h-[92vh] flex items-center justify-center pt-24 sm:pt-36 pb-16 sm:pb-28 px-4 sm:px-6 lg:px-8 border-b-2 border-[#e2e6d8] bg-black font-sans overflow-hidden"
    >
      {/* ── Direct Background Video (Zero Background Color Flashes or Jerks) ── */}
      <div className="absolute inset-0 w-full h-full overflow-hidden pointer-events-none z-0 bg-black">
        <video
          ref={videoRef}
          autoPlay
          loop
          muted
          playsInline
          preload="auto"
          poster="/static/assets/landing-image.png"
          className="absolute inset-0 w-full h-full object-cover"
          style={{
            filter: 'saturate(1.42) contrast(1.12) brightness(1.03)',
            transform: 'translateZ(0)',
            willChange: 'filter, transform'
          }}
        >
          <source src="/static/assets/landing-video.mp4" type="video/mp4" />
          <source src="/static/landing-video.mp4" type="video/mp4" />
        </video>
      </div>

      {/* Legibility scrim: keeps headings readable over the moving video while
          leaving the footage clearly visible. Darkens the very top (behind the
          transparent navbar) and the center band behind the copy. */}
      <div
        className="absolute inset-0 z-[1] pointer-events-none"
        style={{
          background:
            'linear-gradient(to bottom, rgba(0, 0, 0, 0.55), rgba(0, 0, 0, 0.18) 45%, rgba(0, 0, 0, 0.45))',
        }}
      />

      {/* Subtle Bio-Neural & Marine Wave Background Textures (kept light so the
          video reads as motion, not a busy static overlay) */}
      <div className="absolute inset-0 bg-bio-neural opacity-[0.18] pointer-events-none z-[1]" />
      <div className="absolute inset-0 bg-marine-waves opacity-[0.12] pointer-events-none z-[1]" />

      {/* Floating Animated Ambient Bio-Glow Spheres */}
      <div className="absolute top-1/4 left-10 w-64 h-64 rounded-full bg-[#689660]/18 blur-3xl pointer-events-none animate-bio-float z-[1]" />
      <div className="absolute bottom-1/4 right-10 w-72 h-72 rounded-full bg-[#bd3b67]/15 blur-3xl pointer-events-none animate-bio-float z-[1]" style={{ animationDelay: '-3s' }} />

      <div className="relative z-10 max-w-5xl mx-auto text-center flex flex-col items-center justify-center">
        {/* Top Badges with Staggered Pop-In */}
        <StaggerContainer immediate className="flex flex-wrap items-center justify-center gap-2.5 sm:gap-3 mb-6 sm:mb-8" staggerDelay={0.08}>
          <StaggerItem>
            <span className="inline-flex items-center space-x-2 px-3.5 py-1.5 rounded-full bg-[#09140c]/85 border-2 border-[#82b978] text-[11px] sm:text-xs font-bold uppercase tracking-wider text-[#82b978] shadow-lg hover:scale-105 transition-transform backdrop-blur-md">
              <span className="w-2 h-2 rounded-full bg-[#82b978] animate-pulse" />
              <span>{t('hero.badge.sih')}</span>
            </span>
          </StaggerItem>
          <StaggerItem>
            <span className="inline-flex items-center space-x-2 px-3.5 py-1.5 rounded-full bg-[#09140c]/85 border-2 border-white/30 text-[11px] sm:text-xs font-bold text-white shadow-lg backdrop-blur-md">
              <ShieldCheck className="w-3.5 h-3.5 text-[#82b978]" />
              <span>{t('hero.badge.ps')}</span>
            </span>
          </StaggerItem>
          <StaggerItem>
            <span className="inline-flex items-center space-x-2 px-3.5 py-1.5 rounded-full bg-[#09140c]/85 border-2 border-[#bd3b67] text-[11px] sm:text-xs font-bold text-[#f59cb8] shadow-lg backdrop-blur-md">
              <Waves className="w-3.5 h-3.5 text-[#f59cb8]" />
              <span>{t('hero.badge.moes')}</span>
            </span>
          </StaggerItem>
        </StaggerContainer>

        {/* Main Engaging Headings in Bungee font with Spring Pop-Up */}
        <PopUp immediate delay={0.15} duration={0.7} className="w-full">
          <h1 className="text-3xl sm:text-5xl lg:text-6xl font-normal tracking-wide text-white font-heading uppercase leading-tight max-w-4xl mx-auto drop-shadow-[0_4px_16px_rgba(0,0,0,0.95)]">
            {t('hero.title')}
          </h1>
        </PopUp>

        <RiseUp immediate delay={0.25} duration={0.6}>
          <div className="w-24 h-1.5 bg-[#82b978] mx-auto mt-4 sm:mt-5 mb-4 sm:mb-5 rounded-full shadow-[0_0_12px_rgba(130,185,120,0.8)]" />
        </RiseUp>

        <RiseUp immediate delay={0.3} duration={0.65} className="w-full">
          <h2 className="text-base sm:text-2xl font-normal text-[#98e6a0] mb-6 font-heading tracking-wide uppercase max-w-3xl mx-auto drop-shadow-[0_2px_10px_rgba(0,0,0,0.95)]">
            {t('hero.subtitle')}
          </h2>
        </RiseUp>

        {/* Body lede in Poppins with Smooth Rise */}
        <RiseUp immediate delay={0.4} duration={0.7} className="w-full">
          <p className="text-xs sm:text-base lg:text-lg text-[#f0fbf2] leading-relaxed max-w-3xl mx-auto mb-8 sm:mb-10 font-semibold font-sans drop-shadow-[0_2px_8px_rgba(0,0,0,0.95)]">
            {t('hero.lede')}
          </p>
        </RiseUp>

        {/* Action Buttons with Spring Pop-Up */}
        <PopUp immediate delay={0.5} duration={0.65} className="w-full sm:w-auto">
          <div className="flex flex-col sm:flex-row items-center justify-center gap-3.5 sm:gap-4 w-full sm:w-auto">
            <a
              href="#pipeline"
              onClick={onExplorePipeline}
              className="w-full sm:w-auto inline-flex items-center justify-center space-x-2 bg-[#689660] text-white border-2 border-[#82b978] px-8 py-3.5 rounded-full text-xs sm:text-sm font-bold uppercase tracking-wider hover:bg-[#588051] transition-all shadow-tactile-btn transform active:translate-y-0.5 font-sans shadow-[0_4px_20px_rgba(104,150,96,0.5)]"
            >
              <span>{t('hero.btn.explore')}</span>
              <ArrowUpRight className="w-4 h-4" />
            </a>
            <button
              type="button"
              onClick={() => {
                if (onLaunchDemo) onLaunchDemo();
                else window.location.hash = '#analyze';
              }}
              className="w-full sm:w-auto inline-flex items-center justify-center space-x-2 bg-[#bd3b67] text-white border-2 border-[#e66a93] px-8 py-3.5 rounded-full text-xs sm:text-sm font-bold uppercase tracking-wider hover:bg-[#a63057] transition-all shadow-tactile-btn transform active:translate-y-0.5 font-sans shadow-[0_4px_20px_rgba(189,59,103,0.5)]"
            >
              <Sparkles className="w-4 h-4" />
              <span>{t('hero.btn.launch')}</span>
              <ArrowUpRight className="w-4 h-4" />
            </button>
          </div>
        </PopUp>
      </div>
    </section>
  );
};
