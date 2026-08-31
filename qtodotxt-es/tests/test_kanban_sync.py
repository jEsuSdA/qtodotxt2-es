#!/usr/bin/env python3
"""
Tests de sincronización bidireccional Kanban <-> Ventana principal.

Garantizan el contrato esencial:
  1. Mover una tarea de columna en Kanban cambia su prioridad en el modelo
     (visible en la lista principal).
  2. Editar una tarea en la ventana principal actualiza el tablero Kanban.
  3. Crear una tarea nueva en la ventana principal la hace aparecer en el
     bloque Kanban correcto (hueco preexistente, corregido).
  4. Completar/descompletar desde Kanban se refleja en el modelo y widgets.
  5. Tras un rebuild posterior, el tablero converge con los datos reales.
"""

import argparse
import os
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5 import QtCore
from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import QApplication

from qtodotxt2.kanban_window import KanbanColumnWidget, KanbanTaskWidget
from qtodotxt2.main_controller import MainController

LINES = [
    "(A) Tarea uno +ProyectoSync1 @casa",
    "(B) Tarea dos +ProyectoSync1",
    "(C) Tarea tres +ProyectoSync2",
    "Tarea cuatro",
]


class TestKanbanSync(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        QtCore.QCoreApplication.setOrganizationName("QTodoTxt")
        QtCore.QCoreApplication.setApplicationName("TestingKanbanSync")
        QtCore.QSettings().setValue("Preferences/auto_save", False)
        cls.app = QApplication.instance() or QApplication([])

        fd, cls.path = tempfile.mkstemp(suffix=".txt")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write("\n".join(LINES) + "\n")

        cls.mc = MainController(argparse.Namespace(file=None, loglevel=["WARN"]))
        cls.mc.open(cls.path)
        cls.mc.openKanbanView()
        cls.app.processEvents()

    @classmethod
    def tearDownClass(cls):
        try:
            if getattr(cls.mc, "kanban_window", None) is not None:
                cls.mc.kanban_window.close()
        except Exception:
            pass
        os.unlink(cls.path)

    # ---------------- helpers ----------------

    def task_by_text_part(self, part):
        for t in self.mc.allTasks:
            if part in t.text:
                return t
        self.fail("No se encontró la tarea con texto: %s" % part)

    def kanban_ids(self, project, prio):
        data = self.mc.kanban_controller.kanbanData
        if project not in data:
            return None
        return [t["task_id"] for t in data[project]["tasks"][prio]]

    def column_widget(self, project, prio):
        block = self.mc.kanban_window._project_widgets.get(project)
        if block is None:
            return None
        for col in block.findChildren(KanbanColumnWidget):
            if col.priority_key == prio:
                return col
        return None

    def wait_rebuild(self, ms=400):
        QTest.qWait(ms)
        self.app.processEvents()

    # ---------------- 1. Kanban -> Principal ----------------

    def test_move_priority_updates_model(self):
        task = self.task_by_text_part("Tarea uno")
        task_id = str(id(task))
        self.mc.kanban_controller.update_task_priority(task_id, "B")
        self.assertTrue(task.text.startswith("(B) "), task.text)
        self.assertEqual(task.priority, "B")

    # ---------------- 2. Principal -> Kanban (edición) ----------------

    def test_edit_main_updates_kanban(self):
        task = self.task_by_text_part("Tarea cuatro")
        task.text = "(D) Tarea cuatro +ProyectoSyncEdit"
        self.wait_rebuild()
        ids = self.kanban_ids("ProyectoSyncEdit", "D")
        self.assertIsNotNone(ids, "El proyecto no apareció en el Kanban")
        self.assertIn(str(id(task)), ids)
        # restaurar para no contaminar otros tests
        task.text = "Tarea cuatro"
        self.wait_rebuild()

    # ---------------- 3. Principal -> Kanban (nueva tarea) ----------------

    def test_new_task_appears_in_kanban(self):
        idx = self.mc.newTask("(B) Tarea nueva sync +ProyectoSyncNueva")
        task = self.mc.filteredTasks[idx]
        self.wait_rebuild()
        ids = self.kanban_ids("ProyectoSyncNueva", "B")
        self.assertIsNotNone(
            ids, "La tarea nueva no llegó al Kanban (sync Principal->Kanban rota)")
        self.assertIn(str(id(task)), ids)
        # widget presente en la columna correcta
        col = self.column_widget("ProyectoSyncNueva", "B")
        self.assertIsNotNone(col)
        widget_ids = [w.task_id for w in col.findChildren(KanbanTaskWidget)]
        self.assertIn(str(id(task)), widget_ids)
        # limpieza
        self.mc.deleteTasks([task])
        self.wait_rebuild()

    # ---------------- 4. Toggle completada ----------------

    def test_toggle_done_syncs_model_and_widgets(self):
        task = self.task_by_text_part("Tarea tres")
        task_id = str(id(task))

        self.mc.kanban_controller.toggle_task_done(task_id, True)
        self.assertTrue(task.is_complete)
        self.assertTrue(task.text.startswith("x "), task.text)
        for block in self.mc.kanban_window._project_widgets.values():
            for w in block.findChildren(KanbanTaskWidget):
                if w.task_id == task_id:
                    self.assertTrue(w.task_data["is_done"])

        self.mc.kanban_controller.toggle_task_done(task_id, False)
        self.assertFalse(task.is_complete)
        self.assertFalse(task.text.startswith("x "), task.text)

    def test_edit_uses_diff_not_full_rebuild(self):
        window = self.mc.kanban_window
        calls = {"full": 0, "diff": 0}
        orig_full = window._refresh_board
        orig_diff = window._apply_data
        window._refresh_board = lambda: calls.__setitem__("full", calls["full"] + 1)
        window._apply_data = lambda d: calls.__setitem__("diff", calls["diff"] + 1)
        try:
            other = self.task_by_text_part("Tarea cuatro")
            other.text = other.text + " @z"
            self.wait_rebuild()
        finally:
            window._refresh_board = orig_full
            window._apply_data = orig_diff
        self.assertGreaterEqual(calls["diff"], 1, "la edición no pasó por el diff")
        self.assertEqual(calls["full"], 0, "la edición disparó un rebuild completo")

    # ---------------- 5. Convergencia tras rebuild ----------------

    def test_rebuild_converges_after_drag(self):
        task = self.task_by_text_part("Tarea uno")
        task_id = str(id(task))

        # drag simulado: A -> B (movimiento incremental, datos quedan atrás)
        self.mc.kanban_controller.update_task_priority(task_id, "B")
        self.assertEqual(task.priority, "B")

        # una edición cualquiera dispara el rebuild con datos frescos
        other = self.task_by_text_part("Tarea dos")
        other.text = other.text + " @extra"
        self.wait_rebuild()

        ids = self.kanban_ids("ProyectoSync1", "B")
        self.assertIn(task_id, ids, "Tras el rebuild la tarea no está en B")
        col = self.column_widget("ProyectoSync1", "B")
        self.assertIsNotNone(col)
        widget_ids = [w.task_id for w in col.findChildren(KanbanTaskWidget)]
        self.assertIn(task_id, widget_ids, "El widget no está en la columna B")

        # restaurar prioridad original de ambas tareas
        self.mc.kanban_controller.update_task_priority(task_id, "A")
        other.text = other.text.replace(" @extra", "")
        self.wait_rebuild()

    # ---------------- 6. Diff incremental: casos específicos ----------------

    def test_diff_moves_card_between_project_blocks(self):
        task = self.task_by_text_part("Tarea tres")
        tid = str(id(task))
        task.text = task.text + " +ProyectoSyncExtra"
        self.wait_rebuild()

        ids_new = self.kanban_ids("ProyectoSyncExtra", "C")
        self.assertIsNotNone(ids_new)
        self.assertIn(tid, ids_new)
        # integridad: un widget por tarea registrada en el bloque nuevo
        block = self.mc.kanban_window._project_widgets["ProyectoSyncExtra"]
        self.assertEqual(len(block._cards), len(block.findChildren(KanbanTaskWidget)))

        # limpiar: la tarjeta debe salir del bloque extra
        task.text = task.text.replace(" +ProyectoSyncExtra", "")
        self.wait_rebuild()
        block = self.mc.kanban_window._project_widgets.get("ProyectoSyncExtra")
        if block is not None:
            self.assertNotIn(tid, block._cards)

    def test_no_duplicate_cards_after_drag_then_diff(self):
        task = self.task_by_text_part("Tarea dos")
        tid = str(id(task))
        # dos movimientos incrementales seguidos y luego un diff
        self.mc.kanban_controller.update_task_priority(tid, "NP")
        self.mc.kanban_controller.update_task_priority(tid, "B")
        other = self.task_by_text_part("Tarea cuatro")
        other.text = other.text + " @x"
        self.wait_rebuild()

        block = self.mc.kanban_window._project_widgets["ProyectoSync1"]
        widgets = block.findChildren(KanbanTaskWidget)
        self.assertEqual(len(block._cards), len(widgets),
                         "registros _cards y widgets reales desincronizados")
        ids = [w.task_id for w in widgets]
        self.assertEqual(len(ids), len(set(ids)), "tarjetas duplicadas en el bloque")

        other.text = other.text.replace(" @x", "")
        self.wait_rebuild()

    def test_diff_restores_column_order(self):
        i1 = self.mc.newTask("Ordena uno +ProyectoSyncOrden")
        i2 = self.mc.newTask("Ordena dos +ProyectoSyncOrden")
        i3 = self.mc.newTask("Ordena tres +ProyectoSyncOrden")
        tasks = [self.mc.filteredTasks[i] for i in (i1, i2, i3)]
        self.wait_rebuild()

        col = self.column_widget("ProyectoSyncOrden", "NP")
        self.assertIsNotNone(col)
        layout = col.task_layout

        # desordenar manualmente: última tarjeta al frente
        last_card_item = layout.takeAt(layout.count() - 2)
        layout.insertWidget(0, last_card_item.widget())

        # un diff posterior debe restaurar el orden de los datos
        other = self.task_by_text_part("Tarea cuatro")
        other.text = other.text + " @y"
        self.wait_rebuild()

        data_ids = [t["task_id"] for t in
                    self.mc.kanban_controller.kanbanData["ProyectoSyncOrden"]["tasks"]["NP"]]
        widget_ids = [w.task_id for w in col.findChildren(KanbanTaskWidget)]
        self.assertEqual(data_ids, widget_ids, "el diff no restauró el orden de la columna")

        # limpieza
        self.mc.deleteTasks(tasks)
        other.text = other.text.replace(" @y", "")
        self.wait_rebuild()


if __name__ == "__main__":
    unittest.main()
