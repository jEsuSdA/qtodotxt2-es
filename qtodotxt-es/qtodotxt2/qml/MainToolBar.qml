import QtQuick 2.5
import QtQuick.Controls 1.4
import QtQuick.Layouts 1.1
import QtQuick 2.5 as QQ
import "Theme" as Theme

ToolBar {
    id: root

    // Paleta del sistema (siempre existe y siempre tiene .mid)
    SystemPalette { id: sysPal; colorGroup: SystemPalette.Active }

    // Elegante: Theme.activePalette si existe, si no fallback a sysPal
    property var _pal: (Theme.activePalette !== undefined && Theme.activePalette !== null) ? Theme.activePalette : sysPal
    property color separatorColor: _pal.mid

    // Separador reutilizable
    Component {
        id: vSeparator
        Rectangle {
            Layout.preferredWidth: 1
            Layout.preferredHeight: 16
            Layout.alignment: Qt.AlignVCenter
            color: root.separatorColor
        }
    }

    RowLayout {
        anchors.fill: parent

        ToolButton { action: actions.showSearchAction }
        ToolButton { action: actions.showFilterPanel }
        ToolButton { action: actions.showCompleted }

        Loader { sourceComponent: vSeparator }

        ToolButton { action: actions.fileSave }

        Loader { sourceComponent: vSeparator }

        ToolButton { action: actions.newTask }
        ToolButton { action: actions.newTaskFrom }
        ToolButton { action: actions.editTask }
        ToolButton { action: actions.deleteTask }
        ToolButton { action: actions.completeTasks }

        Loader { sourceComponent: vSeparator }

        ToolButton { action: actions.increasePriority }
        ToolButton { action: actions.decreasePriority }

        Loader { sourceComponent: vSeparator }

        ToolButton { action: actions.archive }

        Loader { sourceComponent: vSeparator }

        ToolButton { action: actions.addLink }

        Loader { sourceComponent: vSeparator }

        ToolButton {
            id: kanbanButton
            iconSource: "qrc:///white_icons/resources/white/Kanban.svg"
            onClicked: mainController.openKanbanView()
        }

        Item { Layout.fillWidth: true }
    }
}
