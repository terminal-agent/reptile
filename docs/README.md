# Documentation

We recommend new contributors to start from writing documentation, which helps you quickly understand the Annotation codebase.
Most documentation files are located under the `docs/` folder.

## Quick Start

### Install Dependency

```bash
apt-get update && apt-get install -y pandoc parallel retry
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### Add New Documentation

You can add a markdown file to the `docs` folder and add the file to the `index.rst` file.

```bash
# build html
make html

# serve this thml for viewing
make serve
```
