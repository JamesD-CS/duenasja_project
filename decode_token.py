import jwt
import constants
from datetime import datetime

def decode_token(token):
	try:
		decoded_token = jwt.decode(token, constants.SECRET_KEY,algorithms="HS256")
		
		return decoded_token
	except:
		return None