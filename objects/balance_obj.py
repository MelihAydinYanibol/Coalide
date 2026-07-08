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
from utils import lg,get_config

config = get_config()
BASE_RATE_PER_MINUTE = config.get("BASE_RATE_PER_MINUTE", 5) # credits per minute -> 300 credits per hour baseline
ESCALATION_PER_HOUR = config.get("ESCALATION_PER_HOUR", 0.5) # each additional hour already redeemed *for that date* makes the next hour's minutes 50% pricier
MINUTES_PER_DAY = 24 * 60  # hard cap: can't redeem more screentime for a date than the day physically has

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
    def __init__(self, username: str, initial_balance: int = 0, redeemed_minutes_by_date: dict | None = None, last_reset_date: str | None = None):
        self.username = username
        self.balance = Balance(initial_balance)
        self.redeemed_minutes_by_date = redeemed_minutes_by_date if redeemed_minutes_by_date is not None else {}
        self.last_reset_date = last_reset_date
 
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
 
    def max_redeemable_minutes(self, target_date: str | None = None) -> int:
        """
        The largest number of minutes of screentime the user can currently
        afford for target_date (defaults to today), given their balance and
        how much has already been redeemed for that date. Because the cost
        per minute escalates each hour, this walks minute-by-minute until the
        next minute would exceed the balance. Capped so the total redeemed
        for a date never exceeds 24 hours.
        """
        if target_date is None:
            target_date = date.today().isoformat()

        already_redeemed = self.redeemed_minutes_by_date.get(target_date, 0)
        budget = self.balance.get_balance()

        minutes = 0
        total_cost = 0.0
        max_more = MINUTES_PER_DAY - already_redeemed
        while minutes < max_more:
            minute_index = already_redeemed + minutes
            hour_bracket = minute_index // 60
            rate = BASE_RATE_PER_MINUTE * (1 + ESCALATION_PER_HOUR * hour_bracket)
            if round(total_cost + rate) > budget:
                break
            total_cost += rate
            minutes += 1
        return minutes

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
        (defaults to today; must not be in the past, and must fall within
        the current Monday-to-Sunday week, since credits reset on Monday
        and banking time past the reset would defeat it). The total
        redeemed for any single date can never exceed 24 hours -- a day
        doesn't have more minutes than that. If the user can
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

        if config.get("Credit_Reset_Weekly", True):
            week_end = date.today() + timedelta(days=6 - date.today().weekday())  # this week's Sunday
            if date.fromisoformat(target_date) > week_end:
                print(f"Cannot redeem for {target_date}: credits reset every Monday, so time can only be redeemed through {week_end.isoformat()}.")
                return False  # banking time past the weekly reset would defeat the reset

        already_redeemed = self.redeemed_minutes_by_date.get(target_date, 0)
        if already_redeemed + requested_minutes > MINUTES_PER_DAY:
            print(f"Cannot redeem {requested_minutes} minutes for {target_date}: a day only has {MINUTES_PER_DAY} minutes, and {already_redeemed} are already redeemed for that date (at most {MINUTES_PER_DAY - already_redeemed} more).")
            return False
 
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
 
 
def check_weekly_reset(user: User) -> bool:
    """
    Reset the user's balance to 0 once a new week has started since the
    last reset. Weeks turn over at Monday 00:00 (i.e. right after Sunday
    night), so a user opening the app on e.g. Tuesday will see that no
    reset has happened yet this week and get reset then.

    :return: True if the balance was reset, False otherwise.
    """
    today = date.today()
    week_start = today - timedelta(days=today.weekday())  # this week's Monday

    last_reset = date.fromisoformat(user.last_reset_date) if user.last_reset_date else date.min

    if last_reset < week_start:
        user.balance = Balance(0)
        user.last_reset_date = week_start.isoformat()
        save_data(user)
        return True
    return False


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
        "last_reset_date": user.last_reset_date,
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

    last_reset_date = data.get("last_reset_date")
    if last_reset_date is None:
        # Save file predates weekly reset tracking -- assume already up to
        # date for the current week so we don't wipe an existing balance.
        today = date.today()
        last_reset_date = (today - timedelta(days=today.weekday())).isoformat()

    return User(
        username=data["username"],
        initial_balance=data["balance"],
        redeemed_minutes_by_date=data.get("redeemed_minutes_by_date", {}),
        last_reset_date=last_reset_date,
    )