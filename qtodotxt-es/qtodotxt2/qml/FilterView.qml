import QtQuick 2.5
import QtQuick.Controls 1.4
import QtQml.Models 2.2
import Qt.labs.settings 1.0

import Theme 1.0

TreeView {
    id: treeView
    alternatingRowColors: false

    model: mainController ? mainController.filtersModel : null
    
    selectionMode: SelectionMode.ExtendedSelection
    horizontalScrollBarPolicy: Qt.ScrollBarAlwaysOff
    selection: ItemSelectionModel {
        model: mainController ? mainController.filtersModel : null
        
        onSelectedIndexesChanged: {
            if (!mainController) return;
            taskListView.storeSelection()
            mainController.filterByIndexes(selectedIndexes)
            taskListView.restoreSelection()
        }
    }

    Settings {
        category: "WindowState"
        property alias filter_name_column_width: filterNameCol.width
        property alias filter_total_column_width: totalCol.width
        property alias filter_completed_column_width: completedCol.width
    }

    TableViewColumn {
        id: filterNameCol
        title: "Filtros"
        role: "display"
        delegate: Row {
            spacing: Theme.smallSpace
            height: lbl.implicitHeight + Theme.mediumSpace
            width: filterNameCol.width
            
            Image {
                id: img
                height: 16
                fillMode: Image.PreserveAspectFit
                anchors.verticalCenter: parent.verticalCenter

                source: mainController && mainController.filtersModel ? 
                        Theme.iconSource(mainController.filtersModel.iconFromIndex(styleData.index)) : 
                        ""
            }
            
            Label {
                id: lbl
                anchors.verticalCenter: parent.verticalCenter
                width: parent.width - img.width
                text: styleData.value
                elide: styleData.elideMode
            }
        }
    }

    TableViewColumn {
        id: totalCol
        width: 50
        title: "Tareas"
        role: "totalCount"
    }

    TableViewColumn {
        id: completedCol
        width: 50
        title: "Completas"
        role: "completedCount"
    }

    onClicked: {
        if (mainController) {  
            selection.select(index, ItemSelectionModel.Select | ItemSelectionModel.Current)
        }
    }
    
    function expandAll() {
        if (!model || !model.getRootChildren) return; 
        var rootChildren = model.getRootChildren()
        for (var i = 0; i < rootChildren.length; i++) {
            treeView.expand(rootChildren[i])
        }
    }
}