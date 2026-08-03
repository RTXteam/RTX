from sentence_transformers import SentenceTransformer, models 
import pandas as pd 
import numpy as np 
import os 


word = models.Transformer("cambridgeltl/SapBERT-from-PubMedBERT-fulltext",
                         max_seq_length=128)
pool = models.Pooling(word.get_word_embedding_dimension(),
                     pooling_mode="cls")
model = SentenceTransformer(modules=[word, pool])

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
NODES_TABLE = os.path.join(BASE_DIR, "data", "nodes_table.parquet")
NODE_EMBEDDINGS = os.path.expanduser("~/Desktop/code/large_files/node_embeddings.npy")
CHUNK = 100_000

df = pd.read_parquet(NODES_TABLE, columns=["text"])
texts = df["text"].to_list()

assert df["text"].notna().all()
assert len(texts) == 1_754_754

out = np.lib.format.open_memmap(
    NODE_EMBEDDINGS, mode="w+", dtype="float32", shape=(len(texts), 768))

for start in range(0, len(texts), CHUNK):
    batch = texts[start:start + CHUNK]
    out[start:start + CHUNK] = model.encode(
        batch, 
        batch_size=512,
        normalize_embeddings=True, 
        convert_to_numpy=True, 
        show_progress_bar=False
    )
    out.flush()
    print(f"    {start + len(batch):,} / {len(texts):,}")
