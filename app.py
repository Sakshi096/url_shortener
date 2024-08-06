from flask import Flask, request, redirect, jsonify
import time

app = Flask(__name__)
@app.route('/')
def home():
    return "URL Shortener API is running!"

# In-memory data store
url_store = {}
ttl_store = {}

def generate_random_alias():
    import string, random
    return ''.join(random.choices(string.ascii_letters + string.digits, k=6))

def get_current_timestamp():
    return int(time.time())

@app.route('/shorten', methods=['POST'])
def shorten_url():
    data = request.json
    original_url = data.get('url')
    custom_alias = data.get('alias')
    ttl = data.get('ttl', 120)

    if not original_url:
        return jsonify({'error': 'URL is required'}), 400

    alias = custom_alias if custom_alias else generate_random_alias()
    while alias in url_store:
        alias = generate_random_alias()

    current_time = get_current_timestamp()
    expiration_time = current_time + ttl

    url_store[alias] = {
        "original_url": original_url,
        "ttl": ttl,
        "created_at": current_time,
        "last_accessed": [],
        "access_count": 0
    }

    if expiration_time not in ttl_store:
        ttl_store[expiration_time] = []
    ttl_store[expiration_time].append(alias)

    return jsonify({'shortened_url': f"http://localhost:5000/{alias}"}), 201

@app.route('/<alias>', methods=['GET'])
def redirect_to_url(alias):
    if alias not in url_store:
        return jsonify({'error': 'Alias not found'}), 404

    url_data = url_store[alias]
    url_data['access_count'] += 1
    url_data['last_accessed'].append(get_current_timestamp())

    return redirect(url_data['original_url'], code=302)

@app.route('/analytics/<alias>', methods=['GET'])
def get_analytics(alias):
    if alias not in url_store:
        return jsonify({'error': 'Alias not found'}), 404

    data = url_store[alias]
    return jsonify({
        "access_count": data["access_count"],
        "last_10_access_times": data["last_accessed"][-10:]
    })

@app.route('/update/<alias>', methods=['PUT'])
def update_alias_or_ttl(alias):
    if alias not in url_store:
        return jsonify({'error': 'Alias not found'}), 404

    data = request.json
    new_alias = data.get('new_alias')
    new_ttl = data.get('new_ttl')

    url_data = url_store.pop(alias)

    if new_alias:
        if new_alias in url_store:
            return jsonify({'error': 'New alias already in use'}), 400
        alias = new_alias

    if new_ttl:
        expiration_time = get_current_timestamp() + new_ttl
        if expiration_time not in ttl_store:
            ttl_store[expiration_time] = []
        ttl_store[expiration_time].append(alias)

    url_store[alias] = url_data

    return jsonify({'message': 'Update successful'}), 200

@app.route('/delete/<alias>', methods=['DELETE'])
def delete_url(alias):
    if alias in url_store:
        del url_store[alias]
        return jsonify({'message': 'Delete successful'}), 200
    return jsonify({'error': 'Alias not found'}), 404

@app.before_first_request
def start_cleanup_job():
    from threading import Thread
    def cleanup_expired_aliases():
        while True:
            time.sleep(1)
            current_time = get_current_timestamp()
            expired_keys = [k for k in ttl_store if k <= current_time]
            for key in expired_keys:
                for alias in ttl_store.pop(key, []):
                    url_store.pop(alias, None)
    Thread(target=cleanup_expired_aliases, daemon=True).start()

if __name__ == '__main__':
    app.run(debug=True)
