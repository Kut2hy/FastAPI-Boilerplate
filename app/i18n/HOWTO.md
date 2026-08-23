Commands for your Babel workflow.

**0. Install Babel** (it's not in `pyproject.toml`, so only if missing — it may come transitively with Jinja2):

```bash
pip install Babel
```

**1. Extract translatable strings into a .pot template:**

```bash
pybabel extract -F app/i18n/babel.cfg -o app/i18n/locales/messages.pot .
```

**2. Initialize catalogs for each language** (first time only, per `config.py` you have `en` and `cs`):

```bash
pybabel init -i app/i18n/locales/messages.pot -d app/i18n/locales -l en
pybabel init -i app/i18n/locales/messages.pot -d app/i18n/locales -l cs
```

**3. Update existing catalogs after re-extracting** (step 1 again, then):

```bash
pybabel update -i app/i18n/locales/messages.pot -d app/i18n/locales
```

**4. Compile to .mo files** (what the app actually loads at runtime):

```bash
pybabel compile -d app/i18n/locales
```