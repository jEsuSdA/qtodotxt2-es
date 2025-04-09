#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import logging
import sys
import os

from PyQt5 import QtCore
from PyQt5 import QtWidgets
from PyQt5 import QtGui
from PyQt5.QtQml import QQmlApplicationEngine

import qtodotxt2.qTodoTxt_style_rc

from qtodotxt2.main_controller import MainController
from qtodotxt2.lib.file import FileObserver
from qtodotxt2.lib.tendo_singleton import SingleInstance


def _parseArgs():
    if len(sys.argv) > 1 and sys.argv[1].startswith('-psn'):
        del sys.argv[1]
    parser = argparse.ArgumentParser(description='QTodoTxt2')
    parser.add_argument('file', type=str, nargs='?', metavar='TEXTFILE', help='abrir archivo específico')
    parser.add_argument(
        '-l',
        '--loglevel',
        type=str,
        nargs=1,
        metavar='LOGLEVEL',
        default=['WARN'],
        choices=['DEBUG', 'INFO', 'WARNING', 'WARN', 'ERROR', 'CRITICAL'],
        help='indica uno de estos niveles de log: DEBUG, INFO, WARNING, ERROR, CRITICAL')
    return parser.parse_args()


def _setupLogging(loglevel):
    numeric_level = getattr(logging, loglevel[0].upper(), None)
    if isinstance(numeric_level, int):
        logging.basicConfig(
            format='{asctime}.{msecs:.0f} [{name}] {levelname}: {message}',
            level=numeric_level,
            style='{',
            datefmt='%H:%M:%S')


def setupAnotherInstanceEvent(controller):
    # Connecting to a processor reading TMP file
    needSingleton = QtCore.QSettings().value("Preferences/singleton", False, type=bool)
    if needSingleton:
        dirname = os.path.dirname(sys.argv[0])
        fileObserver = FileObserver()
        fileObserver.addPath(dirname)
        #FIXME maybe do something in qml
        #fileObserver.dirChangetSig.connect(controller.anotherInstanceEvent)


def setupSingleton(args):
    needSingleton = QtCore.QSettings().value("Preferences/singleton", False, type=bool)
    if int(needSingleton):
        me = SingleInstance()
        dirname = os.path.dirname(sys.argv[0])
        tempFileName = dirname + "/qtodo.tmp"
        if me.initialized is True:
            if os.path.isfile(tempFileName):
                os.remove(tempFileName)
        else:
            f = open(tempFileName, 'w')
            f.flush()
            f.close()
            sys.exit(-1)


def run():
    # First set some application settings for QSettings
    QtCore.QCoreApplication.setOrganizationName("QTodoTxt")
    QtCore.QCoreApplication.setApplicationName("QTodoTxt2")
    # Now set up our application and start
    app = QtWidgets.QApplication(sys.argv)
    # it is said, that this is lighter:
    # (without qwidgets, as we probably don't need them anymore, when transition to qml is done)
    # app = QtGui.QGuiApplication(sys.argv)
    name = QtCore.QLocale.system().name()
    system_locale_name = QtCore.QLocale.system().name()
    target_locale = "es_ES" # El idioma que queremos cargar
    print(f"Locale del sistema detectado: {system_locale_name}")
    print(f"Intentando cargar locale: {name}")
    translator = QtCore.QTranslator()
    # 3. Intentar cargar el archivo .qm específico (es_ES.qm)
    translation_dir = "../i18n"
    qm_filename = f"{target_locale}.qm"
    loaded = translator.load(qm_filename, translation_dir)
    
    # 4. Comprobar si la carga fue exitosa e instalar
    if loaded:
    	installed = app.installTranslator(translator)
    	if installed:
    		print(f"Traducción '{qm_filename}' cargada e instalada correctamente.")
    	else:
    		print(f"ERROR: Se cargó '{qm_filename}' pero falló la instalación en la app.")
    else:
    	print(f"ERROR: No se pudo cargar el archivo de traducción '{qm_filename}' desde '{translation_dir}'.")
    	print("Verifica que:")
    	print(f"  1. El archivo '{qm_filename}' existe en la carpeta indicada.")
    	print(f"  2. La ruta '{translation_dir}' es correcta.")
    	print(f"  3. El archivo .qm no está corrupto (regenerarlo con lrelease si es necesario).")

		# --- Fin del bloque de traducción modificado ---    
    
    #if translator.load(str(name) + ".qm", "..//i18n"):
    #    app.installTranslator(translator)

    args = _parseArgs()

    setupSingleton(args)

    _setupLogging(args.loglevel)

    engine = QQmlApplicationEngine(parent=app)
    controller = MainController(args)
    engine.rootContext().setContextProperty("mainController", controller)
    path = os.path.join(os.path.dirname(__file__), 'qml')
    engine.addImportPath(path)
    mainqml = os.path.join(path, 'QTodoTxt.qml')
    engine.load(mainqml)

    setupAnotherInstanceEvent(controller)

    controller.start()
    app.setWindowIcon(QtGui.QIcon(":/qtodotxt"))
    app.exec_()
    sys.exit()


if __name__ == "__main__":
    run()
