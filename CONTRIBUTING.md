# Contributing

Thank you for your interest in contributing to the Community Energy Orchestrator! This guide covers how to submit changes. For dev environment setup, project structure, code style, testing, and CI/CD details, see the [Development Guide](docs/DEVELOPMENT.md).

---

## Table of Contents

- [Getting Started](#getting-started)
- [Branching](#branching)
- [Making Changes](#making-changes)
- [Before You Push](#before-you-push)
- [Submitting a Pull Request](#submitting-a-pull-request)
- [Commit Messages](#commit-messages)

---

## Getting Started

1. Fork the repository on GitHub.
2. Clone your fork and set up the development environment:

   ```bash
   git clone https://github.com/YOUR_USERNAME/community-energy-orchestrator.git
   cd community-energy-orchestrator
   uv sync --all-extras
   ```

   See the [Development Guide](docs/DEVELOPMENT.md) for full setup instructions including the dev container option.

---

## Branching

Create feature branches from `dev`:

```bash
git checkout dev
git pull origin dev
git checkout -b your-feature-name
```

---

## Making Changes

1. Make your changes on your feature branch.
2. Run checks frequently during development to see all issues at once:

   ```bash
   make dev-check
   ```

3. Add or update tests for any changed behaviour. See the [Development Guide — Testing](docs/DEVELOPMENT.md#testing) for conventions.

---

## Before You Push

Run the same strict checks that CI will run:

```bash
make fix-all
```

This will:

1. Auto-format code with black and isort.
2. Run pylint and mypy (stops on first failure).
3. Run all tests with coverage (stops on first failure).

**This must pass cleanly before you push.** If it fails, fix the issues and run again.

> **Tip:** If you want to see all issues at once instead of stopping on the first failure, use `make dev-check` during development, then switch to `make fix-all` when you're ready to push.

---

## Submitting a Pull Request

1. Push your branch to your fork.
2. Open a pull request against the `dev` branch.
3. CI will automatically run all checks on your PR. If `make fix-all` passes locally, CI should pass too.
4. Respond to any review feedback and push follow-up commits to your branch.

---

## Commit Messages

- Keep the first line under 72 characters.
- Reference issue numbers where applicable (e.g. `Fix #42`).
