#!/usr/bin/env python3
"""
Benchmark del modo Kanban.

Genera un todo.txt sintético y mide los costes clave del tablero:
  - apertura completa (openKanbanView)
  - generación de datos (_generate_kanban_data)
  - reconstrucción del tablero (_refresh_board)
  - ciclo edición -> rebuild con debounce (end-to-end)
  - alta de tarea nueva (end-to-end, sincronización Principal->Kanban)
  - filtro de proyectos + ajuste de alturas

Uso:
    QT_QPA_PLATFORM=offscreen python3 tests/bench_kanban.py [n_tareas] [n_proyectos]
"""

import argparse
import os
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import QApplication

from qtodotxt2.kanban_window import KanbanTaskWidget
from qtodotxt2.main_controller import MainController

PRIORITIES = ["(A) ", "(B) ", "(C) ", "(D) ", ""]
CONTEXTS = ["@casa", "@trabajo", "@llamadas", "@recado", ""]


def gen_todo(n_tasks, n_projects):
    lines = []
    for i in range(n_tasks):
        prio = PRIORITIES[i % len(PRIORITIES)]
        ctx = CONTEXTS[i % len(CONTEXTS)]
        # la mayoría de tareas a un proyecto; 1 de cada 7 a dos proyectos
        projects = ["+Proyecto{}".format(i % n_projects)]
        if i % 7 == 0:
            projects.append("+Proyecto{}".format((i + 1) % n_projects))
        if i % 11 == 0:
            line = "x 2026-01-01 {}Tarea sintetica {} {}{}".format(
                prio, " ".join(projects), ctx, " detalle-{}".format(i))
        else:
            line = "{}Tarea sintetica {} {}{}".format(
                prio, " ".join(projects), ctx, " detalle-{}".format(i))
        lines.append(line.strip())
    return "\n".join(lines) + "\n"


def timed(results, label):
    def deco(fn):
        def wrapped(*args, **kwargs):
            t0 = time.perf_counter()
            r = fn(*args, **kwargs)
            dt = (time.perf_counter() - t0) * 1000.0
            results[label] = dt
            print("  {:<44} {:>10.1f} ms".format(label, dt))
            return r
        return wrapped
    return deco


def wait_rebuild(counter, timeout_ms=5000):
    """Espera (procesando eventos) a la siguiente emisión de kanbanDataChanged."""
    target = counter[0] + 1
    waited = 0
    while counter[0] < target and waited < timeout_ms:
        QTest.qWait(10)
        waited += 10
    return waited


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("n_tasks", nargs="?", type=int, default=500)
    parser.add_argument("n_projects", nargs="?", type=int, default=40)
    cli = parser.parse_args()

    print("=" * 66)
    print("BENCHMARK KANBAN: {} tareas / {} proyectos".format(cli.n_tasks, cli.n_projects))
    print("=" * 66)

    results = {}
    app = QApplication.instance() or QApplication(sys.argv)

    fd, path = tempfile.mkstemp(suffix=".txt")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(gen_todo(cli.n_tasks, cli.n_projects))

    try:
        mc = MainController(argparse.Namespace(file=None, loglevel=["WARN"]))
        mc.open(path)

        @timed(results, "apertura openKanbanView()")
        def open_kanban():
            mc.openKanbanView()
            app.processEvents()
        open_kanban()

        kc = mc.kanban_controller
        win = mc.kanban_window
        counter = [0]
        kc.kanbanDataChanged.connect(lambda: counter.__setitem__(0, counter[0] + 1))

        n_cards = sum(len(block.findChildren(KanbanTaskWidget))
                      for block in win._project_widgets.values())
        print("  proyectos en tablero: {} | tarjetas: {}".format(
            len(win._project_widgets), n_cards))

        @timed(results, "generate_kanban_data()")
        def gen():
            kc._generate_kanban_data()
        gen()

        @timed(results, "_refresh_board() (rebuild completo)")
        def rebuild():
            win._refresh_board()
            app.processEvents()
        rebuild()

        @timed(results, "edicion -> rebuild end-to-end (debounce)")
        def edit_cycle():
            task = mc.allTasks[0]
            task.text = task.text + " @nueva"
            wait_rebuild(counter)
            app.processEvents()
        edit_cycle()

        @timed(results, "newTask -> kanban end-to-end (debounce)")
        def new_task_cycle():
            mc.newTask("(B) Tarea bench +ProyectoBench")
            wait_rebuild(counter)
            app.processEvents()
        new_task_cycle()

        @timed(results, "filtro proyecto + ajuste alturas")
        def filter_cycle():
            win.project_filter.setText("Proyecto1")
            QTest.qWait(250)
            win._adjust_columns_height_for_filter()
            app.processEvents()
            win.project_filter.setText("")
        filter_cycle()

        print("-" * 66)
        print("  {:<44} {:>10.1f} ms".format(
            "TOTAL (suma de fases)", sum(results.values())))
        print("=" * 66)
        return 0
    finally:
        try:
            if getattr(mc, "kanban_window", None) is not None:
                mc.kanban_window.close()
        except Exception:
            pass
        os.unlink(path)


if __name__ == "__main__":
    sys.exit(main())
