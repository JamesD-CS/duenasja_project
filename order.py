from flask import Blueprint, request
from google.cloud import datastore
import json
import constants
import decode_token


client = datastore.Client()

bp = Blueprint('order', __name__, url_prefix='/orders')

@bp.route('', methods=['POST','GET', 'DELETE', 'PUT', 'PATCH'])
def order_get_post():
    
    if request.method == 'POST':
        data = request.get_json()
        if "items" not in data or "total" not in data or "order_date" not in data:
            return({"Error": "Missing required field"}, 400)
        if data["items"]==[] or data["total"]=="" or data["order_date"]=="":
            return({"Error": "Missing required field"}, 400)
        new_order = datastore.entity.Entity(key = client.key(constants.orders))
        new_order.update({"customer":None, "restaurant_id":None, "items":data["items"],
            "total":data["total"], "order_date": data["order_date"]})
        client.put(new_order)
        new_order["self"]= request.root_url + "orders/" + str(new_order.key.id)
        new_order["order_id"]=new_order.key.id
        return (new_order, 201)

    elif request.method == 'GET':
        if request.headers['Accept'] != "application/json":
            return({"Error":"Invalid MIME Type"}, 406)
        # check for auth token
        header = request.headers.get('Authorization')
        if header is None:
            return ('Authorization Header Missing', 401)
        # get token from header
        bearer, _, token = header.partition(' ')
        # verify token
        userinfo = decode_token.decode_token(token)
        if userinfo is not None:
            # find user
            
            query = client.query(kind="orders")
            query.add_filter("customer", "=", userinfo["username"])
            orders = list(query.fetch())
            total_orders = len(orders)
            q_limit = int(request.args.get('limit', '5'))
            q_offset = int(request.args.get('offset', '0'))
            l_iterator = query.fetch(limit= q_limit, offset=q_offset)
            pages = l_iterator.pages
            results = list(next(pages))
            if l_iterator.next_page_token:
                next_offset = q_offset + q_limit
                next_url = request.base_url + "?limit=" + str(q_limit) + "&offset=" + str(next_offset)
            else:
                next_url = None
            for order in results:
                order["order_key"]=order.key.id
                order["self"]=request.root_url + "orders/" +str(order.key.id)
            output = {"orders": results, "total": total_orders}
            if next_url:
                output["next"] = next_url
            return json.dumps(output)
        elif userinfo is None:
            return({"Error":"Invalid Token"}, 401)
    else:
        return ({"Error":"Method not Allowed"}, 405)

@bp.route('/<orderid>', methods=['GET', 'DELETE','PUT', 'PATCH'])
def get_order(orderid):
    
    order_key = client.key(constants.orders, int(orderid))
    order = client.get(key=order_key)
    if order is None:
        return({"Error": "No order exists with this id"})
    # check for authorization header if order is owned by user
    if order["customer"] is not None:
        header = request.headers.get('Authorization')
        if header is None:
            return ('Authorization Header Missing', 401)
        query = client.query(kind="users")
        query.add_filter("username", "=", order["customer"])
        results = list(query.fetch())
        # verify auth token    
        user = results[0]
        bearer, _, token = header.partition(' ')
        userinfo = decode_token.decode_token(token)
        if userinfo is None:
            return({"Error": "Invalid Token"}, 401)
        #verify token matches order customer
        if userinfo["username"]!=order["customer"]:
            return({"Error":"User not authorized to access this resource"}, 403)

    if request.method=='GET':      
        if request.headers['Accept'] != "application/json":
            return({"Error":"Invalid MIME Type"}, 406)  
        order["order_id"]=order.key.id
        order["self"] = request.base_url
        return(order, 200)

    elif request.method=='DELETE':

        if order["restaurant_id"] is not None:
            #remove order from restaurant orders list
            restaurant_key = client.key(constants.restaurants, int(order["restaurant_id"]))
            rest = client.get(key=restaurant_key)
            for attr in rest:
                rest[attr]=rest[attr]
            rest["orders"].remove(orderid)
            client.put(rest)
            #remove order from customer orders list
        if order["customer"] is not None:
            
            for attr in user:
                user[attr]=user[attr]
                #remove order from users order list
                user["orders"].remove(orderid)
                #print(get_user["orders"])
            client.put(user)
            client.delete(order_key)
            return('', 204)
        if order["restaurant_id"] is None and order["customer"] is None:
            client.delete(order_key)
            return('', 204)
    elif request.method=='PUT':
        content = request.get_json()
        order_key = client.key(constants.orders, int(orderid))
        order = client.get(key=order_key)
        order.update({"items": content["items"], "order_date": content["order_date"],
            "total": content["total"]})
        client.put(order)
        return ('',200)
    elif request.method=='PATCH':
        content = request.get_json() 
        for attr in order:
            order[attr]=order[attr]
        for key in content:
            for orderkey in order:
                if key == orderkey and key!= "customer" and key != "restaurant":
                    order[orderkey]=content[key]
        client.put(order)
        return ('',200)
