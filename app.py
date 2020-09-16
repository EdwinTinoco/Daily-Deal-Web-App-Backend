from flask import Flask, request, jsonify
from flask_mysqldb import MySQL
from flask_cors import CORS
import bcrypt

from secret_key import HOST, USER, PASSWORD, DB

app = Flask(__name__)
CORS(app)

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

# Enpoints for users table------------------------------------------------------------------------
@app.route('/api/user/signup', methods=['POST'])
def signup_user(): 
   user_role_title = request.json['role']
   user_name = request.json['name']
   user_email = request.json['email']
   user_password = request.json['password']
   user_active = request.json['active']

   cur = mysql.connection.cursor()
   cur.callproc("spCheckEmailExist", ())
   emails = cur.fetchall()
   cur.close() 

   ban = False
   for row in emails:
      if row['user_email'] == user_email:
         ban = True

   if ban:
      return 'A user with that email already exist'
   else:
      hashed = bcrypt.hashpw(user_password.encode('utf-8'), bcrypt.gensalt())
      
      cur = mysql.connection.cursor()
      cur.callproc("spInsertNewUser", [user_role_title, user_name, user_email, hashed, user_active])
      mysql.connection.commit()
      cur.close()

      return jsonify('User registered successfully')


# POST LOGIN USER
@app.route('/api/user/login', methods=['POST'])
def login_user():
   user_email = request.json['email']
   user_password = request.json['password']  

   cur = mysql.connection.cursor()
   cur.callproc("spCheckEmailExist", ())
   emails = cur.fetchall()
   cur.close() 

   ban = False
   for row in emails:
      if row['user_email'] == user_email:
         ban = True
         hash_password = row["user_password"]

   if ban:      
      if bcrypt.checkpw(user_password.encode('utf-8'), hash_password.encode('utf-8')):
         cur = mysql.connection.cursor()
         cur.callproc("spLoginUser", [user_email, user_password])
         user = cur.fetchall()
         cur.close()

         return jsonify(user)         
      else:
         return "Email or password is wrong"
   else:
      return "Email or password is wrong"

# GET CURRENT USER
@app.route('/api/user/<id>', methods=['GET'])
def get_user(id):
   cur = mysql.connection.cursor()
   cur.callproc("spGetCurrentUserById", [id])
   user = cur.fetchall()

   cur.close()

   return jsonify(user)




if __name__ == '__main__':
    app.run(debug=True)