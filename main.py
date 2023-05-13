from google.cloud import datastore
from flask import Flask, request, render_template
import json
import constants
import user, order, restaurant
import jwt
from  werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta

client = datastore.Client()

app = Flask(__name__)
app.url_map.strict_slashes = False
app.register_blueprint(user.bp)
app.register_blueprint(order.bp)
app.register_blueprint(restaurant.bp)
app.config['SECRET_KEY'] = constants.SECRET_KEY

@app.route('/')
def landing_page():
    return render_template('index.html')

@app.route('/register', methods=['GET'])
def register():
    if request.method == 'GET':

        return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')
    elif request.method == 'POST':
        user_data = request.form
        if user_data.get('uname')=="" or user_data.get('password')=="":
            return("missing username or password", 401)
        username = user_data.get('uname')
        password = user_data.get('password')
        query = client.query(kind="users")
        query.add_filter("username", "=", username)
        results = list(query.fetch())
        if results ==[]:
            return({"Error":"User not found"}, 404)
        user = results[0]
        if check_password_hash(user['password'], password):
            #generate JWT
            token = jwt.encode({
            'user_id' : user.key.id,
            'username': username,        
            }, app.config['SECRET_KEY'], algorithm="HS256")

            d_token = jwt.decode(token, app.config['SECRET_KEY'],algorithms="HS256")
            return render_template('user.html', user_name=username, token=token, d_token=d_token)     
        else:
            return({"Error":"Incorrect Password"}, 401)
        
        

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)