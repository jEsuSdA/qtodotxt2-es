import QtQuick 2.5
import QtQuick.Controls 1.4
import QtQuick.Layouts 1.1
import QtQuick.Dialogs 1.1
import QtQuick.Window 2.1
import QtQml 2.2
import QtQml.Models 2.2
import Qt.labs.settings 1.0

import Theme 1.0

ApplicationWindow {
    id: appWindow
    visible: true
    width: 1024
    height: 768

    // =========================
    // NULL OBJECT (fallback)
    // =========================
    QtObject {
        id: nullMain
        property string title: "QTodoTxt"
        property var filteredTasks: []
        property string searchText: ""

        // Señales/métodos usados desde QML
        function canExit() { return true }
        function canAutoReload() { return false }
        function reload() { /* noop */ }
    }

    // Controller seguro
    property var mc: (mainController !== null && mainController !== undefined) ? mainController : nullMain

    title: mc.title

    Timer { id: timer }

    // Adapted from:
    // https://stackoverflow.com/questions/28507619/how-to-create-delay-function-in-qml
    function delay(delayTime, cb) {
        timer.interval = delayTime;
        timer.repeat = false;
        timer.triggered.connect(cb);
        timer.triggered.connect(function release () {
            timer.triggered.disconnect(cb);
            timer.triggered.disconnect(release);
        });
        timer.start();
    }

    Connections {
        target: mainController
        ignoreUnknownSignals: true

        function onError(msg) {
            errorDialog.text = msg
            errorDialog.open()
        }
        function onFileExternallyModified() {
            if (mc.canAutoReload()) {
                delay(1000, function() { mc.reload() })
            } else {
                reloadDialog.open()
            }
        }
        function onFiltersUpdated() {
            filtersTree.expandAll()
        }
    }

    Settings {
        category: "WindowState"
        property alias window_x: appWindow.x
        property alias window_y: appWindow.y
        property alias window_width: appWindow.width
        property alias window_height: appWindow.height
        property alias filters_tree_width: filtersTree.width
    }

    onClosing: {
        if (mc.canExit()) {
            close.accepted = true
        } else {
            close.accepted = false
            confirmExitDialog.open()
        }
    }

    Actions { id: actions }

    menuBar: MainMenu { }

    toolBar: MainToolBar {
        visible: actions.showToolBarAction.checked
    }

    MessageDialog {
        id: errorDialog
        title: "QTodotTxt Error"
        text: "Mensaje de error debería ir aquí!"
    }

    MessageDialog {
        id: reloadDialog
        title: "Archivo modificado externamente"
        icon: StandardIcon.Question
        text: "Tu archivo todo.txt ha sido modificado externamente. ¿Recargar la versión actualizada?"
        standardButtons: StandardButton.Yes | StandardButton.No
        onYes: mc.reload()
    }

    MessageDialog {
        id: confirmExitDialog
        title: "Archivo no guardado"
        icon: StandardIcon.Question
        text: "Tu archivo todo.txt no ha sido guardado. ¿Deseas forzar la salida?"
        standardButtons: StandardButton.Yes | StandardButton.No | StandardButton.Cancel
        onYes: Qt.quit()
    }

    SystemPalette { id: systemPalette }

    SplitView {
        id: splitView
        anchors.fill: parent
        orientation: Qt.Horizontal

        FilterView {
            id: filtersTree
            Layout.minimumWidth: 150
            Layout.fillHeight: true
            visible: actions.showFilterPanel.checked
        }

        ColumnLayout {
            Layout.minimumWidth: 50
            Layout.fillWidth: true

            TextField {
                id: searchField
                Layout.fillWidth: true
                visible: actions.showSearchAction.checked

                placeholderText: "Buscar..."
                onTextChanged: {
                    mc.searchText = text
                    searchField.focus = true
                }

                CompletionPopup { }
            }

            TaskListTableView {
                id: taskListView
                Layout.fillHeight: true
                Layout.fillWidth: true

                taskList: mc.filteredTasks
            }
        }
    }

    Component.onDestruction: {
        taskListView.quitEditing()
    }
}
