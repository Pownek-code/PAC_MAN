# Project management

This folder records how the project was driven. Each document is meant to
be updated as the project moves forward.

| Document | Content |
| --- | --- |
| [planning.md](planning.md) | Milestones, Kanban board and actual progress |
| [analysis_and_choices.md](analysis_and_choices.md) | Subject analysis and technical decisions |
| [risks.md](risks.md) | Risk analysis and mitigations |
| [acceptance_tests.md](acceptance_tests.md) | Acceptance test plan, results, bugs found and fixed |
| [team.md](team.md) | Team organisation, decisions, blocking points |

## Approach

The project follows short, incremental milestones. Each milestone ends with
a playable or testable state, and `make lint` and `make test` pass:

1. Subject analysis: requirements checklist and architecture sketch.
2. Logic core without graphics: config, maze adapter, rules (unit tested).
3. Graphics and scenes: menus, board, HUD, pause, end screens.
4. Theme and polish: Dune art direction, balancing.
5. Packaging: PyInstaller spec, itch.io page.
6. Documentation and review: README, these documents, peer review.

Work is tracked on the Kanban board in `planning.md`, mirrored in GitHub
issues/PRs when useful. Each feature is developed on a branch and merged
through a pull request.
