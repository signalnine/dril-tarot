# Dril-Tarot Project Structure

This document explains how this project is organized and its relationship to semantic-tarot.

## Repository Structure

```
dril-tarot/
├── semantic-tarot/          # Git submodule - core tarot functionality
│   ├── cards.json          # Tarot card data and ASCII art
│   ├── interpretations.json # Four interpretation systems
│   ├── card_embeddings.json # Pre-generated card embeddings
│   ├── tarot.py            # Interactive tarot reader
│   ├── search_cards.py     # Semantic search tool
│   └── generate_embeddings.py
│
├── data/                    # Dril-specific data files
│   ├── driltweets.csv      # ~8,900 dril tweets corpus
│   ├── dril_tweet_embeddings.json # Cached embeddings (370MB, gitignored)
│   └── card_dril_mapping.json # Generated card-to-tweet matches
│
├── docs/plans/              # Design documentation
│   ├── 2025-12-12-dril-tweet-matcher-design.md
│   └── 2025-12-12-dril-tarot-gallery-design.md
│
├── match_dril_tweets.py    # Main matching script
├── requirements.txt         # Python dependencies
└── README.md               # Project documentation
```

## What is semantic-tarot?

The `semantic-tarot` directory is a **git submodule** pointing to the [semantic-tarot](https://github.com/signalnine/semantic-tarot) project. This is a standalone tarot reading application that provides:

- 78-card tarot deck with ASCII art
- 4 interpretation systems (Traditional, Crowley, Jungian, Modern)
- Vector embeddings for semantic search
- Interactive CLI tarot reader

## Why the Separation?

The dril-tarot project extends semantic-tarot with absurdist humor by matching dril tweets to cards. Keeping them separate:

1. **Preserves semantic-tarot** as a clean, standalone tarot project
2. **Makes dril-tarot reusable** - could work with other tweet corpora
3. **Clear dependencies** - dril-tarot depends on semantic-tarot, not vice versa
4. **Independent evolution** - both projects can develop separately

## Working with Submodules

### First-time Clone

```bash
# Clone with submodules
git clone --recursive https://github.com/yourusername/dril-tarot.git

# Or if already cloned
git submodule update --init --recursive
```

### Updating semantic-tarot

```bash
cd semantic-tarot
git pull origin master
cd ..
git add semantic-tarot
git commit -m "Update semantic-tarot submodule"
```

## File Paths in Code

The `match_dril_tweets.py` script references:
- `semantic-tarot/cards.json` - Tarot card definitions
- `semantic-tarot/interpretations.json` - Card interpretations
- `semantic-tarot/card_embeddings.json` - Pre-generated embeddings
- `data/driltweets.csv` - Dril tweets corpus
- `data/card_dril_mapping.json` - Output matches

Always run scripts from the repository root (`/home/gabe/dril-tarot/`).

## Development Workflow

1. Work on dril-specific features in `dril-tarot/`
2. If you need to modify semantic-tarot:
   - Make changes in the submodule directory
   - Commit in semantic-tarot repository
   - Update submodule reference in dril-tarot
3. Keep dril data in `data/` directory
4. Keep dril scripts in repository root

## Migration Notes

This project was extracted from semantic-tarot on 2025-12-12:
- All dril-related commits were removed from semantic-tarot
- Dril files moved to this new repository
- semantic-tarot added as git submodule
- File paths updated to reference submodule
