import datetime
import logging
import os
import time

from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QMainWindow, QScrollArea,
    QVBoxLayout, QWidget,
)

logger = logging.getLogger(__name__)

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
        for t in pendientes:
            # mismo criterio que el CLI (plugins/dashboard): prioridad única
            # (A)-(Z) fuera del inbox; el substring "x 20" en cualquier parte
            # también sale del inbox (quirk heredado: burofax 2024, "x 2026"…)
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
                waiting_pend.append({'task': t, 'edad': max(edad, 0), 'due': due, 'vencida': vencida})

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

        return {
            'hoy': hoy, 'pend': len(pendientes), 'done_total': done_total,
            'cnt': cnt, 'inbox': inbox, 'done_hoy': done_hoy, 'done_sem': done_sem,
            'done_mes': done_mes, 'done_7d': done_7d, 'done_prev': done_prev,
            'velocidad': velocidad, 'est_vaciar': est_vaciar,
            'created_7d': created_7d, 'created_sem': created_sem,
            'balance_neto': balance_neto, 'waiting_pend': waiting_pend,
            'radar_vencidas': radar_vencidas, 'radar_proximas': radar_proximas,
            'vencen_hoy': vencen_hoy, 'dias7': dias7, 'antiguas': antiguas,
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
        card, lay = self._card('📊 Kanban (salud del flujo)')
        for nombre, valor, limite in [
            ("(A) HOY (MITs)", d['cnt']['A'], LIMIT_A),
            ("(B) ESTA SEMANA", d['cnt']['B'], LIMIT_B),
            ("(C) ESTE MES", d['cnt']['C'], 50),
            ("(D) PRÓXIMAS TAREAS", d['cnt']['D'], 100),
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
        card, lay = self._card('♻️ Recurrentes (cron)')
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
        card, lay = self._card('📊 Resumen ejecutivo')
        self._linea(lay,
                    "Pendientes: <b>" + str(d['pend']) + "</b> · Completadas: <b>" + str(d['done_total'])
                    + "</b> · Ratio: <b>" + str(int(round(100.0 * d['done_total'] / max(1, d['pend'] + d['done_total'])))) + "%</b>")
        self._linea(lay,
                    "Hoy: <b>" + str(d['done_hoy']) + "</b> · Esta semana: <b>" + str(d['done_sem'])
                    + "</b> · Este mes: <b>" + str(d['done_mes']) + "</b> · Velocidad: <b>" + str(d['velocidad'])
                    + "</b> tareas/día")
        if d['est_vaciar'] > 0:
            self._linea(lay, '⏱️ Al ritmo actual: <b>~' + str(d['est_vaciar']) + ' días</b> para vaciar (A)+(B)')
        col_bal = COL_VERDE if d['balance_neto'] >= 0 else COL_ROJO
        self._linea(lay, '📥 Creadas (últimos 7d): <b>' + str(d['created_7d']) + '</b> · Balance neto: <span style="color:'
                             + col_bal + '"><b>' + ('+' if d['balance_neto'] >= 0 else '') + str(d['balance_neto'])
                             + '</b></span>')

        # --- S4 · Radar de urgencias ---
        card, lay = self._card('⏰ Radar de urgencias')
        self._linea(lay, "Vencidas: <b>" + str(len(d['radar_vencidas'])) + "</b> · Próximas 7d: <b>"
                             + str(len(d['radar_proximas'])) + "</b>"
                             + ('  ·  🎯 <b>Vencen HOY: ' + str(d['vencen_hoy']) + '</b>' if d['vencen_hoy'] else ''))
        for ddue, tarea in d['radar_vencidas'][:5]:
            dias_atraso = (datetime.date.today() - ddue).days
            self._linea(lay, '🚨 <span style="color:' + COL_ROJO + '"><b>VENCIDA</b> ' + ddue.isoformat()
                                 + ' (hace ' + str(dias_atraso) + 'd)</span> — ' + esc(tarea.text[:60]))
        for ddue, tarea in d['radar_proximas'][:3]:
            self._linea(lay, '⚠️ <span style="color:' + COL_AMARILLO + '"><b>PRÓXIMA</b> ' + ddue.isoformat()
                                 + '</span> — ' + esc(tarea.text[:56]))

        # --- S6 · Progreso de los últimos 7 días ---
        card, lay = self._card('📈 Progreso de los últimos 7 días')
        semana_total = sum(x['n'] for x in d['dias7'])
        for x in d['dias7']:
            dia = x['fecha']
            hoy_marca = '» ' if dia == datetime.date.today() else '   '
            self._linea(lay, '<span style="color:' + COL_MUTED + '">' + dia.isoformat()[5:] + '</span>'
                             + ' · ' + esc(hoy_marca) + '<b>' + str(x['n']) + '</b>', 90)
        self._linea(lay, 'Total de la semana: <b>' + str(semana_total) + '</b> tareas terminadas.')

        # tendencia frente a la semana anterior (rulo = persistente, el CLI usa la misma fórmula)
        if d['done_prev'] > 0:
            pct = int(round((d['done_sem'] - d['done_prev']) * 100.0 / d['done_prev']))
        else:
            pct = 0
        if pct > 0:
            tend = '↑ mejorando (' + str(pct) + '%)'
        elif pct < 0:
            tend = '↓ bajando (' + str(abs(pct)) + '%)'
        else:
            tend = '→ igual'
        col_t = COL_VERDE if pct > 0 else (COL_ROJO if pct < 0 else COL_MUTED)
        self._linea(lay, 'Tendencia: <span style="color:' + col_t + '"><b>' + tend + '</b></span> '
                         + '<span style="color:' + COL_MUTED + '">(esta semana ' + str(d['done_sem'])
                         + ' vs anterior ' + str(d['done_prev'])                          + ')</span>')

        # --- S7 · @waiting delegadas ---
        card, lay = self._card('⏳ Tareas delegadas (@waiting)')
        total_w = len(d['waiting_pend'])
        vencidas_w = sum(1 for x in d['waiting_pend'] if x['vencida'])
        mas7 = sum(1 for x in d['waiting_pend'] if x['edad'] >= 7 and x['edad'] < 30)
        mas30 = sum(1 for x in d['waiting_pend'] if x['edad'] >= 30)
        self._linea(lay, 'Total: <b>' + str(total_w) + '</b> · Vencidas: <span style="color:' + COL_ROJO
                             + '"><b>' + str(vencidas_w) + '</b></span> · +7d: <b>' + str(mas7)
                             + '</b> · +30d: <b>' + str(mas30) + '</b>')
        for x in d['waiting_pend'][:5]:
            t = x['task']
            marca = ' 🚨VENCIDA' if x['vencida'] else ''
            self._linea(lay, '⏳ <b>' + str(x['edad']) + 'd</b> — ' + esc(t.text[:64] + marca))
        if total_w == 0:
            self._linea(lay, '✨ Sin tareas en espera.')
