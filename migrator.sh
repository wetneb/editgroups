#!/usr/bin/env bash

set -e

VENV_DIR=/data/project/editgroups/listener_venv

if [[ -f ${VENV_DIR}/bin/activate ]]; then
      source ${VENV_DIR}/bin/activate
else
      echo "Creating virtualenv"
      rm -rf ${VENV_DIR}
      pyvenv ${VENV_DIR}
      source ${VENV_DIR}/bin/activate
      echo "Installing requirements"
      pip install -r requirements.txt
fi;
echo "Launching migrator"
python3 manage.py migrate
echo "Migrator terminated"
sleep 10
