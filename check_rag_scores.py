from data.rag.retriever import retrieve

# Questions PERTINENTES — mélange FR/EN, formulations naturelles/informelles
RELEVANT_QUERIES = [
    "how much does it cost?",
    "What is the price?",
    "combien ca coute?",
    "We already have a SCADA system",
    "We are in the automotive sector",
    "What certifications does Orbit have?",
    "Comment se passe l'installation ?",
    "Do you support Modbus?",
    "Is my data secure?",
    "Nous avons deja ete decus par un fournisseur IoT",
]

# Questions HORS-SUJET — rien à voir avec Orbit
IRRELEVANT_QUERIES = [
    "What's the weather like today?",
    "Tell me a joke",
    "How do I bake a chocolate cake?",
    "Quelle heure est-il ?",
    "Who won the football match yesterday?",
    "What's your favorite movie?",
]


def show(label, queries):
    print(f"\n===== {label} =====")
    all_top_scores = []
    for q in queries:
        results = retrieve(q, top_k=1)
        top_score = results[0]["score"] if results else 0.0
        all_top_scores.append(top_score)
        print(f"{round(top_score, 3)}  -  {q}")
    avg = sum(all_top_scores) / len(all_top_scores)
    print(f"--> moyenne: {round(avg, 3)}  |  min: {round(min(all_top_scores),3)}  |  max: {round(max(all_top_scores),3)}")
    return all_top_scores


relevant_scores = show("PERTINENTES", RELEVANT_QUERIES)
irrelevant_scores = show("HORS-SUJET", IRRELEVANT_QUERIES)

suggested = (min(relevant_scores) + max(irrelevant_scores)) / 2
print(f"\n>>> Seuil suggere (milieu entre le pire pertinent et le pire hors-sujet): {round(suggested, 3)}")