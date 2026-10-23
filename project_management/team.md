# Team organisation

Fill this in with the real team information before the defence.

| Member (login) | Role / main areas |
| --- | --- |
| <your_42_login> | |

## How decisions are made
- Technical choices are written in `analysis_and_choices.md`, with the
  reason, before or right after they are implemented.
- Every change goes through a branch and a pull request; `make lint` and
  `make test` must pass before merging.

## Blocking points and conflicts

| Date | Problem | How it was solved |
| --- | --- | --- |
| | The maze generator crashes on big mazes (recursion) | Handled in the adapter without modifying the package (see risks R1) |
