**THE OFFENSIVE LAYER**

This is the core layer in which combination of multiple tools act togeather to preform testing on the multiple models i.e AI Models, LLM's, RAG, with a future scope of ML, Neural Networks testing.

We are going to use Garak, PromptFoo, PyRIT tools for testing.

All the output's are pulled to a central database where the data is filtered, segrigated from the large amount of data that is generated after testing the model.

This segrigated data is then fed to scoring/verdict system where the final test results are produced.

These produced data will be fed into **LAYER3** for the further process.

## Setup & Run

### Prerequisites
- Ollama running locally with at least one model (`ollama pull llama3.2:3b`)
- garak and PyRIT each in their OWN Python venv (they need conflicting
  versions of `datasets`)
- Promptfoo installed separately (`brew install promptfoo`)

### Run
    pip install -r requirements.txt
    python3 run_ingest.py --clear        # ingest all three tools
    python3 run_ingest.py --tools garak  # or just one
    python3 scorer.py                    # honest scorer

`findings.db` is created locally on first run and is gitignored —
it is derived data, regenerate it rather than sharing it.

<img width="2720" height="1784" alt="xsignon_layer2_combine_pipeline" src="https://github.com/user-attachments/assets/8a0d7cd6-c6fd-44c3-94f1-670e4f02f1d1" />
