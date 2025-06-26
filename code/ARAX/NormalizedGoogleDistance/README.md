# curie_ngd Database Creation Script

This curie_ngd_builder creates and initializes a sqlite database named **curie_ngd**.

---

## 📌 Requirements

- **Python 3.x**
- Python package: [`redis`](https://redis.io)
- **Redis server** running on the host machine or any other accessible machine
- Properly configured **PloverDB** connection
- Properly downloaded the correct version of curie_to_pmids database

---

## 🚀 Installation

### Python Dependencies

Install required packages using `pip`:

```bash
pip install redis
```

## 🖥️ Redis Server

Make sure the Redis server is installed and running on your machine.

---

## ⚠️ Important Notes

- Ensure you are connected to the **correct version of PloverDB**.
- Ensure you have downloaded the **correct version of curie_to_pmids database**.
- Verify your PloverDB URL and curie_to_pmids database path as logged by the script:

```python
logging.info(f"curie_to_pmids_path: {curie_to_pmids_path}")
logging.info(f"PloverDB url: {RTXConfiguration().plover_url}")
```

## 🔧 Configurable Parameters

You can customize the following parameters in the script:

| Parameter                                                             | Default Value | Description                                      |
|----------------------------------------------------------------------|---------------|--------------------------------------------------|
| `redis_host`                                                         | `'localhost'` | Redis server host address                        |
| `redis_port`                                                         | `6379`        | Redis server port number                         |
| `redis_db`                                                           | `0`           | Redis database number                            |
| `number_of_PubMed_citations_and_abstracts_of_biomedical_literature` | `3.5e+7`      | Total number of PubMed citations and abstracts   |
| `average_MeSH_terms_per_article`                                    | `20`          | Average MeSH terms per PubMed article            |
| `NGD_normalizer`                                                    | _Computed_    | Calculated as citations × average MeSH terms     |


## ▶️ Running the Script

To run the script, execute:

```bash
python curie_ngd_builder.py
