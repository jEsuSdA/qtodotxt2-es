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


if __name__ == "__main__":
    unittest.main()
