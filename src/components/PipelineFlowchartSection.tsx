import React, { useState } from 'react';
import { Droplet, FileCode, CheckCircle2, Sliders, Database, Link, Sparkles } from 'lucide-react';
import { PopUp, RiseUp, StaggerContainer, StaggerItem } from './MotionReveal';
import { useTranslation } from '../i18n/useTranslation';

export const PipelineFlowchartSection: React.FC = () => {
  const { t, isHindi } = useTranslation();
  const [selectedStage, setSelectedStage] = useState(0);

  const stages = [
    {
      id: 1,
      name: isHindi ? 'eDNA नमूनाकरण' : 'eDNA Capture',
      title: isHindi ? 'जल नमूनाकरण व बाह्यकोशिकीय निस्पंदन' : 'Water Sampling & Extracellular Filtration',
      icon: Droplet,
      accent: '#689660',
      badge: isHindi ? 'चरण 01 : क्षेत्रीय नमूनाकरण' : 'Step 01 : Field Sampling',
      summary: isHindi
        ? 'जलीय जीवों द्वारा छोड़े गए DNA अंशों को पकड़ने के लिए 1-लीटर जल के नमूनों को 0.22 माइक्रोन मेम्ब्रेन फिल्टर से छाना जाता है।'
        : '1-litre water samples are filtered through 0.22 micron membrane filters to capture trace DNA shed by aquatic organisms.',
      inputs: isHindi ? 'मुहाना, झील या तटीय सतही जल का नमूना' : 'Ambient estuarine, lake or coastal surface water sample',
      processes: isHindi
        ? [
            'स्थल पर बाँझ (स्टेराइल) पेरिस्टाल्टिक जल निस्पंदन',
            'कोशिकीय और बाह्यकोशिकीय मलबे का लिसिस',
            'माइटोकॉन्ड्रियल साइटोक्रोम सी ऑक्सीडेज सबयूनिट I (COI) जीन प्रवर्धन'
          ]
        : [
            'Sterile peristaltic water filtration on site',
            'Lysis of cellular and extracellular debris',
            'Mitochondrial Cytochrome c Oxidase Subunit I (COI) gene target amplification'
          ],
      output: isHindi ? 'उच्च-शुद्धता युक्त eDNA एम्प्लिकॉन लाइब्रेरी' : 'High-purity pooled eDNA amplicon libraries',
      details: isHindi
        ? 'eDNA सूक्ष्म अवशेषों से व्यापक जैवविविधता को पकड़ता है। जल संग्रह के 4 घंटे के भीतर निस्पंदन करने से नाजुक आनुवंशिक अनुक्रम संरक्षित रहते हैं।'
        : 'eDNA captures macroscopic biodiversity from microscopic traces. Organisms continuously shed genetic material into the water column. By filtering surface water within 4 hours of collection, fragile environmental sequences are preserved before microbial degradation.'
    },
    {
      id: 2,
      name: isHindi ? 'हाई-थ्रूपुट सीक्वेंसिंग' : 'High-Throughput Sequencing',
      title: isHindi ? 'Illumina पेयर्ड-एंड FASTQ जनरेशन' : 'Illumina Paired-End FASTQ Generation',
      icon: FileCode,
      accent: '#689660',
      badge: isHindi ? 'चरण 02 : मेटाजीनोमिक्स' : 'Step 02 : Metagenomics',
      summary: isHindi
        ? 'हाई-थ्रूपुट सीक्वेंसर लाखों बेस अनुक्रमों वाले पेयर्ड फॉरवर्ड (R1) और रिवर्स (R2) FASTQ रीड्स उत्पन्न करते हैं।'
        : 'High-throughput sequencers generate paired forward (R1) and reverse (R2) FASTQ reads containing millions of raw base sequences.',
      inputs: isHindi ? 'फॉरवर्ड और रिवर्स प्राइमरों के साथ एम्प्लिकॉन लाइब्रेरी' : 'Amplicon library with forward and reverse primers (e.g. Leray / Folmer primer sets)',
      processes: isHindi
        ? [
            'Illumina NovaSeq या MiSeq 2x250bp/2x300bp सीक्वेंसिंग',
            'प्रत्येक बेस स्थिति पर Phred गुणवत्ता स्कोर जनरेशन',
            'अद्वितीय इंडेक्स बारकोड के साथ सैंपल मल्टीप्लेक्सिंग'
          ]
        : [
            'Illumina NovaSeq or MiSeq paired-end 2x250bp or 2x300bp sequencing',
            'Phred quality score generation per base position',
            'Sample multiplexing with unique index barcodes'
          ],
      output: isHindi ? 'रॉ पेयर्ड-एंड FASTQ.gz फ़ाइलें और सैंपल मैनिफ़ेस्ट' : 'Raw paired-end FASTQ.gz files and sample manifest',
      details: isHindi
        ? 'प्रत्येक FASTQ रिकॉर्ड में न्यूक्लियोटाइड अनुक्रम और ASCII-एन्कोडेड गुणवत्ता स्कोर होते हैं, जिन्हें BioRadar स्वचालित रूप से मानकीकृत करता है।'
        : 'Each FASTQ record includes nucleotide sequences and ASCII-encoded Phred quality scores. BioRadar normalizes multiple sequencing vendor formats including Illumina standard lane nomenclature, NCBI SRA archives, and plain FASTQ archives.'
    },
    {
      id: 3,
      name: isHindi ? 'स्वचालित प्री-फ़्लाइट' : 'Automated Pre-Flight',
      title: isHindi ? 'तीव्र मार्कर व गुणवत्ता नैदानिक इंजन' : 'Rapid Marker & Quality Diagnostic Engine',
      icon: CheckCircle2,
      accent: '#bd3b67',
      badge: isHindi ? 'चरण 03 : प्री-फ़्लाइट जाँच' : 'Step 03 : BioRadar Pre-Flight',
      summary: isHindi
        ? 'BioRadar आनुवंशिक मार्करों, प्राइमर मिलान और इष्टतम ट्रंकेशन लंबाई का स्वतः पता लगाने के लिए लगभग 1 सेकंड में स्कैन करता है।'
        : 'BioRadar scans the sequencing reads in approximately 1 second to auto-detect genetic markers, primer matches, and optimal truncation lengths.',
      inputs: isHindi ? 'अपलोड किया गया FASTQ फ़ोल्डर और वैकल्पिक सैंपल CSV शीट' : 'Uploaded FASTQ folder and optional sample coordinate CSV sheet',
      processes: isHindi
        ? [
            'प्राइमर पहचान और दिशा सत्यापन',
            'उल्टे मेट्स के लिए स्वचालित स्वैप डिटेक्शन',
            'सटीक ट्रंकेशन लंबाई निर्धारित करने के लिए गुणवत्ता वक्र विश्लेषण'
          ]
        : [
            'Primer detection and orientation verification',
            'Automatic reverse mate swap detection for swapped library orientations',
            'Positional quality curve analysis to determine truncate lengths without manual guessing'
          ],
      output: isHindi ? 'सत्यापित प्री-फ़्लाइट रिपोर्ट और स्वचालित पाइपलाइन पैरामीटर' : 'Validated pre-flight diagnostic report and automated pipeline parameters',
      details: isHindi
        ? 'पारंपरिक पाइपलाइनों में मैनुअल निरीक्षण की आवश्यकता होती थी। BioRadar प्री-फ़्लाइट मात्र एक सेकंड में खराब डेटा और स्वैप्ड फ़ाइलों को पकड़कर रन को सुरक्षित बनाता है।'
        : 'Traditional bioinformatic pipelines require researchers to manually inspect FastQC curves and set truncation parameters. BioRadar pre-flight prevents failed 40-minute runs by catching bad data, swapped mate files, and truncated reads in under a second.'
    },
    {
      id: 4,
      name: isHindi ? 'DADA2 ASV डीनॉइज़िंग' : 'DADA2 / vsearch Denoising',
      title: isHindi ? 'सटीक सीक्वेंस वेरिएंट (ASV) क्लस्टरिंग' : 'Exact Sequence Variant (ASV) Clustering',
      icon: Sliders,
      accent: '#689660',
      badge: isHindi ? 'चरण 04 : गुणवत्ता मॉडलिंग' : 'Step 04 : Quality Modeling',
      summary: isHindi
        ? 'DADA2 सिंगल-न्यूक्लियोटाइड भिन्नता तक वास्तविक जैविक अनुक्रमों को हल करने के लिए सीक्वेंसिंग त्रुटियों का सांख्यिकीय मॉडल तैयार करता है।'
        : 'DADA2 models sequencing errors statistically to resolve true biological sequences down to single-nucleotide differences.',
      inputs: isHindi ? 'cutadapt से प्राप्त प्राइमर-ट्रिम्ड पेयर्ड रीड्स' : 'Primer-trimmed paired reads from cutadapt',
      processes: isHindi
        ? [
            'Cutadapt द्वारा प्राइमर ट्रिमिंग व अनट्रिम्ड रीड्स फ़िल्टरिंग',
            'DADA2 मशीन-लर्निंग त्रुटि दर मैट्रिक्स संगणना',
            'गुणवत्ता स्कोर हटने पर vsearch OTU क्लस्टरिंग का स्वतः चयन'
          ]
        : [
            'cutadapt primer sequence trimming and untrimmed read filtering',
            'DADA2 machine-learning error rate matrix computation',
            'Automatic routing to vsearch OTU clustering if quality scores are stripped'
          ],
      output: isHindi ? 'एम्प्लिकॉन सीक्वेंस वेरिएंट (ASV) गणना तालिका व FASTA फ़ाइल' : 'Amplicon Sequence Variant (ASV) count table and sequence fasta',
      details: isHindi
        ? 'ASVs एकल-न्यूक्लियोटाइड जैविक रिज़ॉल्यूशन प्रदान करते हैं, जिससे निकट संबंधी प्रजातियों और अलग-अलग पारिस्थितिक स्ट्रेन में भेद संभव होता है।'
        : 'ASVs provide single-nucleotide biological resolution. Unlike legacy OTU clustering which clusters sequences at arbitrary 97% similarity thresholds, DADA2 differentiates between closely related sister species and tracks distinct ecological strains.'
    },
    {
      id: 5,
      name: isHindi ? 'टैक्सोनॉमिक वर्गीकरण' : 'Taxonomic Assignment',
      title: isHindi ? 'नेव बेयस भारतीय संदर्भ डेटाबेस मिलान' : 'Naive Bayes India-Curated Reference Matching',
      icon: Database,
      accent: '#bd3b67',
      badge: isHindi ? 'चरण 05 : वर्गीकरण' : 'Step 05 : Classification',
      summary: isHindi
        ? 'प्रशिक्षित नेव बेयस क्लासिफ़ायर भारतीय जलक्षेत्र के 33,611 सीक्वेंस संदर्भ डेटाबेस से प्रजातियों का सटीक वर्गीकरण करता है।'
        : 'Trained Naive Bayes classifier assigns taxonomic lineages against a 33,611 sequence reference database customized for Indian waters.',
      inputs: isHindi ? 'ASV प्रतिनिधि अनुक्रम और प्रशिक्षित QIIME 2 QZA क्लासिफ़ायर' : 'ASV representative sequences and trained QIIME 2 QZA classifier',
      processes: isHindi
        ? [
            'K-mer आधारित मल्टिनोमियल नेव बेयस वर्गीकरण',
            '7 मानक स्तरों (जगत से प्रजाति) पर विश्वास स्कोर मूल्यांकन',
            'BioRadar संरचित तालिका अनुबंध में मानकीकरण'
          ]
        : [
            'K-mer based multinomial Naive Bayes taxonomic classification',
            'Confidence score evaluation across 7 standard taxonomic ranks (Kingdom to Species)',
            'Normalization to BioRadar frozen tabular contract'
          ],
      output: isHindi ? 'प्रजातियों और विश्वास मेट्रिक्स से युक्त मानकीकृत CSV' : 'Taxonomy normalized CSV with species, confidence metrics, and sample distribution',
      details: isHindi
        ? 'प्रजातियों के नाम 8,020 प्रजातियों (43% भारतीय रिकॉर्ड्स) का प्रतिनिधित्व करने वाले 33,611 मान्य अनुक्रमों से आते हैं।'
        : 'Species names come from our COI reference database built from 33,611 validated sequences representing 8,020 species (43% Indian records). The reference is audited for cross-order collisions to eliminate public repository misannotations.'
    },
    {
      id: 6,
      name: isHindi ? 'क्रिप्टोग्राफ़िक कस्टडी लेज़र' : 'Chain-of-Custody',
      title: isHindi ? 'SHA-256 अपरिवर्तनीय लेज़र व सत्यापन' : 'Cryptographic SHA-256 Ledger & Verification',
      icon: Link,
      accent: '#689660',
      badge: isHindi ? 'चरण 06 : डिजिटल साक्ष्य' : 'Step 06 : Provenance Proof',
      summary: isHindi
        ? 'प्रत्येक मध्यवर्ती आउटपुट को SHA-256 द्वारा हैश किया जाता है और एक अपरिवर्तनीय सत्यापन योग्य लेज़र में शृंखलाबद्ध किया जाता है।'
        : 'Every intermediate output is cryptographically hashed with SHA-256 and chained into an append-only verifiable ledger.',
      inputs: isHindi ? 'रॉ FASTQ फ़ाइलें, मध्यवर्ती QZA आर्टिफ़ैक्ट और अंतिम परिणाम' : 'Raw FASTQ files, intermediate QZA artifacts, and final normalized species tables',
      processes: isHindi
        ? [
            'सभी पाइपलाइन कलाकृतियों में डिटर्मिनिस्टिक SHA-256 हैशिंग',
            'स्थानीय लेज़र में अपरिवर्तनीय सत्यापन रिकॉर्ड लॉगिंग',
            'राष्ट्रीय आक्रामक प्रजाति वॉचलिस्ट से स्वचालित मिलान'
          ]
        : [
            'Deterministic SHA-256 hashing across all pipeline artifacts',
            'Immutable verification record logging in local ledger and optional ERC-721 token minting',
            'Automated screening against national invasive species watchlists'
          ],
      output: isHindi ? 'जैवविविधता पहचान का कानूनी डिजिटल साक्ष्य और रिपोर्ट' : 'Tamper-evident legal proof of biodiversity detection and interactive report',
      details: isHindi
        ? 'वैज्ञानिक पर्यावरण निर्णयों के लिए ऑडिटेबिलिटी अनिवार्य है। एक ही डेटासेट दोबारा चलाने पर वही हैश उत्पन्न होता है, जो कानूनी विश्वसनीयता सुनिश्चित करता है।'
        : 'Scientific environmental decisions require auditability. BioRadar ensures byte-identical determinism: re-running the same dataset produces the identical artifact hash, establishing legal and regulatory chain-of-custody.'
    }
  ];

  const current = stages[selectedStage];

  return (
    <section id="pipeline" className="relative bg-[#ffffff] bg-bio-neural py-16 sm:py-20 px-4 sm:px-6 lg:px-8 border-b-2 border-[#e2e6d8] font-sans overflow-hidden">
      {/* Decorative ambient background glows */}
      <div className="absolute top-1/3 left-10 w-72 h-72 rounded-full bg-[#689660]/8 blur-3xl pointer-events-none" />
      <div className="absolute bottom-1/3 right-10 w-72 h-72 rounded-full bg-[#bd3b67]/6 blur-3xl pointer-events-none" />

      <div className="relative z-10 max-w-7xl mx-auto">
        {/* Section Heading with RiseUp */}
        <RiseUp className="text-center max-w-3xl mx-auto mb-12 sm:mb-14">
          <div className="inline-flex items-center space-x-2 px-3.5 py-1.5 rounded-full bg-[#f8fef4] border-2 border-[#689660] text-xs font-bold uppercase tracking-wider text-[#1b5e20] shadow-sm mb-3">
            <Sparkles className="w-3.5 h-3.5 text-[#689660]" />
            <span>{t('pipeline.badge')}</span>
          </div>
          <h2 className="text-2xl sm:text-4xl font-normal uppercase text-[#020404] tracking-wide font-heading">
            {t('pipeline.title')}
          </h2>
          <div className="w-20 h-1.5 bg-[#bd3b67] mx-auto mt-3 rounded-full shadow-sm" />
          <p className="text-xs sm:text-base text-[#5a6258] mt-4 font-sans font-medium">
            {t('pipeline.subtitle')}
          </p>
        </RiseUp>

        {/* Interactive Step Selector Bar (Horizontal Flowchart Diagram) with Staggered Cascading */}
        <StaggerContainer className="hidden sm:grid sm:grid-cols-3 lg:grid-cols-6 gap-3 mb-8 sm:mb-10" staggerDelay={0.08}>
          {stages.map((stage, index) => {
            const StageIcon = stage.icon;
            const isSelected = selectedStage === index;
            return (
              <StaggerItem key={stage.id}>
                <button
                  type="button"
                  onClick={() => setSelectedStage(index)}
                  className={`w-full flex flex-col items-center text-center p-3.5 sm:p-4 rounded-2xl border-2 transition-all relative ${
                    isSelected
                      ? 'bg-[#f8fef4] border-[#689660] shadow-tactile-card transform -translate-y-1'
                      : 'bg-[#ffffff] border-[#e2e6d8] hover:border-[#689660] shadow-sm hover:shadow-md'
                  }`}
                >
                  <div
                    className={`w-11 h-11 rounded-2xl flex items-center justify-center mb-2 shadow-sm transition-transform ${
                      isSelected
                        ? 'bg-[#689660] text-white scale-105'
                        : 'bg-[#f8fef4] text-[#689660] border border-[#e2e6d8]'
                    }`}
                  >
                    <StageIcon className="w-5 h-5" />
                  </div>
                  <span className="text-[10px] sm:text-[11px] font-normal uppercase tracking-wider text-[#bd3b67] font-heading">
                    {isHindi ? `चरण 0${stage.id}` : `Step 0${stage.id}`}
                  </span>
                  <span className="text-xs font-bold text-[#020404] line-clamp-1 mt-0.5 font-sans">
                    {stage.name}
                  </span>
                </button>
              </StaggerItem>
            );
          })}
        </StaggerContainer>

        {/* Active Stage Detailed Panel with PopUp Animation */}
        <PopUp delay={0.2} duration={0.65} className="bg-[#f8fef4] rounded-3xl border-2 border-[#689660] p-6 sm:p-10 shadow-tactile-card">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
            {/* Stage Summary & Details */}
            <div className="lg:col-span-7 space-y-6">
              <div className="flex items-center space-x-3">
                <span className="px-3.5 py-1 rounded-full bg-[#ffffff] border-2 border-[#689660] text-xs font-bold text-[#1b5e20] font-sans shadow-sm">
                  {current.badge}
                </span>
                <span className="text-xs font-bold uppercase tracking-wider text-[#bd3b67] font-heading">
                  {isHindi ? `चरण ${current.id} / 6` : `Stage ${current.id} of 6`}
                </span>
              </div>

              <div>
                <h3 className="text-xl sm:text-3xl font-normal text-[#020404] font-heading uppercase">
                  {current.title}
                </h3>
                <p className="text-xs sm:text-base text-[#020404] font-medium mt-2 leading-relaxed font-sans">
                  {current.summary}
                </p>
              </div>

              <div className="p-4 sm:p-5 rounded-2xl bg-[#ffffff] border-2 border-[#e2e6d8] shadow-sm">
                <h4 className="text-xs font-bold uppercase tracking-wider text-[#bd3b67] mb-2.5 font-sans">
                  {isHindi ? 'कम्प्यूटेशनल व जैविक प्रक्रियाएँ:' : 'Computational & Biological Mechanisms:'}
                </h4>
                <ul className="space-y-2 font-sans">
                  {current.processes.map((proc, pIdx) => (
                    <li key={pIdx} className="flex items-start space-x-2.5 text-xs sm:text-sm text-[#020404] font-medium">
                      <span className="w-2 h-2 rounded-full bg-[#689660] mt-1.5 shrink-0" />
                      <span>{proc}</span>
                    </li>
                  ))}
                </ul>
              </div>

              <p className="text-xs sm:text-sm text-[#5a6258] leading-relaxed font-sans font-medium">
                {current.details}
              </p>
            </div>

            {/* Stage Input / Output Contract Card */}
            <div className="lg:col-span-5 space-y-4 font-sans">
              <div className="p-5 rounded-2xl bg-[#ffffff] border-2 border-[#e2e6d8] shadow-tactile-card">
                <div className="text-xs font-bold uppercase tracking-wider text-[#5a6258] mb-1.5">
                  {isHindi ? 'चरण इनपुट' : 'STAGE INPUT'}
                </div>
                <div className="text-xs sm:text-sm font-semibold text-[#020404]">
                  {current.inputs}
                </div>
              </div>

              <div className="p-5 rounded-2xl bg-[#ffffff] border-2 border-[#689660] shadow-tactile-card">
                <div className="text-xs font-bold uppercase tracking-wider text-[#1b5e20] mb-1.5">
                  {isHindi ? 'चरण आउटपुट' : 'STAGE OUTPUT ARTIFACT'}
                </div>
                <div className="text-xs sm:text-sm font-bold text-[#020404]">
                  {current.output}
                </div>
              </div>

              {/* Navigation buttons between steps with 3D depth */}
              <div className="flex items-center justify-between pt-2 gap-3">
                <button
                  type="button"
                  disabled={selectedStage === 0}
                  onClick={() => setSelectedStage(prev => Math.max(0, prev - 1))}
                  className="flex-1 px-4 py-3 rounded-2xl text-xs font-bold uppercase tracking-wider bg-[#ffffff] border-2 border-[#e2e6d8] disabled:opacity-40 hover:bg-[#f8fef4] shadow-sm transition-all text-center"
                >
                  {isHindi ? 'पिछला चरण' : 'Previous Step'}
                </button>
                <button
                  type="button"
                  disabled={selectedStage === stages.length - 1}
                  onClick={() => setSelectedStage(prev => Math.min(stages.length - 1, prev + 1))}
                  className="flex-1 px-4 py-3 rounded-2xl text-xs font-bold uppercase tracking-wider bg-[#689660] text-white border-2 border-[#476d40] disabled:opacity-40 hover:bg-[#588051] shadow-tactile-btn transition-all text-center"
                >
                  {isHindi ? 'अगला चरण' : 'Next Step'}
                </button>
              </div>
            </div>
          </div>
        </PopUp>
      </div>
    </section>
  );
};
