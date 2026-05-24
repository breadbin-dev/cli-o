# clio

**Command Line Interface — Online.** Deploy data science tools to the web without any UI work. Cli-o gives you a flexible, interactive interface accessible from a browser.
Simply write a standard python component with functions that return text, dataframes, charts, and Cli-o makes it available in a CLI driven web page.

## Installation

```bash
pip install "git+https://github.com/breadbin-dev/cli-o.git#subdirectory=clio-py"
```

Or pin to a specific tag:

```bash
pip install "git+https://github.com/breadbin-dev/cli-o.git@v1.0.0#subdirectory=clio-py"
```

### In `pyproject.toml`

```toml
dependencies = [
    "clio @ git+https://github.com/breadbin-dev/cli-o.git#subdirectory=clio-py",
]
```