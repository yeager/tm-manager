# Translation Memory Manager

A GTK4/Adwaita application for managing local Translation Memory files (.tmx).

![License](https://img.shields.io/github/license/yeager/tm-manager)

## Features

- Open and create TMX files
- Search translation memory with fuzzy matching
- Import from .po, .ts, .xliff to TMX
- Export TMX to other formats
- View statistics (segment count, language pairs)
- Filter by language, project, date
- Edit individual segments
- Merge two TMX files
- Modern Adwaita UI with search and filtering

## Installation

### From .deb package

```bash
sudo dpkg -i tm-manager_0.1.0_all.deb
sudo apt-get install -f
```

### From source

```bash
pip install .
```

## Dependencies

- Python 3.10+
- GTK 4
- libadwaita
- PyGObject

## Usage

```bash
tm-manager
```

Or open a TMX file directly:

```bash
tm-manager /path/to/file.tmx
```

## 🌍 Contributing Translations

Help translate this app into your language! All translations are managed via Transifex.

**→ [Translate on Transifex](https://app.transifex.com/danielnylander/tm-manager/)**

### How to contribute:
1. Visit the [Transifex project page](https://app.transifex.com/danielnylander/tm-manager/)
2. Create a free account (or log in)
3. Select your language and start translating

### Currently supported languages:
Arabic, Czech, Danish, German, Spanish, Finnish, French, Italian, Japanese, Korean, Norwegian Bokmål, Dutch, Polish, Brazilian Portuguese, Russian, Swedish, Ukrainian, Chinese (Simplified)

### Notes:
- Please do **not** submit pull requests with .po file changes — they are synced automatically from Transifex
- Source strings are pushed to Transifex daily via GitHub Actions
- Translations are pulled back and included in releases

New language? Open an [issue](https://github.com/yeager/tm-manager/issues) and we'll add it!
## License

GPL-3.0 — see [LICENSE](LICENSE) for details.

## Author

Daniel Nylander <daniel@danielnylander.se>
