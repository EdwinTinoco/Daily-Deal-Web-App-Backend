from flask import Flask, request, jsonify
from flask_mysqldb import MySQL
from flask_cors import CORS
import bcrypt
import datetime
from datetime import timedelta

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
   #    hashed = bcrypt.hashpw(user_password.encode('utf-8'), bcrypt.gensalt())
      hashed = user_password
      
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
      # if bcrypt.checkpw(user_password.encode('utf-8'), hash_password.encode('utf-8')):
      cur = mysql.connection.cursor()
      cur.callproc("spLoginUser", [user_email, user_password])
      user = cur.fetchall()
      cur.close()

      return jsonify(user)         
      # else:
      #    return "Email or password is wrong"
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


# Enpoints for products, deals table------------------------------------------------------------------------
# POST product and deal tables
@app.route('/api/product/new-deal', methods=['POST'])
def insert_product_deal():
   product_user_id = request.json["userId"]
   product_title = request.json["title"]
   picture_product = request.json["image"]
   product_description = request.json["description"]
   product_price = request.json["price"]
   stock_quantity = request.json["stock"]
   product_shipping_type = request.json["shippingType"]
   # deal_created_date = datetime.datetime.now()
   # deal_started_date = datetime.datetime.now()
   # deal_finished_date = datetime.datetime.now() + timedelta(days=1)

   deal_created_date = request.json["createdDealDate"]
   deal_started_date = request.json["startedDealDate"]
   deal_finished_date = request.json["finishedDealDate"]
   deal_status = request.json['dealStatus']     

   cur = mysql.connection.cursor()
   cur.callproc("spInsertNewDealProduct", [product_user_id, product_title, picture_product, 
   product_description, product_price, stock_quantity, product_shipping_type, 
   deal_created_date, deal_started_date, deal_finished_date, deal_status, 0, None])

   mysql.connection.commit()

   cur.execute('SELECT @productId, @generatedDealProductUrl')
   result = cur.fetchone() 
   cur.close()

   return jsonify(result)


# Enpoints for shipping_type table--------------------------------------------------------------------------------
# GET ALL shipping types
@app.route('/api/shipping-types', methods=['GET'])
def get_shipping_types():
   cur = mysql.connection.cursor()
   cur.callproc("spGetAllShippingType", ())
   shipping_types = cur.fetchall()

   cur.close()

   return jsonify(shipping_types)


# Enpoints for product_deals table--------------------------------------------------------------------------------
# GET the active deal by user and active status
@app.route('/api/active-deal/<id>', methods=['GET'])
def get_active_deal(id):
   cur = mysql.connection.cursor()
   cur.callproc("spGetActiveDealByUserId", [id])
   deal = cur.fetchall()
   cur.close()

   return jsonify(deal)

# GET the active deal by deal_id
@app.route('/api/activate-deal/detail/<id>', methods=['GET'])
def get_active_deal_detail(id):
   cur = mysql.connection.cursor()
   cur.callproc("spGetActivateDealDetailbyDealId", [id])
   deal = cur.fetchall()
   cur.close()

   return jsonify(deal)




if __name__ == '__main__':
    app.run(debug=True)