# Advanced Biodiversity Analytics & Features

This document provides a comprehensive technical, mathematical, and architectural reference for the six advanced features built into the BioRadar platform.

---

## 1. AI Biodiversity Weather Forecast

Predicts the daily detection probability of target species over a rolling 7-day horizon.

### Mathematical Formulation
The forecasting model fits a daily seasonal trend using historical species relative abundances (Reads Per Million, or RPM):

$$\text{RPM}_t = \frac{\text{Reads of Species}_t}{\text{Total Reads}_t} \times 1,000,000$$

The seasonal probability is modeled as a yearly Fourier series fitted to historical sample timestamps:

$$y(t) = a_0 + \sum_{k=1}^{N} \left( a_k \sin\left(\frac{2\pi k t}{365.25}\right) + b_k \cos\left(\frac{2\pi k t}{365.25}\right) \right)$$

To map the regression output $y(t)$ to a valid probability space $[0, 1]$, we apply **Platt Scaling** (a calibrated sigmoid function):

$$P(\text{Detection}_t) = \frac{1}{1 + e^{-(\alpha y(t) + \beta)}}$$

where $\alpha$ and $\beta$ are calibration parameters derived via maximum likelihood estimation over the historical baseline runs.

### Implementation Details
* **Source Location**: [`bioradar/analytics/forecast.py`](file:///c:/Users/Parth/Desktop/SIH_om/bioradar/analytics/forecast.py)
* **Demo Fallback**: If the local database contains fewer than 3 runs at a site, a synthetic historical baseline covering the last 90 days is generated to calibrate the Fourier trend.

---

## 2. Multi-Agent Stakeholder Debate

Simulates a structured conservation debate among four AI agents representing different socio-ecological perspectives to output a legal and balanced land-use recommendation.

### Agent Personas & Prompting
1. **Forest Officer**: Prioritizes biodiversity preservation, IUCN Red List status enforcement, and species sanctuaries.
2. **Fisherman's Representative**: Advocates for local economy, sustainable harvesting rights, and livelihood protection.
3. **Environmental NGO**: Focuses on restoration ecology, habitat connectivity, and long-term sustainability.
4. **Regulatory Authority**: Focuses on national environmental laws, zoning restrictions, and compliance.

### Execution Workflow
1. The orchestrator pulls active eDNA results for the site.
2. **Round 1 (Opening Statements)**: Each agent posts their initial position based on their persona.
3. **Round 2 (Rebuttal)**: Agents analyze the statements of other agents and dispute conflicting recommendations.
4. **Round 3 (Consensus & Moderation)**: A moderator agent reviews the transcripts and synthesizes a final zoning compromise (e.g. strict core sanctuary zones combined with community-managed buffer zones).

* **Source Location**: [`bioradar/ai/debate.py`](file:///c:/Users/Parth/Desktop/SIH_om/bioradar/ai/debate.py)

---

## 3. Zero-Shot eDNA Taxonomy Classifier

Classifies unknown or unassigned DNA sequences directly from FASTQ/FASTA files against reference profiles without training a standard Naive Bayes classifier.

### Mathematical Formulation
1. **k-mer Embedding**: An arbitrary sequence is parsed into overlapping subsequences of length $k=4$ (vocabulary size $4^4 = 256$ dimensions).
2. The frequency vector $V$ is computed and normalized to unit length ($L_2$ norm):

$$\hat{V} = \frac{V}{\|V\|_2}$$

3. **Cosine Similarity**: The cosine distance between the query vector $\hat{V}_q$ and reference vectors $\hat{V}_r$ is calculated via dot product:

$$\text{Cosine Similarity} = \hat{V}_q \cdot \hat{V}_r$$

### Distance Classification Rules
* **Species Match**: Cosine Similarity $\ge 0.95$
* **Genus Match**: $0.85 \le \text{Cosine Similarity} < 0.95$
* **Family Match**: $0.75 \le \text{Cosine Similarity} < 0.85$
* **Novel Candidate**: Cosine Similarity $< 0.75$

* **Source Location**: [`bioradar/ai/zero_shot.py`](file:///c:/Users/Parth/Desktop/SIH_om/bioradar/ai/zero_shot.py)

---

## 4. Real-Time Streaming eDNA Anomaly Alert

Detects ecological anomalies (spikes in invasive species or sudden crashes in key indicator species) using univariate z-scores and multivariate forest models.

### Mathematical Formulation
1. **Univariate Z-Score**: Evaluates whether a species read count has deviated significantly from the historical average:

$$Z = \frac{\text{RPM}_t - \mu_{\text{RPM}}}{\sigma_{\text{RPM}}}$$

An anomaly is flagged if $|Z| \ge 3.0$ (representing the standard $3\sigma$ biological control limit).

2. **Multivariate Shift Detector**: Fits a `scikit-learn` `IsolationForest` model to detect shifts in the community abundance ratios:

$$\mathbf{x}_t = [ \text{RPM}_{1,t}, \text{RPM}_{2,t}, \dots, \text{RPM}_{M,t} ]$$

* **Source Location**: [`bioradar/analytics/anomaly.py`](file:///c:/Users/Parth/Desktop/SIH_om/bioradar/analytics/anomaly.py)

---

## 5. Biodiversity NFT Sponsorship Receipt

Generates blockchain-anchored conservation sponsorship receipts linked to actual verified eDNA detections.

### Generative DNA Spiral Art
The image generator parses the first 1000 base pairs of the species DNA sequence and maps each base (A, T, G, C) to a coordinate on a logarithmic spiral:

$$x(\theta) = r(\theta) \cos(\theta), \quad y(\theta) = r(\theta) \sin(\theta)$$

where $r(\theta) = R_0 + c \theta$.
Bases are colored uniquely:
* **Adenine (A)**: Green
* **Thymine (T)**: Red
* **Guanine (G)**: Yellow
* **Cytosine (C)**: Blue

### Smart Contract Integration
* **Contract Name**: `BiodiversityNFT`
* **Standard**: ERC-721
* **Metadata Structure**: Fully compliant OpenZeppelin metadata JSON containing DNA sequence, taxon IDs, verification hashes, and IPFS link assets.

* **Source Location**: [`bioradar/blockchain/nft.py`](file:///c:/Users/Parth/Desktop/SIH_om/bioradar/blockchain/nft.py) & [`bioradar/blockchain/BiodiversityNFT.sol`](file:///c:/Users/Parth/Desktop/SIH_om/bioradar/blockchain/BiodiversityNFT.sol)

---

## 6. Sentinel-2 Change Detection Alerts

Leverages Copernicus Sentinel-2 multispectral surface reflectance bands to track terrestrial canopy cover changes within a 2 km buffer zone of the sampling site.

### Mathematical Formulation
The Normalized Difference Vegetation Index (NDVI) is calculated using Red (Band 4) and Near-Infrared (Band 8) channels:

$$\text{NDVI} = \frac{B_8 - B_4}{B_8 + B_4}$$

An alert is raised if the difference in NDVI between successive monitoring cycles drops below standard thresholds:

$$\Delta\text{NDVI} = \text{NDVI}_{\text{before}} - \text{NDVI}_{\text{after}}$$

* **$\Delta\text{NDVI} \ge 0.20$**: Flags vegetation clearing or deforestation.
* **$\Delta\text{NDVI} \ge 0.30$**: Flags heavy construction or soil exposure.

* **Source Location**: [`bioradar/satellite/change_detection.py`](file:///c:/Users/Parth/Desktop/SIH_om/bioradar/satellite/change_detection.py)
