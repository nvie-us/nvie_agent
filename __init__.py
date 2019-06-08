from flask import Flask
import json
app = Flask(__name__)

@app.route('/spawn')
def index():
    return json.dumps({'status':True})

if __name__=='__main__':
    app.run(debug=True)