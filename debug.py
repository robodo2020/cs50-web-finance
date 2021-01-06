import os

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

def getkey(list, value):
    return [k for k, v in dict.items() if v == value]

db = SQL("sqlite:///finance.db")

stock_table = db.execute("SELECT Symbol, Name, Shares, Price, TOTAL FROM personal")


UserStock = db.execute("SELECT * FROM holdings WHERE Symbol = 'TSLA' ")
print (UserStock)
