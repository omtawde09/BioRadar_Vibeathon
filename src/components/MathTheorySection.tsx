import React, { useState } from 'react';
import { LineChart, Binary, Eye, ShieldAlert, Sparkles } from 'lucide-react';
import { PopUp, RiseUp } from './MotionReveal';
import { useTranslation } from '../i18n/useTranslation';

export const MathTheorySection: React.FC = () => {
  const { t, isHindi } = useTranslation();
  const [activeTab, setActiveTab] = useState(0);

  const models = [
    {
      id: 'forecast',
      name: isHindi ? 'घटनाक्रम पूर्वानुमान' : 'Weather Forecast',
      title: isHindi
        ? 'प्रजाति घटनाक्रम पूर्वानुमान : फूरियर श्रेणी व प्लैट स्केलिंग'
        : 'Species Occurrence Forecasting : Fourier Series & Platt Scaling',
      icon: LineChart,
      color: '#bd3b67',
      formula: 'y(t) = a_0 + \\sum_{k=1}^N [a_k \\sin(2\\pi k t / 365.25) + b_k \\cos(2\\pi k t / 365.25)]',
      probabilityFormula: 'P(Detection_t) = \\frac{1}{1 + e^{-(\\alpha y(t) + \\beta)}}',
      explanation: isHindi
        ? 'किसी स्थल पर लक्षित प्रजातियों की 7-दिवसीय उपस्थिति संभावना की गणना करता है। ऐतिहासिक प्रचुरता को RPM में मापा जाता है, फूरियर श्रेणी मौसमी बदलावों को हल करती है, और प्लैट स्केलिंग सटीक संभाव्यता अंतराल [0, 1] प्रदान करती है।'
        : 'Calculates the 7-day future probability of detecting specific target species at a given site. Historical species abundance is measured in Reads Per Million (RPM). A Fourier series decomposes seasonal hydrological fluctuations, and Platt Scaling calibrates the continuous regression output into an exact probabilistic confidence interval [0, 1].',
      metrics: [
        { label: isHindi ? 'हार्मोनिक्स' : 'Harmonics', val: isHindi ? 'N = 3 वार्षिक चक्र' : 'N = 3 Annual Cycles' },
        { label: isHindi ? 'स्केलिंग' : 'Scaling', val: isHindi ? 'मैक्सिमम लाइक्लीहुड सिग्मॉइड' : 'Maximum Likelihood Sigmoid' },
        { label: isHindi ? 'क्षितिज' : 'Horizon', val: isHindi ? '7-दिवसीय रोलिंग विंडो' : '7-Day Rolling Window' }
      ]
    },
    {
      id: 'zeroshot',
      name: isHindi ? 'ज़ीरो-शॉट क्लासिफ़ायर' : 'Zero-Shot Classifier',
      title: isHindi
        ? 'संरेखण-मुक्त टैक्सोनॉमी : 4-mer कोसाइन वेक्टर एम्बेडिंग'
        : 'Alignment-Free Taxonomy : 4-mer Cosine Vector Embeddings',
      icon: Binary,
      color: '#689660',
      formula: 'V \\in \\mathbb{R}^{256}, \\quad \\hat{V} = \\frac{V}{\\|V\\|_2}, \\quad \\text{Similarity} = \\hat{V}_q \\cdot \\hat{V}_r',
      probabilityFormula: isHindi
        ? 'सीमाएँ: \\ge 0.95 \\text{ (प्रजाति)}, \\ge 0.85 \\text{ (जीनस)}, \\ge 0.75 \\text{ (कुल)}'
        : 'Thresholds: \\ge 0.95 \\text{ (Species)}, \\ge 0.85 \\text{ (Genus)}, \\ge 0.75 \\text{ (Family)}',
      explanation: isHindi
        ? 'बड़े बेयस मॉडल को पुनः प्रशिक्षित किए बिना FASTQ रीड्स से सीधे अप्रकाशित या अज्ञात eDNA अनुक्रमों को वर्गीकृत करता है। 4-बेस सबसीक्वेंस 256-आयामी k-mer वेक्टर बनाते हैं जो संदर्भ प्रोफाइल से समानता मापते हैं।'
        : 'Classifies novel or unassigned environmental DNA sequences directly from FASTQ reads without retraining large Bayes models. Overlapping 4-base subsequences form a 256-dimensional k-mer frequency vector. The unit-normalized dot product measures structural conservation across biological reference profiles.',
      metrics: [
        { label: isHindi ? 'शब्दावली' : 'Vocabulary', val: isHindi ? '4^4 = 256 आयाम' : '4^4 = 256 Dimensions' },
        { label: isHindi ? 'दूरी माप' : 'Distance', val: isHindi ? 'सामान्यीकृत कोसाइन डॉट प्रोडक्ट' : 'Normalized Cosine Dot Product' },
        { label: isHindi ? 'गति' : 'Speed', val: isHindi ? '< 5 ms प्रति रीड' : '< 5 ms per read' }
      ]
    },
    {
      id: 'anomaly',
      name: isHindi ? 'विसंगति संसूचन' : 'Anomaly Detection',
      title: isHindi
        ? 'जैवसुरक्षा चेतावनी : 3-सिग्मा Z-स्कोर व आइसोलेशन फ़ॉरेस्ट'
        : 'Biosecurity Alert : 3-Sigma Z-Score & Isolation Forest',
      icon: ShieldAlert,
      color: '#bd3b67',
      formula: 'Z = \\frac{\\text{RPM}_t - \\mu_{\\text{RPM}}}{\\sigma_{\\text{RPM}}}, \\quad |Z| \\ge 3.0 \\implies \\text{Alert}',
      probabilityFormula: 'x_t = [\\text{RPM}_{1,t}, \\text{RPM}_{2,t}, \\dots, \\text{RPM}_{M,t}] \\in \\text{IsolationForest}',
      explanation: isHindi
        ? 'अचानक आक्रामक प्रजातियों के प्रसार या प्रमुख स्थानीय प्रजातियों की गिरावट पर निरंतर निगरानी। जब प्रचुरता बेसलाइन से 3 मानक विचलन से अधिक हो जाती है, तो Z-स्कोर तत्काल अलर्ट जारी करता है।'
        : 'Continuous surveillance against sudden invasive species outbreaks or crashes in sensitive keystone species. Univariate Z-scores trigger instant alerts when abundance exceeds 3 standard deviations from baseline, while multivariate Isolation Forests detect subtle shifts across community compositions.',
      metrics: [
        { label: isHindi ? 'एकचर सीमा' : 'Univariate Limit', val: isHindi ? '3.0 सिग्मा मानक नियंत्रण' : '3.0 Sigma Standard Control' },
        { label: isHindi ? 'बहुचर मॉडल' : 'Multivariate', val: isHindi ? '100-ट्री आइसोलेशन एन्सेम्बल' : '100-Tree Isolation Ensemble' },
        { label: isHindi ? 'प्रतिक्रिया' : 'Response', val: isHindi ? 'तात्कालिक SSE पुश नोटिफिकेशन' : 'Instant SSE Push Notification' }
      ]
    },
    {
      id: 'ndvi',
      name: isHindi ? 'रिमोट सेंसिंग' : 'Remote Sensing',
      title: isHindi
        ? 'तटीय कैनोपी सहसंबंध : सेंटिनल-2 NDVI ट्रैकिंग'
        : 'Riparian Canopy Correlation : Sentinel-2 NDVI Tracking',
      icon: Eye,
      color: '#689660',
      formula: '\\text{NDVI} = \\frac{B_8 (\\text{NIR}) - B_4 (\\text{Red})}{B_8 (\\text{NIR}) + B_4 (\\text{Red})}',
      probabilityFormula: isHindi
        ? '\\Delta\\text{NDVI} = \\text{NDVI}_{\\text{पहले}} - \\text{NDVI}_{\\text{बाद}} \\ge 0.20 \\implies \\text{पर्यावास हानि}'
        : '\\Delta\\text{NDVI} = \\text{NDVI}_{\\text{before}} - \\text{NDVI}_{\\text{after}} \\ge 0.20 \\implies \\text{Habitat Loss}',
      explanation: isHindi
        ? 'नमूना स्टेशनों के आसपास 2 किमी क्षेत्र में स्थलीय पर्यावास परिवर्तनों के साथ जलीय eDNA की तुलना करता है। कॉपरनिकस सेंटिनल-2 इमेजरी द्वारा NDVI में गिरावट से जल गुणवत्ता पर असर डालने वाले वनों की कटाई का तुरंत पता चलता है।'
        : 'Correlates aquatic environmental DNA detections with terrestrial habitat changes within a 2 km buffer zone around sampling stations. Using Copernicus Sentinel-2 multispectral imagery, drops in NDVI highlight agricultural clearing or construction runoff affecting water quality.',
      metrics: [
        { label: isHindi ? 'स्थानिक बफर' : 'Spatial Buffer', val: isHindi ? 'साइट के चारों ओर 2.0 किमी' : '2.0 km Radius around Site' },
        { label: isHindi ? 'स्पेक्ट्रल बैंड' : 'Bands', val: isHindi ? 'बैंड 4 (लाल) व बैंड 8 (NIR)' : 'Band 4 (Red) & Band 8 (NIR)' },
        { label: isHindi ? 'पर्यावास ह्रास' : 'Deforestation', val: 'Delta NDVI >= 0.20' }
      ]
    }
  ];

  const current = models[activeTab];

  return (
    <section id="models" className="relative bg-[#ffffff] bg-bio-neural py-16 sm:py-20 px-4 sm:px-6 lg:px-8 border-b-2 border-[#e2e6d8] font-sans overflow-hidden">
      {/* Decorative ambient background glows */}
      <div className="absolute top-1/4 left-10 w-80 h-80 rounded-full bg-[#689660]/8 blur-3xl pointer-events-none" />
      <div className="absolute bottom-1/4 right-10 w-80 h-80 rounded-full bg-[#bd3b67]/6 blur-3xl pointer-events-none" />

      <div className="relative z-10 max-w-7xl mx-auto">
        {/* Section Header with RiseUp */}
        <RiseUp className="text-center max-w-3xl mx-auto mb-12 sm:mb-14">
          <div className="inline-flex items-center space-x-2 px-3.5 py-1.5 rounded-full bg-[#f8fef4] border-2 border-[#bd3b67] text-xs font-bold uppercase tracking-wider text-[#bd3b67] shadow-sm mb-3">
            <Sparkles className="w-3.5 h-3.5 text-[#bd3b67]" />
            <span>{t('math.badge')}</span>
          </div>
          <h2 className="text-2xl sm:text-4xl font-normal uppercase text-[#020404] tracking-wide font-heading">
            {t('math.title')}
          </h2>
          <div className="w-20 h-1.5 bg-[#689660] mx-auto mt-3 rounded-full shadow-sm" />
          <p className="text-xs sm:text-base text-[#5a6258] mt-4 font-sans font-medium">
            {t('math.subtitle')}
          </p>
        </RiseUp>

        {/* Model Tabs with RiseUp */}
        <RiseUp delay={0.15} className="flex flex-wrap items-center justify-center gap-2.5 sm:gap-3 mb-8 sm:mb-10 font-sans">
          {models.map((m, idx) => {
            const Icon = m.icon;
            const isSel = activeTab === idx;
            return (
              <button
                key={m.id}
                type="button"
                onClick={() => setActiveTab(idx)}
                className={`inline-flex items-center space-x-2 px-4 sm:px-5 py-2.5 sm:py-3 rounded-2xl text-xs font-bold uppercase tracking-wider transition-all border-2 ${
                  isSel
                    ? 'bg-[#689660] text-white border-[#476d40] shadow-tactile-btn transform -translate-y-0.5'
                    : 'bg-[#f8fef4] text-[#020404] border-[#e2e6d8] hover:border-[#689660] shadow-sm'
                }`}
              >
                <Icon className="w-4 h-4" />
                <span>{m.name}</span>
              </button>
            );
          })}
        </RiseUp>

        {/* Active Model Deep Dive Box with PopUp */}
        <PopUp delay={0.25} duration={0.65} className="bg-[#f8fef4] rounded-3xl border-2 border-[#689660] p-6 sm:p-10 shadow-tactile-card">
          <div className="space-y-6">
            <div>
              <span className="text-xs font-bold text-[#bd3b67] uppercase tracking-wider block mb-1 font-sans">
                {isHindi ? `मॉडल विनिर्देश ${activeTab + 1} / 4` : `Model Specification ${activeTab + 1} of 4`}
              </span>
              <h3 className="text-xl sm:text-2xl font-normal text-[#020404] font-heading uppercase">
                {current.title}
              </h3>
            </div>

            {/* Formula Block */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <div className="p-4 sm:p-5 rounded-2xl bg-[#ffffff] border-2 border-[#e2e6d8] font-mono text-sm text-[#020404] shadow-sm">
                <div className="text-[11px] font-bold uppercase tracking-wider text-[#5a6258] mb-2 font-sans">
                  {isHindi ? 'प्राथमिक रिग्रेशन / मैपिंग समीकरण:' : 'Primary Regression / Mapping Function:'}
                </div>
                <div className="p-3 bg-[#f8fef4] rounded-xl text-[#bd3b67] font-bold text-xs sm:text-sm overflow-x-auto border border-[#ebd2dc]">
                  {current.formula}
                </div>
              </div>

              <div className="p-4 sm:p-5 rounded-2xl bg-[#ffffff] border-2 border-[#e2e6d8] font-mono text-sm text-[#020404] shadow-sm">
                <div className="text-[11px] font-bold uppercase tracking-wider text-[#5a6258] mb-2 font-sans">
                  {isHindi ? 'वर्गीकरण / निर्णय सीमा:' : 'Classification / Decision Threshold:'}
                </div>
                <div className="p-3 bg-[#f8fef4] rounded-xl text-[#1b5e20] font-bold text-xs sm:text-sm overflow-x-auto border border-[#d6e4d0]">
                  {current.probabilityFormula}
                </div>
              </div>
            </div>

            {/* Description Narrative */}
            <div className="p-5 sm:p-6 rounded-2xl bg-[#ffffff] border-2 border-[#e2e6d8] font-sans shadow-sm">
              <h4 className="text-xs font-bold uppercase tracking-wider text-[#020404] mb-2 font-sans">
                {isHindi ? 'गणितीय संदर्भ व जैविक अनुप्रयोग:' : 'Mathematical Context & Biological Application:'}
              </h4>
              <p className="text-xs sm:text-sm text-[#020404] font-medium leading-relaxed font-sans">
                {current.explanation}
              </p>
            </div>

            {/* Parameter Badges */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3.5 sm:gap-4 font-sans">
              {current.metrics.map((m, mIdx) => (
                <div key={mIdx} className="p-4 rounded-2xl bg-[#ffffff] border-2 border-[#e2e6d8] text-center shadow-sm">
                  <div className="text-xs font-bold text-[#5a6258] uppercase tracking-wider mb-1 font-sans">
                    {m.label}
                  </div>
                  <div className="text-sm font-bold text-[#020404] font-sans">
                    {m.val}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </PopUp>
      </div>
    </section>
  );
};
