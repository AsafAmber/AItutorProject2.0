# Streamlit Community Cloud demo

Streamlit hosts the UI and course search on CPU. A hosted model API generates
answers, performs answer checks, and translates Hebrew. No Ollama or GPU is needed.

## Deploy

1. Commit and push these changes to `AsafAmber/AItutorProject2.0`, branch `main`.
   Keep the tracked course materials and `db/*.json`. Do not upload `.env`,
   `.streamlit/secrets.toml`, `.venv`, or local model weights.
2. Sign into https://share.streamlit.io with GitHub and choose **Create app**.
3. Select that repository, branch `main`, and entry point **`cloud/streamlit_app.py`**.
   The repository root is the local `tutor-bot` directory; do not prefix the path
   with `tutor-bot/` for this repository.
4. In **Advanced settings**, select **Python 3.11** and paste this into **Secrets**:

```toml
LLM_PROVIDER = "openai"
OPENAI_API_KEY = "replace-with-your-key"
OPENAI_MODEL = "gpt-4o-mini"
TRANSLATION_PROVIDER = "tutor"
LLM_MAX_TOKENS = "1200"
LLM_TIMEOUT_SECONDS = "120"
```

5. Deploy. First startup downloads the small embedding model and builds the index
   from the English notes on CPU. Allow a few minutes. Building this index makes
   no paid LLM calls. Sessions reuse the running app's cached resources; a fresh
   container rebuilds the index.
6. Verify a week-1 question, a later-week refusal, a Hebrew question, and a homework
   hint. Check API usage in your provider dashboard.

Copyable template: `.streamlit/secrets.toml.example`. Secrets uses TOML, including
quoted strings. To preview locally, save your settings in the ignored
`.streamlit/secrets.toml` and run from the repository root:

```sh
streamlit run cloud/streamlit_app.py
```

## Manage models

Visitors can select **OpenAI** or **OpenRouter** in the **Provider** menu.
`LLM_PROVIDER` sets the initial selection. Each model stays fixed to the ID in
Secrets. For a provider with no key in Secrets, visitors can enter a key in a
password field. Leave `TRANSLATION_PROVIDER = "tutor"` to use whichever provider
and key the visitor selects for Hebrew too.

| Role | Setting | Where it runs |
|---|---|---|
| Answers and background checks | `LLM_PROVIDER`, `OPENAI_MODEL` or `OPENROUTER_MODEL` | Provider API |
| Hebrew translation | `TRANSLATION_PROVIDER = "tutor"` reuses the answering model/key | Provider API |
| Search embeddings | `EMBED_MODEL`, default `BAAI/bge-small-en-v1.5` | Streamlit CPU |

For a separate translator, choose `openai` with `TRANSLATION_MODEL` and
`OPENAI_API_KEY`, or `openrouter` with `TRANSLATION_OPENROUTER_MODEL` and
`OPENROUTER_API_KEY`. Dense retrieval avoids loading the optional reranker.
Changing `EMBED_MODEL` requires a reboot and automatically rebuilds the index;
retrieval thresholds may need recalibration for a different embedding model.

To start with OpenRouter, set these values in Secrets:

```toml
LLM_PROVIDER = "openrouter"
OPENROUTER_API_KEY = "replace-with-your-key"
OPENROUTER_MODEL = "openai/gpt-4o-mini"
TRANSLATION_PROVIDER = "tutor"
LLM_MAX_TOKENS = "1200"
```

Choose a model ID available to your provider account. No training or model-weight
upload is needed. The provider receives retrieved course passages and conversation
context to generate responses.

## Costs and limits

Hosting and inference are separate. Your API account pays for tokens. Each question
can involve several API calls for checks, retries, and translation.
`LLM_MAX_TOKENS` caps individual outputs, not total spending. Set provider-side
usage controls or prepaid credit before sharing a funded public demo. The app
does not enforce a global budget or a per-user request quota.

The embedding model and Chroma still need RAM. The cloud dependency file installs
CPU-only PyTorch to avoid NVIDIA packages, but memory fit must be confirmed on
the deployed app. If it exceeds Community Cloud limits, move retrieval to a
hosted service or use a larger host.

## Persistent homework progress

Set `HOMEWORK_PROGRESS_DATABASE_URL` in Streamlit Secrets to a reachable
PostgreSQL database to keep resume codes through reboots and redeployments.
Use a connection URL such as `postgresql://user:password@host/database?sslmode=require`.
The database user needs permission to create and use the `tutor_homework_progress`
table. Set the same URL in a Docker or local deployment with the same course to
resume there using the same code.

Without a database, codes use the current server's disk. In Homework mode, open
**Resume saved progress** and use **Download progress backup** to keep a copy on
your device. Use **Restore backup** to continue from that file on any deployment
with the same course. You can also use this to move existing disk saves before
switching to PostgreSQL.

Official references: [deployment](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy),
[secrets](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management),
[dependencies](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/app-dependencies).
