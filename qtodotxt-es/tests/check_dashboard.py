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
        "x " + (hoy - datetime.timedelta(days=10)).isoformat() + " Cerrado esta semana +kam",
    ]
    # base para el milestone (S16): completadas antiguas con +viejo
    velda = (hoy - datetime.timedelta(days=280)).isoformat()
    for i in range(44):
        done_lines.append("x " + velda + " Vieja " + str(i) + " +viejo")
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
    check("done_total", d["done_total"], 47)
    check("done_hoy", d["done_hoy"], 2)
    check("waiting", len(d["waiting_pend"]), 2)
    check("waiting_vencidas", sum(1 for x in d["waiting_pend"] if x["vencida"]), 1)
    check("vencidas", len(d["radar_vencidas"]), 2)
    check("proximas", len(d["radar_proximas"]), 2)
    check("antiguas", d["antiguas"], [])  # ninguna línea date-first
    # S5 · foco
    check("foco_top5", d["foco_top5"], [
        # desempate del CLI: mismo count → nombre DESC («proyecto» > «kam»)
        ("proyecto", {"count": 1, "a": 0, "b": 1}),
        ("kam", {"count": 1, "a": 1, "b": 0}),
    ])
    check("dormant", d["dormant_projects"], 1)  # total 3 (todo.txt) − activos 2
    check("foco_reco", d["foco_reco"], {"proy": "kam", "ab": 1, "venc": 1})
    # S8 · alertas
    check("a_sin_due", d["a_sin_due"], 0)
    check("due_sin_prio", d["due_sin_prio"], 2)  # waiting 2020 + Vencida vieja
    check("vencidas_a", d["vencidas_a"], 1)
    check("desnudas", d["desnudas_n"], 1)  # "(D) Sobre la agenda"
    check("estancado_proy", d["estancado"][0], "viejo")
    check("estancado_dias", d["estancado"][1] > 30, True)
    # S9 · antigüedad
    check("ant90", d["ant90"], 0)
    check("ant60", d["ant60"], 0)
    check("ant30", d["ant30"], 0)
    check("ab_medio", d["ab_medio"], 0)
    check("sin_creacion", d["sin_creacion"], 9)
    # S10 · contextos
    check("ctx_top5", d["ctx_top5"], [("waiting", 2), ("office", 1)])
    check("ctx_venc_office", d["ctx_venc"].get("office"), 1)
    # S11 · balance 4 semanas
    check("hist4", d["hist4"], [0, 0, 1, 2])
    check("semanas_vaciar", d["semanas_vaciar"], 5)  # ceil(9/2)
    # S12 · quick wins (ningún proyecto elegible)
    check("quick_wins", d["quick_wins"], [])
    # S13 · cuellos (semántica web)
    check("cuellos", d["cuellos"], [{"proy": "delegadas", "waiting": 2,
                                     "tot": 2, "pct": 100, "dias": 0}])
    # S14 · estado
    check("cnt_waiting", d["cnt_waiting"], 2)
    check("wait_nodate", d["wait_nodate"], 1)
    check("incubadora", d["incubadora_n"], 0)
    check("zombies", d["zombie_n"], 0)
    check("orphan", d["orphan_n"], 1)
    # S15 · salud: -2 huérfanas -4 vencidas -1 desnudas -5 sin-creación
    check("salud", d["salud"], 88)
    # S16 · logros
    check("racha", d["racha"], 1)
    check("milestone", d["milestone"], {"meta": 50, "resto": 3})
    # extras S4/S6
    check("proys_urg_top", d["proys_urg_top"],
          [("proyecto", 2), ("kam", 1), ("delegadas", 1)])
    check("creadas_hoy", d["creadas_hoy"], 0)
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
