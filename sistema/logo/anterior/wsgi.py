# -*- coding: utf-8 -*-
"""Ponto de entrada para o gunicorn.  Uso:  gunicorn -c gunicorn.conf.py wsgi:app"""
from app import app
