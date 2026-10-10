"""Species Ecological Knowledge Base & Legal Mapping for India.

Contains ecological traits, Indian Wildlife Protection Act (WLPA 1972) Schedules,
National Biodiversity Authority (NBA) Invasive Alien Species listings, prey-predator
interactions, and recommended legal/field response protocols.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

# Structured Knowledge Base for Indian Aquatic Taxa
SPECIES_KNOWLEDGE: Dict[str, Dict[str, Any]] = {
    "clarias gariepinus": {
        "scientific_name": "Clarias gariepinus",
        "common_name": "African Catfish",
        "phylum": "Chordata",
        "group": "Freshwater Fish",
        "native_to": "Africa & Middle East",
        "india_status": "invasive",
        "legal_status": "Banned for breeding and culture in India since 2000 (Ministry of Agriculture / WLPA)",
        "legal_sections": ["Wildlife Protection Act 1972 Section 11", "National Biodiversity Act 2002 Sec 36"],
        "ecological_impact": "Voracious air-breathing carnivore. Preys on native fish fry, eggs, amphibians, and invertebrates. Outcompetes native Clarias magur (magur).",
        "target_threatened_species": ["Tor putitora", "Clarias magur", "Labeo rohita"],
        "urgency_level": "CRITICAL",
        "action_protocol": "Dispatch field team for net/eDNA confirmation within 7 days. Initiate physical containment & eradication protocols under WLPA Section 11.",
        "trophic_level": 3.8,
        "max_size_cm": 170.0,
    },
    "oreochromis mossambicus": {
        "scientific_name": "Oreochromis mossambicus",
        "common_name": "Mozambique Tilapia",
        "phylum": "Chordata",
        "group": "Freshwater Fish",
        "native_to": "Southeast Africa",
        "india_status": "invasive",
        "legal_status": "Listed on National Biodiversity Authority (NBA) High-Risk Invasive Alien Species Register",
        "legal_sections": ["National Biodiversity Act 2002 Sec 36(1)"],
        "ecological_impact": "Aggressive nest defender and rapid breeder. Competes with native cichlids and cyprinids for food and breeding grounds. Alters water turbidity.",
        "target_threatened_species": ["Etroplus suratensis", "Etroplus maculatus"],
        "urgency_level": "HIGH",
        "action_protocol": "Deploy mesh netting survey within 14 days. Monitor temporal population growth; restrict transfer of live fish across river basins.",
        "trophic_level": 2.5,
        "max_size_cm": 39.0,
    },
    "pterygoplichthys pardalis": {
        "scientific_name": "Pterygoplichthys pardalis",
        "common_name": "Amazon Sailfin Catfish / Sucker Catfish",
        "phylum": "Chordata",
        "group": "Freshwater Fish",
        "native_to": "South America (Amazon Basin)",
        "india_status": "invasive",
        "legal_status": "Regulated Invasive Species (NBA & State Fisheries Acts)",
        "legal_sections": ["Invasive Species Management Protocol 2021"],
        "ecological_impact": "Burrows extensive nesting tunnels into riverbanks causing severe bank erosion and siltation. Displaces native bottom feeders.",
        "target_threatened_species": ["Garra mullya", "Batasio travancoria"],
        "urgency_level": "HIGH",
        "action_protocol": "Inspect riverbanks for burrow nests. Implement barrier control and localized mechanical removal.",
        "trophic_level": 2.1,
        "max_size_cm": 49.0,
    },
    "gambusia holbrooki": {
        "scientific_name": "Gambusia holbrooki",
        "common_name": "Eastern Mosquitofish",
        "phylum": "Chordata",
        "group": "Freshwater Fish",
        "native_to": "North America",
        "india_status": "invasive",
        "legal_status": "Restricted Vector-Control Introduced Species",
        "legal_sections": ["State Inland Fisheries Guidelines"],
        "ecological_impact": "Nips fins of native fish and eats frog eggs/tadpoles. Fails to control mosquitoes better than native Aplocheilus species.",
        "target_threatened_species": ["Aplocheilus lineatus", "Indirana frogs"],
        "urgency_level": "MEDIUM",
        "action_protocol": "Halt further releases for mosquito control; promote indigenous Aplocheilus lineatus as biological replacement.",
        "trophic_level": 3.2,
        "max_size_cm": 6.0,
    },
    "tor putitora": {
        "scientific_name": "Tor putitora",
        "common_name": "Golden Mahseer",
        "phylum": "Chordata",
        "group": "Freshwater Fish",
        "native_to": "Himalayan & Indian River Basins",
        "india_status": "native_endangered",
        "legal_status": "IUCN Endangered (EN) · State Fish of Jammu & Kashmir and Uttarakhand",
        "legal_sections": ["Wildlife Protection Act 1972 Schedule I", "IUCN Red List Endangered"],
        "ecological_impact": "Indicator species for clean, oxygenated, fast-flowing river ecosystems. Highly sensitive to habitat fragmentation and invasive predators.",
        "target_threatened_species": [],
        "urgency_level": "CONSERVATION_PRIORITY",
        "action_protocol": "Establish critical riverine sanctuary zone. Monitor water quality BOD/DO and enforce strict anti-poaching and barrier mitigation.",
        "trophic_level": 3.5,
        "max_size_cm": 275.0,
    },
    "chelonia mydas": {
        "scientific_name": "Chelonia mydas",
        "common_name": "Green Sea Turtle",
        "phylum": "Chordata",
        "group": "Reptile",
        "native_to": "Indian Ocean & Coastal Waters",
        "india_status": "native_endangered",
        "legal_status": "Wildlife Protection Act 1972 Schedule I (Highest Protection)",
        "legal_sections": ["WLPA 1972 Schedule I Part II", "CITES Appendix I"],
        "ecological_impact": "Keystone coastal herbivore maintaining seagrass bed health and marine nutrient cycling.",
        "target_threatened_species": [],
        "urgency_level": "PROTECTED_KEYSTONE",
        "action_protocol": "Protect nesting beach and offshore foraging grounds. Enforce Turtle Excluder Devices (TED) on commercial trawlers.",
        "trophic_level": 2.1,
        "max_size_cm": 150.0,
    },
    "lepidochelys olivacea": {
        "scientific_name": "Lepidochelys olivacea",
        "common_name": "Olive Ridley Turtle",
        "phylum": "Chordata",
        "group": "Reptile",
        "native_to": "Indian Ocean (Arribada nesting in Odisha/Lakshadweep)",
        "india_status": "native_vulnerable",
        "legal_status": "Wildlife Protection Act 1972 Schedule I · IUCN Vulnerable",
        "legal_sections": ["WLPA 1972 Schedule I", "CITES Appendix I"],
        "ecological_impact": "Arribada mass nesting species essential for coastal sand dune nourishment and marine food web balance.",
        "target_threatened_species": [],
        "urgency_level": "PROTECTED_KEYSTONE",
        "action_protocol": "Seasonal fishing bans within 20 km of coastal congregation sites. Guard nesting habitats.",
        "trophic_level": 3.1,
        "max_size_cm": 75.0,
    },
}


def get_species_profile(scientific_name: str) -> Optional[Dict[str, Any]]:
    """Retrieve ecological and legal profile for a species by name."""
    if not scientific_name:
        return None
    return SPECIES_KNOWLEDGE.get(scientific_name.strip().lower())


def get_all_profiles() -> Dict[str, Dict[str, Any]]:
    """Return the complete knowledge base map."""
    return SPECIES_KNOWLEDGE
