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
    title: mainController.title

    Timer {
        id: timer
    }

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
        onError: {
            errorDialog.text = msg
            errorDialog.open()
        }
        onFileExternallyModified: {
            if ( mainController.canAutoReload() ) {
                delay(1000, function() {
                    mainController.reload()
                })
            } else {
                reloadDialog.open()
            }
        }
        onFiltersUpdated: {
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
        if ( mainController.canExit() ) {
            close.accepted = true
        } else {
            close.accepted = false
            confirmExitDialog.open()
        }
    }

    Actions {
        id: actions
    }

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
        onYes: mainController.reload() 
    }

    MessageDialog {
        id: confirmExitDialog
        title: "Archivo no guardado"
        icon: StandardIcon.Question
        text: "Tu archivo todo.txt no ha sido guardado. ¿Deseas forzar la salida?"
        standardButtons: StandardButton.Yes | StandardButton.No | StandardButton.Cancel
        onYes: {
            Qt.quit()
        }
    }

    SystemPalette {
        id: systemPalette
    }

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
                    mainController.searchText = text
                    searchField.focus = true
                }

                CompletionPopup { }
            }

            TaskListTableView {
                id: taskListView
                Layout.fillHeight: true
                Layout.fillWidth: true

                taskList: mainController.filteredTasks
            }
        }
    }
    Component.onDestruction: {
        taskListView.quitEditing()
    }
}
