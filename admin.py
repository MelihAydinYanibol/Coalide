"""
This file contains the admin mode for coalide. It is a separate mode that can be accessed from the main menu. It is intended for parents to use and manage.
"""

from utils import cls

def _prompt_amount(prompt: str) -> int | None:
    """Ask for a positive integer amount. Returns the amount, or None if the
    parent cancels (blank input or 'iptal'/'cancel')."""
    while True:
        raw = input(prompt).strip()
        if raw == "" or raw.lower() in ("iptal", "cancel"):
            return None
        try:
            amount = int(raw)
        except ValueError:
            print("That's not a valid number, try again.")
            continue
        if amount <= 0:
            print("Please enter a positive amount.")
            continue
        return amount


def credit_management(user):
    """Sub-menu for viewing and adjusting the child's credit balance."""
    from objects.balance_obj import save_data

    while True:
        cls()
        print("\n--- Credit Management ---")
        print(f"Current balance: {user.get_balance()} credits\n")
        options = {1: "View Balance", 2: "Add Credits", 3: "Remove Credits", 4: "Back"}
        for k, v in options.items():
            print(f"{k}. {v}")
        opt = input("\nSelect an option: ").strip()

        if opt == "1":
            print(f"\n{user.username}'s current balance is {user.get_balance()} credits.")

        elif opt == "2":
            amount = _prompt_amount("\nHow many credits to add? (blank to cancel): ")
            if amount is None:
                continue
            user.add_credits(amount)  # add_credits saves the data
            print(f"Added {amount} credits. New balance: {user.get_balance()} credits.")

        elif opt == "3":
            amount = _prompt_amount("\nHow many credits to remove? (blank to cancel): ")
            if amount is None:
                continue
            current = user.get_balance()
            if amount > current:
                print(f"That's more than the current balance ({current}). "
                      f"Removing all {current} credits instead.")
                amount = current
            user.balance.balance -= amount
            save_data(user)
            print(f"Removed {amount} credits. New balance: {user.get_balance()} credits.")

        elif opt == "4":
            return

        else:
            print("Please select a valid option.")


def _authenticate() -> bool:
    """Gate admin mode behind the ADMIN_PASSWORD from the .env file.

    Returns True if the parent entered the correct password, False if they
    failed all attempts or admin mode isn't password-protected yet."""
    import os
    from getpass import getpass
    from dotenv import load_dotenv

    load_dotenv()
    admin_password = os.getenv("ADMIN_PASSWORD", "")

    if not admin_password:
        print("Admin Mode is not password-protected. Set ADMIN_PASSWORD in the "
              ".env file to enable it. Access denied.")
        return False

    attempts = 3
    for remaining in range(attempts - 1, -1, -1):
        entered = getpass("Enter admin password: ")
        if entered == admin_password:
            return True
        if remaining:
            print(f"Incorrect password. {remaining} attempt(s) left.")
        else:
            print("Incorrect password. Access denied.")
    return False


def main():
    from utils import get_current_user
    from objects.balance_obj import load_data

    if not _authenticate():
        return
    cls()

    user = load_data(get_current_user())

    print("\nWelcome to Admin Mode. Here you can manage your child's account and view their progress.\n")
    while True:
        options = {1: "Credit Management", 2: "Exit"}
        print("Options:")
        for k, v in options.items():
            print(f"{k}. {v}")
        opt = input("\nSelect an option: ").strip()

        if opt == "1":
            cls()
            credit_management(user)
        elif opt == "2":
            cls()
            print("Exiting Admin Mode...")
            return
        else:
            print("Please select a valid option.\n")


if __name__ == "__main__":
    main()
