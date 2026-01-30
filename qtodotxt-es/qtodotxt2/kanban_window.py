import sys
import re
import unicodedata

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QGridLayout,
    QScrollArea, QFrame, QLabel, QCheckBox, QApplication, QLineEdit, QSizePolicy
)
from PyQt5.QtCore import Qt, QMimeData, pyqtSignal, QTimer, QEvent
from PyQt5.QtGui import QDrag, QPixmap, QPainter, QMouseEvent


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
        self.line_index = task_data['line_index']
        self.setAcceptDrops(False)
        self.setMouseTracking(True)

        layout = QGridLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(5)

        self.checkbox = QCheckBox()
        self.checkbox.setChecked(task_data['is_done'])
        self.checkbox.clicked.connect(self.on_checkbox_clicked)

        task_text_html = self._format_task_text(task_data)
        self.text_label = QLabel(task_text_html)
        self.text_label.setWordWrap(True)
        self.text_label.setOpenExternalLinks(True)

        layout.addWidget(self.checkbox, 0, 0, Qt.AlignTop)
        layout.addWidget(self.text_label, 0, 1)
        layout.setColumnStretch(1, 1)

        self._apply_priority_style(task_data['priority'], task_data['is_done'])

        self.text_label.installEventFilter(self)

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
        text = task_data['text']
        if text.startswith('x '):
            text = text[2:]
        text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        text = re.sub(r'(\s|^)(\+\S+)', r'\1<span style="color: #3498db;">\2</span>', text)
        text = re.sub(r'(\s|^)(@\S+)', r'\1<span style="color: #9b59b6;">\2</span>', text)
        text = re.sub(r'(https?://\S+)', r'<a href="\1">\1</a>', text)
        return text

    def _apply_priority_style(self, priority, is_done):
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
        mime_data.setText(str(self.line_index))
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
            parent.task_toggled.emit(self.line_index, checked)



class KanbanColumnWidget(QWidget):
    task_dropped = pyqtSignal(int, str)
    task_toggled = pyqtSignal(int, bool)
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
        # Acepta sólo drags que tengan un texto numérico (line_index)
        txt = event.mimeData().text() if event.mimeData() else ""
        if txt.isdigit():
            event.acceptProposedAction()

    def dropEvent(self, event):
        txt = event.mimeData().text() if event.mimeData() else ""
        if not txt.isdigit():
            return
        line_index = int(txt)
        self.task_dropped.emit(line_index, self.priority_key)
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
            self.controller.kanbanDataChanged.connect(self._refresh_board)

        self._refresh_board()

        #self.timer = QTimer()
        #self.timer.timeout.connect(self._check_file_changes)
        #self.timer.start(5000)
        #self.last_modified = 0

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
    # Board build
    # -------------------------
    def _refresh_board(self):
        # limpia layout y mapa
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

        # reaplica filtro actual tras reconstrucción
        self._apply_project_filter()

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

        for prio, tasks in project_data['tasks'].items():
            if prio in block_columns:
                for task_data in tasks:
                    task_widget = KanbanTaskWidget(task_data)
                    block_columns[prio].add_task(task_widget)

        # Altura base (modo normal)
        max_content_height = 0
        for column in block_columns.values():
            max_content_height = max(max_content_height, column.task_container.sizeHint().height())

        target_height = max(self.MIN_CONTENT_HEIGHT, max_content_height)
        target_height = min(self.MAX_CONTENT_HEIGHT, target_height)

        for column in block_columns.values():
            column.scroll_area.setMinimumHeight(target_height)
            column.scroll_area.setMaximumHeight(16777215)
            column.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            column.scroll_area.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)

        block_layout.addWidget(columns_container)
        return block

    def on_task_moved(self, line_index, new_priority):
        """Handle task moved between columns."""
        self.controller.update_task_priority(line_index, new_priority)

    def on_task_toggled(self, line_index, is_done):
        """Handle task completion toggle."""
        self.controller.toggle_task_done(line_index, is_done)

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
