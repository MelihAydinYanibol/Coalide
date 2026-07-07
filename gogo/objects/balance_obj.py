"""
This module calculates/redeems/adds/removes balance for a user.
It is used to keep track of the user's credits and to ensure that
the user has enough credits to get screentime -- for today or a
future date the parent/kid chooses to bank hours for.
 
Redeeming credits is what actually grants real screentime, via the
parental controls API in parental_api.py.
"""
 
import json
import os
from datetime import date, timedelta
from pathlib import Path
 
from parental_connection import add_exceptional_time
 
BASE_RATE_PER_MINUTE = 5       # credits per minute -> 300 credits per hour baseline
ESCALATION_PER_HOUR = 0.5       # each additional hour already redeemed *for that date* makes the next hour's minutes 50% pricier

import dotenv
dotenv.load_dotenv()  # Load environment variables from .env file

DEFAULT_BASE_URL = os.getenv("PARENTAL_CONTROL_URL","192.168.1.1")
DEFAULT_APP_NAME = "OVERALL"   # e.g. "chrome.exe"
DATA_DIR = Path(__file__).resolve().parent.parent
 
 
class Balance:
    def __init__(self, initial_balance: int = 0):
        self.balance = initial_balance
 
    def add_credits(self, amount: int):
        self.balance += amount
 
    def redeem_credits(self, amount: int) -> bool:
        if self.balance >= amount:
            self.balance -= amount
            return True
        else:
            return False
 
    def get_balance(self) -> int:
        return self.balance
 
 
class User:
    def __init__(self, username: str, initial_balance: int = 0, redeemed_minutes_by_date: dict | None = None):
        self.username = username
        self.balance = Balance(initial_balance)
        self.redeemed_minutes_by_date = redeemed_minutes_by_date if redeemed_minutes_by_date is not None else {}
 
    def add_credits(self, amount: int):
        self.balance.add_credits(amount)
        save_data(self)
 
    def get_balance(self) -> int:
        return self.balance.get_balance()
 
    def cost_for_minutes(self, requested_minutes: int, target_date: str | None = None) -> int:
        """
        Calculate the cost of redeeming `requested_minutes` of screentime
        *for target_date* (defaults to today). Escalation is based on how
        much has already been redeemed for that specific date -- each
        date's pricing curve is independent, so banking hours for a future
        date doesn't inherit today's escalation, and vice versa.
        """
        if target_date is None:
            target_date = date.today().isoformat()
 
        already_redeemed = self.redeemed_minutes_by_date.get(target_date, 0)
 
        total_cost = 0
        for m in range(requested_minutes):
            minute_index = already_redeemed + m
            hour_bracket = minute_index // 60
            rate = BASE_RATE_PER_MINUTE * (1 + ESCALATION_PER_HOUR * hour_bracket)
            total_cost += rate
        return round(total_cost)
 
    def redeem_screentime(
        self,
        requested_minutes: int,
        target_date: str | None = None,
        app_name: str | None = None,
        base_url: str | None = None,
        reason: str = "Doğru cevaplarla kazanıldı",
    ) -> bool:
        """
        Attempt to redeem `requested_minutes` of screentime for target_date
        (defaults to today; must not be in the past). If the user can
        afford the escalating cost, this actually calls the parental
        controls API to grant the time.
 
        Credits are only permanently spent if the grant succeeds (or is
        queued for later delivery by the server, which still counts as a
        guaranteed grant). If the API call hard-fails -- server reachable
        but rejected the request, or unreachable entirely -- the credits
        are refunded and nothing is recorded as redeemed.
 
        :return: True if screentime was actually granted (or queued), False otherwise.
        """
        reason = f"{requested_minutes} Dakika Aktarıldı - COALIDE"  # prepend the "5" to the reason so the parental controls server knows it's a COALIDE redemption
        if target_date is None:
            target_date = date.today().isoformat()
 
        if date.fromisoformat(target_date) < date.today():
            print(f"Cannot redeem for a past date: {target_date}.")
            return False  # can't redeem for a date that's already passed
 
        cost = self.cost_for_minutes(requested_minutes, target_date)
 
        if not self.balance.redeem_credits(cost):
            print(f"Not enough credits to redeem {requested_minutes} minutes for {target_date}. Needed: {cost}, Available: {self.balance.get_balance()}.")
            return False  # not enough credits -- nothing deducted, nothing to refund
 
        resolved_app = app_name or DEFAULT_APP_NAME
        resolved_url = base_url or DEFAULT_BASE_URL
 
        result = add_exceptional_time(
            base_url=resolved_url,
            app_name=resolved_app,
            duration_seconds=requested_minutes * 60,
            exception_date=target_date,
            reason=reason,
        )
 
        if result is None:
            # Hard failure -- refund the credits, don't record the redemption.
            self.balance.add_credits(cost)
            print(f"Ooops! Something went wrong, try again. Credits refunded.")
            return False
 
        # result == 1 means the grant succeeded OR was queued for later delivery --
        # either way the server has guaranteed it, so commit the redemption.
        self.redeemed_minutes_by_date[target_date] = self.redeemed_minutes_by_date.get(target_date, 0) + requested_minutes
        save_data(self)
        return True
 
 
def garbage_collect_old_redeemed_minutes(user: User):
    """
    Remove entries from redeemed_minutes_by_date that are older than two months.
    This helps keep the data clean and prevents unnecessary growth of the dictionary.
    """
    cutoff_date = date.today() - timedelta(days=60)
    user.redeemed_minutes_by_date = {
        d: m for d, m in user.redeemed_minutes_by_date.items() if date.fromisoformat(d) >= cutoff_date
    }
 
 
def save_data(user: User):
    """
    Save the user's balance and redeemed minutes to a JSON file.
    """
    garbage_collect_old_redeemed_minutes(user)  # clean up BEFORE building the dict to save
 
    data = {
        "username": user.username,
        "balance": user.balance.get_balance(),
        "redeemed_minutes_by_date": user.redeemed_minutes_by_date,
    }
 
    data_file_path = DATA_DIR / f"{user.username}_data.json"

    with open(data_file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)
 
 
def load_data(username: str) -> User:
    """
    Load a User from their saved JSON file. If no save file exists yet
    (first time this username has been used), returns a fresh User with
    zero balance and no redemption history.
    """
    file_path = DATA_DIR / f"{username}_data.json"
 
    if not file_path.exists():
        return User(username)
 
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
 
    return User(
        username=data["username"],
        initial_balance=data["balance"],
        redeemed_minutes_by_date=data.get("redeemed_minutes_by_date", {}),
    )