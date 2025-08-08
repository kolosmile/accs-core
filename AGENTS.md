# AGENTS.md

## 1) Dokumentáció (docstrings & modul README)

* **Stílus:** Google-style docstring (PEP257 kompatibilis).
* **Kötelező:**

  * Publikus függvények/metódusok.
  * Publikus osztályok és Pydantic modellek.
  * Modul szint (rövid leírás + fontos megjegyzések).
* **Tartalom:** *miért* (intent), bemenetek (egységek/korlátok), visszatérés (alak/sorrend), kivételek, mellékhatások.

**Függvény docstring minta**

```python
def claim_tasks(service: str, limit: int) -> list[JobTask]:
    """Selects and claims runnable tasks for a service.

    Args:
        service: Logical service name (e.g. "renderer").
        limit: Upper bound on the number of tasks to claim (must be > 0).

    Returns:
        Tasks ordered by global job sequence; length <= limit.

    Raises:
        ValueError: If limit <= 0.
    """
```

**Osztály / modell docstring minta**

```python
class JobTask(BaseModel):
    """Unit of work belonging to a Job.

    Notes:
        - Status transitions must follow TaskStatus FSM.
        - Collections use default_factory to avoid shared mutable defaults.
    """
```

**Pydantic mezők dokumentálása**

```python
class WorkflowStep(BaseModel):
    key: str = Field(..., description="Stable step key.")
    service: str = Field(..., description="Service name that executes this step.")
    depends_on: list[str] = Field(default_factory=list, description="Predecessor step keys.")
```

> **Pydantic verzió:**
>
> * Ha `pyproject.toml` Pydantic **v2** → használd `model_dump()`/`model_dump_json()` és `Field(..., description="...")`.
> * Ha **v1** → `.dict()`/`.json()`; a docstring és Field-leírás ugyanaz marad.

---

## 2) Kommentek

* **Alapelv:** a komment a **miért**-et magyarázza (invariáns, döntés okai, locking/backoff ok), nem a kód triviális tartalmát.
* **Rövid címkék:**

  * `TODO(owner): … [#issue]` – feladat
  * `FIXME: …` – ismert hiba/korlát, van megoldási terv
  * `HACK: …` – ideiglenes workaround + kivezetési terv
  * `NOTE: …` – fontos kontextus/előfeltétel

**Példák**

```python
# NOTE: FOR UPDATE SKIP LOCKED to avoid agent contention; order by jobs.order_seq is required.
# TODO(kristof): Replace ad-hoc backoff with exponential policy (#142)
# HACK: Keep v1 compatibility until settings migrate; remove after v2 cutover.
```

---

## 3) Lint és formázás

* **Egy eszköz:** Ruff (lint + format). Ne használj külön Black-et.
* **Importok:** stdlib → third-party → local, üres sorokkal; **nincs** wildcard import.
* **Stringek:** f-string preferált (SQL kivétel: mindig bind paraméter).
* **Sorhossz:** ruff-format alapértelmezett (nem kényszerítünk kézi sortörést, ha nem kell).

**`pyproject.toml` – Ruff beállítás minta**

```toml
[tool.ruff]
target-version = "py311"

[tool.ruff.lint]
select = ["E","F","B","UP","I","N","PTH","D","C90"]
ignore = [
  "D105",  # Missing docstring in magic method
  "D107",  # Missing docstring in __init__
]
mccabe.max-complexity = 10

[tool.ruff.lint.pydocstyle]
convention = "google"

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
line-ending = "lf"
```

**Pre-commit (kötelező)**

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.6.9
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
```

**Típusellenőrzés (mypy) – része a minőségi kapunak**

```ini
# mypy.ini
[mypy]
python_version = 3.11
warn_unused_ignores = True
warn_redundant_casts = True
warn_unreachable = True
disallow_incomplete_defs = True
no_implicit_optional = True
strict_equality = True
```

---

## 4) Pydantic-specifikus szabályok (mindig tartsd be)

* **Kollekciós defaultok:** *mindig* `Field(default_factory=list|dict|set)`.
* **Enum** minden lezárt értékkészletre (státuszok, típusok).
* **Szerializáció:** v2 → `model_dump()`; v1 → `.dict()`. Ne ad-hoc kézzel építs dict-et.
* **Validátorok:** invariáns/formaellenőrzés (üzleti logika ne itt legyen).
* **Határvédelem:** DB/API/raw → **először modellbe töltsd**, azzal dolgozz tovább.

---

## 5) Minimális tesztelési elv (a lint részeként ellenőrizhető)

* Adj **docstringet** minden publikus szimbólumhoz (Ruff `D` szabályok figyelik).
* Tarts **mutable default** tesztet (két példány izolációja) az érintett modellekhez.

---

**Követés:** minden PR csak akkor zöld, ha **Ruff (lint+format)** és **mypy** zöld, és a docstring-szabályok teljesülnek.
