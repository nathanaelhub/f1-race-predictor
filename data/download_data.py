#!/usr/bin/env python3
"""
F1 Data Downloader - Simple FastF1 Data Fetcher
Downloads and caches F1 race data for model training
"""

import os
import pandas as pd
import fastf1
from datetime import datetime
import json
import argparse

# Configuration
CACHE_DIR = 'fastf1_cache'
OUTPUT_DIR = '.'
SEASONS = [2023, 2024]

def setup_fastf1():
    """Initialize FastF1 with caching"""
    cache_path = os.path.join(OUTPUT_DIR, CACHE_DIR)
    os.makedirs(cache_path, exist_ok=True)
    fastf1.Cache.enable_cache(cache_path)
    print(f"✅ FastF1 cache enabled at: {cache_path}")

def get_race_calendar(year):
    """Get race calendar for a specific year"""
    try:
        schedule = fastf1.get_event_schedule(year)
        races = []
        
        for idx, event in schedule.iterrows():
            if event['EventFormat'] != 'conventional':
                continue  # Skip sprint weekends for simplicity
                
            races.append({
                'round': event['RoundNumber'],
                'name': event['EventName'],
                'location': event['Location'],
                'country': event['Country'],
                'date': event['Session5Date'].strftime('%Y-%m-%d') if pd.notna(event['Session5Date']) else None
            })
        
        return races
    except Exception as e:
        print(f"❌ Error getting calendar for {year}: {e}")
        return []

def download_race_data(year, round_num, session_types=['Q', 'R']):
    """
    Download race data for specific year and round
    
    Args:
        year (int): Season year
        round_num (int): Race round number
        session_types (list): List of session types to download ('Q', 'R', 'FP1', etc.)
    
    Returns:
        dict: Race data with results and metadata
    """
    try:
        race_data = {
            'year': year,
            'round': round_num,
            'sessions': {}
        }
        
        # Get event info
        event = fastf1.get_event(year, round_num)
        race_data['event_name'] = event['EventName']
        race_data['location'] = event['Location']
        race_data['country'] = event['Country']
        
        print(f"📊 Processing {event['EventName']} ({year} Round {round_num})")
        
        # Download each session
        for session_type in session_types:
            try:
                print(f"  🔄 Loading {session_type} session...", end=" ")
                
                session = fastf1.get_session(year, round_num, session_type)
                session.load()
                
                # Extract session results
                if hasattr(session, 'results') and session.results is not None:
                    results_df = session.results.copy()
                    
                    # Clean and standardize the data
                    session_data = {
                        'session_type': session_type,
                        'session_date': session.date.isoformat() if session.date else None,
                        'results': []
                    }
                    
                    # Extract driver results
                    for idx, row in results_df.iterrows():
                        driver_result = {
                            'driver_number': int(row.get('DriverNumber', 0)),
                            'driver_code': row.get('Abbreviation', ''),
                            'driver_name': f"{row.get('FirstName', '')} {row.get('LastName', '')}".strip(),
                            'team': row.get('TeamName', ''),
                            'position': int(row.get('Position', 0)) if pd.notna(row.get('Position')) else None,
                        }
                        
                        # Session-specific data
                        if session_type == 'Q':  # Qualifying
                            driver_result.update({
                                'q1_time': str(row.get('Q1', '')) if pd.notna(row.get('Q1')) else None,
                                'q2_time': str(row.get('Q2', '')) if pd.notna(row.get('Q2')) else None,
                                'q3_time': str(row.get('Q3', '')) if pd.notna(row.get('Q3')) else None,
                                'grid_position': int(row.get('Position', 0)) if pd.notna(row.get('Position')) else None
                            })
                        elif session_type == 'R':  # Race
                            driver_result.update({
                                'finish_position': int(row.get('Position', 0)) if pd.notna(row.get('Position')) else None,
                                'classified_position': int(row.get('ClassifiedPosition', 0)) if pd.notna(row.get('ClassifiedPosition')) else None,
                                'points': float(row.get('Points', 0)) if pd.notna(row.get('Points')) else 0,
                                'status': row.get('Status', ''),
                                'time': str(row.get('Time', '')) if pd.notna(row.get('Time')) else None,
                                'fastest_lap': row.get('FastestLap', False)
                            })
                        
                        session_data['results'].append(driver_result)
                    
                    race_data['sessions'][session_type] = session_data
                    print("✅")
                else:
                    print("❌ No results available")
                    
            except Exception as e:
                print(f"❌ Error loading {session_type}: {e}")
                continue
        
        return race_data
        
    except Exception as e:
        print(f"❌ Error downloading race data: {e}")
        return None

def save_race_data(race_data, format='both'):
    """Save race data to CSV and/or JSON"""
    if not race_data:
        return
    
    year = race_data['year']
    round_num = race_data['round']
    event_name = race_data['event_name'].replace(' ', '_').replace('/', '_')
    
    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    if format in ['csv', 'both']:
        # Save as CSV (flattened structure)
        csv_data = []
        
        quali_results = race_data['sessions'].get('Q', {}).get('results', [])
        race_results = race_data['sessions'].get('R', {}).get('results', [])
        
        # Merge qualifying and race results
        for quali in quali_results:
            # Find corresponding race result
            race_result = next((r for r in race_results if r['driver_number'] == quali['driver_number']), {})
            
            merged_row = {
                'year': year,
                'round': round_num,
                'event_name': race_data['event_name'],
                'location': race_data['location'],
                'country': race_data['country'],
                'driver_number': quali['driver_number'],
                'driver_code': quali['driver_code'],
                'driver_name': quali['driver_name'],
                'team': quali['team'],
                'qualifying_position': quali.get('position'),
                'grid_position': quali.get('grid_position'),
                'q1_time': quali.get('q1_time'),
                'q2_time': quali.get('q2_time'),
                'q3_time': quali.get('q3_time'),
                'race_position': race_result.get('finish_position'),
                'classified_position': race_result.get('classified_position'),
                'points': race_result.get('points', 0),
                'status': race_result.get('status', ''),
                'race_time': race_result.get('time'),
                'fastest_lap': race_result.get('fastest_lap', False)
            }
            csv_data.append(merged_row)
        
        # Save CSV
        if csv_data:
            csv_filename = f"{year}_Round_{round_num:02d}_{event_name}.csv"
            csv_path = os.path.join(OUTPUT_DIR, csv_filename)
            
            df = pd.DataFrame(csv_data)
            df.to_csv(csv_path, index=False)
            print(f"💾 CSV saved: {csv_filename}")
    
    if format in ['json', 'both']:
        # Save as JSON (full structure)
        json_filename = f"{year}_Round_{round_num:02d}_{event_name}.json"
        json_path = os.path.join(OUTPUT_DIR, json_filename)
        
        with open(json_path, 'w') as f:
            json.dump(race_data, f, indent=2, default=str)
        print(f"💾 JSON saved: {json_filename}")

def download_season_data(year, max_rounds=None):
    """Download data for an entire season"""
    print(f"\n🏁 Downloading {year} season data...")
    
    # Get race calendar
    races = get_race_calendar(year)
    if not races:
        print(f"❌ Could not get race calendar for {year}")
        return
    
    print(f"📅 Found {len(races)} races for {year}")
    
    # Limit rounds if specified
    if max_rounds:
        races = races[:max_rounds]
        print(f"🔢 Limited to first {max_rounds} rounds")
    
    success_count = 0
    total_count = len(races)
    
    for race in races:
        round_num = race['round']
        
        try:
            race_data = download_race_data(year, round_num)
            if race_data:
                save_race_data(race_data)
                success_count += 1
            
        except KeyboardInterrupt:
            print("\n⏹️  Download interrupted by user")
            break
        except Exception as e:
            print(f"❌ Failed to download Round {round_num}: {e}")
            continue
    
    print(f"\n📈 Season {year} download complete: {success_count}/{total_count} races")

def create_combined_dataset():
    """Combine all CSV files into a single dataset"""
    print("\n🔗 Creating combined dataset...")
    
    csv_files = [f for f in os.listdir(OUTPUT_DIR) if f.endswith('.csv')]
    
    if not csv_files:
        print("❌ No CSV files found to combine")
        return
    
    combined_data = []
    
    for csv_file in sorted(csv_files):
        csv_path = os.path.join(OUTPUT_DIR, csv_file)
        try:
            df = pd.read_csv(csv_path)
            combined_data.append(df)
            print(f"  ✅ Added {csv_file}: {len(df)} drivers")
        except Exception as e:
            print(f"  ❌ Error reading {csv_file}: {e}")
    
    if combined_data:
        combined_df = pd.concat(combined_data, ignore_index=True)
        
        # Save combined dataset
        combined_path = os.path.join(OUTPUT_DIR, 'f1_races_combined.csv')
        combined_df.to_csv(combined_path, index=False)
        
        print(f"\n💾 Combined dataset saved: f1_races_combined.csv")
        print(f"📊 Total records: {len(combined_df)}")
        print(f"📅 Years: {sorted(combined_df['year'].unique())}")
        print(f"🏁 Races: {len(combined_df.groupby(['year', 'round']))}")
        print(f"🏎️  Unique drivers: {combined_df['driver_code'].nunique()}")

def main():
    """Main function with command line interface"""
    parser = argparse.ArgumentParser(description='Download F1 race data using FastF1')
    parser.add_argument('--years', nargs='+', type=int, default=SEASONS,
                      help='Years to download (default: 2023 2024)')
    parser.add_argument('--rounds', type=int, help='Limit number of rounds per season')
    parser.add_argument('--race', nargs=2, metavar=('YEAR', 'ROUND'), type=int,
                      help='Download specific race (year round)')
    parser.add_argument('--format', choices=['csv', 'json', 'both'], default='csv',
                      help='Output format (default: csv)')
    parser.add_argument('--combine', action='store_true',
                      help='Create combined dataset from all CSV files')
    
    args = parser.parse_args()
    
    print("🏎️  F1 Data Downloader")
    print("=" * 50)
    
    # Setup FastF1
    setup_fastf1()
    
    if args.combine:
        create_combined_dataset()
        return
    
    if args.race:
        # Download specific race
        year, round_num = args.race
        print(f"📊 Downloading {year} Round {round_num}")
        race_data = download_race_data(year, round_num)
        if race_data:
            save_race_data(race_data, args.format)
    else:
        # Download full seasons
        for year in args.years:
            try:
                download_season_data(year, args.rounds)
            except KeyboardInterrupt:
                print("\n⏹️  Downloads interrupted")
                break
            except Exception as e:
                print(f"❌ Error downloading {year}: {e}")
                continue
        
        # Create combined dataset if CSV format
        if args.format in ['csv', 'both']:
            create_combined_dataset()
    
    print("\n✅ Download process completed!")
    print("\n📋 Next steps:")
    print("1. Check the generated CSV/JSON files")
    print("2. Run the Jupyter notebook: model/train_model.ipynb")
    print("3. Train your model and save it as model/f1_model.pkl")
    print("4. Start the Flask app: python app.py")

if __name__ == "__main__":
    main()