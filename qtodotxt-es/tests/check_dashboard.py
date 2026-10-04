#!/usr/bin/env python3
"""Smoke test standalone del dashboard (fenêtre offscreen, datos en sandbox).

Ejecutar desde la raíz del repo:
    QT_QPA_PLATFORM=offscreen python3 qtodotxt-es/tests/check_dashboard.py

Crea todo.txt/done.txt temporales y valida las fórmulas de paridad
(paridad con plugins/dashboard: inbox con quirk "x 20", contadores A-D,
completadas hoy/sem, waiting, radar, antigüedad solo date-first).
Imprime OK/FALLO y sale 0/1. No escribe en los datos del usuario.
"""
import datetime
import os
import sys
import tempfile

app_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, app_dir)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtWidgets import QApplication  # noqa: E402

from qtodotxt2.lib.file import File  # noqa: E402
from qtodotxt2.dashboard_window import DashboardWindow  # noqa: E402


class FakeController:
    def __init__(self, todo_path):
        self._file = File()
        self._file.load(todo_path)


def main():
    hoy = datetime.date.today()
    today = hoy.isoformat()
    tmp = tempfile.mkdtemp(prefix="dash_smoke_")
    todo = os.path.join(tmp, "todo.txt")
    done = os.path.join(tmp, "done.txt")

    todo_lines = [
        "(A) Tarea MIT hoy +kam @office due:" + today,
        "(B) Semana +proyecto due:" + today,
        "(C) Mes tranqui +proyecto",
        "(D) Sobre la agenda",
        "Sin prioridad en inbox",
        "burofax con x 2026 a mitad (debe salir del inbox)",
        "Esperando respuesta +delegadas @waiting",
        "Esperando muerto +delegadas @waiting due:2020-01-01",
        "Vencida vieja +proyecto due:2020-01-01",
    ]
    done_lines = [
        "x " + today + " Termina hoy +proyecto",
        "x " + today + " Termina hoy tambien +kam",
        "x 2026-10-01 Cerrado esta semana +kam",
    ]
    with open(todo, "wt", encoding="utf-8") as fd:
        fd.write("\n".join(todo_lines) + "\n")
    with open(done, "wt", encoding="utf-8") as fd:
        fd.write("\n".join(done_lines) + "\n")
    with open(os.path.join(tmp, ".ice_recur_completed"), "wt") as fd:
        fd.write("")

    app = QApplication([])
    win = DashboardWindow(FakeController(todo))
    win.refresh()  # render completo sin timers
    d = win._gather_data()

    fallos = []

    def check(nombre, real, esperado):
        if real != esperado:
            fallos.append("%s: %s != %s" % (nombre, real, esperado))

    check("pend", d["pend"], 9)
    check("cnt", d["cnt"], {"A": 1, "B": 1, "C": 1, "D": 1})
    check("inbox", d["inbox"], 4)  # 5 sin prioridad − 1 con "x 20" en el texto
    check("done_total", d["done_total"], 3)
    check("done_hoy", d["done_hoy"], 2)
    check("waiting", len(d["waiting_pend"]), 2)
    check("waiting_vencidas", sum(1 for x in d["waiting_pend"] if x["vencida"]), 1)
    check("vencidas", len(d["radar_vencidas"]), 2)
    check("proximas", len(d["radar_proximas"]), 2)
    check("antiguas", d["antiguas"], [])  # ninguna línea date-first
    win.hide()
    app.processEvents()

    if fallos:
        print("FALLO — dashboard smoke:")
        for f in fallos:
            print("   " + f)
        return 1
    print("OK — dashboard smoke (pend=%d, inbox=%d, waiting=%d)" % (
        d["pend"], d["inbox"], len(d["waiting_pend"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
