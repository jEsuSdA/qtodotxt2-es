import logging
import sys
import re
import unicodedata

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QGridLayout,
    QScrollArea, QFrame, QLabel, QCheckBox, QApplication, QLineEdit, QSizePolicy
)
from PyQt5.QtCore import Qt, QMimeData, pyqtSignal, QTimer, QEvent
from PyQt5.QtGui import QDrag, QPixmap, QPainter, QMouseEvent

logger = logging.getLogger(__name__)


def format_task_html(text):
    """Convierte el texto de una tarea en HTML con proyectos/contextos/enlaces coloreados."""
    if text.startswith('x '):
        text = text[2:]
    text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    text = re.sub(r'(\s|^)(\+\S+)', r'\1<span style="color: #3498db;">\2</span>', text)
    text = re.sub(r'(\s|^)(@\S+)', r'\1<span style="color: #9b59b6;">\2</span>', text)
    text = re.sub(r'(https?://\S+)', r'<a href="\1">\1</a>', text)
    return text


class KanbanTaskWidget(QFrame):
    """
    Final version of the task card widget.
    It expands to fill available width and allows dragging from anywhere on the task.
    """

    PRIORITY_COLORS = {
        'A': '#e74c3c', 'B': '#f39c12', 'C': '#f1c40f',
        'D': '#8fb021', 'NP': '#bdc3c7', 'DONE': '#d0d0d0'
    }

    def __init__(self, task_data, parent=None):
        super().__init__(parent)
        self.task_data = task_data
        self.task_id = task_data['task_id']
        self.task_ref = task_data['task_ref']
        self.setAcceptDrops(False)
        self.setMouseTracking(True)

        # Cachés para saltar setText/setStyleSheet cuando no hay cambios
        self._last_html = None
        self._last_style_key = None

        layout = QGridLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(5)

        self.checkbox = QCheckBox()
        self.checkbox.setChecked(task_data['is_done'])
        self.checkbox.clicked.connect(self.on_checkbox_clicked)

        task_text_html = self._format_task_text(task_data)
        self._last_html = task_text_html
        self.text_label = QLabel(task_text_html)
        self.text_label.setWordWrap(True)
        self.text_label.setOpenExternalLinks(True)

        layout.addWidget(self.checkbox, 0, 0, Qt.AlignTop)
        layout.addWidget(self.text_label, 0, 1)
        layout.setColumnStretch(1, 1)

        self._apply_priority_style(task_data['priority'], task_data['is_done'])

        self.text_label.installEventFilter(self)

    def update_data(self, task_data):
        """Actualizar los datos de un widget existente sin destruirlo.
        Sólo toca Qt cuando algo cambia realmente (caché de HTML y estilo)."""
        self.task_data = task_data
        self.task_id = task_data['task_id']
        self.task_ref = task_data['task_ref']

        if self.checkbox.isChecked() != task_data['is_done']:
            self.checkbox.setChecked(task_data['is_done'])

        html = self._format_task_text(task_data)
        if html != self._last_html:
            self._last_html = html
            self.text_label.setText(html)

        style_key = (task_data['priority'], task_data['is_done'])
        if style_key != self._last_style_key:
            self._apply_priority_style(style_key[0], style_key[1])

    def eventFilter(self, source, event):
        if source is self.text_label:
            if event.type() == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
                mapped_event = QMouseEvent(
                    event.type(), self.mapFromGlobal(event.globalPos()),
                    event.button(), event.buttons(), event.modifiers()
                )
                self.mousePressEvent(mapped_event)
                return False
            elif event.type() == QEvent.MouseMove and event.buttons() & Qt.LeftButton:
                mapped_event = QMouseEvent(
                    event.type(), self.mapFromGlobal(event.globalPos()),
                    event.button(), event.buttons(), event.modifiers()
                )
                self.mouseMoveEvent(mapped_event)
                return True
        return super().eventFilter(source, event)

    def _format_task_text(self, task_data):
        return format_task_html(task_data['text'])

    def _apply_priority_style(self, priority, is_done):
        self._last_style_key = (priority, is_done)
        base_style = (
            "QFrame {{ background-color: #ffffff; border: 1px solid #e0e0e0; "
            "border-radius: 3px; border-left: 5px solid {color}; }}"
        )
        if is_done:
            color = self.PRIORITY_COLORS['DONE']
            self.setStyleSheet(base_style.format(color=color))
            self.text_label.setStyleSheet(
                "font-size: 12px; color: #999; text-decoration: line-through; "
                "background-color: transparent; border: none;"
            )
        else:
            color = self.PRIORITY_COLORS.get(priority, self.PRIORITY_COLORS['NP'])
            self.setStyleSheet(base_style.format(color=color))
            self.text_label.setStyleSheet(
                "font-size: 12px; color: #333; background-color: transparent; border: none;"
            )

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_start_position = event.pos()

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.LeftButton) or not hasattr(self, 'drag_start_position'):
            return
        if (event.pos() - self.drag_start_position).manhattanLength() < QApplication.startDragDistance():
            return
        drag = QDrag(self)
        mime_data = QMimeData()
        mime_data.setText(self.task_id)
        drag.setMimeData(mime_data)
        pixmap = QPixmap(self.size())
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setOpacity(0.75)
        self.render(painter)
        painter.end()
        drag.setPixmap(pixmap)
        drag.exec_(Qt.MoveAction)
        if hasattr(self, 'drag_start_position'):
            del self.drag_start_position

    def on_checkbox_clicked(self, checked):
        parent = self.parent()
        while parent and not isinstance(parent, KanbanColumnWidget):
            parent = parent.parent()
        if parent:
            parent.task_toggled.emit(self.task_id, checked)



class KanbanColumnWidget(QWidget):
    task_dropped = pyqtSignal(str, str)
    task_toggled = pyqtSignal(str, bool)
    HEADER_COLORS = {'A': '#e74c3c', 'B': '#f39c12', 'C': '#f1c40f', 'D': '#8fb021', 'NP': '#7f8c8d'}

    def __init__(self, priority_key, title, parent=None):
        super().__init__(parent)
        self.priority_key = priority_key

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        header = QLabel(title)
        header.setAlignment(Qt.AlignCenter)
        header_color = self.HEADER_COLORS.get(self.priority_key, '#7f8c8d')
        header.setStyleSheet(
            f"QLabel {{ background-color: {header_color}; color: #fff; padding: 10px; "
            f"font-weight: bold; font-size: 14px; }}"
        )
        main_layout.addWidget(header)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setStyleSheet("border: none;")

        self.task_container = QWidget()
        self.task_container.setStyleSheet("background-color: #f5f5f5; border-right: 1px solid #e0e0e0;")

        self.task_layout = QVBoxLayout(self.task_container)
        self.task_layout.setContentsMargins(8, 8, 8, 8)
        self.task_layout.setSpacing(8)
        self.task_layout.addStretch()

        self.scroll_area.setWidget(self.task_container)
        main_layout.addWidget(self.scroll_area)

        # ✅ NP también debe aceptar drops (para quitar prioridad)
        self.setAcceptDrops(True)

    def add_task(self, task_widget):
        self.task_layout.insertWidget(self.task_layout.count() - 1, task_widget)

    def clear(self):
        while self.task_layout.count() > 1:
            child = self.task_layout.takeAt(0).widget()
            if child:
                child.deleteLater()

    def dragEnterEvent(self, event):
        # Acepta sólo drags que tengan texto (task_id)
        txt = event.mimeData().text() if event.mimeData() else ""
        if txt:
            event.acceptProposedAction()

    def dropEvent(self, event):
        txt = event.mimeData().text() if event.mimeData() else ""
        if not txt:
            return
        task_id = txt
        self.task_dropped.emit(task_id, self.priority_key)
        event.acceptProposedAction()


class KanbanWindow(QMainWindow):
    MIN_CONTENT_HEIGHT = 150
    MAX_CONTENT_HEIGHT = 600

    def __init__(self, main_controller, parent=None):
        super().__init__(parent)

        self.main_controller = main_controller
        self.setWindowTitle("QTodoTxt2 - Tablero Kanban")
        self.resize(1920, 1080)

        # --- estado de filtro ---
        self._project_widgets = {}          # project_name -> QWidget(block)
        self._card_pool = []                # pool persistente de tarjetas entre actualizaciones
        self._card_pool_max = 1000          # tope de tarjetas recicladas en memoria
        self._board_built = False           # primer build -> rebuild completo
        self._current_project_filter = ""   # texto actual
        self._filter_timer = QTimer(self)
        self._filter_timer.setSingleShot(True)
        self._filter_timer.setInterval(150)
        self._filter_timer.timeout.connect(self._apply_project_filter)

        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # =====================
        # HEADER + filtro
        # =====================
        header = QWidget()
        header.setStyleSheet("QWidget { background-color: #2c3e50; padding: 5px; }")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(10, 10, 10, 10)

        title = QLabel("Tablero Kanban")
        title.setStyleSheet("color: white; font-size: 20px; font-weight: bold;")
        header_layout.addWidget(title)

        header_layout.addStretch()

        self.project_filter = QLineEdit()
        self.project_filter.setPlaceholderText("Filtrar proyectos…")
        self.project_filter.setClearButtonEnabled(True)
        self.project_filter.setFixedWidth(360)
        self.project_filter.setStyleSheet(
            "QLineEdit { background: white; border-radius: 4px; padding: 6px 10px; }"
        )
        self.project_filter.textChanged.connect(self._on_project_filter_text_changed)
        header_layout.addWidget(self.project_filter)

        self.filter_count_label = QLabel("")
        self.filter_count_label.setStyleSheet("color: #ecf0f1; padding-left: 10px;")
        header_layout.addWidget(self.filter_count_label)

        main_layout.addWidget(header)

        # =====================
        # SCROLL AREA
        # =====================
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea { border: none; }")
        main_layout.addWidget(scroll)

        self.projects_container = QWidget()
        self.projects_layout = QVBoxLayout(self.projects_container)
        self.projects_layout.setSpacing(20)
        self.projects_layout.setContentsMargins(0, 20, 0, 20)
        scroll.setWidget(self.projects_container)

        self.controller = main_controller.kanban_controller if hasattr(main_controller, 'kanban_controller') else None
        if self.controller:
            self.controller.kanbanDataChanged.connect(self._on_kanban_data_changed)

        self._refresh_board()

    # -------------------------
    # Normalización de texto (sin acentos, case-insensitive)
    # -------------------------
    def _norm(self, s: str) -> str:
        if not s:
            return ""
        s = s.strip().lower()
        s = unicodedata.normalize("NFD", s)
        s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")  # quita acentos
        return s

    # -------------------------
    # Filtro (debounce)
    # -------------------------
    def _on_project_filter_text_changed(self, text: str):
        self._current_project_filter = text or ""
        self._filter_timer.start()

    def _apply_project_filter(self):
        needle = self._norm(self._current_project_filter)
        total = len(self._project_widgets)
        shown = 0

        if needle == "":
            for _, w in self._project_widgets.items():
                w.setVisible(True)
                shown += 1
            self.filter_count_label.setText(f"Mostrando {shown}/{total}")
            QTimer.singleShot(0, self._adjust_columns_height_for_filter)
            return

        for project_name, w in self._project_widgets.items():
            hay = self._norm(project_name)
            match = (needle in hay)
            w.setVisible(match)
            if match:
                shown += 1

        self.filter_count_label.setText(f"Mostrando {shown}/{total}")
        QTimer.singleShot(0, self._adjust_columns_height_for_filter)

    # -------------------------
    # Ajuste de altura kanban cuando filtro activo
    # -------------------------
    def _adjust_columns_height_for_filter(self):
        """
        When a project filter is active, expand visible project blocks so that each column
        shows all tasks without internal vertical scrolling. When filter is empty, restore
        normal capped height + per-column scrolling.
        """
        filter_active = bool(self._norm(self._current_project_filter))

        for _, block in self._project_widgets.items():
            # En modo normal siempre visibles, en modo filtro sólo ajustamos visibles
            if filter_active and not block.isVisible():
                continue

            columns = block.findChildren(KanbanColumnWidget)
            if not columns:
                continue

            # Fuerza recalculo del layout antes de medir (clave para wordWrap)
            if block.layout():
                block.layout().activate()

            for col in columns:
                if col.task_container.layout():
                    col.task_container.layout().activate()
                col.task_container.adjustSize()

            max_content_height = 0
            for col in columns:
                max_content_height = max(max_content_height, col.task_container.sizeHint().height())

            if filter_active:
                target_height = max_content_height

                for col in columns:
                    col.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

                    # Bloqueo reversible: min = max
                    col.scroll_area.setMinimumHeight(target_height)
                    col.scroll_area.setMaximumHeight(target_height)

                    # Evita que el layout "infle" el scroll_area
                    col.scroll_area.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
            else:
                target_height = max(self.MIN_CONTENT_HEIGHT, max_content_height)
                target_height = min(self.MAX_CONTENT_HEIGHT, target_height)

                for col in columns:
                    col.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

                    col.scroll_area.setMinimumHeight(target_height)
                    col.scroll_area.setMaximumHeight(16777215)  # libera el lock

                    col.scroll_area.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)

    # -------------------------
    # Ajuste de tamaños cuando cambia tamaño de la ventana
    # -------------------------
    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._norm(self._current_project_filter):
            QTimer.singleShot(0, self._adjust_columns_height_for_filter)

    # -------------------------
    # Al reabrir la ventana: reconstruir si quedó pendiente estando oculta
    # -------------------------
    def showEvent(self, event):
        super().showEvent(event)
        if self.controller is not None:
            self.controller.consume_dirty()

    # -------------------------
    # Board build / update
    # -------------------------
    def _on_kanban_data_changed(self):
        """Aplica los datos al tablero: diff incremental con fallback a rebuild completo."""
        if self.controller is None:
            return
        kanban_data = self.controller.kanbanData or {}
        try:
            if not self._board_built:
                self._refresh_board()
                return
            self._apply_data(kanban_data)
        except Exception:
            logger.exception("Diff incremental falló; aplicando rebuild completo")
            self._refresh_board()

    def _refresh_board(self):
        # Rebuild completo: red de seguridad y primera construcción.
        # 1. Reciclar todas las tarjetas al pool persistente
        for block in self._project_widgets.values():
            cards = getattr(block, '_cards', None)
            if cards:
                for w in list(cards.values()):
                    self._recycle_card(w)
                cards.clear()
                getattr(block, '_card_cols', {}).clear()

        # 2. Destruir project blocks (las columnas se destruyen con ellos)
        while self.projects_layout.count() > 0:
            child_item = self.projects_layout.takeAt(0)
            child = child_item.widget()
            if child:
                child.deleteLater()

        self._project_widgets.clear()

        kanban_data = self.controller.kanbanData if self.controller else {}

        for project_name, project_data in kanban_data.items():
            has_tasks = any(len(project_data['tasks'][prio]) > 0 for prio in ['NP', 'D', 'C', 'B', 'A'])
            if not has_tasks and project_name == '(Sin Proyecto)':
                continue

            project_block = self._create_project_block(project_name, project_data)
            self.projects_layout.addWidget(project_block)
            self._project_widgets[project_name] = project_block

        self.projects_layout.addStretch()
        self._board_built = True

        # reaplica filtro actual tras reconstrucción
        if self._norm(self._current_project_filter):
            self._apply_project_filter()
        else:
            total = len(self._project_widgets)
            self.filter_count_label.setText(f"Mostrando {total}/{total}")

    def _apply_data(self, kanban_data):
        """Actualización diferencial: crea/elimina bloques, mueve y actualiza tarjetas."""
        # proyectos efectivos (la bandeja de entrada vacía no muestra bloque)
        effective = {}
        for name, pdata in kanban_data.items():
            if name == '(Sin Proyecto)' and not any(pdata['tasks'].values()):
                continue
            effective[name] = pdata

        # actualizar existentes o crear nuevos
        for name, pdata in effective.items():
            block = self._project_widgets.get(name)
            if block is None or not hasattr(block, '_cards'):
                self._remove_block(name)
                block = self._create_project_block(name, pdata)
                self._project_widgets[name] = block
                self.projects_layout.addWidget(block)
            else:
                self._update_project_block(block, pdata)

        # eliminar bloques que ya no deben estar
        for name in list(self._project_widgets.keys()):
            if name not in effective:
                self._remove_block(name)

        # reordenar bloques según el orden de los datos
        self._reorder_projects(list(effective.keys()))

        # reaplica filtro actual tras actualización (igual que _refresh_board)
        if self._norm(self._current_project_filter):
            self._apply_project_filter()
        else:
            total = len(self._project_widgets)
            self.filter_count_label.setText(f"Mostrando {total}/{total}")

    def _update_project_block(self, block, project_data):
        """Diff de tarjetas de un bloque: altas, bajas, cambios de columna, datos y orden."""
        columns = block._columns
        cards = block._cards
        card_cols = block._card_cols

        # conjunto deseado: task_id -> (prio, task_data)
        desired = {}
        for prio, tasks in project_data['tasks'].items():
            if prio not in columns:
                continue
            for td in tasks:
                desired[td['task_id']] = (prio, td)

        # 1) retirar tarjetas que ya no corresponden
        for tid in list(cards.keys()):
            if tid not in desired:
                widget = cards.pop(tid)
                card_cols.pop(tid, None)
                self._recycle_card(widget)

        # 2) añadir nuevas, mover entre columnas y actualizar datos
        seen = set()
        for prio, tasks in project_data['tasks'].items():
            if prio not in columns:
                continue
            column = columns[prio]
            for td in tasks:
                tid = td['task_id']
                if tid in seen:
                    continue
                seen.add(tid)
                widget = cards.get(tid)
                if widget is None:
                    widget = self._obtain_card(td)
                    cards[tid] = widget
                    card_cols[tid] = prio
                    column.add_task(widget)
                elif card_cols.get(tid) != prio:
                    old_column = columns.get(card_cols.get(tid))
                    if old_column is not None:
                        old_column.task_layout.removeWidget(widget)
                    column.add_task(widget)
                    card_cols[tid] = prio
                widget.update_data(td)

        # 3) reordenar dentro de cada columna según el orden de los datos
        for prio, tasks in project_data['tasks'].items():
            if prio not in columns:
                continue
            layout = columns[prio].task_layout
            for pos, td in enumerate(tasks):
                tid = td['task_id']
                widget = cards.get(tid)
                if widget is None or card_cols.get(tid) != prio:
                    continue
                if layout.indexOf(widget) != pos:
                    layout.insertWidget(pos, widget)

    def _reorder_projects(self, ordered_names):
        """Recoloca los bloques para reflejar el orden de los datos (el stretch queda al final)."""
        layout = self.projects_layout
        for idx, name in enumerate(ordered_names):
            block = self._project_widgets.get(name)
            if block is None:
                continue
            target = min(idx, layout.count() - 1)
            if layout.indexOf(block) != target:
                layout.insertWidget(target, block)

    def _remove_block(self, name):
        block = self._project_widgets.pop(name, None)
        if block is None:
            return
        cards = getattr(block, '_cards', None)
        if cards:
            for w in list(cards.values()):
                self._recycle_card(w)
            cards.clear()
            getattr(block, '_card_cols', {}).clear()
        self.projects_layout.removeWidget(block)
        block.setParent(None)
        block.deleteLater()

    def _obtain_card(self, task_data):
        """Tarjeta del pool persistente o nueva; siempre actualizada con los datos dados."""
        if self._card_pool:
            widget = self._card_pool.pop()
        else:
            widget = KanbanTaskWidget(task_data)
        widget.update_data(task_data)
        return widget

    def _recycle_card(self, widget):
        """Devuelve una tarjeta al pool persistente (o la destruye si el tope se alcanzó)."""
        widget.setParent(None)
        if len(self._card_pool) < self._card_pool_max:
            self._card_pool.append(widget)
        else:
            widget.deleteLater()

    def _create_project_block(self, project_name, project_data):
        block = QWidget()
        block_layout = QVBoxLayout(block)
        block_layout.setContentsMargins(0, 0, 0, 0)

        if project_name != '(Sin Proyecto)':
            title = QLabel(f"{project_name}")
            title.setAlignment(Qt.AlignCenter)
            title.setStyleSheet(
                "QLabel { background-color: #2c3e50; color: white; padding: 12px; "
                "font-size: 16px; font-weight: bold; border-radius: 0; margin: 0; }"
            )
            block_layout.addWidget(title)

        columns_container = QWidget()
        columns_layout = QHBoxLayout(columns_container)
        columns_layout.setSpacing(0)
        columns_layout.setContentsMargins(0, 0, 0, 0)

        block_columns = {}
        if self.controller:
            for prio, title in self.controller.columns.items():
                column = KanbanColumnWidget(prio, title)
                column.task_dropped.connect(self.on_task_moved)
                column.task_toggled.connect(self.on_task_toggled)
                block_columns[prio] = column
                columns_layout.addWidget(column)

        # registros para el diff incremental
        block._columns = block_columns
        block._cards = {}
        block._card_cols = {}

        for prio, tasks in project_data['tasks'].items():
            if prio in block_columns:
                for task_data in tasks:
                    widget = self._obtain_card(task_data)
                    block._cards[task_data['task_id']] = widget
                    block._card_cols[task_data['task_id']] = prio
                    block_columns[prio].add_task(widget)

        # Altura base: estimacion sin sizeHint() (mucho mas rapida)
        max_tasks = max(len(tasks) for tasks in project_data['tasks'].values())
        target_height = max(50 * max_tasks, self.MIN_CONTENT_HEIGHT)
        target_height = min(target_height, self.MAX_CONTENT_HEIGHT)

        for column in block_columns.values():
            column.scroll_area.setMinimumHeight(target_height)
            column.scroll_area.setMaximumHeight(16777215)
            column.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            column.scroll_area.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)

        block_layout.addWidget(columns_container)
        return block

    def on_task_moved(self, task_id, new_priority):
        """Handle task moved between columns."""
        self.controller.update_task_priority(task_id, new_priority)

    def on_task_toggled(self, task_id, is_done):
        """Handle task completion toggle."""
        self.controller.toggle_task_done(task_id, is_done)

    def update_task_widget(self, task_id, is_done=None, priority=None):
        """Actualizar widget(s) in-place sin reconstruir el tablero."""
        for block in self._project_widgets.values():
            for w in block.findChildren(KanbanTaskWidget):
                if w.task_id == task_id:
                    w.task_data['text'] = w.task_ref.text
                    if is_done is not None:
                        w.task_data['is_done'] = is_done
                    if priority is not None:
                        w.task_data['priority'] = priority
                    w.update_data(w.task_data)

    def move_task_widget(self, task_id, new_priority):
        """Mover widget entre columnas sin reconstruir el tablero."""
        for block in self._project_widgets.values():
            widget = None
            old_column = None
            for col in block.findChildren(KanbanColumnWidget):
                for w in col.findChildren(KanbanTaskWidget):
                    if w.task_id == task_id:
                        widget = w
                        old_column = col
                        break
                if widget:
                    break
            if not widget:
                continue
            # mantener los registros del diff coherentes con el movimiento incremental
            cards = getattr(block, '_cards', None)
            card_cols = getattr(block, '_card_cols', None)
            if cards is not None:
                cards.setdefault(task_id, widget)
            new_column = None
            for col in block.findChildren(KanbanColumnWidget):
                if col.priority_key == new_priority:
                    new_column = col
                    break
            if new_column and old_column != new_column:
                old_column.task_layout.removeWidget(widget)
                new_column.add_task(widget)
            if card_cols is not None:
                card_cols[task_id] = new_priority
            widget.task_data['text'] = widget.task_ref.text
            widget.task_data['priority'] = new_priority if new_priority != 'NP' else ''
            widget.update_data(widget.task_data)

#    def _check_file_changes(self):
#        if hasattr(self.main_controller._file, 'filename') and self.main_controller._file.filename:
#            import os
#            try:
#                current_mtime = os.path.getmtime(self.main_controller._file.filename)
#                if current_mtime > self.last_modified:
#                    self.last_modified = current_mtime
#                    self.main_controller._file.load(self.main_controller._file.filename)
#            except:
#                pass
