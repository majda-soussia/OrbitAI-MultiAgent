"""
chunker.py
----------
Lit tous les fichiers JSON presents dans data/rag/sources/ et les
transforme en chunks (texte + metadata) prets a etre embeddes.

Pour chaque fichier connu (orbit_products, pricing, faq_objections),
un handler dedie produit un texte lisible et precis.

Pour un fichier inconnu ou un nouveau fichier ajoute plus tard sans
handler dedie, le fallback generique transforme automatiquement chaque
entree de liste en "cle: valeur, cle: valeur..." -> rien ne plante,
mais la qualite du texte est moins bonne qu'un handler dedie.
Ajoutez un handler specifique des que possible pour un nouveau fichier
metier important (ex: clients.json, plans.json).
"""

import json
import os

SOURCES_DIR = os.path.join(os.path.dirname(__file__), "sources")


def load_json(filename):
    path = os.path.join(SOURCES_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ---------- Handlers specifiques ----------

def chunk_products(filename="orbit_products.json"):
    """
    Adapte au vrai schema orbit_products.json (pas de cle "products", mais
    plusieurs sections : company, key_stats, modules, ai_agents_suite,
    engineering_services, supported_hardware, certifications_standards,
    key_differentiators, reference_clients_by_sector, contact_channels).

    Chaque section produit un ou plusieurs chunks de type distinct, pour
    permettre un filtrage precis par type dans retriever.retrieve().
    """
    data = load_json(filename)
    chunks = []

    # --- Company (1 chunk) ---
    company = data.get("company", {})
    if company:
        text = (
            f"{company.get('name', 'Orbit')} — {company.get('tagline', '')}. "
            f"{company.get('description', '')} "
            f"Region: {company.get('region', '')}. Model: {company.get('model', '')}. "
            f"Website: {company.get('website', '')}. Contact: {company.get('email', '')}, "
            f"{company.get('phone', '')}. Location: {company.get('location', '')}."
        )
        chunks.append({"id": "company_0", "text": text,
                        "metadata": {"source": filename, "type": "company"}})

    # --- Key stats (1 chunk) ---
    stats = data.get("key_stats", {})
    if stats:
        text = "Orbit key stats: " + ", ".join(f"{k.replace('_', ' ')}: {v}" for k, v in stats.items())
        chunks.append({"id": "key_stats_0", "text": text,
                        "metadata": {"source": filename, "type": "key_stats"}})

    # --- Modules (1 chunk par module) ---
    for i, m in enumerate(data.get("modules", [])):
        text = (
            f"Orbit module: {m.get('name')} ({m.get('id')}). Category: {m.get('category')}. "
            f"Description: {m.get('description')}. More info: {m.get('url', '')}."
        )
        chunks.append({"id": f"module_{i}", "text": text,
                        "metadata": {"source": filename, "type": "module",
                                     "module_id": m.get("id"), "category": m.get("category")}})

    # --- AI agents suite (1 chunk groupe) ---
    agents = data.get("ai_agents_suite", [])
    if agents:
        text = "Orbit AI agents suite includes: " + ", ".join(a.get("name", "") for a in agents) + "."
        chunks.append({"id": "ai_agents_0", "text": text,
                        "metadata": {"source": filename, "type": "ai_agents_suite"}})

    # --- Engineering services (1 chunk par service) ---
    for i, s in enumerate(data.get("engineering_services", [])):
        text = f"Orbit engineering service: {s.get('name')}. {s.get('description')}"
        chunks.append({"id": f"engineering_service_{i}", "text": text,
                        "metadata": {"source": filename, "type": "engineering_service"}})

    # --- Supported hardware (1 chunk) ---
    hw = data.get("supported_hardware", {})
    if hw:
        text = (
            f"Orbit supported hardware and protocols: device types: {', '.join(hw.get('device_types', []))}. "
            f"Protocols: {', '.join(hw.get('protocols', []))}. "
            f"{hw.get('vendor_count', '')}. Example vendors: {', '.join(hw.get('example_vendors', []))}."
        )
        chunks.append({"id": "supported_hardware_0", "text": text,
                        "metadata": {"source": filename, "type": "hardware"}})

    # --- Certifications (1 chunk) ---
    certs = data.get("certifications_standards", [])
    if certs:
        text = "Orbit certifications and standards compliance: " + ", ".join(certs) + "."
        chunks.append({"id": "certifications_0", "text": text,
                        "metadata": {"source": filename, "type": "certification"}})

    # --- Key differentiators (1 chunk par argument, utile pour objections commerciales) ---
    for i, d in enumerate(data.get("key_differentiators", [])):
        chunks.append({"id": f"differentiator_{i}", "text": f"Orbit differentiator: {d}",
                        "metadata": {"source": filename, "type": "differentiator"}})

    # --- Reference clients par secteur (1 chunk par secteur) ---
    ref_clients = data.get("reference_clients_by_sector", {})
    for sector, clients_list in ref_clients.items():
        text = f"Orbit reference clients in {sector}: " + ", ".join(clients_list) + "."
        chunks.append({"id": f"reference_clients_{sector.lower().replace(' ', '_').replace('/', '_')}",
                        "text": text,
                        "metadata": {"source": filename, "type": "reference_client", "sector": sector}})

    # --- Contact channels (1 chunk) ---
    contacts = data.get("contact_channels", {})
    if contacts:
        text = "Orbit contact channels: " + ", ".join(f"{k.replace('_', ' ')}: {v}" for k, v in contacts.items())
        chunks.append({"id": "contact_channels_0", "text": text,
                        "metadata": {"source": filename, "type": "contact"}})

    return chunks


def chunk_pricing(filename="pricing.json"):
    data = load_json(filename)
    chunks = []
    for i, row in enumerate(data.get("pricing", [])):
        price = row.get("price_eur_per_month")
        price_str = f"{price} EUR/month" if price is not None else "custom quotation (contact sales)"
        setup = row.get("setup_fee_eur")
        setup_str = f"{setup} EUR" if setup is not None else "custom"
        text = (
            f"Pricing for {row.get('product_id')}, tier {row.get('tier')}, "
            f"for {row.get('meters_range')} meters: {price_str}. "
            f"Setup fee: {setup_str}. Notes: {row.get('notes', '')}."
        )
        chunks.append({
            "id": f"pricing_{i}",
            "text": text,
            "metadata": {"source": filename, "type": "pricing",
                         "product_id": row.get("product_id"), "tier": row.get("tier")},
        })
    return chunks


def chunk_faq(filename="faq_objections.json"):
    data = load_json(filename)
    chunks = []
    for i, item in enumerate(data.get("faq", [])):
        text = f"Question: {item['question']} Answer: {item['answer']}"
        chunks.append({"id": f"faq_{i}", "text": text,
                        "metadata": {"source": filename, "type": "faq"}})
    # NOTE: le vrai fichier utilise la cle "objection_handling", pas "objections"
    for i, item in enumerate(data.get("objection_handling", [])):
        text = f"Objection: {item['objection']} Suggested response: {item['response']}"
        chunks.append({"id": f"objection_{i}", "text": text,
                        "metadata": {"source": filename, "type": "objection"}})
    return chunks


def chunk_sector_qualification(filename="sector_qualification.json"):
    data = load_json(filename)
    chunks = []
    for i, scenario in enumerate(data.get("sector_qualification_scenarios", [])):
        text = (
            f"Sector: {scenario.get('sector')}. "
            f"Typical concerns: {', '.join(scenario.get('typical_concerns', []))}. "
            f"Priority Orbit modules: {', '.join(scenario.get('priority_modules', []))}. "
            f"Qualification questions to ask: {' | '.join(scenario.get('qualification_questions', []))} "
            f"Reference clients: {', '.join(scenario.get('reference_clients', []))}."
        )
        chunks.append({
            "id": f"sector_{i}",
            "text": text,
            "metadata": {"source": filename, "type": "sector_qualification",
                         "sector": scenario.get("sector")},
        })

    fallback = data.get("general_qualification_fallback")
    if fallback:
        text = "General qualification questions (unknown sector): " + " | ".join(fallback.get("questions", []))
        chunks.append({"id": "sector_fallback_0", "text": text,
                        "metadata": {"source": filename, "type": "sector_qualification_fallback"}})
    return chunks


SPECIFIC_HANDLERS = {
    "orbit_products.json": chunk_products,
    "pricing.json": chunk_pricing,
    "faq_objections.json": chunk_faq,
    "sector_qualification.json": chunk_sector_qualification,
}


# ---------- Fallback generique ----------

def chunk_generic(filename):
    """Pour tout JSON sans handler dedie (clients.json, plans.json,
    sector_qualification.json, ou tout nouveau fichier futur)."""
    data = load_json(filename)

    # On essaie de trouver une liste d'objets, quelle que soit la cle racine
    items = None
    if isinstance(data, list):
        items = data
    elif isinstance(data, dict):
        for value in data.values():
            if isinstance(value, list):
                items = value
                break
    if items is None:
        items = [data]

    chunks = []
    base_type = os.path.splitext(filename)[0]
    for i, item in enumerate(items):
        if isinstance(item, dict):
            text = ", ".join(f"{k}: {v}" for k, v in item.items() if v not in (None, "", []))
        else:
            text = str(item)
        chunks.append({
            "id": f"{base_type}_{i}",
            "text": text,
            "metadata": {"source": filename, "type": base_type},
        })
    return chunks


def build_all_chunks():
    """Parcourt tous les .json de data/rag/sources/, applique le handler
    dedie s'il existe, sinon le fallback generique."""
    chunks = []
    resolved_path = os.path.abspath(SOURCES_DIR)

    if not os.path.isdir(SOURCES_DIR):
        print(f"[chunker] ATTENTION: dossier introuvable -> {resolved_path}")
        return chunks

    json_files = [f for f in sorted(os.listdir(SOURCES_DIR)) if f.endswith(".json")]
    print(f"[chunker] Lecture de {resolved_path} -> {len(json_files)} fichier(s) .json trouve(s): {json_files}")

    for filename in sorted(os.listdir(SOURCES_DIR)):
        if not filename.endswith(".json"):
            continue
        handler = SPECIFIC_HANDLERS.get(filename, lambda f=filename: chunk_generic(f))
        try:
            chunks += handler()
        except Exception as e:
            print(f"[chunker] Erreur sur {filename}: {e}")
    return chunks


if __name__ == "__main__":
    all_chunks = build_all_chunks()
    print(f"{len(all_chunks)} chunks generes depuis {SOURCES_DIR}")
    for c in all_chunks[:5]:
        print(c)