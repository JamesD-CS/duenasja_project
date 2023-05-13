from flask import Blueprint, request
from google.cloud import datastore
import json
import constants

client = datastore.Client()

bp = Blueprint('restaurant', __name__, url_prefix='/restaurants')

@bp.route('', methods=['POST','GET', 'DELETE', 'PUT', 'PATCH'])
def restaurant_get_post():
    
    if request.method == 'POST':
        data = request.get_json()
        if "name" not in data or "type" not in data or "address" not in data or "phone" not in data:
            return({"Error": "Missing required field"}, 400)
        if data["name"]=="" or data["type"]==[] or data["address"]=="" or data["phone"]=="":
            return({"Error": "Missing required field"}, 400)
        new_restaurant = datastore.entity.Entity(key = client.key(constants.restaurants))
        new_restaurant.update({"name":data["name"], "type":data["type"], "address":data["address"],
            "phone":data["phone"],"orders":[]})
        client.put(new_restaurant)
        new_restaurant["self"]= request.base_url + "/" + str(new_restaurant.key.id)
        new_restaurant["restaurant_id"]=new_restaurant.key.id
        return (new_restaurant, 201)

    elif request.method == 'GET':
        if request.headers['Accept'] != "application/json":
            return({"Error":"Invalid MIME Type"}, 406)
        query = client.query(kind=constants.restaurants)
        rest_list = list(query.fetch())
        total_count = len(rest_list)
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
        for e in results:
            e["restaurant_id"] = e.key.id
            e["self"] = request.base_url + "/" + str(e.key.id)
        output = {"restaurants": results, "total": total_count}
        if next_url:
            output["next"] = next_url
        return json.dumps(output)
    else:
        return ({"Error":"Method not Allowed"}, 405)

@bp.route('/<rest_id>', methods=['GET', 'DELETE','PUT','PATCH'])
def get_delete_rest(rest_id):
    rest_key = client.key(constants.restaurants, int(rest_id))
    restaurant = client.get(key=rest_key)
    if restaurant is None:
        return({"Error": "No restaurant exists with this id"},404)
    if request.method=='GET':   
        restaurant["restaurant_id"]=restaurant.key.id
        restaurant["self"] = request.base_url
        return(restaurant, 200)
    elif request.method=='DELETE':
        orders = restaurant["orders"]
        for order in orders:
            order_key = client.key(constants.orders,int(order))
            rest_order = client.get(key=order_key)
            for attr in rest_order:
                rest_order[attr]=rest_order[attr]
            rest_order["restaurant_id"]=None
            client.put(rest_order)
            #delete restaurant
            client.delete(rest_key)
        return('', 204)
    elif request.method=='PUT':
        content = request.get_json()
        rest_key = client.key(constants.restaurants, int(rest_id))
        restaurant = client.get(key=rest_key)
        restaurant.update({"name": content["name"], "type": content["type"],
          "address": content["address"], "phone":content["phone"]})
        restaurant["orders"]=restaurant["orders"]
        client.put(restaurant)
        return ('',200)
    elif request.method=='PATCH':
        content = request.get_json() 
        for attr in restaurant:
            restaurant[attr]=restaurant[attr]
        for key in content:
            for rkey in restaurant:
                if key == rkey:
                    restaurant[rkey]=content[key]
        client.put(restaurant)
        return('',200)


@bp.route('/<rest_id>/orders/<order_id>', methods=['GET','POST','DELETE'])
def get_post_order(rest_id, order_id):
    rest_key = client.key(constants.restaurants, int(rest_id))
    restaurant = client.get(key=rest_key)
    if restaurant is None:
        return({"Error": "No restaurant exists with this id"})
    if request.method=='POST':      
        order_key = client.key(constants.orders, int(order_id))
        order = client.get(key=order_key)
        if order is None:
            return({"Error":"Order not found"}, 404)
        for attr in restaurant:
            restaurant[attr]=restaurant[attr]
        restaurant["orders"].append(order.key.id)
        client.put(restaurant)
        #update order with restaurant_id
        for attr in order:
            order[attr]=order[attr]
        order["restaurant_id"]=restaurant.key.id
        client.put(order)
        return('', 204)
    elif request.method=='DELETE':
        orders = restaurant["orders"]
        if int(order_id) not in orders:
            return({"Error":"Order not found at this restaurant"}, 404)
        for attr in restaurant:
            restaurant[attr]=restaurant[attr]
        restaurant["orders"].remove(int(order_id))
        client.put(restaurant)
        order_key = client.key(constants.orders, int(order_id))
        order = client.get(key=order_key)
        for attr in order:
            order[attr]=order[attr]
        order["restaurant_id"]=None
        client.put(order)
        return('', 204)


