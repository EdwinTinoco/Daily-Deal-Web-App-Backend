from flask import Flask, request, jsonify, url_for
from flask_mysqldb import MySQL
from flask_cors import CORS
import bcrypt
import datetime
from datetime import timedelta
import stripe
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer, SignatureExpired
from flask_heroku import Heroku
import os
from environs import Env

from secret_key import HOST, USER, PASSWORD, DB, MASTER_ADMIN_CODE
from email_key import MAIL_SERVER, MAIL_USERNAME, MAIL_PASSWORD, MAIL_DEFAULT_SENDER, MAIL_PORT, MAIL_USE_SSL, MAIL_USE_TLS, URL_SAFE_SERIALIZER_KEY, SALT_KEY
from stripe_keys import TEST_SECRET_KEY, SUCCESS_URL, CANCEL_URL, ENPOINT_SECRET_KEY, TAX_RATE_ID

app = Flask(__name__)
CORS(app)
heroku = Heroku(app)

env = Env()
env.read_env() 

# PRODUCTION ENVIRONMENT
# stripe.api_key = os.environ.get('TEST_SECRET_KEY')
# endpoint_secret = os.environ.get('ENPOINT_SECRET_KEY')

# DEBUG ENVIRONMENT
stripe.api_key = TEST_SECRET_KEY
endpoint_secret = ENPOINT_SECRET_KEY

# PRODUCTION ENVIRONMENT
# app.config['MYSQL_HOST'] = os.environ.get('HOST')
# app.config['MYSQL_USER'] = os.environ.get('USER')
# app.config['MYSQL_PASSWORD'] = os.environ.get('PASSWORD')
# app.config['MYSQL_DB'] = os.environ.get('DB')
# app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

# DEBUG ENVIRONMENT
app.config['MYSQL_HOST'] = HOST
app.config['MYSQL_USER'] = USER
app.config['MYSQL_PASSWORD'] = PASSWORD
app.config['MYSQL_DB'] = DB
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'
mysql = MySQL(app)


app.config['MAIL_SERVER'] = MAIL_SERVER
app.config['MAIL_USERNAME'] = MAIL_USERNAME
app.config['MAIL_PASSWORD'] = MAIL_PASSWORD
app.config['MAIL_DEFAULT_SENDER'] = MAIL_DEFAULT_SENDER
app.config['MAIL_PORT'] = MAIL_PORT
app.config['MAIL_USE_SSL'] = MAIL_USE_SSL
app.config['MAIL_USE_TLS'] = MAIL_USE_TLS
mail = Mail(app)

# s = URLSafeTimedSerializer(env("URL_SAFE_SERIALIZER_KEY"))


# Enpoints for Home page -----------------------------------------------------------------------------------------------
@app.route('/')
def home():   

   # print(env("TEST_SECRET_KEY"))
   # print(env("MAIL_SERVER"))
   # print(env("SALT_KEY"))
   return "<h1>Kudu Web Application RESTful APIs</h1>"

# Endpoints for forgot password
@app.route('/api/user/forgot-password', methods=['POST'])
def forgot_password(): 
   email = request.json['email']   

   # todo checar si el email existe

   # token = s.dumps(email, salt=env("SALT_KEY"))
   # link = url_for('reset_password', token=token, _external=True)

   # msg = Message('Kudu Reset Password', recipients=[email])
   # msg.body = 'Your link to reset your password is {}'.format(link)
   # mail.send(msg)

   return jsonify({'message': "The email sent succesfully", "token": token})    

@app.route('/reset-password/<token>', methods=['GET', 'POST'])   
def reset_password(token):  
   
   try:
      # email = s.loads(token, salt=env("SALT_KEY"), max_age=25)

      if request.method == 'GET':
        return f'''<form action="/reset-password/{token}" method="POST">
         <h2>Reset Password</h2>
         <input type="password" name="password">
         <input type="password" name="confirm-password">
         <input type="submit"></form>'''


      userPassword = request.form['password']

      # hashed = bcrypt.hashpw(userPassword.encode('utf-8'), bcrypt.gensalt())

      # cur = mysql.connection.cursor()
      # cur.callproc("spUpdateUserPasswordByEmail", [email, hashed])
      # mysql.connection.commit()
      # cur.close()

   except SignatureExpired:
      return '<h2>The reset-password link is expired!'
   
   return '<h2>The password has been reseted succesfully</h2>'



# STRIPE ENDPOINTS --------------------------------------------------------------------------------------------------------
# POST for create de session when user is going to pay.
@app.route('/create-session', methods=['POST'])
def create_checkout_session():
   product_id = request.json['productId']
   product_name = request.json['productName']
   product_image = request.json['productImage']   
   product_description = request.json['productDescription']   
   product_stripe_id = request.json['stripeProductId']
   sales_customer_user_id = request.json['customerUserId']
   customer_user_email = request.json['customerEmail']
   sales_deal_id = request.json['dealId']
   sales_date = request.json['saleDate']
   sales_subtotal = request.json['subtotal']
   sales_taxes = request.json['taxes']
   sales_total = request.json['total']
   shipping_type_title = request.json['shippingTypeTitle']
   user_stripe_customer_id = request.json['stripeCustomerId']

   total = int(float(sales_total) * 100)

   if shipping_type_title == "Shipping to customer's address":
      allowed_countries = {
            'allowed_countries': ['US']
         }
   else:
      allowed_countries = {}

   try:
      checkout_session = stripe.checkout.Session.create(        
         billing_address_collection='auto',
         shipping_address_collection= allowed_countries,
         customer = user_stripe_customer_id,
         payment_method_types=['card'],
         line_items=[
               {
                  'price_data': {
                     'currency': 'usd',
                     'unit_amount': total,
                     'product': product_stripe_id                     
                  },
                  'quantity': 1
                  # 'tax_rates': [TAX_RATE_ID]
               },
         ],         
         metadata= {
            'productId': product_id,
            'customerUserId': sales_customer_user_id,
            'customerEmail': customer_user_email,
            'dealId': sales_deal_id,
            'salesDate': sales_date,
            'subtotal': sales_subtotal,
            'taxes': sales_taxes,
            'shippingTypeTitle': shipping_type_title
         },
         mode='payment',
         success_url= "http://localhost:3000/success/" + sales_deal_id + '?success=true',
         cancel_url= "http://localhost:3000/deal/product/" + sales_deal_id + '?canceled=true'
      )
      return jsonify({'id': checkout_session.id})

   except Exception as e:
      return jsonify(error=str(e)), 403

# POST webhook sending headers to make secure the session and payment
@app.route('/stripe/webhook', methods=['POST'])
def my_webhook():
   payload = request.data
   sig_header = request.headers['STRIPE_SIGNATURE']
   event = None

   try:
      event = stripe.Webhook.construct_event(
         payload, sig_header, endpoint_secret
      )
   except ValueError as e:
      # Invalid payload
      return jsonify("error"), 400
   except stripe.error.SignatureVerificationError as e:
      # Invalid signature
      return jsonify("error"), 400

      # Handle the checkout.session.completed event
   if event['type'] == 'checkout.session.completed':
      session = event['data']['object']

      # Fulfill the purchase...
      fulfill_order(session)

   # Passed signature verification
   return jsonify("Successfull payment with webhooks"), 200

def fulfill_order(session): 
   print(session)
   
   if session['shipping'] != None:
      name = session['shipping']['name']
      line_1 = session['shipping']['address']['line1']
      city = session['shipping']['address']['city']
      zip_code = session['shipping']['address']['postal_code']
      state = session['shipping']['address']['state']
      country = session['shipping']['address']['country']

      if session['shipping']['address']['line2'] != None:
         line_2 = session['shipping']['address']['line2']
      else:
         line_2 = ""
   else:
      name = ""
      line_1 = ""
      line_2 = ""
      city = ""
      zip_code = ""
      state = ""
      country = ""


   total = session['amount_total'] / 100

   product_id = session['metadata']['productId']
   sales_customer_user_id = session['metadata']['customerUserId']
   sales_deal_id = session['metadata']['dealId']
   sales_date = session['metadata']['salesDate']
   sales_subtotal = session['metadata']['subtotal']
   sales_taxes = session['metadata']['taxes']
   sales_total = total
   shipping_title = session['metadata']['shippingTypeTitle']
   shipping_name = name
   shipping_line_1 = line_1
   shipping_line_2 = line_2
   shipping_city = city
   shipping_zip_code = zip_code
   shipping_state = state
   shipping_country = country
   sales_stripe_session_id = session['id']
   sales_stripe_payment_intent_id = session['payment_intent']

   cur = mysql.connection.cursor()
   cur.callproc("spInsertNewSale", [product_id, sales_customer_user_id, sales_deal_id, sales_date, sales_subtotal,
   sales_taxes, sales_total, shipping_title, shipping_name, shipping_line_1, shipping_line_2, shipping_city, 
   shipping_zip_code, shipping_state, shipping_country, sales_stripe_session_id, sales_stripe_payment_intent_id])
   mysql.connection.commit()
   cur.close()

   if shipping_title == "Pick up to the store":
      cur = mysql.connection.cursor()
      cur.callproc("spGetPickupStoreAddressByDealId", [sales_deal_id])
      pickup = cur.fetchone()
      cur.close()

      print(pickup)
   
      msg = Message('Kudu -- Pick the product up to the store --', recipients=[session['metadata']['customerEmail']])
      msg.body = f'''You need to pick the product up in the store {pickup['pickup_name']}
                  The address is:
                  {pickup['pickup_line_1']} {pickup['pickup_line_2']}
                  {pickup['pickup_city']}, {pickup['pickup_state']} 
                  {pickup['pickup_country']}, {pickup['pickup_zip_code']}
                  '''
      mail.send(msg)      

   return jsonify('Sale inserted successfully')

# POST a product
@app.route('/v1/products', methods=['POST'])
def add_product():
   product_user_id = request.json["userId"]
   product_title = request.json["title"]
   picture_product = request.json["thumbImage1"]
   product_description = request.json["description"]
   product_price = request.json["price"]
   product_compare_price = request.json["comparePrice"]
   product_squ =request.json['squ']
   stock_quantity = request.json["stock"]
   deal_shipping_type_id = request.json["shippingTypeId"]
   # deal_created_date = datetime.datetime.now()
   # deal_started_date = datetime.datetime.now()
   # deal_finished_date = datetime.datetime.now() + timedelta(days=1)

   deal_created_date = request.json["createdDealDate"]
   deal_started_date = request.json["startedDealDate"]
   deal_finished_date = request.json["finishedDealDate"]
   deal_status = request.json['dealStatus']  

   try:
      cur = mysql.connection.cursor()
      cur.callproc("spCheckIfActiveDeal", [product_user_id, ""])
      cur.execute('SELECT @message')
      message = cur.fetchone()  
      cur.close() 
      
      if message['@message'] == "":
         product = stripe.Product.create(
            name = product_title,
            description = product_description
         )

         product_stripe_id = product['id']

         cur = mysql.connection.cursor()
         cur.callproc("spInsertNewDealProduct", [product_user_id, product_title, picture_product, 
         product_description, product_price, product_compare_price, product_squ, product_stripe_id, stock_quantity, deal_shipping_type_id, 
         deal_created_date, deal_started_date, deal_finished_date, deal_status, 0, ""])

         mysql.connection.commit()

         cur.execute('SELECT @dealId, @generatedDealProductUrl')
         result = cur.fetchone() 
         cur.close()

         return jsonify({'message': '', 'result': result}), 200
      else:
         return jsonify({'message': message['@message']})

   except Exception as e:
      return jsonify(error=str(e)), 403


# POST a customer
@app.route('/v1/customers', methods=['POST'])
def add_customer():
   user_role_title = request.json['role']
   user_name = request.json['name']
   user_email = request.json['email']
   user_password = request.json['password']
   user_active = request.json['active']

   if user_role_title == "master_admin":
      adminCode = request.json['code']
   
   if user_role_title == "business_admin":
      user_logo = request.json['logo']
      pickup_line_1 = request.json['line1']
      pickup_line_2 = request.json['line2']
      pickup_city = request.json['city']
      pickup_zip_code = request.json['zp']
      pickup_state = request.json['state']
   else:
      user_logo = ""
      pickup_line_1 = ""
      pickup_line_2 = ""
      pickup_city = ""
      pickup_zip_code = ""
      pickup_state = ""   
   
   try:
      cur = mysql.connection.cursor()
      cur.callproc("spCheckEmailExist", [user_email, "", ""])
      cur.execute('SELECT @message, @userPassword')
      message = cur.fetchone()  
      cur.close() 

      print(message)      

      if message['@message'] == "A user with that email already exist":
         return jsonify({'message': message['@message']}) 

      elif user_role_title == "master_admin":
         hash_code = bcrypt.hashpw(MASTER_ADMIN_CODE.encode('utf-8'), bcrypt.gensalt())
         print('admin code', adminCode)
         print('hash code', hash_code)
         #revisar este if porquem no funciona
         if bcrypt.checkpw(adminCode.encode('utf-8'), hash_code.encode('utf-8')):
            print('si entro master admin')
            customer = stripe.Customer.create(
               email = user_email,
               name = user_name
            )

            user_stripe_customer_id = customer['id']

            hashed = bcrypt.hashpw(user_password.encode('utf-8'), bcrypt.gensalt())
               
            cur = mysql.connection.cursor()
            cur.callproc("spInsertNewUser", [user_role_title, user_name, user_email, hashed, user_active, 
            user_stripe_customer_id, user_logo, pickup_line_1, pickup_line_2, pickup_city, pickup_zip_code, pickup_state, 0])
            mysql.connection.commit()

            cur.execute('SELECT @userId')
            result = cur.fetchone() 
            cur.close()        

            return jsonify({'message': "Customer created succesfully", 'result': result}), 200
         else:
            return jsonify({'message': 'The admin code is wrong'})
      else:
         customer = stripe.Customer.create(
            email = user_email,
            name = user_name
         )

         user_stripe_customer_id = customer['id']

         hashed = bcrypt.hashpw(user_password.encode('utf-8'), bcrypt.gensalt())
               
         cur = mysql.connection.cursor()
         cur.callproc("spInsertNewUser", [user_role_title, user_name, user_email, hashed, user_active, 
         user_stripe_customer_id, user_logo, pickup_line_1, pickup_line_2, pickup_city, pickup_zip_code, pickup_state, 0])
         mysql.connection.commit()

         cur.execute('SELECT @userId')
         result = cur.fetchone() 
         cur.close()        

         return jsonify({'message': "Customer created succesfully", 'result': result}), 200

   except Exception as e:
      return jsonify(error=str(e)), 403



# Enpoints for users table------------------------------------------------------------------------
# @app.route('/api/user/signup', methods=['POST'])
# def signup_user(): 
#    user_role_title = request.json['role']
#    user_name = request.json['name']
#    user_email = request.json['email']
#    user_password = request.json['password']
#    user_active = request.json['active']
#    pickup_line_1 = request.json['line1']
#    pickup_line_2 = request.json['line2']
#    pickup_city = request.json['city']
#    pickup_zip_code = request.json['zp']
#    pickup_state = request.json['state']

#    cur = mysql.connection.cursor()
#    cur.callproc("spCheckEmailExist", ())
#    emails = cur.fetchall()
#    cur.close() 

#    ban = False
#    for row in emails:
#       if row['user_email'] == user_email:
#          ban = True

#    if ban:
#       return 'A user with that email already exist'
#    else:
#    #    hashed = bcrypt.hashpw(user_password.encode('utf-8'), bcrypt.gensalt())
#       hashed = user_password
      
#       cur = mysql.connection.cursor()
#       cur.callproc("spInsertNewUser", [user_role_title, user_name, user_email, hashed, user_active, 
#       pickup_line_1, pickup_line_2, pickup_city, pickup_zip_code, pickup_state, 0])
#       mysql.connection.commit()

#       cur.execute('SELECT @userId')
#       result = cur.fetchone() 
#       cur.close()

#       return jsonify(result)


# POST LOGIN USER
@app.route('/api/user/login', methods=['POST'])
def login_user():
   userEmail = request.json['email']
   user_password = request.json['password']  
   
   cur = mysql.connection.cursor()
   cur.callproc("spCheckEmailExist", [userEmail, "", ""])
   cur.execute('SELECT @message, @hashPassword')
   message = cur.fetchone()  
   cur.close()    

   if message['@message'] == "A user with that email already exist":
      hash_password = message['@hashPassword']       

      if bcrypt.checkpw(user_password.encode('utf-8'), hash_password.encode('utf-8')):
         cur = mysql.connection.cursor()
         cur.callproc("spLoginUser", [userEmail, hash_password])
         user = cur.fetchall()
         cur.close()

         return jsonify({'message': 'Login successfully', 'user': user})         
      else:
         return jsonify({'message': "Email or password is wrong"})
   else:
      return jsonify({'message': "Email or password is wrong"}) 

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
# @app.route('/api/product/new-deal', methods=['POST'])
# def insert_product_deal():
#    product_user_id = request.json["userId"]
#    product_title = request.json["title"]
#    picture_product = request.json["thumbImage1"]
#    product_description = request.json["description"]
#    product_price = request.json["price"]
#    stock_quantity = request.json["stock"]
#    deal_shipping_type_id = request.json["shippingTypeId"]
#    # deal_created_date = datetime.datetime.now()
#    # deal_started_date = datetime.datetime.now()
#    # deal_finished_date = datetime.datetime.now() + timedelta(days=1)

#    deal_created_date = request.json["createdDealDate"]
#    deal_started_date = request.json["startedDealDate"]
#    deal_finished_date = request.json["finishedDealDate"]
#    deal_status = request.json['dealStatus']     

#    cur = mysql.connection.cursor()
#    cur.callproc("spInsertNewDealProduct", [product_user_id, product_title, picture_product, 
#    product_description, product_price, stock_quantity, deal_shipping_type_id, 
#    deal_created_date, deal_started_date, deal_finished_date, deal_status, 0, None])

#    mysql.connection.commit()

#    cur.execute('SELECT @dealId, @generatedDealProductUrl')
#    result = cur.fetchone() 
#    cur.close()

#    return jsonify(result)


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
# GET the active deal by user and active status - for business account
@app.route('/api/active-deals/<id>', methods=['GET'])
def get_active_deal(id):
   cur = mysql.connection.cursor()
   cur.callproc("spGetActiveDealsByUserId", [id])
   deal = cur.fetchall()
   cur.close()

   return jsonify(deal)

# GET the active deal by deal_id
@app.route('/api/active-deal/detail/<id>', methods=['GET'])
def get_active_deal_detail(id):
   cur = mysql.connection.cursor()
   cur.callproc("spGetActiveDealDetailbyDealId", [id])
   deal = cur.fetchall()
   cur.close()

   return jsonify(deal)

# GET all active deals - for master admin account
@app.route('/api/all-active-deals', methods=['GET'])
def get_all_active_deal():
   cur = mysql.connection.cursor()
   cur.callproc("spMAGetAllActiveDeals", ())
   all_deals = cur.fetchall()
   cur.close()

   return jsonify(all_deals)

# GET product deal - contains url generated
@app.route('/deal/product/<id>', methods=['GET'])
def get_product_deal_url(id):
   cur = mysql.connection.cursor()
   cur.callproc("spGetActiveDealDetailbyDealId", [id])
   product_deal = cur.fetchall()
   cur.close()   

   return jsonify(product_deal)

# Enpoints for sales table--------------------------------------------------------------------------------
# GET the active deals totals by user id
@app.route('/api/active-deals/totals/<id>', methods=['GET'])
def get_active_deals_totlas(id):
   cur = mysql.connection.cursor()
   cur.callproc("spGetActiveDealsTotalsByUserId", [id])
   deals_totals = cur.fetchall()
   cur.close()

   return jsonify(deals_totals)

# POST Check if the user already made a purchase
@app.route('/api/user/check-sdp', methods={'POST'})
def check_user_purchase():
   userId = request.json['userId']
   dealId = request.json['dealId']
   currentDate = request.json['currentDate']

   cur = mysql.connection.cursor()
   cur.callproc("checkStockDatePurchase", [userId, dealId, currentDate, ""])
   mysql.connection.commit()

   cur.execute('SELECT @message')
   result = cur.fetchone() 
   cur.close()

   return jsonify(result)

# GET DEALS SALES DETAIL BY PRODUCT DEAL
@app.route('/api/sales-deal/detail/<id>', methods=['GET'])
def get_sales_deal(id):
   cur = mysql.connection.cursor()
   cur.callproc("spGetSalesByDealId", [id])
   sales_deal = cur.fetchall()
   cur.close()

   return jsonify(sales_deal)


# ENDPOINTS For product_stock TABLE
# GET how many items are in stock
@app.route('/api/check-stock-left/<id>', methods=['GET'])
def check_stock(id):
   cur = mysql.connection.cursor()
   cur.callproc("spCheckStockByDealId", [id])
   stock = cur.fetchone()
   cur.close()

   return jsonify(stock)


# ENDPOINTS For pickup_store_addresses TABLE
# GET PICK UP STORE ADDRESS
@app.route('/api/user/pickup-store/<id>', methods=['GET'])
def get_pickup_store_address(id):
   cur = mysql.connection.cursor()
   cur.callproc("spGetPickupStoreAddressByUserId", [id])
   pickup_address = cur.fetchall()

   cur.close()

   return jsonify(pickup_address)

# PUT update the pickup to store address
@app.route('/api/user/update/pickup-store', methods=['POST'])
def update_pickup_store_address():
   user_id = request.json['userId']
   pickup_name = request.json['storeName']
   pickup_line_1 = request.json['line1']
   pickup_line_2 = request.json['line2']
   pickup_city = request.json['city']
   pickup_zip_code = request.json['zp']
   pickup_state = request.json['state']

   cur = mysql.connection.cursor()
   cur.callproc("spUpdatePickupStoreAddressByUserId", [user_id, pickup_name, pickup_line_1, pickup_line_2, 
   pickup_city, pickup_zip_code, pickup_state])
   mysql.connection.commit()
   cur.close()

   return jsonify({'message': 'The pick up to the store address has been updated succesfully'})




if __name__ == '__main__':
    app.run(debug=True)