# Contributing

This app is part of [Trivena Cloud](https://github.com/TrivenaCloud).

**Do not invent a custom setup.** Use the shared developer toolchain and docs:

→ **https://github.com/TrivenaCloud/trivena-development**

Especially:

| Doc | URL |
|-----|-----|
| Getting started | https://github.com/TrivenaCloud/trivena-development/blob/main/docs/GETTING_STARTED.md |
| CLI reference | https://github.com/TrivenaCloud/trivena-development/blob/main/docs/CLI_REFERENCE.md |
| Contributing workflow | https://github.com/TrivenaCloud/trivena-development/blob/main/docs/CONTRIBUTING_WORKFLOW.md |
| Apps catalog | https://github.com/TrivenaCloud/trivena-development/blob/main/docs/APPS_CATALOG.md |
| Staging & environments | https://github.com/TrivenaCloud/trivena-development/blob/main/docs/STAGING_AND_ENVIRONMENTS.md |
| Troubleshooting | https://github.com/TrivenaCloud/trivena-development/blob/main/docs/TROUBLESHOOTING.md |

## Quick path

```bash
uv tool install --from git+https://github.com/TrivenaCloud/trivena-development.git trivena-dev
gh auth login
trivena-dev doctor
trivena-dev setup
trivena-dev work <app-key> -n short-description   # see catalog for keys
trivena-dev test
trivena-dev pr
```

- Branches: `dev/<github-user>/<slug>`
- PRs need **1** code-owner approval (`@khadeem100`) and green **`lint / lint`**
- Staging: https://staging.trivena.tech
