from flask import Blueprint, request, render_template
from google.cloud import datastore
import json
import constants
import decode_token
import re
from  werkzeug.security import generate_password_hash, check_password_hash


client = datastore.Client()

bp = Blueprint('user', __name__, url_prefix='/users')

def validate_input(name):
    isValid = True    
    
    pattern = "[^a-zA-Z0-9-]"
    z=re.search(pattern, name)
    if not(z is None) or len(name) > 20:
        isValid = False        
            
    return isValid

@bp.route('', methods=['POST','GET', 'DELETE'])
def user_get_post():
    
    if request.method == 'POST':
        data = request.form
        if data.get('uname') == "" or data.get('fname') == "" or data.get('lname') == "" or data.get('address')=="" \
        or data.get('phone')=="" or data.get('password')=="":
            return({"Error": "Missing required field"}, 400)
        username = data.get('uname')
        #cast username to lowercase
        username = username.lower()
        #check if username is valid
        valid_name = validate_input(username)
        if valid_name == False:
            return({"Error": "Username contains invalid characters or is too long"}, 400)
        #enforce unique username property
        name_query = client.query(kind=constants.users)
        users = list(name_query.fetch())
        for user in users:
            if username==user["username"]:
                return({"Error": "Username is taken"}, 403)
        firstname = data.get('fname')
        lastname = data.get('lname')
        address = data.get('address')
        phone = data.get('phone')
        password = data.get('password')
        password = generate_password_hash(password)
        new_user = datastore.entity.Entity(key = client.key(constants.users))
        new_user.update({"username":username, "firstname" : firstname, "lastname":lastname, "address":address,
            "phone":phone, "password":password, "orders":[]})
        client.put(new_user)
        new_user["user_id"]=new_user.key.id
        new_user["self"]=request.url_root + "users/" + username
        return (render_template('reg_success.html'),201)

    elif request.method == 'GET':
        if request.headers['Accept'] != "application/json":
            return({"Error":"Invalid MIME Type"}, 406)
        query = client.query(kind=constants.users)
        results = list(query.fetch())
        pub_users_list=[]
        for e in results:

            e["user_id"] = e.key.id
            e["self"] = request.base_url + "/" + e["username"]
            #remove password key from public user list
            del e['password']
            pub_users_list.append(e["username"])
        output = {"users": results}
        
        return json.dumps(output)
    else:
        return ({"Error":"Method not allowed"}, 405)

@bp.route('/<username>', methods=['GET'])
def get_userid(username):
    if request.headers['Accept'] != "application/json":
        return({"Error":"Invalid MIME Type"}, 406)
    query = client.query(kind="users")
    query.add_filter("username", "=", username)
    results = list(query.fetch())
    if results ==[]:
        return({"Error":"User not found"}, 404)
    user = results[0]
    
    if request.method=='GET':
        user["user_id"] = user.key.id
        user["self"]= request.root_url + "users/" + user["username"]
        del user["password"]
        return (user, 200)
        
    
@bp.route('/<username>/orders/<orderid>', methods=['PUT', 'DELETE'])
def add_user_order(username, orderid):
    # Check for authorization header
    header = request.headers.get('Authorization')
    if header is None:
        return ('Authorization Header Missing', 401)
    #Find user
    query = client.query(kind="users")
    query.add_filter("username", "=", username)
    results = list(query.fetch())
    if results ==[]:
        return({"Error":"User not found"}, 404)
    user = results[0]
    #verify authorization token is valid
    bearer, _, token = header.partition(' ')
    userinfo = decode_token.decode_token(token)
    if userinfo is None:
        return({"Error": "Invalid Token"}, 401)
    #verify token matches user route
    if userinfo["username"]==user["username"] and userinfo["user_id"]==user.key.id:
        #Find order
        order_key = client.key(constants.orders, int(orderid))
        order = client.get(key=order_key)
        if order is None:
            return({"Error":"Order not found"}, 404)
        if request.method=='PUT':                 
            for value in user:
                user[value]=user[value]
            user["orders"].append(orderid)
            client.put(user)
            for attr in order:
                order[attr]=order[attr]
            order["customer"]=user["username"]
            client.put(order)
            return('', 204)
        
        elif request.method == 'DELETE':
            for value in user:
                user[value]=user[value]
            user["orders"].remove(orderid)
            client.put(user)
            #remove user from order customer field
            for attr in order:
                order[attr]=order[attr]
            order["customer"]=None
            client.put(order)
            return('', 204)
    else:
        return({"Error":"User not authorized to access this resource"}, 403)

