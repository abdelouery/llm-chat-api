from flask import Flask, Response, request
from flask_cors import CORS, cross_origin
from openai import OpenAI
from pymongo import MongoClient
from bson.json_util import dumps

app = Flask(__name__)
cors = CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'

openai_client = OpenAI(base_url="http://192.168.1.11:1234/v1", api_key="lm-studio")
mongoClient = MongoClient('localhost', 27017)

# load history from
db = mongoClient.llm_chat
history_collection = db.history
history = list(history_collection.find())

def send_request():
    completion = openai_client.chat.completions.create(
        model="model-identifier",
        messages=dumps(history),
        temperature=0.7,
    )
    response = completion.choices[0].message.content
    resp = {"role": "assistant", "content": response}
    history_collection.insert_one(resp)
    history.append(resp)
    return dumps(resp)

@app.get('/api/history')
@cross_origin()
def get_history():
    return Response(dumps(history), mimetype='application/json')

@app.post('/api/prompt')
@cross_origin()
def prompt():
    request_body = request.get_json()
    msg = {"role": "user", "content": request_body.get('content') }
    history_collection.insert_one(msg)
    history.append(msg)
    return send_request()
