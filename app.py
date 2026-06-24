#!/usr/bin/env python3
"""
F1 Race Predictor - Advanced UI with Feature Tuning
Modern F1 broadcast interface with animations and real-time updates
"""

import json
import sys
from pathlib import Path

from flask import Flask, request, jsonify, Response

sys.path.insert(0, str(Path(__file__).resolve().parent / "model"))
from predict import available, predict_race  # noqa: E402

app = Flask(__name__)

# Real 2026 grid + circuit list, sourced from the trained-model snapshot
# (model/driver_form_2026.json, built by model/train.py from the Jolpica data).
_FORM = available()
_DRV = _FORM["drivers"]

# code -> {name, team, number} for the UI, ordered by current championship points
DRIVERS = {
    code: {"name": d["driver_name"], "team": d["constructor_name"], "number": d["car_number"]}
    for code, d in sorted(_DRV.items(), key=lambda kv: -(kv[1].get("drv_pts_season") or 0))
}

# <option> list for the circuit selector
CIRCUIT_OPTIONS = "".join(
    f'<option value="{c["circuit_id"]}">{c["circuit_name"]}</option>'
    for c in _FORM["circuits"]
)

# Headline backtest number shown in the metrics strip (from model/metrics.json)
_METRICS = json.loads((Path(__file__).resolve().parent / "model" / "metrics.json").read_text())
WINNER_ACC = int(round(_METRICS["backtest"]["pooled"]["model"]["winner_hit"] * 100))

# HTML with advanced UI
HTML_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>F1 AI Race Predictor</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: 'Formula1 Display', -apple-system, BlinkMacSystemFont, sans-serif;
            background: #0f0f0f;
            color: #fff;
            overflow-x: hidden;
            min-height: 100vh;
        }
        
        /* Animated gradient background */
        body::before {
            content: '';
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: linear-gradient(45deg, #ff1e00, #0f0f0f, #ff1e00, #0f0f0f);
            background-size: 400% 400%;
            animation: gradientShift 20s ease infinite;
            opacity: 0.3;
            z-index: -1;
        }
        
        @keyframes gradientShift {
            0% { background-position: 0% 50%; }
            50% { background-position: 100% 50%; }
            100% { background-position: 0% 50%; }
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }
        
        /* Header */
        .header {
            text-align: center;
            margin-bottom: 40px;
            position: relative;
        }
        
        h1 {
            font-size: 4rem;
            font-weight: 900;
            background: linear-gradient(90deg, #ff1e00, #fff, #ff1e00);
            background-size: 200% auto;
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            animation: shine 3s linear infinite;
            text-transform: uppercase;
            letter-spacing: 2px;
        }
        
        @keyframes shine {
            to { background-position: 200% center; }
        }
        
        .subtitle {
            color: #888;
            font-size: 1.2rem;
            margin-top: 10px;
        }
        
        /* Main grid */
        .main-grid {
            display: grid;
            grid-template-columns: 1fr 2fr 1fr;
            gap: 20px;
            margin-bottom: 30px;
        }
        
        /* Cards */
        .card {
            background: rgba(30, 30, 46, 0.8);
            border-radius: 15px;
            padding: 25px;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 30, 0, 0.3);
            transition: all 0.3s ease;
        }
        
        .card:hover {
            transform: translateY(-5px);
            box-shadow: 0 10px 30px rgba(255, 30, 0, 0.3);
        }
        
        .card h2 {
            color: #ff1e00;
            margin-bottom: 20px;
            font-size: 1.5rem;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        /* Feature sliders */
        .feature-slider {
            margin-bottom: 25px;
        }
        
        .feature-slider label {
            display: block;
            margin-bottom: 10px;
            color: #ccc;
            font-size: 0.9rem;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        .slider-container {
            display: flex;
            align-items: center;
            gap: 15px;
        }
        
        input[type="range"] {
            flex: 1;
            height: 8px;
            background: #333;
            border-radius: 4px;
            outline: none;
            -webkit-appearance: none;
        }
        
        input[type="range"]::-webkit-slider-thumb {
            -webkit-appearance: none;
            width: 20px;
            height: 20px;
            background: #ff1e00;
            border-radius: 50%;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        
        input[type="range"]::-webkit-slider-thumb:hover {
            transform: scale(1.2);
            box-shadow: 0 0 10px rgba(255, 30, 0, 0.8);
        }
        
        .slider-value {
            background: #ff1e00;
            color: #fff;
            padding: 5px 12px;
            border-radius: 5px;
            font-weight: bold;
            min-width: 50px;
            text-align: center;
        }
        
        /* Podium display */
        .podium-container {
            display: flex;
            justify-content: center;
            align-items: flex-end;
            gap: 10px;
            margin: 30px 0;
            height: 250px;
        }
        
        .podium-place {
            text-align: center;
            transition: all 0.5s ease;
            animation: slideUp 0.8s ease-out;
        }
        
        @keyframes slideUp {
            from { transform: translateY(50px); opacity: 0; }
            to { transform: translateY(0); opacity: 1; }
        }
        
        .podium-place.first { order: 2; }
        .podium-place.second { order: 1; }
        .podium-place.third { order: 3; }
        
        .podium-stand {
            width: 120px;
            background: linear-gradient(180deg, #ff1e00, #8b0000);
            border-radius: 10px 10px 0 0;
            position: relative;
            overflow: hidden;
        }
        
        .podium-stand::before {
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(90deg, transparent, rgba(255,255,255,0.3), transparent);
            animation: shimmer 3s infinite;
        }
        
        @keyframes shimmer {
            to { left: 100%; }
        }
        
        .first .podium-stand { height: 150px; background: linear-gradient(180deg, #FFD700, #B8860B); }
        .second .podium-stand { height: 120px; background: linear-gradient(180deg, #C0C0C0, #808080); }
        .third .podium-stand { height: 90px; background: linear-gradient(180deg, #CD7F32, #8B4513); }
        
        .podium-driver {
            background: rgba(0,0,0,0.8);
            padding: 15px;
            border-radius: 10px;
            margin-bottom: 10px;
            font-weight: bold;
        }
        
        .podium-position {
            font-size: 2rem;
            margin-bottom: 5px;
        }
        
        .confidence-bar {
            height: 8px;
            background: #333;
            border-radius: 4px;
            overflow: hidden;
            margin-top: 10px;
        }
        
        .confidence-fill {
            height: 100%;
            background: #4CAF50;
            transition: width 0.8s ease;
        }
        
        /* Weather widget */
        .weather-widget {
            background: rgba(0, 123, 255, 0.1);
            border: 1px solid rgba(0, 123, 255, 0.3);
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 20px;
            text-align: center;
        }
        
        .weather-temp {
            font-size: 3rem;
            font-weight: bold;
            color: #ff1e00;
        }
        
        .weather-condition {
            color: #888;
            margin-top: 10px;
        }
        
        /* Metrics cards */
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 15px;
            margin-bottom: 30px;
        }
        
        .metric-card {
            background: rgba(255, 30, 0, 0.1);
            border: 1px solid rgba(255, 30, 0, 0.3);
            border-radius: 10px;
            padding: 20px;
            text-align: center;
        }
        
        .metric-value {
            font-size: 2rem;
            font-weight: bold;
            color: #ff1e00;
        }
        
        .metric-label {
            color: #888;
            font-size: 0.9rem;
            margin-top: 5px;
        }
        
        /* Feature importance bars */
        .importance-bar {
            margin-bottom: 15px;
        }
        
        .importance-label {
            display: flex;
            justify-content: space-between;
            margin-bottom: 5px;
            font-size: 0.9rem;
        }
        
        .importance-track {
            height: 10px;
            background: #333;
            border-radius: 5px;
            overflow: hidden;
        }
        
        .importance-fill {
            height: 100%;
            background: linear-gradient(90deg, #ff1e00, #ff6b6b);
            transition: width 1s ease;
            position: relative;
            overflow: hidden;
        }
        
        .importance-fill::after {
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(90deg, transparent, rgba(255,255,255,0.4), transparent);
            animation: slide 2s infinite;
        }
        
        @keyframes slide {
            to { left: 100%; }
        }
        
        /* Predictions table */
        .predictions-table {
            background: rgba(30, 30, 46, 0.6);
            border-radius: 10px;
            overflow: hidden;
            margin-top: 30px;
        }
        
        .predictions-table table {
            width: 100%;
            border-collapse: collapse;
        }
        
        .predictions-table th {
            background: #ff1e00;
            padding: 15px;
            text-align: left;
            font-weight: bold;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        .predictions-table td {
            padding: 15px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }
        
        .predictions-table tr:hover {
            background: rgba(255, 30, 0, 0.1);
        }
        
        .position-change {
            font-weight: bold;
        }
        
        .position-up { color: #4CAF50; }
        .position-down { color: #f44336; }
        .position-same { color: #888; }
        
        /* Button */
        .predict-button {
            background: linear-gradient(45deg, #ff1e00, #ff4444);
            color: white;
            border: none;
            padding: 15px 40px;
            font-size: 1.1rem;
            font-weight: bold;
            border-radius: 50px;
            cursor: pointer;
            text-transform: uppercase;
            letter-spacing: 2px;
            transition: all 0.3s ease;
            display: block;
            margin: 30px auto;
            position: relative;
            overflow: hidden;
        }
        
        .predict-button:hover {
            transform: translateY(-3px);
            box-shadow: 0 10px 30px rgba(255, 30, 0, 0.5);
        }
        
        .predict-button::before {
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(90deg, transparent, rgba(255,255,255,0.3), transparent);
            transition: left 0.5s;
        }
        
        .predict-button:hover::before {
            left: 100%;
        }
        
        /* Loading animation */
        .loading-spinner {
            display: none;
            width: 50px;
            height: 50px;
            border: 3px solid #333;
            border-top: 3px solid #ff1e00;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin: 20px auto;
        }
        
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
        
        /* Track selector */
        select {
            width: 100%;
            padding: 12px;
            background: #2a2a3e;
            border: 1px solid #444;
            color: #fff;
            border-radius: 5px;
            font-size: 1rem;
            margin-bottom: 20px;
        }
        
        @media (max-width: 1024px) {
            .main-grid { grid-template-columns: 1fr; }
            .metrics-grid { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>F1 AI Race Predictor</h1>
            <p class="subtitle">Advanced Machine Learning for Motorsport Analytics</p>
        </div>
        
        <div class="main-grid">
            <!-- Left Panel - Model Controls -->
            <div class="card">
                <h2>⚙️ Model Controls</h2>

                <div class="feature-slider">
                    <label>Qualifying influence</label>
                    <div class="slider-container">
                        <input type="range" id="quali-weight" min="0" max="100" value="70">
                        <span class="slider-value">70%</span>
                    </div>
                    <p style="color:#888; font-size:0.8rem; margin-top:8px; line-height:1.4;">
                        Blends the raw grid order with the model's form-aware
                        prediction. 100% = trust qualifying; 0% = trust the model's
                        view of car &amp; driver form.
                    </p>
                </div>

                <div style="border-top:1px solid #2a2a2a; margin:18px 0; padding-top:16px;">
                    <h3 style="font-size:0.95rem; color:#bbb; margin-bottom:10px;">Model card</h3>
                    <div style="font-size:0.82rem; color:#999; line-height:1.7;">
                        <div>Data&nbsp;·&nbsp;<b style="color:#ddd;">Jolpica / Ergast</b>, 2014–2026</div>
                        <div>Model&nbsp;·&nbsp;<b style="color:#ddd;">HistGradientBoosting</b></div>
                        <div>Backtest winner acc&nbsp;·&nbsp;<b style="color:#ff1e00;">""" + str(WINNER_ACC) + """%</b></div>
                        <div>Validated on&nbsp;·&nbsp;<b style="color:#ddd;">92 races (2022–25)</b></div>
                    </div>
                </div>
            </div>
            
            <!-- Center Panel - Main Display -->
            <div>
                <!-- Track Selection -->
                <div class="card" style="margin-bottom: 20px;">
                    <label style="font-weight: bold; margin-bottom: 10px; display: block;">Select Circuit:</label>
                    <select id="track">""" + CIRCUIT_OPTIONS + """</select>
                </div>
                
                <!-- Podium Display -->
                <div class="card">
                    <h2>🏆 Predicted Podium</h2>
                    <div class="podium-container" id="podium">
                        <div class="podium-place second">
                            <div class="podium-driver">
                                <div class="podium-position">P2</div>
                                <div class="driver-name">-</div>
                                <div class="confidence-bar">
                                    <div class="confidence-fill" style="width: 0%"></div>
                                </div>
                            </div>
                            <div class="podium-stand"></div>
                        </div>
                        <div class="podium-place first">
                            <div class="podium-driver">
                                <div class="podium-position">P1</div>
                                <div class="driver-name">-</div>
                                <div class="confidence-bar">
                                    <div class="confidence-fill" style="width: 0%"></div>
                                </div>
                            </div>
                            <div class="podium-stand"></div>
                        </div>
                        <div class="podium-place third">
                            <div class="podium-driver">
                                <div class="podium-position">P3</div>
                                <div class="driver-name">-</div>
                                <div class="confidence-bar">
                                    <div class="confidence-fill" style="width: 0%"></div>
                                </div>
                            </div>
                            <div class="podium-stand"></div>
                        </div>
                    </div>
                </div>
                
                <!-- Model Metrics -->
                <div class="metrics-grid">
                    <div class="metric-card">
                        <div class="metric-value" id="accuracy">0%</div>
                        <div class="metric-label">Winner Acc (backtest)</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value" id="confidence">0%</div>
                        <div class="metric-label">Podium Confidence</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value" id="volatility">0</div>
                        <div class="metric-label">Avg Δ vs Grid</div>
                    </div>
                </div>
                
                <button class="predict-button" onclick="generatePredictions()">
                    Generate AI Predictions
                </button>
                
                <div class="loading-spinner" id="loading"></div>
            </div>
            
            <!-- Right Panel -->
            <div>
                <!-- Weather Widget -->
                <div class="weather-widget">
                    <div class="weather-temp" id="temperature">22°C</div>
                    <div class="weather-condition">Partly Cloudy</div>
                    <div style="margin-top: 15px;">
                        <div style="color: #888; font-size: 0.9rem;">Rain Probability</div>
                        <div style="font-size: 1.5rem; font-weight: bold; color: #00BCD4;">15%</div>
                    </div>
                </div>
                
                <!-- Feature Importance -->
                <div class="card">
                    <h2>📊 Feature Importance</h2>
                    
                    <p style="color:#888; font-size:0.8rem; margin:-6px 0 14px; line-height:1.4;">
                        Permutation importance on the 2025 hold-out (grouped).
                    </p>

                    <div class="importance-bar">
                        <div class="importance-label">
                            <span>Qualifying &amp; grid</span>
                            <span>39%</span>
                        </div>
                        <div class="importance-track">
                            <div class="importance-fill" style="width: 39%"></div>
                        </div>
                    </div>

                    <div class="importance-bar">
                        <div class="importance-label">
                            <span>Car / constructor form</span>
                            <span>27%</span>
                        </div>
                        <div class="importance-track">
                            <div class="importance-fill" style="width: 27%"></div>
                        </div>
                    </div>

                    <div class="importance-bar">
                        <div class="importance-label">
                            <span>Driver recent form</span>
                            <span>21%</span>
                        </div>
                        <div class="importance-track">
                            <div class="importance-fill" style="width: 21%"></div>
                        </div>
                    </div>

                    <div class="importance-bar">
                        <div class="importance-label">
                            <span>Experience &amp; teammate gap</span>
                            <span>9%</span>
                        </div>
                        <div class="importance-track">
                            <div class="importance-fill" style="width: 9%"></div>
                        </div>
                    </div>

                    <div class="importance-bar">
                        <div class="importance-label">
                            <span>Circuit history</span>
                            <span>4%</span>
                        </div>
                        <div class="importance-track">
                            <div class="importance-fill" style="width: 4%"></div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Full Race Predictions Table -->
        <div class="predictions-table" id="predictions-table" style="display: none;">
            <table>
                <thead>
                    <tr>
                        <th>Position</th>
                        <th>Driver</th>
                        <th>Team</th>
                        <th>Qualifying</th>
                        <th>Change</th>
                        <th>Podium %</th>
                    </tr>
                </thead>
                <tbody id="predictions-body">
                </tbody>
            </table>
        </div>
    </div>

    <script>
        const drivers = """ + json.dumps(DRIVERS) + """;
        
        // Update slider values
        document.querySelectorAll('input[type="range"]').forEach(slider => {
            slider.addEventListener('input', function() {
                this.nextElementSibling.textContent = this.value + '%';
            });
        });
        
        // Generate qualifying positions
        function generateQualifying() {
            const driverCodes = Object.keys(drivers);
            const qualifying = {};
            let baseTime = 78.5;
            
            // Shuffle for random qualifying
            driverCodes.sort(() => Math.random() - 0.5);
            
            driverCodes.forEach((code, i) => {
                qualifying[code] = baseTime + (i * 0.3) + (Math.random() * 0.5);
            });
            
            return qualifying;
        }
        
        // Generate predictions from a simulated qualifying order + the live model
        async function generatePredictions() {
            const loading = document.getElementById('loading');
            loading.style.display = 'block';

            const qualiInfluence = document.getElementById('quali-weight').value / 100;
            const qualifying = generateQualifying();
            const circuit = document.getElementById('track').value;

            try {
                const response = await fetch('/api/predict', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        qualifying: qualifying,
                        circuit: circuit,
                        quali_influence: qualiInfluence
                    })
                });
                
                const data = await response.json();
                displayPredictions(data);
            } catch (error) {
                console.error('Error:', error);
            } finally {
                loading.style.display = 'none';
            }
        }
        
        // Display predictions
        function displayPredictions(data) {
            // Update podium
            const podiumPlaces = document.querySelectorAll('.podium-place');
            data.predictions.slice(0, 3).forEach((pred, i) => {
                const place = podiumPlaces[i];
                place.querySelector('.driver-name').textContent = pred.name;
                const confidenceFill = place.querySelector('.confidence-fill');
                setTimeout(() => {
                    confidenceFill.style.width = (pred.confidence * 100) + '%';
                }, 100 + (i * 200));
            });
            
            // Update metrics
            document.getElementById('accuracy').textContent = data.accuracy + '%';
            document.getElementById('confidence').textContent = data.avgConfidence + '%';
            document.getElementById('volatility').textContent = data.volatility;
            
            // Update full predictions table
            const tbody = document.getElementById('predictions-body');
            tbody.innerHTML = '';
            
            data.predictions.forEach(pred => {
                const row = tbody.insertRow();
                row.innerHTML = `
                    <td style="font-weight: bold;">P${pred.position}</td>
                    <td>${pred.name}</td>
                    <td style="color: #888;">${pred.team}</td>
                    <td>P${pred.qualifying}</td>
                    <td class="${pred.change > 0 ? 'position-down' : pred.change < 0 ? 'position-up' : 'position-same'}">
                        ${pred.change > 0 ? '↓' + pred.change : pred.change < 0 ? '↑' + Math.abs(pred.change) : '—'}
                    </td>
                    <td>
                        <div style="display: flex; align-items: center;">
                            <div style="width: 60px; height: 6px; background: #333; border-radius: 3px; margin-right: 10px;">
                                <div style="width: ${pred.confidence * 100}%; height: 100%; background: #4CAF50; border-radius: 3px;"></div>
                            </div>
                            ${Math.round(pred.confidence * 100)}%
                        </div>
                    </td>
                `;
            });
            
            document.getElementById('predictions-table').style.display = 'block';
        }
        
        // Initialize with sample prediction on load
        setTimeout(() => {
            generatePredictions();
        }, 1000);
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return Response(HTML_PAGE, mimetype='text/html')

@app.route('/api/predict', methods=['POST'])
def predict():
    data = request.get_json() or {}
    qualifying = data.get('qualifying', {})            # {code: simulated_quali_value}
    circuit = data.get('circuit') or (_FORM["circuits"][0]["circuit_id"])
    influence = float(data.get('quali_influence', 0.7))

    # qualifying order (P1..Pn) = drivers sorted by their simulated quali value
    grid_order = [code for code, _ in sorted(qualifying.items(), key=lambda x: x[1])
                  if code in DRIVERS]

    result = predict_race(grid_order, circuit_id=circuit, quali_influence=influence)
    return jsonify({
        'predictions': result['predictions'],
        'accuracy': WINNER_ACC,                                  # real backtest winner acc
        'avgConfidence': int(round(result['podium_confidence'] * 100)),
        'volatility': result['reshuffle'],                       # avg positions moved vs grid
    })

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)