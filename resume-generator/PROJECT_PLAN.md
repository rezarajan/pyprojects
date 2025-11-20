# Harvard Resume Generator Project Overview

## 1. Project Plan

### 1.1 Scope

The project generates a Harvard-style resume from a TOML input file,
producing HTML and PDF outputs, styled with internal CSS and without
external libraries.

### 1.2 Goals

-   Provide deterministic, testable resume generation.
-   Allow declarative input using TOML.
-   Produce HTML and PDF outputs in the Harvard template layout.

### 1.3 Sprints

**Sprint 1:** Define TOML schema, create parser, unit tests\
**Sprint 2:** Implement HTML generation with Jinja2, build CSS\
**Sprint 3:** Implement PDF generation using WeasyPrint\
**Sprint 4:** Add validation, error handling, extensibility\
**Sprint 5:** Final testing, packaging, CLI

## 2. Trade-Off Analysis: JSON vs YAML vs TOML

### JSON

-   Pros: deterministic, simple
-   Cons: no comments, noisy for users\
    **Assessment:** safe but not user-friendly.

### YAML

-   Pros: very readable, comments supported
-   Cons: parsing ambiguity, indentation errors\
    **Assessment:** risky for deterministic résumé rendering.

### TOML

-   Pros: deterministic, readable, comments, good for configs
-   Cons: slightly verbose for deep nesting\
    **Assessment:** **Best choice** for this project.

## 3. Architecture & Stack Choices

### 3.1 Overview

**Input:** TOML → Python dict\
**Processing:** Jinja2 HTML templates\
**Output:** HTML → WeasyPrint PDF

### 3.2 Components

-   TOML loader (`tomllib`)
-   Template engine: **Jinja2**
-   HTML renderer with internal CSS
-   PDF generator: **WeasyPrint**
-   CLI wrapper

### 3.3 Rationale

-   Python ecosystem provides simple TOML handling and powerful
    templating.
-   Jinja2 enables clear separation between layout and data.
-   WeasyPrint produces consistent academic-style PDFs with minimal
    config.
