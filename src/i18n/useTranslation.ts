import { useState, useEffect, useCallback } from 'react';
import { translations, TranslationDictionary } from './translations';

export type Language = 'en' | 'hi';

export function useTranslation() {
  const [currentLang, setCurrentLangState] = useState<Language>(() => {
    if (typeof window !== 'undefined') {
      const saved =
        localStorage.getItem('bioradar.lang') ||
        localStorage.getItem('bioradar_lang') ||
        (window as any).BioRadarI18n?.language() ||
        'en';
      return (saved === 'hi' ? 'hi' : 'en') as Language;
    }
    return 'en';
  });

  useEffect(() => {
    const handleLangEvent = (e: any) => {
      const newLang = e.detail;
      if (newLang === 'en' || newLang === 'hi') {
        setCurrentLangState(newLang);
      }
    };

    document.addEventListener('bioradar:language', handleLangEvent);
    window.addEventListener('storage', (e) => {
      if (e.key === 'bioradar.lang' || e.key === 'bioradar_lang') {
        if (e.newValue === 'en' || e.newValue === 'hi') {
          setCurrentLangState(e.newValue);
        }
      }
    });

    return () => {
      document.removeEventListener('bioradar:language', handleLangEvent);
    };
  }, []);

  const setLanguage = useCallback((lang: Language) => {
    setCurrentLangState(lang);
    if (typeof window !== 'undefined') {
      try {
        localStorage.setItem('bioradar.lang', lang);
        localStorage.setItem('bioradar_lang', lang);
      } catch (e) {
        // private mode
      }

      if ((window as any).BioRadarI18n && typeof (window as any).BioRadarI18n.setLanguage === 'function') {
        (window as any).BioRadarI18n.setLanguage(lang);
      }

      document.body.setAttribute('data-lang', lang);
      document.documentElement.setAttribute('lang', lang);
      document.dispatchEvent(new CustomEvent('bioradar:language', { detail: lang }));
    }
  }, []);

  const t = useCallback(
    (key: string, fallback?: string): string => {
      const langDict = translations[currentLang] || translations.en;
      if (langDict && key in langDict) {
        return langDict[key];
      }
      if (translations.en && key in translations.en) {
        return translations.en[key];
      }
      return fallback || key;
    },
    [currentLang]
  );

  return {
    currentLang,
    setLanguage,
    t,
    isHindi: currentLang === 'hi',
    isEnglish: currentLang === 'en'
  };
}
