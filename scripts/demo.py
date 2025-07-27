#!/usr/bin/env python3
"""
F1 Race Predictor - Simple Demo Script
Academic research project demonstration without web server

Usage:
    python demo.py
    
This script demonstrates the core prediction functionality:
- Takes Monaco qualifying results as input
- Gets mock weather data for Monaco
- Makes race predictions using XGBoost model
- Displays results in a formatted table
"""

import os
import pickle
import numpy as np
import pandas as pd
from datetime import datetime

# Configuration
MODEL_PATH = 'model/f1_model.pkl'

# Monaco qualifying results (example from Monaco 2024)
MONACO_QUALIFYING = {
    'LEC': 78.291,   # P1 - Charles Leclerc
    'PIA': 78.301,   # P2 - Oscar Piastri  
    'SAI': 78.348,   # P3 - Carlos Sainz
    'NOR': 78.365,   # P4 - Lando Norris
    'VER': 78.392,   # P5 - Max Verstappen
    'RUS': 78.441,   # P6 - George Russell
    'HAM': 78.507,   # P7 - Lewis Hamilton
    'TSU': 78.717,   # P8 - Yuki Tsunoda
    'ALB': 78.898,   # P9 - Alexander Albon
    'GAS': 79.049,   # P10 - Pierre Gasly
    'OCO': 79.128,   # P11 - Esteban Ocon
    'HUL': 79.215,   # P12 - Nico Hulkenberg
    'PER': 79.307,   # P13 - Sergio Perez
    'ALO': 79.408,   # P14 - Fernando Alonso
    'BOT': 79.512,   # P15 - Valtteri Bottas
    'ZHO': 79.634,   # P16 - Zhou Guanyu
    'MAG': 79.758,   # P17 - Kevin Magnussen
    'RIC': 79.891,   # P18 - Daniel Ricciardo
    'STR': 80.024,   # P19 - Lance Stroll
    'SAR': 80.177    # P20 - Logan Sargeant
}

# Driver names for display
DRIVER_NAMES = {
    'VER': 'Max Verstappen', 'PER': 'Sergio Perez',
    'HAM': 'Lewis Hamilton', 'RUS': 'George Russell',
    'LEC': 'Charles Leclerc', 'SAI': 'Carlos Sainz',
    'NOR': 'Lando Norris', 'PIA': 'Oscar Piastri',
    'ALO': 'Fernando Alonso', 'STR': 'Lance Stroll',
    'TSU': 'Yuki Tsunoda', 'RIC': 'Daniel Ricciardo',
    'HUL': 'Nico Hulkenberg', 'MAG': 'Kevin Magnussen',
    'GAS': 'Pierre Gasly', 'OCO': 'Esteban Ocon',
    'BOT': 'Valtteri Bottas', 'ZHO': 'Zhou Guanyu',
    'SAR': 'Logan Sargeant', 'ALB': 'Alexander Albon'
}

class F1DemoPredictor:
    def __init__(self):
        self.model = None
        self.feature_names = [
            'qualifying_position', 'driver_rating', 'team_performance',
            'weather_dry', 'track_temperature', 'tire_strategy'
        ]
        self.load_model()
    
    def load_model(self):
        """Load the trained XGBoost model or use fallback"""
        try:
            if os.path.exists(MODEL_PATH):
                with open(MODEL_PATH, 'rb') as f:
                    self.model = pickle.load(f)
                print("✅ XGBoost model loaded successfully")
                return True
            else:
                print("⚠️  Model not found at", MODEL_PATH)
                print("💡 Run the Jupyter notebook first: model/train_model.ipynb")
                print("🔄 Using statistical fallback predictions")
                self.model = None
                return False
        except Exception as e:
            print(f"❌ Error loading model: {e}")
            print("🔄 Using statistical fallback predictions")
            self.model = None
            return False
    
    def get_monaco_weather(self):
        """Get mock weather data for Monaco"""
        return {
            'temperature': 24.5,  # Typical Monaco race day
            'condition': 'clear',  # Clear skies
            'humidity': 68.0      # Mediterranean humidity
        }
    
    def create_features(self, qualifying_position, driver_code, weather):
        """Create feature vector for ML model"""
        # Driver ratings based on 2024 performance
        driver_ratings = {
            'VER': 0.95, 'HAM': 0.90, 'LEC': 0.88, 'RUS': 0.82, 'SAI': 0.80,
            'NOR': 0.78, 'PIA': 0.76, 'PER': 0.74, 'ALO': 0.72, 'GAS': 0.65,
            'OCO': 0.63, 'TSU': 0.60, 'HUL': 0.58, 'RIC': 0.56, 'ALB': 0.54,
            'MAG': 0.52, 'BOT': 0.50, 'ZHO': 0.48, 'STR': 0.46, 'SAR': 0.42
        }
        
        # Team performance based on 2024 car competitiveness
        team_performance = {
            'VER': 0.92, 'PER': 0.92,  # Red Bull Racing
            'LEC': 0.85, 'SAI': 0.85,  # Ferrari
            'HAM': 0.78, 'RUS': 0.78,  # Mercedes
            'NOR': 0.82, 'PIA': 0.82,  # McLaren
            'ALO': 0.62, 'STR': 0.62,  # Aston Martin
            'TSU': 0.58, 'RIC': 0.58,  # RB (AlphaTauri)
            'HUL': 0.55, 'MAG': 0.55,  # Haas
            'GAS': 0.60, 'OCO': 0.60,  # Alpine
            'BOT': 0.48, 'ZHO': 0.48,  # Kick Sauber
            'ALB': 0.52, 'SAR': 0.52   # Williams
        }
        
        return [
            qualifying_position,
            driver_ratings.get(driver_code, 0.5),
            team_performance.get(driver_code, 0.5),
            1.0 if weather['condition'] != 'rain' else 0.0,
            weather['temperature'],
            1.0  # Default tire strategy
        ]
    
    def predict_race(self, qualifying_results, weather):
        """Generate race predictions"""
        predictions = []
        
        # Sort drivers by qualifying time
        sorted_drivers = sorted(qualifying_results.items(), key=lambda x: x[1])
        
        for i, (driver_code, quali_time) in enumerate(sorted_drivers):
            qualifying_position = i + 1
            
            # Create feature vector
            features = self.create_features(qualifying_position, driver_code, weather)
            
            # Make prediction
            if self.model:
                try:
                    # Use XGBoost model
                    feature_array = np.array(features).reshape(1, -1)
                    probabilities = self.model.predict_proba(feature_array)[0]
                    predicted_position = np.argmax(probabilities) + 1
                    confidence = np.max(probabilities)
                except Exception as e:
                    print(f"⚠️  Model prediction error for {driver_code}: {e}")
                    predicted_position, confidence = self.fallback_prediction(qualifying_position, driver_code)
            else:
                predicted_position, confidence = self.fallback_prediction(qualifying_position, driver_code)
            
            predictions.append({
                'driver_code': driver_code,
                'driver_name': DRIVER_NAMES[driver_code],
                'qualifying_position': qualifying_position,
                'qualifying_time': quali_time,
                'predicted_position': predicted_position,
                'confidence': confidence,
                'position_change': predicted_position - qualifying_position
            })
        
        # Sort by predicted position for final results table
        predictions.sort(key=lambda x: x['predicted_position'])
        
        return predictions
    
    def fallback_prediction(self, qualifying_position, driver_code):
        """Statistical fallback prediction when model is unavailable"""
        # Monaco-specific factors (low overtaking, qualifying matters more)
        base_change = 0.0  # Less position change at Monaco
        
        # Driver skill factor (better drivers more likely to gain positions)
        driver_skill = {
            'VER': 0.3, 'HAM': 0.2, 'LEC': 0.1, 'NOR': 0.1, 'SAI': 0.0,
            'RUS': 0.0, 'PIA': -0.1, 'ALO': 0.1, 'PER': -0.2, 'GAS': -0.1,
        }
        
        skill_bonus = driver_skill.get(driver_code, -0.2)  # Default slight penalty
        
        # Add controlled randomness
        random_factor = np.random.normal(0, 1.5)  # Monaco has less variance
        
        # Calculate position change
        position_change = base_change + skill_bonus + random_factor
        
        # Apply constraints
        predicted_position = max(1, min(20, int(qualifying_position + position_change)))
        
        # Calculate confidence based on prediction certainty
        confidence = max(0.4, min(0.9, 0.7 - abs(position_change) / 10))
        
        return predicted_position, confidence

def print_header():
    """Print demo header"""
    print("=" * 70)
    print("🏎️  F1 RACE PREDICTOR - MONACO GRAND PRIX DEMO")
    print("=" * 70)
    print("🎯 Academic Research Project - XGBoost ML Prediction")
    print("📍 Circuit: Monaco Street Circuit")
    print("📅 Demo Date:", datetime.now().strftime("%Y-%m-%d %H:%M"))
    print()

def print_weather_info(weather):
    """Print weather information"""
    print("🌤️  RACE DAY WEATHER CONDITIONS")
    print("-" * 40)
    print(f"🌡️  Temperature:  {weather['temperature']}°C")
    print(f"☁️  Condition:    {weather['condition'].title()}")
    print(f"💧 Humidity:     {weather['humidity']}%")
    print()

def print_qualifying_results(qualifying_results):
    """Print qualifying results table"""
    print("🏁 SATURDAY QUALIFYING RESULTS")
    print("-" * 50)
    print(f"{'Pos':<4} {'Driver':<18} {'Time':<10} {'Gap':<8}")
    print("-" * 50)
    
    sorted_results = sorted(qualifying_results.items(), key=lambda x: x[1])
    pole_time = sorted_results[0][1]
    
    for i, (driver_code, time) in enumerate(sorted_results, 1):
        gap = f"+{time - pole_time:.3f}" if i > 1 else "POLE"
        driver_name = DRIVER_NAMES[driver_code]
        print(f"{i:<4} {driver_name:<18} {time:.3f}s {gap:<8}")
    print()

def print_predictions_table(predictions):
    """Print race predictions in a formatted table"""
    print("🔮 RACE PREDICTIONS - EXPECTED FINISHING ORDER")
    print("-" * 80)
    print(f"{'Pos':<4} {'Driver':<18} {'Quali':<6} {'Change':<8} {'Confidence':<12} {'Notes'}")
    print("-" * 80)
    
    for pred in predictions:
        pos = pred['predicted_position']
        driver = pred['driver_name']
        quali_pos = f"P{pred['qualifying_position']}"
        
        # Format position change
        change = pred['position_change']
        if change > 0:
            change_str = f"↓{change}"
            change_color = "📉"
        elif change < 0:
            change_str = f"↑{abs(change)}"
            change_color = "📈"
        else:
            change_str = "—"
            change_color = "🔒"
        
        confidence_pct = f"{pred['confidence']*100:.1f}%"
        
        # Add contextual notes
        if change > 3:
            note = "Major drop expected"
        elif change < -3:
            note = "Significant gain expected"
        elif abs(change) <= 1:
            note = "Holds position"
        else:
            note = "Moderate change"
        
        print(f"P{pos:<3} {driver:<18} {quali_pos:<6} {change_color}{change_str:<7} {confidence_pct:<12} {note}")
    
    print("-" * 80)

def print_analysis(predictions):
    """Print prediction analysis"""
    print("📊 PREDICTION ANALYSIS")
    print("-" * 40)
    
    # Calculate statistics
    big_movers_up = [p for p in predictions if p['position_change'] < -3]
    big_movers_down = [p for p in predictions if p['position_change'] > 3]
    avg_confidence = np.mean([p['confidence'] for p in predictions])
    
    print(f"🎯 Average Confidence: {avg_confidence*100:.1f}%")
    print(f"📈 Big Gainers ({len(big_movers_up)}): ", end="")
    if big_movers_up:
        print(", ".join([p['driver_code'] for p in big_movers_up]))
    else:
        print("None")
    
    print(f"📉 Big Losers ({len(big_movers_down)}): ", end="")
    if big_movers_down:
        print(", ".join([p['driver_code'] for p in big_movers_down]))
    else:
        print("None")
    
    print()
    print("🏎️  Monaco Factor: Low overtaking expected due to track characteristics")
    print("⚡ Key Insight: Qualifying position heavily influences race outcome")
    print()

def print_footer():
    """Print demo footer"""
    print("=" * 70)
    print("✅ Demo completed successfully!")
    print()
    print("📋 To run your own predictions:")
    print("   1. Install dependencies: pip install -r requirements.txt")
    print("   2. Download data: python data/download_data.py")
    print("   3. Train model: jupyter notebook model/train_model.ipynb")
    print("   4. Run web app: python app.py")
    print()
    print("🔬 Research Project: Machine Learning for F1 Race Prediction")
    print("📄 Citation: F1 Race Predictor Academic Research Project (2024)")
    print("=" * 70)

def main():
    """Run the F1 prediction demo"""
    # Print header
    print_header()
    
    # Initialize predictor
    predictor = F1DemoPredictor()
    
    # Get weather data
    weather = predictor.get_monaco_weather()
    print_weather_info(weather)
    
    # Show qualifying results
    print_qualifying_results(MONACO_QUALIFYING)
    
    # Generate predictions
    print("🤖 Generating ML predictions...")
    predictions = predictor.predict_race(MONACO_QUALIFYING, weather)
    print("✅ Predictions generated!")
    print()
    
    # Display results
    print_predictions_table(predictions)
    
    # Show analysis
    print_analysis(predictions)
    
    # Print footer
    print_footer()

if __name__ == "__main__":
    main()