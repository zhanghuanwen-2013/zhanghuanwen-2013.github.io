# -*- coding: utf-8 -*-

from flask import Flask, render_template, request, jsonify, send_file
import subprocess
import os
import sys
import time

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False

if not os.path.exists('static'):
    os.makedirs('static')

def generate_inputs_file(handles, days, problems):
    inputs_path = 'inputs.txt'
    with open(inputs_path, 'w', encoding='utf-8') as f:
        f.write(','.join(handles) + '\n')
        f.write(str(days) + '\n')
        for problem in problems:
            f.write(problem + '\n')
    return inputs_path

def run_cf_query():
    status_path = os.path.join('static', 'status.txt')
    result = subprocess.run(
        [sys.executable, 'cf_query.py'],
        capture_output=True,
        encoding='utf-8'
    )
    if os.path.exists(status_path):
        return True, "OK"
    else:
        return False, f"Runtime Error: {result.stderr}"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/run-query', methods=['POST'])
def run_query():
    try:
        data = request.json
        handles = [h.strip() for h in data['handles'].split(',') if h.strip()]
        days = int(data['days'])
        problems = [p.strip() for p in data['problems'] if p.strip()]

        if not handles:
            return jsonify({'success': False, 'msg': 'User name mustn\'t be empty!'})
        if days <= 0:
            return jsonify({'success': False, 'msg': 'Time must >0!'})
        if not problems:
            return jsonify({'success': False, 'msg': 'The list of problems mustn\'t be empty!'})

        generate_inputs_file(handles, days, problems)

        success, msg = run_cf_query()
        if success:
            return jsonify({'success': True, 'msg': msg})
        else:
            return jsonify({'success': False, 'msg': msg})

    except Exception as e:
        return jsonify({'success': False, 'msg': f'error:{str(e)}'})

@app.route('/get-status')
def get_status():
    status_path = os.path.join('static', 'status.txt')
    if os.path.exists(status_path):
        with open(status_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return jsonify({'success': True, 'content': content})
    else:
        return jsonify({'success': False, 'msg': 'No results now.'})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
