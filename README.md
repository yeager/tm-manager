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

## Translation

Translation is managed via [Transifex](https://app.transifex.com/danielnylander/tm-manager/).

## License

GPL-3.0 — see [LICENSE](LICENSE) for details.

## Author

Daniel Nylander <daniel@danielnylander.se>
