#!/bin/bash


cp ../../qTodoTxt_style_rc.py ../../qTodoTxt_style_rc.py.bak

pyrcc5 res.qrc -o qTodoTxt_style_rc.py

cp qTodoTxt_style_rc.py ../../qTodoTxt_style_rc.py