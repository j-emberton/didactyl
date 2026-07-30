# Didactyl

Didactyl is a Python-native engine for building repository-based, exercise-driven tutorials.

You provide the teaching content; Didactyl handles repository scaffolding, exercise checks, learner progress and a terminal interface.

> [!NOTE]
> Didactyl is currently at an early stage. The core workflow works, but some APIs and the course format may change before the first stable release.

## Current functionality

Didactyl currently supports:

* creating a tutorial repository scaffold;
* adding exercises from the command line;
* defining courses in `tutorial.toml`;
* starter files, checks, hints, lessons and reference solutions;
* running individual exercises or the whole course;
* tracking learner progress locally;
* invalidating progress when completed files change;
* automatically rerunning the current exercise after edits;
* resetting exercises to their starter content;
* a full-screen terminal interface;
* tutorial-specific commands such as `uv run my-tutorial`.

## Install

Add Didactyl to your tutorial project’s development dependencies:

```bash
uv add --dev didactyl
```

## Create a tutorial

From your tutorial repository:

```bash
uv run didactyl init . --title "My Tutorial"
```

Add `--example` to include a small example exercise:

```bash
uv run didactyl init . --title "My Tutorial" --example
```

Didactyl creates the following tutorial structure:

```text
tutorial/
├── exercises/   # Files learners edit
├── starters/    # Clean copies used for resets
├── checks/      # Pytest checks
├── solutions/   # Reference solutions
├── lessons/     # Companion explanations
└── README.md
```

Course configuration and exercise ordering live in `tutorial.toml`.

## Add an exercise

```bash
uv run didactyl add-exercise first-steps --title "First steps"
```

Didactyl creates the exercise, starter, check, solution and lesson files and adds the exercise to `tutorial.toml`.

You can then replace the generated placeholders with your own teaching content and checks.

## Run the tutorial

Start the terminal interface:

```bash
uv run didactyl
```

Individual commands are also available:

```bash
uv run didactyl list
uv run didactyl run first-steps
uv run didactyl hint first-steps
uv run didactyl solution first-steps
uv run didactyl reset first-steps
uv run didactyl check-all
uv run didactyl verify
```

## Give your tutorial its own command

Didactyl can sit behind a command named after your tutorial, so learners do not need to interact with the generic `didactyl` command.

Add a project script to your tutorial repository’s `pyproject.toml`:

```toml
[project.scripts]
my-tutorial = "didactyl._cli:course_main"
```

Refresh the project environment:

```bash
uv sync
```

You can now run:

```bash
uv run my-tutorial
```

Didactyl subcommands work through the same project script:

```bash
uv run my-tutorial list
uv run my-tutorial run first-steps
uv run my-tutorial check-all
```

The current entry point uses the private `didactyl._cli` module. It works today, but will be replaced by a stable public entry point before the API is considered stable.

## Develop your tutorial

Run the generated repository tests with:

```bash
uv run pytest
```

The basic authoring workflow is:

```text
Create a tutorial
→ add exercises
→ replace the generated content
→ run the checks
→ give the tutorial its own command
```

## Planned development

The following features are planned but are not yet part of the stable public contract.

### Stable public APIs

The immediate priority is to stabilise:

* the `tutorial.toml` format;
* the course, exercise and progress models;
* public functions for running a tutorial;
* a supported public entry point for tutorial-specific commands;
* compatibility and migration behaviour between course versions.

The planned project-script configuration will look more like:

```toml
[project.scripts]
my-tutorial = "didactyl:run_course_cli"
```

### Stronger authoring tools

Planned improvements include:

* a friendly `doctor` command for diagnosing course problems;
* stronger `verify` checks for continuous integration;
* clearer errors for missing files and invalid configuration;
* better handling of duplicate exercise names and paths;
* more flexible scaffold generation;
* documented public scaffolding functions.

### Learner experience

The terminal interface will continue to improve with:

* clearer failure output;
* more reliable automatic reruns;
* smoother progression between exercises;
* better hint, solution and reset handling;
* improved terminal resizing and shutdown;
* clearer completion feedback.

### Platform and release support

Before a stable release, the project is expected to add:

* releases through PyPI;
* Python 3.12–3.14 testing;
* Linux, macOS and Windows CI;
* clean-install tests using the built package;
* automated versioning and changelogs;
* a documented compatibility policy.

### Real-world validation

Didactyl will be developed alongside practical internal tutorial projects at the Whittle Laboratory and a small example course used for integration testing.

These real tutorials will guide the public API and help avoid adding speculative abstractions.

## Project direction

Didactyl is intended to remain a small, composable tutorial engine rather than becoming a large educational platform.

Web interfaces, cloud progress synchronisation, remote execution and a general plugin framework are not immediate priorities.
