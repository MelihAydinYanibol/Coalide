import requests
import json
from datetime import datetime
from main import lg

SECONDS_PER_MINUTE = 60

def calculate_exceptional_time_seconds(correct_answers, multiplier=1):
    """
    Calculate exceptional time in seconds.

    :param correct_answers: Number of correct answers.
    :param multiplier: Time multiplier to apply on awarded time.
    :return: Awarded exceptional time in seconds.

    Formula: correct_answers * 60 * max(multiplier, 0)
    Invalid multiplier values default to 1. Negative multipliers are clamped to 0.
    """
    try:
        multiplier_value = float(multiplier)
    except (TypeError, ValueError):
        multiplier_value = 1.0

    if multiplier_value < 0:
        multiplier_value = 0.0

    return int(round(correct_answers * SECONDS_PER_MINUTE * multiplier_value))

def add_exceptional_time(base_url, app_name, duration_seconds, exception_date=None,reason="Sebep belirtilmedi"):
    """
    Sends a POST request to the Secondary API to add an exception for a specific app.
    
    :param base_url: The URL of the Secondary API (e.g., 'http://YOUR_SERVER_IP:5001')
    :param app_name: Name of the executable (e.g., 'discord.exe')
    :param duration_seconds: Extra time allowed in seconds
    :param exception_date: Date string (YYYY-MM-DD). Defaults to today.
    :return: Response dictionary from the API
    """
    
    # Default to today's date if not provided
    if not exception_date:
        exception_date = datetime.now().strftime('%Y-%m-%d')
    
    endpoint = f"{base_url}/api/exceptions"
    
    # Construct the payload based on your API documentation
    payload = {
        "app_name": app_name,
        "date": exception_date,
        "exception_time": duration_seconds,
        "reason": reason
    }
    
    try:
        response = requests.post(
            endpoint, 
            json=payload, 
            timeout=5,
            headers={'Content-Type': 'application/json'}
        )
        
        # Parse the JSON response
        result = response.json()
        

        if response.status_code == 200 or response.status_code == 201:
            if result.get("status") != "queued":
                lg(f"✅ [Success] Exception added for {app_name} on {exception_date}.")
                return 1
        elif result.get("status") == "queued":
                lg(f"⚠️ [Queued] Primary API offline. Request for {app_name} saved to buffer.")
                return 1
        else:

            lg(f"❌ [Error] Server returned status {response.status_code}: {response.text}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"🚨 [Connection Error] Could not reach the Secondary API: {e}")
        return None

def get_exceptional_time(base_url, app_name, query_date=None):
    """
    Sends a GET request to retrieve exception details for a specific app and date.
    Corresponds to: curl http://localhost:5000/api/exceptions/<date>/<app_name>
    
    :param base_url: The URL of the API (e.g., 'http://localhost:5000')
    :param app_name: Name of the executable (e.g., 'chrome.exe')
    :param query_date: Date string (YYYY-MM-DD). Defaults to today.
    :return: Response JSON dictionary or None if failed.
    """
    
    # Default to today's date if not provided
    if not query_date:
        query_date = datetime.now().strftime('%Y-%m-%d')
    
    # Construct the URL with path parameters
    # This matches: /api/exceptions/2026-02-21/chrome.exe
    endpoint = f"{base_url}/api/exceptions/{query_date}/{app_name}"
    
    try:
        # standard curl implies a GET request
        response = requests.get(
            endpoint, 
            timeout=5
        )
        
        # Check for successful response
        if response.status_code == 200:
            result = response.json()
            print(f"✅ [Success] Data retrieved for {app_name} on {query_date}")
            return result
        elif response.status_code == 404:
            print(f"ℹ️ [Info] No exception found for {app_name} on {query_date}")
            # Return an empty, consistent structure so callers can safely iterate
            return {"data": []}
        else:
            print(f"❌ [Error] Server returned status {response.status_code}: {response.text}")
            # Return empty data to avoid NoneType errors in callers
            return {"data": []}

    except requests.exceptions.RequestException as e:
        print(f"🚨 [Connection Error] Could not reach the API: {e}")
        # If the API is unreachable, return empty data to allow caller to handle add flow
        return {"data": []}

def get_pending_exceptional_time(base_url, app_name, query_date=None, reason_contains=None):
    """
    Returns total queued exception_time (seconds) from PCV2 secondary queue
    for a specific app/date pair.
    """
    if not query_date:
        query_date = datetime.now().strftime('%Y-%m-%d')

    endpoint = f"{base_url}/api/server/queue"

    try:
        response = requests.get(endpoint, timeout=5)
        if response.status_code != 200:
            return 0

        result = response.json()
        items = result.get("data", {}).get("items", [])
        total_pending = 0

        for item in items:
            if str(item.get("method", "")).upper() != "POST":
                continue
            if not str(item.get("endpoint", "")).endswith("/exceptions"):
                continue

            payload = item.get("data", {})
            if isinstance(payload, str):
                try:
                    payload = json.loads(payload)
                except json.JSONDecodeError:
                    continue
            if not isinstance(payload, dict):
                continue

            if payload.get("app_name") != app_name or payload.get("date") != query_date:
                continue

            if reason_contains:
                reason_text = str(payload.get("reason", ""))
                if reason_contains.lower() not in reason_text.lower():
                    continue

            try:
                pending_seconds = int(payload.get("exception_time", 0))
            except (TypeError, ValueError):
                pending_seconds = 0

            if pending_seconds > 0:
                total_pending += pending_seconds

        return total_pending
    except requests.exceptions.RequestException:
        return 0


# --- Example Usage ---
# API_URL = "http://192.168.1.50:5001"
# add_exceptional_time(API_URL, "chrome.exe", 3600) # Adds 1 hour for today