from flask import Flask, request, jsonify
from flask_mysqldb import MySQL

from secret_key import HOST, USER, PASSWORD, DB

app = Flask(__name__)

app.config['MYSQL_HOST'] = HOST
app.config['MYSQL_USER'] = USER
app.config['MYSQL_PASSWORD'] = PASSWORD
app.config['MYSQL_DB'] = DB
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'
mysql = MySQL(app)

# Enpoints for Home page ------------------------------------------------------------------------------
@app.route('/')
def home():    
    return "<h1>Daily Deal Web Application</h1>"



if __name__ == '__main__':
    app.run(debug=True)