from data.rag.retriever import retrieve

TEST_QUERIES = [
    "une vraie question client",
    "quelle est la météo à Tunis",
    "combien coûte votre solution EMS",
    "quel est le meilleur restaurant à Tunis",
]

for q in TEST_QUERIES:
    print(f"\n=== {q!r} ===")
    for r in retrieve(q, top_k=3):
        print(f"  {r['score']:.3f}  {r['text'][:80]}")