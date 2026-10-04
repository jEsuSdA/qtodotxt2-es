# AGENTS.md

QTodoTxt2-es: Spanish fork of QTodoTxt2 — a PyQt5/QML GUI for `todo.txt` files. GPL3. Single-maintainer repo on `main`; commit messages are in Spanish, short, no conventional-commits prefix. No CI, linter, formatter, or typecheck is configured.

## Layout (two-level, non-obvious)

- Repo **root** holds only packaging/install helpers: `build-deb.sh`, `install-env.sh`, `install-sys.sh`, `uninstall.sh`, `qtodotxt-es.desktop`, `qtodotxt.png`, `requirements.txt`.
- The **actual application** lives in `qtodotxt-es/` (note: subdir name differs from the importable package name `qtodotxt2`).
  - `qtodotxt-es/qtodotxt2/` — Python package (`app.py`, `main_controller.py`, `kanban_controller.py`, `kanban_window.py`, `dashboard_window.py`, `filters_controller.py`, `lib/`, `qml/`).
  - `qtodotxt-es/bin/qtodotxt` — Linux launcher (adds parent dir to `sys.path`, calls `qtodotxt2.app.run()`). `qtodotxt.pyw` is the Windows launcher.
  - `qtodotxt-es/tests/`, `qtodotxt-es/i18n/`, `qtodotxt-es/setup.py`, `qtodotxt-es/pylupdate.py`, `qtodotxt-es/compile_rc.py`.

## Versioning — bump all three sites on every release

Versions follow `YYYYMMDD` (the release date). The version string is duplicated in three places with no single source of truth — **update all three together** when cutting a release:

1. `qtodotxt-es/qtodotxt2/qml/AboutBox.qml` — the `<p><b>Versión: YYYYMMDD</b></p>` block shown in the "Acerca de" dialog (F1). User-visible.
2. `build-deb.sh` — `VERSION="YYYYMMDD"` at the top; controls the `.deb` filename and package metadata.
3. `qtodotxt-es/setup.py` — `version="YYYYMMDD"`; pip/setuptools metadata.

Do not leave these out of sync. There is no test that guards consistency.

## Run the app

```bash
python3 qtodotxt-es/bin/qtodotxt [path/to/todo.txt]
# optional: -l DEBUG|INFO|WARNING|ERROR
```

Real entrypoint is `qtodotxt2/app.py:run()` (also the `setup.py` gui_scripts entry point). `app.py` forces `target_locale = "es_ES"` and loads translations from the relative path `../i18n`, so it depends on being launched from `bin/`.

## Dependencies — PyQt5 must come from the system, not pip

`requirements.txt` lists `PyQt5` + `python-dateutil`, but **do not `pip install PyQt5`**: the pip wheel lacks GTK theme integration. Install PyQt5 + QML modules via apt (`python3-pyqt5`, `python3-pyqt5.qtquick`, `qml-module-qtquick-controls`, `qml-module-qtquick-dialogs`, `qml-module-qtquick-layouts`, `qml-module-qtquick-window2`, `qml-module-qt-labs-settings`, ...). Only `python-dateutil` should come from pip. `install-env.sh` enforces this by creating the venv with `--system-site-packages` and `grep -v PyQt5` on requirements.txt.

## Tests (unittest)

Run from inside `qtodotxt-es/` so the `qtodotxt2` package is importable. Use offscreen for headless runs:

```bash
cd qtodotxt-es
QT_QPA_PLATFORM=offscreen python3 -m unittest tests.test_tasks tests.test_file tests.test_controller tests.test_kanban_sync
# single module / single test:
QT_QPA_PLATFORM=offscreen python3 -m unittest tests.test_tasks.TestTasks.test_priority
```

- **Passing suites** (42 tests): `tests.test_tasks` (19), `tests.test_file` (9), `tests.test_controller` (5), `tests.test_kanban_sync` (9 — guards the Kanban↔main-window sync contract; see Kanban section below).
- **`tests.test_htmlizer` is currently broken — 11 failures are expected.** The fork translated the invalid-date error strings to Spanish ("Fecha errónea, se esperaba yyyy-mm-dd...") but never updated the test expectations, which still assert the English text. The **app code is correct**; the tests are stale. Don't "fix" `task_htmlizer.py` to emit English — update the test expectations if you need a green suite.
- **Standalone scripts, NOT unittest `TestCase`s** (`unittest discover` won't run them):
  - `tests/test_kanban.py` — contains a hardcoded developer path (`/home/jesusda/work-in-progress/...`) and won't run elsewhere. Consider deleting or fixing if you touch it.
  - `tests/demo_kanban.py` — creates a temp `todo.txt` and opens a real Kanban window.
  - `tests/check_kanban_scenarios.py` — exercises special paths (external reload with new ids, dirty-flag on hidden window, repeated reopen, drag+reload mix, forced full-rebuild fallback). Prints `OK`/`FALLO` per scenario; exits non-zero on failure.
  - `tests/check_dashboard.py` — dashboard parity smoke test (see Dashboard section). Prints `OK`/`FALLO`; sandbox data only.
  - `tests/bench_kanban.py [n_tareas] [n_proyectos]` — Kanban benchmark (default 500/40). Use it **before and after** any perf-related change to the board.
- Fixtures: `tests/todo_valid.txt`, `tests/todo_test_output.txt`.

## Dashboard window (read-only parity panel)

`qtodotxt2/dashboard_window.py` is a second window with the same 17 blocks and formulas as the CLI dashboard (`/home/jesusda/Público/owncloud/todotxt/plugins/dashboard`) and the web dashboard — single spec: `todotxt/docs/dashboard-paridad.md`. Opened from the toolbar (`MainToolBar.qml` dashboardButton → `MainController.openDashboardView()`; icon registered in `qml/Theme/res.qrc`, recompile with `compile_rc.py` after qrc edits).

- **`openDashboardView` MUST keep its `@QtCore.pyqtSlot()`** — QML can only invoke slots; a plain Python method raises `TypeError: ... is not a function` when clicked (this was the original bug; `openKanbanView` set the pattern).
- **Strictly read-only**: data comes from `main_controller._file.tasks` plus a pure read of `done.txt` next to the todo file and the `.ice_recur_completed` sentinel. Auto-refresh every 30 s while visible (`showEvent`/`hideEvent`).
- **Intentional parity quirks** (replicate the CLI exactly, they are load-bearing for number equality):
  - inbox counts pending lines without a leading `([A-Z])` whose text does NOT contain the substring `"x 20"` (CLI grep quirk, e.g. "burofax 2024");
  - creation date is only the first 10 chars of the line — `"(X) 2024-..."` counts as sin-creación (antigüedad, creadas, estancado);
  - balance uses the documented formula for done.txt creations, which differs from the CLI by 1 in rare cases (the CLI awk has a `substr` off-by-one there);
  - block 13 (cuellos de botella) uses the **web/PHP semantics**; the CLI's awk is dead code that always prints "Sin cuellos de botella";
  - ties in foco/contextos/urgencias replicate the CLI `sort -rn` fallback: name DESC (sort twice: name desc, then stable by count).
- **No emojis**: Qt/DejaVu renders them as tofu. All display glyphs go through the module-level `SIMBOLOS` dict + `_nice()` (applied in `_card`/`_linea`), using plain BMP symbols from `/home/jesusda/base/templates/simbolos-en-texto-plano.txt`. If you add UI text, use only those glyphs or extend the dict.
- Test it with the standalone sandbox script: `QT_QPA_PLATFORM=offscreen python3 tests/check_dashboard.py` (asserts ~45 parity formulas; creates its own temp todo/done, never touches user data).

## Kanban architecture (read before touching kanban_*.py)

Priority → column mapping (fork-specific convention, not standard todo.txt): no priority → inbox (`NP`), `D` → soon, `C` → this month, `B` → this week, `A` → today. A task appears in **every** project block it belongs to (cards are duplicated across projects). Drag between columns changes the priority; drag onto `NP` removes it.

**Sync contract (bidirectional, instant) — protected by `tests.test_kanban_sync`; do not break it:**

- Kanban → main: `KanbanController.update_task_priority()` / `toggle_task_done()` mutate `task.text`, which emits `Task.modified` → `File.setModified(True)` → `fileModified(True)` → `MainController._fileModified` → `applyFilters()` refreshes the QML list. During this, `_self_modified=True` suppresses board rebuilds, and the board updates its widgets in place (`move_task_widget` / `update_task_widget`).
- Main → Kanban: `KanbanController` listens to `fileModified`, `fileExternallyModified` **and `filteredTasksChanged`**. The last one is what makes **new tasks** reach the board: `MainController.newTask()` deliberately does NOT emit `fileModified` (calling `applyFilters` inside it would break the inline-edit index it returns). Don't "fix" `newTask` — the `filteredTasksChanged` connection is the intended path.

**Rebuild pipeline:** triggers → `_schedule_rebuild` (ignores `fileModified(False)` = save-without-change; skipped while `_self_modified`) → `_request_rebuild` (window visible? → 250 ms debounce timer; hidden? → `_dirty` flag) → `_rebuild_now` → `_generate_kanban_data()` + `_signature()` compare (skip emit if unchanged) → `kanbanDataChanged` → `KanbanWindow._on_kanban_data_changed` → `_apply_data()` (differential) or `_refresh_board()` (full rebuild: first build, or any exception in the diff — logged and retried as full).

**Differential board invariants** (`KanbanWindow`):

- Per project block registries: `block._columns` (prio → `KanbanColumnWidget`), `block._cards` (task_id → widget, exactly one widget per task per block), `block._card_cols` (task_id → prio). The incremental paths `move_task_widget`/`update_task_widget` MUST keep these registries in sync (they do — keep it that way).
- `_card_pool` is a persistent free-list of recycled card widgets (cap `_card_pool_max = 1000`); `_obtain_card()`/`_recycle_card()` are the only ways in/out.
- `KanbanTaskWidget.update_data()` caches `_last_html` and `_last_style_key` and skips `setText`/`setStyleSheet` when nothing changed — **never call `setText`/`setStyleSheet` on cards directly**, and never restyle in loops; `setStyleSheet` is the single most expensive call here (re-polishes the widget and all children).
- `format_task_html()` (module-level in `kanban_window.py`) is the single task-text→HTML formatter, shared by widget and controller-side code. Payload dicts carry `text`/`priority`/`is_done`/`task_id`/`task_ref` — the widget derives HTML itself, so incremental mutations of `text` stay consistent.
- `task_id = str(id(task))` — **not stable across `File.load()`** (new Task objects). The diff handles this as remove+add via the pool; never persist or cache task ids outside a board cycle. If you need stable ids, that's a feature, not a refactor — add explicit UIDs to `Task`.
- `_signature()` must include every visually-relevant field (currently task_id, priority, is_done, text, per column, per project, in order). If `_generate_kanban_data()` payload grows, extend the signature too, or edits will stop refreshing the board.
- Full rebuild (`_refresh_board`) is the safety net and the first-build path. Keep it working: `test_kanban_sync` and `check_kanban_scenarios.py` force it explicitly.

**Perf rule of thumb** (measured with `bench_kanban.py`, 500 tasks/40 projects, offscreen): a full board rebuild costs ~2.3 s; the differential path after an edit costs ~70 ms (plus the intentional 250 ms debounce). `generate_kanban_data()` is ~2 ms — data generation is never the bottleneck, widget churn is. Never "optimize" by adding threads: Qt widgets must stay on the main thread.

## Generated / committed artifacts

- `qtodotxt2/qml/*.qmlc` are Qt-compiled QML bytecode **committed to git** — don't hand-edit; they're regenerated by Qt at runtime.
- `i18n/*.qm` are compiled translations, also committed.
- `qtodotxt2/__pycache__/*.pyc` are tracked (historical accident, kept in sync by runtime); `tests/__pycache__/` is NOT tracked — don't `git add` it.
- Release binaries (`qtodotxt-es_*.deb`, `.7z` archives) are committed at repo root by the maintainer. `build-deb.sh` regenerates the `.deb` (run from repo root; non-root is fine for building).

### Regenerating resources / translations (requires Qt tools)

- After editing `qtodotxt2/qml/Theme/res.qrc`, run `python3 qtodotxt-es/compile_rc.py` → regenerates `qtodotxt2/qTodoTxt_style_rc.py` via `pyrcc5`.
- Translations via `python3 qtodotxt-es/pylupdate.py <upd|clr|fix>` (`upd` update `.ts`, `clr` drop obsolete strings, `fix` compile `.qm` via `lrelease`). The `locale` variable is hardcoded to `es_ES` at the top of `pylupdate.py`. Requires `pylupdate5` + `lrelease`.
- Note: the README/`TRANSLATION.md` say the QML i18n module "appears not working"; the UI is translated **directly in the source code** rather than via `.ts`/`.qm` for the app strings.

## Install / package scripts (root, require root/sudo)

Three installation methods share `/opt/qtodotxt-es`; **only one can be installed at a time**. They detect each other: scripts abort/prompt if the `.deb` is installed, and the `.deb`'s `preinst` warns over script installs. A marker `/opt/qtodotxt-es/.install-method` (`deb`/`env`/`sys`) records which method owns the install.

- `build-deb.sh` — builds `qtodotxt-es_<version>_all.deb` (version hardcoded in script, see Versioning). Installs to `/opt/qtodotxt-es`, launcher `/usr/bin/qtodotxt-es` (with `QT_QPA_PLATFORMTHEME=gtk2` + `PYTHONDONTWRITEBYTECODE`, same as the venv launcher). Uses `--root-owner-group` (files end up root:root). Payload excludes `tests/`, `examples/`, screenshots, dev docs, venvs and `__pycache__`. `postinst` writes the method marker; `postrm` cleans leftover venv under `/opt/qtodotxt-es`.
- `install-env.sh` — installs to `/opt/qtodotxt-es` using an isolated venv (`--system-site-packages`) for pip deps + system PyQt5; launcher at `/usr/local/bin/qtodotxt-es`. Requires `python3-venv`; warns (doesn't install) if Qt apt deps are missing.
- `install-sys.sh` — installs to `/opt/qtodotxt-es` using only system apt packages (installs them via apt); launcher at `/usr/local/bin/qtodotxt-es`.
- `uninstall.sh` — universal: `dpkg -r qtodotxt-es` if the package is installed, then removes `/opt/qtodotxt-es`, BOTH launchers (`/usr/local/bin` and `/usr/bin`), desktop file and icon. Apt dependencies are preserved.
