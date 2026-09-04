from jarvis.embeddings import cosine, hashed_embedding, lexical_overlap


def test_embedding_has_unit_shape():
    v = hashed_embedding("hello world")
    assert len(v) == 256
    assert 0.9 < cosine(v, v) <= 1.000001


def test_lexical_overlap():
    assert lexical_overlap("alpha beta", "alpha gamma") == 0.5
