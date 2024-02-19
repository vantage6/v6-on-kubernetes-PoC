from flask import Flask, request

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def handle_request():
    if request.method == 'POST':
        data = request.data.decode('utf-8')  # Decode the data if it's POST
    else:
        data = request.args.to_dict()  # Get query parameters if it's GET

    return f"Message-forwarded: {data}"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
