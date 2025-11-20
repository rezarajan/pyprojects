project:
  name: harvard-resume-generator
  description: |
    A Python-based command-line application that generates Harvard-style
    resumes from a declarative TOML input file. Produces HTML and PDF outputs
    using Jinja2 templates and WeasyPrint. Template, model, and rendering
    layers must be modular and testable. Output must visually match the Harvard
    resume style.

  goals:
    - Deterministic, reproducible resume output
    - Pure HTML generation with embedded CSS (no external assets)
    - PDF generation through WeasyPrint
    - Strict input validation with clear error messages
    - Clean separation between parsing, modeling, templating, and rendering
    - CLI-driven workflow
    - Full testability (unit + snapshot)

  input_format:
    type: "TOML"
    parser: "tomllib (Python 3.11+) or tomli for <3.11"
    description: "Declarative structured resume content"

  runtime_stack:
    language: "Python"
    minimum_version: "3.11"
    libraries:
      - name: "jinja2"
        purpose: "HTML templating"
      - name: "weasyprint"
        purpose: "HTML → PDF rendering"
      - name: "tomli"
        condition: "required if Python < 3.11"
      - name: "python-dateutil"
        optional: true
        purpose: "Date normalization and formatting utilities"
    dev_libraries:
      - pytest
      - pytest-cov
      - ruff
      - mypy (optional)

  cli:
    command: "resume-gen"
    entrypoint: "src/resume_generator/cli/main.py"
    arguments:
      - name: "input"
        type: "file"
        required: true
      - name: "--html"
        type: "file"
        required: false
      - name: "--pdf"
        type: "file"
        required: false
      - name: "--template"
        type: "string"
        default: "harvard"
      - name: "--verbose"
        type: "flag"
    behavior:
      - If neither --html nor --pdf is given, generate both
      - Validate input before rendering
      - Print user-friendly errors

  directory_structure:
    root:
      - pyproject.toml
      - README.md
      - LICENSE
      - Makefile (optional)
      - src/
      - tests/
      - examples/

    src:
      resume_generator:
        - "__init__.py"
        - "cli/"
        - "core/"
        - "render/"
        - "templates/"
        - "utils/"

    cli:
      - "__init__.py"
      - "main.py"

    core:
      - "__init__.py"
      - "loader.py"
      - "model.py"
      - "validator.py"
      - "exceptions.py"

    render:
      - "__init__.py"
      - "html_renderer.py"
      - "pdf_renderer.py"
      - "postprocess.py"

    templates:
      harvard:
        - "base.html.j2"
        - "styles.css.j2"
        - "components/"
      components:
        - "header.html.j2"
        - "education.html.j2"
        - "experience.html.j2"
        - "skills.html.j2"
        - "projects.html.j2"
        - "leadership.html.j2"

    utils:
      - "__init__.py"
      - "fs.py"
      - "formatting.py"
      - "logging.py"
      - "toml_tools.py"

    tests:
      - "test_loader.py"
      - "test_validator.py"
      - "test_html_renderer.py"
      - "test_pdf_renderer.py"
      - fixtures/
      - snapshots/

  module_responsibilities:
    loader.py:
      - Load TOML from file
      - Handle errors: unreadable file, invalid TOML
      - Convert TOML → Python dict
      - Normalize fields (strip whitespace, unify lists)
    model.py:
      - Define dataclasses representing:
        - Resume
        - Section
        - Entry
        - Bullet
      - Provide helper methods:
        - .from_dict()
        - .validate()
    validator.py:
      - Enforce required fields (name, education)
      - Enforce formats for dates and sections
      - Raise ValidationError with contextual messages
    html_renderer.py:
      - Initialize Jinja2 environment
      - Load templates from templates/harvard/
      - Render HTML from model data
      - Inject CSS inline
    pdf_renderer.py:
      - Convert HTML → PDF using WeasyPrint
      - Configure margins and DPI
    postprocess.py:
      - Optional cleanup (whitespace, HTML minify)
    main.py:
      - Parse CLI arguments
      - Call loader → validator → html_renderer → pdf_renderer
      - Write output files
      - Display messages/errors

  testing_strategy:
    - Unit tests for TOML loader
    - Unit tests for data model construction
    - Validation tests for incorrect input
    - Snapshot tests for HTML
    - Visual equivalence tests for PDF (text/structural)
    - CLI integration tests

  future_extensions:
    - Multiple templates (modern, tech, minimal)
    - Resume preview server
    - Support LinkedIn and JSON Resume input formats
    - Plugin system for new renderers
