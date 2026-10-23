# Risk analysis

| # | Risk | Probability | Impact | Mitigation | Status |
| --- | --- | --- | --- | --- | --- |
| R1 | The assigned maze package crashes or misbehaves (e.g. recursion limit on big mazes, prints, odd sizes) | High (seen: RecursionError at 60×45) | High | Adapter raises the recursion limit while generating, clamps sizes to 45×35, captures prints, validates output, retries 3 seeds, then shows an error screen | Mitigated |
| R2 | Package is re-installed / slightly different at the defence | Medium | High | Only the public constructor and `maze` property are used, isolated in `maze.py` | Mitigated |
| R3 | Config changed live during the defence with invalid values | High | Medium | Every key validated, clamped or defaulted with a warning; tests cover bad types and ranges | Mitigated |
| R4 | A crash (traceback) during review = project fails | Medium | Very high | Top-level catch in `cli.main`, MazeError screen, highscore I/O never raises, unit tests | Mitigated |
| R5 | Levels impossible within the time limit | Medium | Medium | Time limits scale with maze size (120–240 s), timer refill cheat, play-testing | Monitor |
| R6 | Generated mazes have dead ends where ghosts trap the player | Medium | Low | `PERFECT=False` adds loops; ghosts avoid U-turns; frightened ghosts slow down | Accepted |
| R7 | Packaged build missing files (fonts, generator) | Medium | High | Spec lists the hidden import; build smoke-tested by running the binary | Mitigated on Linux; test other OS |
| R8 | PyInstaller cannot cross-compile | Certain | Medium | Build on each target OS; Linux build done first | Open |
| R9 | Not able to explain AI-generated code at the defence | Medium | Very high | Read every module, run the tests, practise small live modifications | Open |
| R10 | Running out of time before the deadline | Medium | High | Milestones each end in a playable state; nice-to-haves (sound) dropped first | Monitor |
