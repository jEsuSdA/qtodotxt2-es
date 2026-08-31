#!/usr/bin/env python3
"""Verificación de caminos especiales del Kanban (offscreen)."""
import argparse
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import QApplication

from qtodotxt2.kanban_window import KanbanTaskWidget
from qtodotxt2.main_controller import MainController

LINES = "(A) Alfa +P1\n(B) Beta +P1\n(C) Gamma +P2\nDelta\n"

app = QApplication.instance() or QApplication(sys.argv)
fd, path = tempfile.mkstemp(suffix=".txt")
with os.fdopen(fd, "w", encoding="utf-8") as f:
    f.write(LINES)

ok = True
try:
    mc = MainController(argparse.Namespace(file=None, loglevel=["WARN"]))
    mc.open(path)
    mc.openKanbanView()
    app.processEvents()
    win, kc = mc.kanban_window, mc.kanban_controller

    def integrity():
        data = kc.kanbanData
        assert set(win._project_widgets) == {
            k for k, v in data.items()
            if not (k == "(Sin Proyecto)" and not any(v["tasks"].values()))
        }, "bloques != datos"
        for name, block in win._project_widgets.items():
            assert len(block._cards) == len(block.findChildren(KanbanTaskWidget)), \
                "registro/widgets desincronizados en " + name
            for tid in block._cards:
                assert block._cards[tid].task_id == tid

    # 1) recarga externa: todos los ids cambian
    mc.open(path)
    QTest.qWait(400)
    app.processEvents()
    integrity()
    print("OK  recarga externa (ids nuevos)")

    # 2) dirty-flag: ocultar, editar, reabrir
    win.hide()
    assert not win.isVisible()
    task = mc.allTasks[3]  # Delta
    task.text = "(D) Delta +P2"
    QTest.qWait(400)  # el debounce dispara pero la ventana está oculta
    assert kc._dirty, "no se marcó dirty con la ventana oculta"
    blocks_before = len(win._project_widgets)
    win.show()
    app.processEvents()
    QTest.qWait(400)
    # la bandeja vacía desaparece legítimamente; lo que debe cumplirse es
    # que el tablero coincide exactamente con los datos efectivos
    assert "P2" in kc.kanbanData, "el cambio hecho oculto no llegó al tablero"
    integrity()
    print("OK  dirty-flag oculto->reabrir (bloques {} -> {})".format(
        blocks_before, len(win._project_widgets)))

    # 3) aperturas/cierres repetidos de openKanbanView
    for _ in range(5):
        mc.openKanbanView()
        app.processEvents()
    integrity()
    print("OK  openKanbanView repetido")

    # 4) drag + recarga + drag (mezcla de ids)
    t = mc.allTasks[0]
    kc.update_task_priority(str(id(t)), "B")
    mc.open(path)  # recarga: ids nuevos otra vez
    QTest.qWait(400)
    app.processEvents()
    t2 = [x for x in mc.allTasks if "Alfa" in x.text][0]
    kc.update_task_priority(str(id(t2)), "C")
    QTest.qWait(400)
    app.processEvents()
    integrity()
    print("OK  drag + recarga + drag")

    # 5) el fallback (rebuild completo) sigue operativo
    win._board_built = False
    win._on_kanban_data_changed()
    app.processEvents()
    integrity()
    assert win._board_built
    print("OK  fallback rebuild completo")

    print("\nTODOS LOS ESCENARIOS OK")
except AssertionError as e:
    ok = False
    print("FALLO:", e)
finally:
    try:
        mc.kanban_window.close()
    except Exception:
        pass
    os.unlink(path)

sys.exit(0 if ok else 1)
