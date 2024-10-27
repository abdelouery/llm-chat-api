from flask import Flask, Response, request
from flask_cors import CORS, cross_origin
from openai import OpenAI
from pymongo import MongoClient
from bson.json_util import dumps
from bson.objectid import ObjectId

app = Flask(__name__)
cors = CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'

openai_client = OpenAI(base_url="http://192.168.1.11:1234/v1", api_key="lm-studio")
mongoClient = MongoClient('localhost', 27017)

# load history from
db = mongoClient.llm_chat
current_conversation = db.conversations.find_one()
history = list(current_conversation['history'])

def create_history_entry(conversation_id, entry):
    db.conversations.update_one(
        {'_id': ObjectId(conversation_id)},
        {'$push': {'history': entry}}
    )

def send_request(id):
    stream = openai_client.chat.completions.create(
        model="model-identifier",
        messages=dumps(history),
        temperature=0.7,
        stream=True
    )
    def generate_stream_response():
        total_response = ''
        for chunk in stream:
            if chunk.choices[0].delta.content is not None:
                total_response += chunk.choices[0].delta.content
                yield chunk.choices[0].delta.content
        resp = {"role": "assistant", "content": total_response}
        create_history_entry(id, resp)
        history.append(resp)

    return generate_stream_response()

@app.get('/api/conversations')
@cross_origin()
def get_conversations():
    conversations = db.conversations.find()
    return Response(dumps(conversations))

@app.post('/api/conversations')
@cross_origin()
def create_conversation():
    request_body = request.get_json()
    result = db.conversations.insert_one(request_body)
    created_conv = db.conversations.find_one({'_id': result.inserted_id})
    return Response(dumps(created_conv))

@app.get('/api/history/<id>')
@cross_origin()
def get_history(id):
    conversation_history = db.conversations.find_one({'_id': ObjectId(id)})
    return Response(dumps(conversation_history['history']), mimetype='application/json')

@app.post('/api/prompt/<id>')
@cross_origin()
def prompt(id):
    request_body = request.get_json()
    msg = {"role": "user", "content": request_body.get('content')}
    create_history_entry(id, msg)
    history.append(msg)
    return send_request(id)
