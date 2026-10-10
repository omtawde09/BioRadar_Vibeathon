import React from 'react';
import { Tag, MapPin, ArrowUpRight, Sparkles } from 'lucide-react';
import { PopUp, RiseUp, StaggerContainer, StaggerItem } from './MotionReveal';
import { useTranslation } from '../i18n/useTranslation';

interface IndianEcosystemsSectionProps {
  onNavigateView?: (viewId: string) => void;
}

export const IndianEcosystemsSection: React.FC<IndianEcosystemsSectionProps> = ({ onNavigateView }) => {
  const { t, isHindi } = useTranslation();

  const sites = [
    {
      id: 1,
      name: isHindi ? 'मांडवी मुहाना' : 'MANDOVI ESTUARY',
      state: isHindi ? 'गोवा' : 'Goa',
      locationCode: 'GOA',
      type: isHindi ? 'मुहाना मैंग्रोव व ज्वारीय लवणता' : 'Estuarine Mangrove & Tidal Salinity',
      taxaCount: isHindi ? '1,420+ प्रजातियाँ' : '1,420+ Taxa',
      invasiveStatus: isHindi ? 'निगरानीधीन' : 'Monitored',
      image: '/static/assets/mandovi.png',
      desc: isHindi
        ? 'मुहाना शंख-सीपी और वाणिज्यिक मत्स्य पालन को सहारा देने वाला ज्वारीय संगम।'
        : 'Tidal confluence supporting estuarine shellfish and commercial fisheries.'
    },
    {
      id: 2,
      name: isHindi ? 'वेम्बनाड झील' : 'VEMBANAD LAKE',
      state: isHindi ? 'केरल' : 'Kerala',
      locationCode: 'KL',
      type: isHindi ? 'रामसर आर्द्रभूमि व खारा लैगून' : 'Ramsar Wetland & Brackish Lagoon',
      taxaCount: isHindi ? '1,890+ प्रजातियाँ' : '1,890+ Taxa',
      invasiveStatus: isHindi ? 'जलकुंभी' : 'Water Hyacinth',
      image: '/static/assets/vembanand.png',
      desc: isHindi
        ? 'भारत का सबसे बड़ा खारा लैगून; पोषक तत्वों की प्रचुरता की निरंतर निगरानी।'
        : 'Largest brackish lagoon in India; monitored for nutrient enrichment.'
    },
    {
      id: 3,
      name: isHindi ? 'कोलेरु झील' : 'KOLLERU LAKE',
      state: isHindi ? 'आंध्र प्रदेश' : 'Andhra Pradesh',
      locationCode: 'AP',
      type: isHindi ? 'मीठे जल की पेलाजिक आर्द्रभूमि' : 'Freshwater Pelagic Wetland',
      taxaCount: isHindi ? '1,120+ प्रजातियाँ' : '1,120+ Taxa',
      invasiveStatus: isHindi ? 'एक्वाकल्चर' : 'Aquaculture',
      image: '/static/assets/kolleru.png',
      desc: isHindi
        ? 'अन्तर्देशीय मछली पालन तालाबों से घिरा पेलिकन पक्षी अभयारण्य।'
        : 'Critical pelican sanctuary surrounded by inland aquaculture ponds.'
    },
    {
      id: 4,
      name: isHindi ? 'मन्नार की खाड़ी' : 'GULF OF MANNAR',
      state: isHindi ? 'तमिलनाडु' : 'Tamil Nadu',
      locationCode: 'TN',
      type: isHindi ? 'राष्ट्रीय समुद्री बायोस्फीयर रिज़र्व' : 'Marine Biosphere Reserve',
      taxaCount: isHindi ? '2,450+ प्रजातियाँ' : '2,450+ Taxa',
      invasiveStatus: isHindi ? 'प्रवाल निगरानी' : 'Coral Watch',
      image: '/static/assets/gulf-of-manner.png',
      desc: isHindi
        ? 'डुगोंग, समुद्री कछुओं और 117 प्रवाल प्रजातियों से समृद्ध प्रवाल भित्ति द्वीपसमूह।'
        : 'Coral reef archipelago supporting dugongs, turtles, and 117 coral taxa.'
    },
    {
      id: 5,
      name: isHindi ? 'कवरत्ती लैगून' : 'KAVARATTI LAGOON',
      state: isHindi ? 'लक्षद्वीप' : 'Lakshadweep',
      locationCode: 'LD',
      type: isHindi ? 'एटोल लैगून व समुद्री घास' : 'Atoll Lagoon & Seagrass',
      taxaCount: isHindi ? '1,680+ प्रजातियाँ' : '1,680+ Taxa',
      invasiveStatus: isHindi ? 'प्राचीन' : 'Pristine',
      image: '/static/assets/kavaretti.png',
      desc: isHindi
        ? 'शुद्ध महासागरीय बेसलाइन के रूप में मॉनिटर किया गया एटोल और समुद्री घास पर्यावास।'
        : 'Seagrass and coral atoll habitat monitored as a pristine oceanic baseline.'
    },
    {
      id: 6,
      name: isHindi ? 'दक्षिण अंडमान' : 'SOUTH ANDAMAN',
      state: isHindi ? 'अंडमान व निकोबार' : 'Andaman & Nicobar',
      locationCode: 'AN',
      type: isHindi ? 'गहरी समुद्री खाई व मैंग्रोव' : 'Deep Trench & Mangrove Creek',
      taxaCount: isHindi ? '2,110+ प्रजातियाँ' : '2,110+ Taxa',
      invasiveStatus: isHindi ? 'बैलास्ट अलर्ट' : 'Ballast Alert',
      image: '/static/assets/south-andaman.png',
      desc: isHindi
        ? 'जहाज बैलास्ट जल द्वारा नई विदेशी प्रजातियों के प्रवेश की निगरानी हेतु रणनीतिक केंद्र।'
        : 'International shipping lane junction monitored for ballast water introductions.'
    }
  ];

  const handleViewSite = (siteId: number) => {
    if (onNavigateView) {
      onNavigateView('results');
    } else {
      window.location.hash = '#results';
    }
  };

  return (
    <section id="sites" className="relative bg-[#fcfcf0] bg-bio-neural py-16 sm:py-20 px-4 sm:px-6 lg:px-8 border-b-2 border-[#e2e6d8] font-sans overflow-hidden">
      {/* Decorative ambient background glows */}
      <div className="absolute top-1/4 right-10 w-80 h-80 rounded-full bg-[#689660]/8 blur-3xl pointer-events-none" />
      <div className="absolute bottom-1/4 left-10 w-80 h-80 rounded-full bg-[#bd3b67]/6 blur-3xl pointer-events-none" />

      <div className="relative z-10 max-w-7xl mx-auto">
        {/* Section Header with RiseUp */}
        <RiseUp className="text-center max-w-3xl mx-auto mb-12 sm:mb-14">
          <div className="inline-flex items-center space-x-2 px-3.5 py-1.5 rounded-full bg-[#ffffff] border-2 border-[#689660] text-xs font-bold uppercase tracking-wider text-[#1b5e20] shadow-sm mb-3">
            <Sparkles className="w-3.5 h-3.5 text-[#689660]" />
            <span>{t('eco_sites.badge')}</span>
          </div>
          <h2 className="text-2xl sm:text-4xl font-normal uppercase text-[#020404] tracking-wide font-heading">
            {t('eco_sites.title')}
          </h2>
          <div className="w-20 h-1.5 bg-[#bd3b67] mx-auto mt-3 rounded-full shadow-sm" />
          <p className="text-xs sm:text-base text-[#5a6258] mt-4 font-sans font-medium">
            {t('eco_sites.subtitle')}
          </p>
        </RiseUp>

        {/* Full-Bleed Immersive Cards Grid with 4px Glowing Borders and Staggered Reveal */}
        <StaggerContainer
          staggerDelay={0.1}
          className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 sm:gap-8 font-sans"
        >
          {sites.map((site) => (
            <StaggerItem
              key={site.id}
              className="group relative aspect-[9/13] sm:aspect-[9/12] rounded-[30px] overflow-hidden transition-all duration-300 flex flex-col justify-between p-6 border-[4px] border-[#689660] shadow-[0_0_22px_rgba(104,150,96,0.55),0_10px_30px_rgba(0,0,0,0.25)] hover:border-[#82b978] hover:shadow-[0_0_35px_rgba(130,185,120,0.85),0_16px_40px_rgba(0,0,0,0.35)] hover:-translate-y-1.5 transform"
            >
              {/* Full-Bleed Background Image */}
              <img
                src={site.image}
                alt={site.name}
                className="absolute inset-0 w-full h-full object-cover group-hover:scale-105 transition-transform duration-700"
              />

              {/* Dark Gradient Overlay for Maximum Text Contrast */}
              <div className="absolute inset-0 bg-gradient-to-t from-[#020404]/95 via-[#020404]/40 to-black/20" />

              {/* Top Row: Location State Tag */}
              <div className="relative z-10 flex items-center justify-between">
                <span className="px-3.5 py-1 rounded-full bg-white/20 backdrop-blur-md border border-white/30 text-white text-[11px] font-bold uppercase tracking-wider shadow-sm">
                  {site.state}
                </span>
                <span className="px-2.5 py-0.5 rounded-full bg-black/60 backdrop-blur-md border border-white/25 text-white/90 text-[10px] font-semibold shadow-sm">
                  {site.invasiveStatus}
                </span>
              </div>

              {/* Bottom Floating Content */}
              <div className="relative z-10 space-y-3">
                <div>
                  <h3 className="text-xl sm:text-2xl font-normal text-white font-heading tracking-wide uppercase leading-tight drop-shadow-sm">
                    {site.name}
                  </h3>
                  <p className="text-xs text-white/90 font-medium font-sans mt-1">
                    {site.type}
                  </p>
                </div>

                {/* Metadata Row */}
                <div className="flex items-center space-x-3 text-xs text-white/90 font-semibold pt-1">
                  <div className="flex items-center space-x-1.5 bg-white/20 backdrop-blur-sm px-3 py-1 rounded-full border border-white/30 shadow-sm">
                    <Tag className="w-3.5 h-3.5 text-[#82b978]" />
                    <span>{site.taxaCount}</span>
                  </div>
                  <div className="flex items-center space-x-1.5 bg-white/20 backdrop-blur-sm px-3 py-1 rounded-full border border-white/30 shadow-sm">
                    <MapPin className="w-3.5 h-3.5 text-[#faedf3]" />
                    <span>{site.locationCode}</span>
                  </div>
                </div>

                {/* White Pill Action Button with 3D Tactile Depth */}
                <button
                  type="button"
                  onClick={() => handleViewSite(site.id)}
                  className="w-full bg-[#ffffff] text-[#020404] hover:bg-[#689660] hover:text-white border-2 border-white hover:border-[#4d7346] py-3.5 px-6 rounded-full text-xs font-bold font-sans uppercase tracking-wider text-center transition-all shadow-tactile-btn flex items-center justify-center space-x-2 transform active:translate-y-0.5"
                >
                  <span>{isHindi ? 'बेसलाइन डेटा देखें' : 'View Site Baseline'}</span>
                  <ArrowUpRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </StaggerItem>
          ))}
        </StaggerContainer>
      </div>
    </section>
  );
};
