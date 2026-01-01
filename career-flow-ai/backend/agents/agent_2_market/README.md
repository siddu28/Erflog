# Agent 2 - Market Sentinel 

**Agent 2** is the eyes and ears of the system. It continuously scans the job market (mock or real) to find opportunities that match the user's high-level skills.

## Features

- **Job Search** - Scans for "Software Engineer" roles tailored to the user's top skills.
- **Deduplication** - Saves unique jobs to the `jobs` table in Supabase.
- **Vectorization** - Converts job descriptions into embeddings.
- **Pinecone Indexing** - Stores job vectors in **Pinecone** to enable semantic matching by Agent 3.

---

## Workflow

![Agent Workflow](image.png)

## Key Components

- **`tools.py`**: Contains the search logic (integrating with search APIs).
- **`graph.py`**: Managing the pipeline of searching, filtering, and storing results.

## Pinecone Metadata

Each job vector stored in Pinecone includes:
- `job_id`: Database Primary Key
- `title`: Job Title
- `company`: Company Name
- `summary`: Short description for fast matching
