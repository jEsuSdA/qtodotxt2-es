import datetime
import logging
import os
import random
import re
import time

from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QMainWindow, QScrollArea,
    QVBoxLayout, QWidget,
)

logger = logging.getLogger(__name__)

# Regex de paridad con el CLI (plugins/dashboard)
PROJ_RE = re.compile(r'\+[A-Za-z0-9_-]+')
CTX_RE = re.compile(r'@[A-Za-z0-9_-]+')
DUE_RE = re.compile(r'due:[0-9]{4}-[0-9]{2}-[0-9]{2}')

# Paleta (misma que el kanban interno) para que el panel sea homogéneo
COL_VERDE = '#27ae60'
COL_ROJO = '#e74c3c'
COL_AMARILLO = '#f39c12'
COL_GRIS = '#7f8c8d'
COL_MUTED = '#95a5a6'

LIMIT_A = 5
LIMIT_B = 20


def today_str():
    return datetime.date.today().isoformat()


def iso_date(s):
    try:
        return datetime.date.fromisoformat(s)
    except (ValueError, TypeError):
        return None


def esc(t):
    return (
        str(t).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    )


class DashboardWindow(QMainWindow):
    """
    Ventana del dashboard: lectura pura de las tareas cargadas + done.txt del
    disco, con las fórmulas de paridad de los dashboards CLI (plugins/dashboard)
    y web (todotxt-dashboard.php). Ver docs/dashboard-paridad.md.
    Esta ventana jamás escribe en fichero alguno.
    """

    def __init__(self, main_controller, parent=None):
        super().__init__(parent)
        self.main_controller = main_controller
        self.setWindowTitle("QTodoTxt2 - Dashboard")
        self.resize(1000, 760)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)

        header = QWidget()
        header.setStyleSheet("QWidget { background-color: #2c3e50; padding: 5px; }")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(10, 10, 10, 10)
        self.header_label = QLabel("Dashboard")
        self.header_label.setStyleSheet("color: white; font-size: 20px; font-weight: bold;")
        header_layout.addWidget(self.header_label)
        header_layout.addStretch()
        layout.addWidget(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea { border: none; }")
        layout.addWidget(scroll)

        self.cards_container = QWidget()
        self.cards_container.setStyleSheet("background: #ecf0f1;")
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setSpacing(12)
        self.cards_layout.setContentsMargins(12, 12, 12, 12)
        self.cards_layout.addStretch(1)
        scroll.setWidget(self.cards_container)

        # refresco periódico mientras visible (KISS, solo lectura)
        self._timer = QTimer(self)
        self._timer.setInterval(30000)
        self._timer.timeout.connect(self._auto_refresh)

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh()
        self._timer.start()

    def hideEvent(self, event):
        super().hideEvent(event)
        self._timer.stop()

    def _auto_refresh(self):
        if self.isVisible():
            self.refresh()

    def refresh(self):
        try:
            data = self._gather_data()
        except Exception as ex:
            logger.exception("dashboard: error al recopilar datos")
            data = {'error': str(ex)}
        self._render(data)

    def _done_path(self):
        filename = self.main_controller._file.filename
        if not filename:
            return None
        return os.path.join(os.path.dirname(os.path.abspath(filename)), 'done.txt')

    def _rec_age(self):
        """Edad (min) del sentinel del cron; None si no está."""
        done_path = self._done_path()
        if not done_path:
            return None
        sentinel = os.path.join(os.path.dirname(done_path), '.ice_recur_completed')
        if not os.path.isfile(sentinel):
            return None
        try:
            return (time.time() - os.path.getmtime(sentinel)) / 60.0
        except OSError:
            return None

    # -------------------------------------------------------------------------
    # Datos (fórmulas de paridad)
    # -------------------------------------------------------------------------
    def _gather_data(self):
        hoy = today_str()
        tasks = list(self.main_controller._file.tasks)
        pendientes = [t for t in tasks if not t.is_complete]

        done_path = self._done_path()
        done_lines = []
        if done_path and os.path.isfile(done_path):
            with open(done_path, 'rt', encoding='utf-8', errors='replace') as fd:
                for line in fd:
                    line = line.strip()
                    if line.startswith('x '):
                        done_lines.append(line)

        # done.txt: "x AAAA-MM-DD resto" → fechas de completo (+ creación opcional)
        done_total = len(done_lines)
        fecha_completado = dict()
        edades_done = []
        for line in done_lines:
            parts = line.split(' ')
            cd = iso_date(parts[1]) if len(parts) >= 2 else None
            if cd:
                fecha_completado[cd] = fecha_completado.get(cd, 0) + 1
                resto = parts[2:]
                crd = iso_date(resto[0]) if resto and len(resto[0]) == 10 else None
                if crd:
                    edades_done.append(crd)

        cnt = {'A': 0, 'B': 0, 'C': 0, 'D': 0}
        inbox = 0
        waiting_pend = []
        for nr, t in enumerate(tasks, 1):
            # mismo criterio que el CLI (plugins/dashboard): prioridad única
            # (A)-(Z) fuera del inbox; el substring "x 20" en cualquier parte
            # también sale del inbox (quirk heredado: burofax 2024, "x 2026"…)
            if t.is_complete:
                continue
            if t.priority and 'A' <= t.priority <= 'Z':
                if t.priority in cnt:
                    cnt[t.priority] += 1
            elif 'x 20' in t.text:
                pass
            else:
                inbox += 1
            if 'waiting' in t.contexts:
                cr = t.creation_date
                edad = (datetime.date.today() - cr).days if cr else 0
                due = t.due
                vencida = bool(due and due.date() <= datetime.date.today())
                waiting_pend.append({'nr': nr, 'task': t, 'edad': max(edad, 0),
                                     'due': due, 'vencida': vencida})

        done_7d = sum(v for d, v in fecha_completado.items() if d >= datetime.date.today() - datetime.timedelta(days=6))
        done_hoy = fecha_completado.get(datetime.date.today(), 0)
        week_start = datetime.date.today() - datetime.timedelta(days=datetime.date.today().weekday())
        done_sem = sum(v for d, v in fecha_completado.items() if d >= week_start)
        done_mes = sum(v for d, v in fecha_completado.items() if d >= datetime.date.today().replace(day=1))
        done_prev = sum(v for d, v in fecha_completado.items()
                        if datetime.date.today() - datetime.timedelta(days=13) <= d <= datetime.date.today() - datetime.timedelta(days=7))

        # creadas (paridad CLI: fecha de creación solo al principio de la
        # línea, sin "(X) " delante; en done.txt, tras la fecha de completo)
        created_7d = 0
        created_sem = 0
        lim7 = datetime.date.today() - datetime.timedelta(days=6)
        for t in pendientes:
            if t.text and t.text[0] != '(':
                cr = iso_date(t.text[:10])
            else:
                cr = None
            if cr:
                if cr >= lim7:
                    created_7d += 1
                if cr >= week_start:
                    created_sem += 1
        for crd in edades_done:
            if crd >= datetime.date.today() - datetime.timedelta(days=6):
                created_7d += 1
            if crd >= week_start:
                created_sem += 1
        balance_neto = done_7d - created_7d

        velocidad = round(done_7d / 7.0, 1)
        ab = cnt['A'] + cnt['B']
        est_vaciar = 0
        if done_7d > 0:
            est_vaciar = -(-ab * 7 // done_7d)

        radar_vencidas, radar_proximas = [], []
        for t in pendientes:
            if t.priority == 'D' or 'incubadora' in t.contexts:
                continue
            due = t.due
            if not due:
                continue
            ddue = due.date()
            if ddue < datetime.date.today():
                radar_vencidas.append((ddue, t))
            elif ddue <= datetime.date.today() + datetime.timedelta(days=7):
                radar_proximas.append((ddue, t))
        radar_vencidas.sort(key=lambda x: x[0])
        radar_proximas.sort(key=lambda x: x[0])
        vencen_hoy = sum(1 for d, _ in radar_vencidas if d == datetime.date.today())

        dias7 = []
        for i in range(6, -1, -1):
            d = datetime.date.today() - datetime.timedelta(days=i)
            dias7.append({'fecha': d, 'n': fecha_completado.get(d, 0)})

        antiguas = []
        for t in pendientes:
            # paridad con el CLI: solo despierta como creación los primeros
            # 10 caracteres de la línea; con "(X) " delante = sin-creación
            cr = iso_date(t.text[:10]) if t.text and t.text[0] != '(' else None
            if cr:
                edad = (datetime.date.today() - cr).days
                antiguas.append((edad, t))
        antiguas.sort(key=lambda x: x[0], reverse=True)
        antiguas = antiguas[:3]

        # -------------------------------------------------------------------------
        # Datos extra (S5, S8..S17) — sweating de la paridad CLI/web
        # -------------------------------------------------------------------------
        today_d = datetime.date.today()
        next_week = today_d + datetime.timedelta(days=7)
        current_year = today_d.year

        # --- S5 · Foco: proyectos en (A)/(B) (substring por línea, como CLI) ---
        proy_foco = {}
        active_projects = set()
        for t in pendientes:
            if t.priority in ('A', 'B'):
                for p in set(PROJ_RE.findall(t.text)):
                    p = p[1:]
                    e = proy_foco.setdefault(p, {'count': 0, 'a': 0, 'b': 0})
                    e['count'] += 1
                    if t.priority == 'A':
                        e['a'] += 1
                    else:
                        e['b'] += 1
                active_projects.update(x[1:] for x in PROJ_RE.findall(t.text))
        # desempate tipo `sort -rn` del CLI: -count y luego nombre DESC
        foco_top5 = sorted(sorted(proy_foco.items(), key=lambda kv: kv[0], reverse=True),
                           key=lambda kv: kv[1]['count'], reverse=True)[:5]
        total_projects = len({x[1:] for t in tasks
                              for x in re.findall(r'\+[A-Za-z0-9_-]*', t.text)})
        dormant_projects = total_projects - len(active_projects)

        # proyecto recomendado: score +2 (due ≤ +7d) / +1 ((A) sin due cercano)
        score = {}
        for t in pendientes:
            if t.priority in ('A', 'B'):
                urg = 0
                due = t.due
                if due and due.date() <= next_week:
                    urg = 2
                if urg == 0 and t.priority == 'A':
                    urg = 1
                if urg:
                    for p in PROJ_RE.findall(t.text):
                        p = p[1:]
                        score[p] = score.get(p, 0) + urg
        foco_reco = None
        if score:
            rp, _rs = sorted(score.items(), key=lambda kv: (-kv[1], kv[0]))[0]
            rec_ab = sum(1 for t in pendientes
                         if t.priority in ('A', 'B') and ('+' + rp) in t.text)
            rec_venc = sum(1 for t in pendientes
                           if t.priority in ('A', 'B') and ('+' + rp) in t.text
                           and t.due and t.due.date() <= next_week)
            foco_reco = {'proy': rp, 'ab': rec_ab, 'venc': rec_venc}

        # --- S8 · Alertas de riesgo ---
        a_sin_due = sum(1 for t in pendientes
                        if t.priority == 'A' and not DUE_RE.search(t.text))
        due_sin_prio = sum(1 for t in pendientes
                           if DUE_RE.search(t.text)
                           and not (t.priority and 'A' <= t.priority <= 'Z'))
        vencidas_a = sum(1 for t in pendientes
                         if t.priority == 'A' and t.due
                         and t.due.date() <= today_d)
        desnudas_n = sum(1 for t in pendientes
                         if t.priority and 'A' <= t.priority <= 'Z'
                         and not PROJ_RE.search(t.text) and '@' not in t.text)
        caida_vel = bool(done_prev > 0 and done_sem < (done_prev // 2))

        # proyecto estancado: última actividad = máx(creación pendiente date-first,
        # completa en done.txt) por proyecto
        acts = {}
        for line in done_lines:
            m = PROJ_RE.search(line)
            if m:
                p = m.group(0)[1:]
                cd = iso_date(line[2:12]) if len(line) >= 12 else None
                if cd and (p not in acts or cd > acts[p]):
                    acts[p] = cd
        for t in pendientes:
            m = PROJ_RE.search(t.text)
            if m:
                p = m.group(0)[1:]
                crd = iso_date(t.text[:10])
                if crd and (p not in acts or crd > acts[p]):
                    acts[p] = crd
        estancado = ('', 0)
        for p, dd in acts.items():
            dias = (today_d - dd).days
            if dias > estancado[1]:
                estancado = (p, dias)

        # --- S9 · Antigüedad ---
        ant30 = ant60 = ant90 = 0
        ab_sum = ab_n = 0
        sin_creacion = 0
        for t in pendientes:
            cr = iso_date(t.text[:10])
            if not cr:
                sin_creacion += 1
                continue
            edad = max((today_d - cr).days, 0)
            if edad >= 90:
                ant90 += 1
            elif edad >= 60:
                ant60 += 1
            elif edad >= 30:
                ant30 += 1
            if t.priority in ('A', 'B'):
                ab_sum += edad
                ab_n += 1
        ab_medio = (ab_sum // ab_n) if ab_n else 0

        # --- S10 · Contextos activos (dedup por línea, con vencidas) ---
        ctx_tot = {}
        ctx_venc = {}
        for t in pendientes:
            venc = 1 if (t.due and t.due.date() <= today_d) else 0
            for c in set(CTX_RE.findall(t.text)):
                c = c[1:]
                ctx_tot[c] = ctx_tot.get(c, 0) + 1
                if venc:
                    ctx_venc[c] = ctx_venc.get(c, 0) + 1
        ctx_top5 = sorted(sorted(ctx_tot.items(), key=lambda kv: kv[0], reverse=True),
                          key=lambda kv: kv[1], reverse=True)[:5]

        # --- S11 · Balance E/S (últimas 4 semanas) ---
        p4 = today_d - datetime.timedelta(days=28)
        p1 = today_d - datetime.timedelta(days=21)
        p3 = today_d - datetime.timedelta(days=14)
        p2 = today_d - datetime.timedelta(days=7)

        def _idx4(dd):
            if p4 <= dd < p1:
                return 0
            if p1 <= dd < p3:
                return 1
            if p3 <= dd < p2:
                return 2
            if dd >= p2:
                return 3
            return None

        created4 = [0, 0, 0, 0]
        for t in pendientes:
            cr = iso_date(t.text[:10])
            if cr:
                i = _idx4(cr)
                if i is not None:
                    created4[i] += 1
        done4 = [0, 0, 0, 0]
        for dd, n in fecha_completado.items():
            i = _idx4(dd)
            if i is not None:
                done4[i] += n
        hist4 = [done4[i] - created4[i] for i in range(4)]

        semanas_vaciar = 0
        if balance_neto > 0 and len(pendientes) > 0:
            semanas_vaciar = -(-len(pendientes) // balance_neto)

        # --- S12 · Quick wins (proyectos cerrables) ---
        kt = {}
        nk = {}
        for t in tasks:
            m = PROJ_RE.search(t.text)
            if m:
                p = m.group(0)[1:]
                kt[p] = kt.get(p, 0) + 1
                if not t.is_complete:
                    nk[p] = nk.get(p, 0) + 1
        for line in done_lines:
            m = PROJ_RE.search(line)
            if m:
                p = m.group(0)[1:]
                kt[p] = kt.get(p, 0) + 1
        quick_wins = []
        for p in sorted(kt):
            if nk.get(p, 0) > 0 and nk.get(p, 0) <= 3:
                porc = (kt[p] - nk[p]) * 100 // kt[p]
                if porc > 75:
                    quick_wins.append({'proy': p, 'nk': nk[p], 'kt': kt[p],
                                       'porc': porc})
        quick_wins.sort(key=lambda x: (x['nk'], x['proy']))
        quick_wins = quick_wins[:3]

        # --- S13 · Cuellos de botella (semántica del web N3; el CLI cumple muerto) ---
        w_dias = {}
        tot_pend = {}
        wait_proj = {}
        for x in waiting_pend:
            for p in set(PROJ_RE.findall(x['task'].text)):
                p = p[1:]
                if x['edad'] > w_dias.get(p, -1):
                    w_dias[p] = x['edad']
        for t in pendientes:
            for p in set(PROJ_RE.findall(t.text)):
                p = p[1:]
                tot_pend[p] = tot_pend.get(p, 0) + 1
                if 'waiting' in t.contexts:
                    wait_proj[p] = wait_proj.get(p, 0) + 1
        cuellos = []
        for p, wp in wait_proj.items():
            tp = tot_pend.get(p, 0)
            if tp > 0:
                cuellos.append({'proy': p, 'waiting': wp, 'tot': tp,
                                'pct': wp * 100 // tp,
                                'dias': w_dias.get(p, 0)})
        cuellos.sort(key=lambda x: (-x['pct'], x['proy']))
        cuellos = cuellos[:3]

        # --- S14 · Estado del sistema ---
        cnt_waiting = len(waiting_pend)
        wait_nodate = sum(1 for x in waiting_pend
                          if not DUE_RE.search(x['task'].text))
        incubadora_n = sum(1 for t in pendientes if 'incubadora' in t.contexts)
        zombie_n = sum(1 for t in pendientes
                       if t.priority == 'D' and len(t.text) > 13
                       and t.text[0] == '('
                       and iso_date(t.text[4:14]) is not None
                       and int(t.text[4:8]) < current_year)
        orphan_n = sum(1 for t in pendientes
                       if t.priority and 'A' <= t.priority <= 'Z'
                       and not re.search(r'\+[A-Za-z]', t.text))

        # --- S15 · Salud /100 (fórmula M12 del web, calcada del CLI) ---
        count_vencidas = len(radar_vencidas)
        salud = 100
        if inbox > 10:
            salud -= min(20, inbox)
        elif 5 < inbox <= 10:
            salud -= 5
        if zombie_n > 0:
            salud -= min(15, zombie_n * 3)
        if orphan_n > 0:
            salud -= min(10, orphan_n * 2)
        if count_vencidas > 0:
            salud -= min(20, count_vencidas * 2)
        if desnudas_n > 0:
            salud -= min(5, desnudas_n)
        if sin_creacion > 0:
            salud -= min(5, sin_creacion)
        if balance_neto < 0:
            salud -= min(10, -balance_neto * 2)
        salud = max(0, salud)

        # --- S16 · Logros ---
        racha = 0
        dchk = today_d
        while fecha_completado.get(dchk, 0) > 0:
            racha += 1
            dchk -= datetime.timedelta(days=1)
        milestone = None
        for m in (50, 100, 250, 500, 1000, 2500, 5000):
            if done_total < m:
                resto_m = m - done_total
                if resto_m <= m // 5:
                    milestone = {'meta': m, 'resto': resto_m}
                break

        # --- S4 extra · proyectos con urgencias (top 3; desempate nombre DESC) ---
        proys_urg = {}
        for _dd, t in radar_vencidas + radar_proximas:
            m = PROJ_RE.search(t.text)
            if m:
                p = m.group(0)[1:]
                proys_urg[p] = proys_urg.get(p, 0) + 1
        proys_urg_top = sorted(sorted(proys_urg.items(), key=lambda kv: kv[0], reverse=True),
                               key=lambda kv: kv[1], reverse=True)[:3]

        # --- S6 extra · creadas hoy ---
        creadas_hoy = sum(1 for t in pendientes
                          if t.text and t.text[0] != '('
                          and iso_date(t.text[:10]) == today_d)
        creadas_hoy += sum(1 for crd in edades_done if crd == today_d)

        return {
            'hoy': hoy, 'pend': len(pendientes), 'done_total': done_total,
            'cnt': cnt, 'inbox': inbox, 'done_hoy': done_hoy, 'done_sem': done_sem,
            'done_mes': done_mes, 'done_7d': done_7d, 'done_prev': done_prev,
            'velocidad': velocidad, 'est_vaciar': est_vaciar,
            'created_7d': created_7d, 'created_sem': created_sem,
            'balance_neto': balance_neto, 'waiting_pend': waiting_pend,
            'radar_vencidas': radar_vencidas, 'radar_proximas': radar_proximas,
            'vencen_hoy': vencen_hoy, 'dias7': dias7, 'antiguas': antiguas,
            # S5
            'foco_top5': foco_top5, 'dormant_projects': dormant_projects,
            'active_projects': len(active_projects), 'foco_reco': foco_reco,
            # S8
            'a_sin_due': a_sin_due, 'due_sin_prio': due_sin_prio,
            'vencidas_a': vencidas_a, 'desnudas_n': desnudas_n,
            'caida_vel': caida_vel, 'estancado': estancado,
            # S9
            'ant30': ant30, 'ant60': ant60, 'ant90': ant90,
            'ab_medio': ab_medio, 'sin_creacion': sin_creacion,
            # S10
            'ctx_top5': ctx_top5, 'ctx_venc': ctx_venc,
            # S11
            'hist4': hist4, 'semanas_vaciar': semanas_vaciar,
            # S12
            'quick_wins': quick_wins,
            # S13
            'cuellos': cuellos,
            # S14
            'cnt_waiting': cnt_waiting, 'wait_nodate': wait_nodate,
            'incubadora_n': incubadora_n, 'zombie_n': zombie_n,
            'orphan_n': orphan_n,
            # S15
            'salud': salud,
            # S16
            'racha': racha, 'milestone': milestone,
            # extras
            'proys_urg_top': proys_urg_top, 'creadas_hoy': creadas_hoy,
        }

    # -------------------------------------------------------------------------
    # Render (cards; QLabel rich-text + QProgressBar)
    # -------------------------------------------------------------------------
    def _card(self, titulo):
        card = QFrame()
        card.setStyleSheet("QFrame { background: white; border: 1px solid #d5dbdb; border-radius: 8px; }")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(14, 10, 14, 12)
        lay.setSpacing(6)
        h = QLabel(titulo)
        h.setStyleSheet("font-size: 14px; font-weight: bold; color: #2c3e50; border: none;")
        lay.addWidget(h)
        # insertar antes del stretch final
        self.cards_layout.insertWidget(self.cards_layout.count() - 1, card)
        return card, lay

    def _linea(self, lay, html, size=90):
        lbl = QLabel(html)
        lbl.setWordWrap(True)
        lbl.setStyleSheet("font-size: %d%%; border: none; color: #2d2a26;" % size)
        lay.addWidget(lbl)
        return lbl

    def _render(self, d):
        while self.cards_layout.count() > 1:
            item = self.cards_layout.takeAt(self.cards_layout.count() - 2)
            w = item.widget()
            if w is not None:
                w.deleteLater()
        self.header_label.setText("Dashboard · " + d.get('hoy', ''))

        if 'error' in d:
            card, lay = self._card("⚠ Error al recopilar datos")
            self._linea(lay, "No se ha podido calcular el dashboard:<br>" + esc(d['error']))
            return

        # --- S1 · Kanban (salud del flujo) ---
        card, lay = self._card('📊 1. SALUD DEL FLUJO (KANBAN)')
        for nombre, valor, limite in [
            ("(A) HOY (MITs)", d['cnt']['A'], LIMIT_A),
            ("(B) ESTA SEMANA", d['cnt']['B'], LIMIT_B),
            ("(C) ESTE MES", d['cnt']['C'], 50),
            ("(D) BACKLOG", d['cnt']['D'], 100),
        ]:
            if valor > limite:
                badge = '<span style="color:' + COL_ROJO + '">⚠ DEMASIADAS</span>'
            else:
                badge = '<span style="color:' + COL_VERDE + '">✓ OK</span>'
            self._linea(lay,
                        "<b>" + nombre + "</b>: <b>" + str(valor) + "</b> / " + str(limite) + " · " + badge)
        inbox = d['inbox']
        if inbox > 0:
            badge_in = '<span style="color:' + COL_ROJO + '">¡PROCESAR!</span>'
        else:
            badge_in = '<span style="color:' + COL_VERDE + '">CLEAN</span>'
        self._linea(lay, "<b>[ ] INBOX</b>: <b>" + str(inbox) + "</b> · " + badge_in)

        # --- S2 · Recurrentes (cron) ---
        card, lay = self._card('♻️ 2. RECURRENTES (cron)')
        edad = self._rec_age()
        if edad is None:
            self._linea(lay, '<span style="color:' + COL_GRIS + '">· Sin registro de ejecución '
                             '(.ice_recur_completed no existe)</span>')
        elif edad <= 1500:
            if edad < 120:
                idad = str(int(edad)) + " min"
            else:
                idad = str(int(edad // 60)) + " h"
            self._linea(lay, '<span style="color:' + COL_VERDE + '">✔ Recurrentes OK</span> · última ejecución hace <b>'
                             + idad + '</b>')
        else:
            dias_atraso = int(edad // 1440) or 1
            self._linea(lay, '<span style="color:' + COL_ROJO + '">⚠ RECURRENTES ATASCADOS</span> · última ejecución hace <b>'
                             + str(dias_atraso) + ' d</b> (¿cron roto? ¿ownCloud?)')

        # --- S3 · Resumen ejecutivo ---
        card, lay = self._card('📊 3. RESUMEN EJECUTIVO')
        total_rel = d['pend'] + d['done_total']
        ratio_i = (100 * d['done_total'] // total_rel) if total_rel > 0 else 0
        self._linea(lay,
                    "Pendientes: <b>" + str(d['pend']) + "</b> · Completadas: <b>" + str(d['done_total'])
                    + "</b> · Ratio: <b>" + str(ratio_i) + "%</b>")
        self._linea(lay,
                    "Hoy: <b>" + str(d['done_hoy']) + "</b> · Esta semana: <b>" + str(d['done_sem'])
                    + "</b> · Este mes: <b>" + str(d['done_mes']) + "</b> · Velocidad: <b>"
                    + ('%.1f' % d['velocidad']) + "</b>/día")
        col_bal = COL_VERDE if d['balance_neto'] >= 0 else COL_ROJO
        if d['est_vaciar'] > 0:
            self._linea(lay, '⏱️ Al ritmo actual: <b>~' + str(d['est_vaciar']) + ' días</b> para vaciar (A)+(B) '
                             '<span style="color:' + COL_MUTED + '">(' + str(d['cnt']['A']) + ' de (A) + '
                             + str(d['cnt']['B']) + ' de (B))</span>')
        self._linea(lay, '📥 Creadas: semana <b>' + str(d['created_sem']) + '</b> · últimos 7d <b>'
                             + str(d['created_7d']) + '</b> · Balance neto(7d): <span style="color:'
                             + col_bal + '"><b>' + ('+' if d['balance_neto'] >= 0 else '')
                             + str(d['balance_neto']) + '</b></span> <span style="color:' + col_bal + '">'
                             + ('(reduciendo backlog)' if d['balance_neto'] >= 0 else '(creciendo)')
                             + '</span>')

        # --- S4 · Radar de urgencias ---
        card, lay = self._card('⏰ 4. RADAR DE URGENCIAS')
        self._linea(lay, "Vencidas: <b>" + str(len(d['radar_vencidas'])) + "</b> · Próximas 7d: <b>"
                             + str(len(d['radar_proximas'])) + "</b>"
                             + ('  ·  🎯 <b>Vencen HOY: ' + str(d['vencen_hoy']) + '</b>' if d['vencen_hoy'] else ''))

        def _radar_desc(t):
            txt = t.text[4:] if (t.text and t.text[0] == '(') else t.text
            extra = '...' if len(txt) > 60 else ''
            return esc(txt[:60]) + extra

        if not d['radar_vencidas'] and not d['radar_proximas']:
            self._linea(lay, '<span style="color:' + COL_VERDE + '">✨ Horizonte despejado. Nada urgente a la vista.</span>')
        for ddue, tarea in d['radar_vencidas']:
            dias_atraso = (datetime.date.today() - ddue).days
            prio = ('(' + tarea.priority + ') ') if (tarea.priority and 'A' <= tarea.priority <= 'Z') else ''
            self._linea(lay, '🚨 <span style="color:' + COL_ROJO + '"><b>VENCIDA (' + ddue.isoformat()
                                 + ' hace ' + str(dias_atraso) + 'd)</b></span> ' + prio
                                 + '<span style="color:' + COL_MUTED + '">' + _radar_desc(tarea) + '</span>')
        for ddue, tarea in d['radar_proximas']:
            prio = ('(' + tarea.priority + ') ') if (tarea.priority and 'A' <= tarea.priority <= 'Z') else ''
            self._linea(lay, '⚠️ <span style="color:' + COL_AMARILLO + '"><b>PRÓXIMA (' + ddue.isoformat()
                                 + ')</b></span> ' + prio
                                 + '<span style="color:' + COL_MUTED + '">' + _radar_desc(tarea) + '</span>')
        if d['proys_urg_top']:
            self._linea(lay, '📌 Proyectos con urgencias: <b>' + ' '.join(
                '+' + esc(p) + '(' + str(n) + ')' for p, n in d['proys_urg_top']) + '</b>')

        # --- S5 · Foco actual ---
        card, lay = self._card('🎯 5. FOCO ACTUAL (Top 5 Proyectos en A/B)')
        if not d['foco_top5'] and not d['active_projects']:
            self._linea(lay, '<span style="color:' + COL_VERDE + '">✨ Sin proyectos activos en (A)/(B).</span>')
        for p, v in d['foco_top5']:
            self._linea(lay, '<span style="color:' + COL_AMARILLO + '"><b>+' + esc(p) + '</b></span> : <b>'
                             + str(v['count']) + '</b> tareas <span style="color:' + COL_MUTED + '">('
                             + str(v['a']) + ' (A) · ' + str(v['b']) + ' (B))</span>')
        self._linea(lay, 'Proyectos Dormidos (C/D) : <b>' + str(d['dormant_projects'])
                             + '</b> proyectos sin acción esta semana.', 88)
        if d['active_projects'] > 8:
            self._linea(lay, '<span style="color:' + COL_ROJO + '">⚠ ALERTA DISPERSIÓN:</span> Estás trabajando en <b>'
                             + str(d['active_projects']) + '</b> proyectos a la vez.')
        if d['foco_reco']:
            r = d['foco_reco']
            tip = ', ' + str(r['venc']) + ' vencen en 7 días' if r['venc'] > 0 else ''
            self._linea(lay, '💡 <b>Concentra esfuerzo en:</b> <span style="color:' + COL_AMARILLO
                             + '"><b>+' + esc(r['proy']) + '</b></span> <span style="color:' + COL_MUTED + '">('
                             + str(r['ab']) + ' tareas (A)/(B)' + tip + ')</span>')

        # --- S6 · Progreso de los últimos 7 días ---
        card, lay = self._card('📈 6. PROGRESO DE LOS ÚLTIMOS 7 DÍAS')
        semana_total = sum(x['n'] for x in d['dias7'])
        for x in d['dias7']:
            dia = x['fecha']
            hoy_marca = '» ' if dia == datetime.date.today() else '   '
            self._linea(lay, '<span style="color:' + COL_MUTED + '">' + dia.isoformat()[5:] + '</span>'
                             + ' · ' + esc(hoy_marca) + '<b>' + str(x['n']) + '</b>', 90)
        self._linea(lay, 'Total de la semana: <b>' + str(semana_total) + '</b> tareas terminadas.')

        # creadas del día (paridad CLI: «Creadas hoy» + entradas ya hechas)
        self._linea(lay, '<span style="color:' + COL_MUTED + '">Creadas hoy:</span> <b>' + str(d['creadas_hoy'])
                             + '</b> <span style="color:' + COL_MUTED + '">(más entradas del día)</span>', 88)

        # tendencia frente a la semana anterior (paridad CLI: icono + palabra)
        if d['done_sem'] > d['done_prev']:
            tend = '↑ mejorando'
            col_t = COL_VERDE
        elif d['done_sem'] < d['done_prev']:
            tend = '↓ bajando'
            col_t = COL_ROJO
        else:
            tend = '→ igual'
            col_t = COL_MUTED
        self._linea(lay, '<span style="color:' + col_t + '"><b>' + tend + '</b></span> '
                         + '<span style="color:' + COL_MUTED + '">(esta semana ' + str(d['done_sem'])
                         + ' vs anterior ' + str(d['done_prev']) + ')</span>')

        # --- S7 · @waiting delegadas ---
        card, lay = self._card('⏳ 7. @WAITING DELEGADAS')
        total_w = len(d['waiting_pend'])
        vencidas_w = sum(1 for x in d['waiting_pend'] if x['vencida'])
        mas7 = sum(1 for x in d['waiting_pend'] if x['edad'] >= 7 and x['edad'] < 30)
        mas30 = sum(1 for x in d['waiting_pend'] if x['edad'] >= 30)
        self._linea(lay, 'Total: <b>' + str(total_w) + '</b> · Vencidas: <span style="color:' + COL_ROJO
                             + '"><b>' + str(vencidas_w) + '</b></span> · +7d: <b>' + str(mas7)
                             + '</b> · +30d: <b>' + str(mas30) + '</b>')

        # orden del CLI: vencidas primero, luego por due ascendente
        wait_list = sorted(d['waiting_pend'],
                           key=lambda x: (0 if x['vencida'] else 1,
                                          x['due'].date().isoformat() if x['due'] else ''))
        for x in wait_list[:5]:
            t = x['task']
            txt = t.text
            prio = ''
            if txt and txt[0] == '(':
                prio = txt[:3] + ' '
            m = PROJ_RE.search(txt)
            proy = m.group(0) if m else ''
            if t.priority and 'A' <= t.priority <= 'Z':
                desc = txt[4:]
            else:
                desc = txt
            due_txt = x['due'].date().isoformat() if x['due'] else ''
            marca = ' 🚨' if (x['due'] and x['vencida']) else ''
            self._linea(lay, '<span style="color:' + COL_MUTED + '">' + ('%04d' % x['nr']) + '</span> '
                             + esc(prio) + '<span style="color:' + COL_MUTED + '">' + esc(proy)
                             + '</span> · ' + due_txt + marca
                             + ' <span style="color:' + COL_MUTED + '">' + esc(desc[:50]) + '</span>')
        proys_wait = {}
        for x in d['waiting_pend']:
            m = PROJ_RE.search(x['task'].text)
            if m:
                proys_wait[m.group(0)[1:]] = proys_wait.get(m.group(0)[1:], 0) + 1
        if proys_wait:
            top3 = sorted(sorted(proys_wait.items(), key=lambda kv: kv[0], reverse=True),
                          key=lambda kv: kv[1], reverse=True)[:3]
            self._linea(lay, '📌 Proyectos con esperas: <b>' + ' '.join(
                '+' + esc(p) + '(' + str(n) + ')' for p, n in top3) + '</b>')
        self._linea(lay, '<span style="color:' + COL_MUTED + '">(' + str(total_w)
                             + ') tareas en espera — la edad usa la fecha de creación; sin ella, 0d</span>', 85)

        # --- S8 · Alertas de riesgo ---
        card, lay = self._card('⚠️ 8. ALERTAS DE RIESGO')
        n_alertas = 0

        def alerta(html):
            nonlocal n_alertas
            self._linea(lay, html)
            n_alertas += 1

        if d['a_sin_due'] > 0:
            alerta('<span style="color:' + COL_AMARILLO + '">⚠️ ' + str(d['a_sin_due'])
                   + ' tareas (A) sin fecha de vencimiento</span> <span style="color:'
                   + COL_MUTED + '">— riesgo de olvido</span>')
        if d['due_sin_prio'] > 0:
            alerta('📋 ' + str(d['due_sin_prio'])
                   + ' tareas con fecha pero sin prioridad <span style="color:' + COL_MUTED
                   + '">— considera priorizar</span>')
        if d['cnt']['A'] > LIMIT_A:
            alerta('<span style="color:' + COL_ROJO + '">⚖️ Prioridad (A) sobrecargada: ' + str(d['cnt']['A'])
                   + ' tareas</span> <span style="color:' + COL_MUTED
                   + '">— máximo recomendado ' + str(LIMIT_A) + '</span>')
        if d['vencidas_a'] > 0:
            alerta('<span style="color:' + COL_ROJO + '">🚨 ' + str(d['vencidas_a'])
                   + ' tareas (A) vencidas</span> <span style="color:' + COL_MUTED
                   + '">— tus prioridades máximas fuera de plazo</span>')
        if d['inbox'] > 10:
            alerta('<span style="color:' + COL_AMARILLO + '">📥 Inbox con ' + str(d['inbox'])
                   + ' tareas sin procesar</span> <span style="color:' + COL_MUTED
                   + '">— dedica tiempo a vaciarlo</span>')
        if d['desnudas_n'] > 0:
            alerta('🏷️ ' + str(d['desnudas_n'])
                   + ' tareas desnudas (sin +proyecto ni @contexto) <span style="color:' + COL_MUTED
                   + '">— asigna metadata</span>')
        if d['caida_vel']:
            alerta('<span style="color:' + COL_AMARILLO + '">📉 Productividad en caída (>50% vs semana anterior): '
                   + str(d['done_sem']) + ' vs ' + str(d['done_prev']) + '</span>')
        est_p, est_d = d['estancado']
        if est_p and est_d > 30:
            alerta('<span style="color:' + COL_AMARILLO + '">🐢 Proyecto +' + esc(est_p)
                   + ' estancado hace ' + str(est_d) + ' días</span> <span style="color:' + COL_MUTED
                   + '">— necesita atención o debería aparcarse (<b>t adtv save</b>)</span>')
        if n_alertas == 0:
            self._linea(lay, '<span style="color:' + COL_VERDE + '">✅ Sin alertas críticas — el sistema está en buen estado.</span>')

        # --- S9 · Análisis de antigüedad ---
        card, lay = self._card('⏱️ 9. ANÁLISIS DE ANTIGÜEDAD')
        self._linea(lay, '+90 días: <span style="color:' + COL_ROJO + '"><b>' + str(d['ant90'])
                             + '</b></span> · +60: <span style="color:' + COL_AMARILLO + '"><b>' + str(d['ant60'])
                             + '</b></span> · +30: <b>' + str(d['ant30']) + '</b> · Edad media (A)+(B): <b>'
                             + str(d['ab_medio']) + ' d</b>')
        if d['sin_creacion'] > 0:
            self._linea(lay, '<span style="color:' + COL_MUTED + '">❓ ' + str(d['sin_creacion'])
                                 + ' tareas sin fecha de creación (sin datos de antigüedad)</span>', 88)
        if d['antiguas']:
            self._linea(lay, '🧊 Top 3 más antiguas:')
            for edad, tarea in d['antiguas']:
                self._linea(lay, '<span style="color:' + COL_MUTED + '">(' + str(edad) + 'd)</span> '
                                 + esc(tarea.text[:58]), 88)
        else:
            self._linea(lay, '<span style="color:' + COL_MUTED + '">🧊 Top 3: sin tareas con fecha de creación.</span>', 88)

        # --- S10 · Contextos activos ---
        card, lay = self._card('🔄 10. CONTEXTOS ACTIVOS')
        self._linea(lay, '<span style="color:' + COL_MUTED + '">(top 5 por pendientes)</span>', 88)
        for c, n in d['ctx_top5']:
            venc = d['ctx_venc'].get(c, 0)
            self._linea(lay, '@' + esc(c) + ' <b>' + str(n) + '</b> pend.'
                             + (' <span style="color:' + COL_ROJO + '">(⚠ ' + str(venc) + ' vencidas)</span>'
                                if venc > 0 else ''))
        if d['ctx_top5']:
            self._linea(lay, '<span style="color:' + COL_MUTED + '">Más cargado: @' + esc(d['ctx_top5'][0][0])
                                 + '</span>', 88)

        # --- S11 · Balance entrada/salida ---
        card, lay = self._card('⚖️ 11. BALANCE ENTRADA/SALIDA')
        col_sb = COL_VERDE if d['balance_neto'] >= 0 else COL_ROJO
        pies = []
        for etiqueta, valor in [('S-3', d['hist4'][0]), ('S-2', d['hist4'][1]),
                                ('S-1', d['hist4'][2]), ('Hoy7d', d['hist4'][3])]:
            bcol = COL_VERDE if valor >= 0 else COL_ROJO
            pies.append('<span style="color:' + COL_MUTED + '">' + etiqueta + ':</span> '
                        + '<span style="color:' + bcol + '"><b>' + ('+' if valor >= 0 else '')
                        + str(valor) + '</b></span>')
        self._linea(lay, 'Últimas 4 semanas (comp. − cread.): ' + ' · '.join(pies))
        self._linea(lay, 'Estado del backlog: <span style="color:' + col_sb + '"><b>'
                             + ('↓ reduciendo (' if d['balance_neto'] >= 0 else '↑ creciendo (')
                             + str(d['balance_neto']) + '/7d)</b></span>')
        if d['semanas_vaciar'] > 0:
            self._linea(lay, '🏁 Al ritmo actual: <b>~' + str(d['semanas_vaciar'])
                                 + ' semanas</b> para vaciar el backlog')

        # --- S12 · Quick wins ---
        card, lay = self._card('🚀 12. QUICK WINS')
        self._linea(lay, '<span style="color:' + COL_MUTED + '">(proyectos con pocas pendientes: ciérralos y suma un proyecto)</span>', 88)
        if d['quick_wins']:
            for q in d['quick_wins']:
                self._linea(lay, '<span style="color:' + COL_AMARILLO + '"><b>+' + esc(q['proy']) + '</b></span>: <b>'
                                 + str(q['nk']) + '</b> pend. / ' + str(q['kt']) + ' total ('
                                 + '<span style="color:' + COL_VERDE + '">' + str(q['porc']) + '%</span>) '
                                 + '<span style="color:' + COL_MUTED + '">→ <b>t kanban '
                                 + esc(q['proy']) + '</b></span>')
        else:
            self._linea(lay, '<span style="color:' + COL_VERDE + '">✨ Sin quick wins: ningún proyecto activo se puede cerrar rápido.</span>', 88)

        # --- S13 · Cuellos de botella ---
        card, lay = self._card('🔒 13. CUELLOS DE BOTELLA')
        self._linea(lay, '<span style="color:' + COL_MUTED + '">(proyectos bloqueados por @waiting; semántica del web)</span>', 88)
        if d['cuellos']:
            for cb in d['cuellos']:
                colc = COL_ROJO if cb['pct'] > 50 else COL_AMARILLO
                self._linea(lay, '<span style="color:' + colc + '">🔒 <b>+' + esc(cb['proy']) + '</b></span>'
                                 + (' <span style="color:' + COL_ROJO + '">BLOQUEADO</span>' if cb['pct'] > 50 else '')
                                 + ': <b>' + str(cb['waiting']) + '</b> waiting / ' + str(cb['tot'])
                                 + ' pendientes (<span style="color:' + colc + '"><b>' + str(cb['pct'])
                                 + '%</b></span>)'
                                 + (' <span style="color:' + COL_MUTED + '">💡 Espera máx. ' + str(cb['dias'])
                                    + ' días</span>' if cb['dias'] > 0 else ''))
        else:
            self._linea(lay, '<span style="color:' + COL_VERDE + '">✨ Sin cuellos de botella.</span>')

        # --- S14 · Estado del sistema ---
        card, lay = self._card('🧹 14. ESTADO DEL SISTEMA')
        self._linea(lay, '<span style="color:' + COL_AMARILLO + '">⏳ @waiting</span> : <b>' + str(d['cnt_waiting'])
                             + '</b> tareas esperando a terceros (<span style="color:' + COL_AMARILLO + '"><b>'
                             + str(vencidas_w) + '</b></span> vencidas sin respuesta, <span style="color:'
                             + COL_MUTED + '">' + str(d['wait_nodate']) + '</span> sin fecha)')
        self._linea(lay, '<span style="color:#2980b9">🧊 @incubadora</span> : <b>' + str(d['incubadora_n'])
                             + '</b> ideas guardadas para el futuro.')
        if d['zombie_n'] > 0:
            self._linea(lay, '<span style="color:' + COL_ROJO + '">🧟 Zombies (D)</span> : <b>' + str(d['zombie_n'])
                                 + '</b> tareas creadas antes de ' + str(datetime.date.today().year) + '.'
                                 + ' <span style="color:' + COL_MUTED + '">(Considera borrar o mover a @incubadora)</span>', 88)
        if d['orphan_n'] > 0:
            self._linea(lay, '<span style="color:' + COL_ROJO + '">🗑 Huérfanas</span> : <b>' + str(d['orphan_n'])
                                 + '</b> tareas sin +proyecto asignado.')

        # --- S15 · Salud del sistema ---
        card, lay = self._card('🩺 15. SALUD DEL SISTEMA')
        if d['salud'] >= 80:
            col_s = COL_VERDE
        elif d['salud'] >= 50:
            col_s = COL_AMARILLO
        else:
            col_s = COL_ROJO
        self._linea(lay, '<span style="color:' + COL_MUTED + '">Salud del sistema:</span> '
                             + '<span style="color:' + col_s + '"><b>' + str(d['salud']) + '/100</b></span> '
                             + '<span style="color:' + COL_MUTED + '">(penalizaciones por inbox · zombies · huérfanas · '
                             + 'desnudas · vencidas · sin-creación · balance)</span>', 88)

        # --- S16 · Logros ---
        card, lay = self._card('🏆 16. LOGROS')
        if d['done_hoy'] > 0:
            self._linea(lay, '🎉 <b>' + str(d['done_hoy']) + '</b> tareas completadas HOY.')
        if d['racha'] > 0:
            self._linea(lay, '🔥 Racha: <b>' + str(d['racha']) + ' días</b> consecutivos.')
        if d['milestone']:
            m = d['milestone']
            self._linea(lay, '🎯 Milestone: faltan <b>' + str(m['resto'])
                                 + ' tareas</b> para completar ' + str(m['meta']) + '.')
        if d['done_hoy'] == 0 and d['racha'] == 0:
            self._linea(lay, '💪 ¡Empieza ahora! Completa tu primera tarea del día.')

        # --- S17 · Consejo ZTD ---
        card, lay = self._card('🧘 17. CONSEJO ZTD')
        if len(d['radar_vencidas']) > 0:
            self._linea(lay, '<span style="color:' + COL_ROJO + '">🛑 MODO CRISIS:</span> Tienes <b>'
                                 + str(len(d['radar_vencidas'])) + '</b> tareas vencidas. Ignora el Inbox. Ignora la planificación.')
            self._linea(lay, '<span style="color:' + COL_MUTED + '">Ejecuta las tareas marcadas con 🚨 AHORA MISMO.</span>', 88)
        elif d['inbox'] > 5:
            self._linea(lay, '<span style="color:' + COL_AMARILLO + '">📥 LIMPIEZA MENTAL:</span> Tu Inbox tiene '
                                 + str(d['inbox']) + ' elementos.')
            self._linea(lay, '<span style="color:' + COL_MUTED + '">Antes de trabajar, procesa el Inbox a 0. Tu mente necesita claridad.</span>', 88)
        elif d['cnt']['A'] > 6:
            self._linea(lay, '<span style="color:' + COL_ROJO + '">⚖️ SOBRECARGA:</span> Has planificado <b>'
                                 + str(d['cnt']['A']) + '</b> tareas para HOY.')
            self._linea(lay, '<span style="color:' + COL_MUTED + '">Sé realista. Mueve al menos '
                                 + str(d['cnt']['A'] - 5) + ' tareas a la prioridad (B).</span>', 88)
        elif d['cnt']['A'] == 0:
            self._linea(lay, '<span style="color:#2980b9">🎯 ENFOQUE:</span> No has definido tus MITs (Tareas Más Importantes) de hoy.')
            self._linea(lay, '<span style="color:' + COL_MUTED + '">Elige tus 3 tareas clave de la lista (B) y pásalas a (A).</span>', 88)
        elif vencidas_w > 0:
            self._linea(lay, '<span style="color:' + COL_AMARILLO + '">⏳ ESPERAS VENCIDAS:</span> Tienes <b>'
                                 + str(vencidas_w) + '</b> tareas @waiting con fecha pasada.')
            self._linea(lay, '<span style="color:' + COL_MUTED + '">A alguien aún no le han respondido. Reclama tú: el dueño de la respuesta es otro.</span>', 88)
        elif d['zombie_n'] > 0:
            self._linea(lay, '<span style="color:#2980b9">🧟 ZOMBIES:</span> ' + str(d['zombie_n'])
                                 + ' tareas (D) arrastradas de años anteriores.')
            self._linea(lay, '<span style="color:' + COL_MUTED + '">Decide: hazlas, bórralas o márcalas con @incubadora. Ninguna tercera opción.</span>', 88)
        elif d['orphan_n'] > 0:
            self._linea(lay, '<span style="color:#2980b9">🗑 HUÉRFANAS:</span> ' + str(d['orphan_n'])
                                 + ' tareas priorizadas sin +proyecto.')
            self._linea(lay, '<span style="color:' + COL_MUTED + '">Etiquétalas o decide si de verdad son actionables.</span>', 88)
        else:
            if d['active_projects'] > 8:
                self._linea(lay, '<span style="color:' + COL_AMARILLO + '">🔍 DISPERSIÓN:</span> Estás tocando <b>'
                                     + str(d['active_projects']) + '</b> proyectos distintos esta semana.')
                self._linea(lay, '<span style="color:' + COL_MUTED + '">Intenta cerrar proyectos completos antes de abrir novos.</span>', 88)
            else:
                self._linea(lay, '<span style="color:' + COL_VERDE + '">🚀 FLUJO ZEN:</span> Sistema limpio y prioridades claras.')
                self._linea(lay, '<span style="color:' + COL_MUTED + '">Ejecuta la lista (A) en orden. Sin distracciones.</span>', 88)

        # tip dinámico (rota con cada refresco, como el CLI en cada ejecución)
        tips = (
            'Si una (A) lleva 3 días sin arrancar, no es urgente: bájala a (B) sin culpa.',
            'Cierra la sesión de trabajo con el plugin donow: sabrás cuánto tiempo real invertiste.',
            'Tarea > 2 semanas sin arrancar = candidata a @incubadora o a borrarse.',
            'Grapa la decisión: si al leerla no sabes cómo empezar, aún es un proyecto: divídela.',
            '1 tarea hecha al día = 7 a la semana: eso es lo que no rompe la cadena.',
            'Revisa tu @waiting una vez por semana como máximo: reclamar más es contraer el estrés jurídico.',
        )
        self._linea(lay, '<span style="color:' + COL_MUTED + '">💡 ' + esc(random.choice(tips)) + '</span>', 85)
