import os
import requests
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://analyst-assessment-production.up.railway.app/api/v1"

# Keep token out of the source code.
API_TOKEN = os.getenv("CLIPBOARD_API_TOKEN")


def get_headers():
    if not API_TOKEN:
        raise ValueError(
            "Missing CLIPBOARD_API_TOKEN environment variable."
        )

    return {
        "Authorization": f"Bearer {API_TOKEN}",
        "Accept": "application/json",
    }


def get_all_accounts(page_size=50):
    """
    Pull every CRM account using pagination.
    """

    all_accounts = []
    page = 1

    while True:
        url = f"{BASE_URL}/accounts"

        params = {
            "page": page,
            "page_size": page_size,
        }

        response = requests.get(
            url,
            headers=get_headers(),
            params=params,
            timeout=30,
        )

        response.raise_for_status()

        payload = response.json()

        accounts = payload.get("data", [])
        total = payload.get("total", 0)

        all_accounts.extend(accounts)

        print(
            f"Fetched page {page}: "
            f"{len(accounts)} accounts "
            f"({len(all_accounts)}/{total})"
        )

        # Stop when we have everything
        if len(all_accounts) >= total:
            break

        # Extra safety in case API returns no data
        if not accounts:
            break

        page += 1

    return all_accounts


def get_account(account_id):
    """
    Get one CRM account by account_id.
    """

    url = f"{BASE_URL}/accounts/{account_id}"

    response = requests.get(
        url,
        headers=get_headers(),
        timeout=30,
    )

    response.raise_for_status()

    return response.json()


def search_accounts(
    q=None,
    city=None,
    state=None,
    zip_code=None,
    street=None,
    parent_id=None,
    page=1,
    page_size=50,
):
    """
    Search/filter CRM accounts.
    """

    url = f"{BASE_URL}/accounts"

    params = {
        "q": q,
        "city": city,
        "state": state,
        "zip": zip_code,
        "street": street,
        "parent_id": parent_id,
        "page": page,
        "page_size": page_size,
    }

    # Remove empty parameters
    params = {
        key: value
        for key, value in params.items()
        if value not in [None, ""]
    }

    response = requests.get(
        url,
        headers=get_headers(),
        params=params,
        timeout=30,
    )

    response.raise_for_status()

    return response.json()


def validate_accounts(df):
    """
    Basic checks so we know the API pull worked.
    """

    print("\n--- CRM Validation ---")

    print(f"Total accounts: {len(df)}")

    if "account_id" in df.columns:
        print(
            "Unique account IDs:",
            df["account_id"].nunique()
        )

    if "name" in df.columns:
        print(
            "Missing names:",
            df["name"].fillna("").eq("").sum()
        )

    if "parent_id" in df.columns:
        print(
            "Accounts with parent:",
            df["parent_id"].fillna("").ne("").sum()
        )

        print(
            "Accounts without parent:",
            df["parent_id"].fillna("").eq("").sum()
        )

    if "status" in df.columns:
        print("\nStatus counts:")
        print(
            df["status"]
            .fillna("Missing")
            .value_counts()
        )


def show_bellhaven_summary(df):
    """
    Quick sanity check for Bellhaven-related CRM records.
    """

    if "name" not in df.columns:
        return

    bellhaven = df[
        df["name"]
        .fillna("")
        .str.contains(
            "bellhaven",
            case=False,
            na=False
        )
    ]

    print("\n--- Bellhaven Name Matches ---")
    print(f"Bellhaven-name accounts: {len(bellhaven)}")

    columns_to_show = [
        column
        for column in [
            "account_id",
            "name",
            "parent_name",
            "billing_city",
            "billing_state",
            "billing_zip",
            "lifetime_revenue",
            "outstanding_ar",
            "status",
        ]
        if column in bellhaven.columns
    ]

    print(
        bellhaven[columns_to_show]
        .to_string(index=False)
    )


def save_accounts(df, filename="crm_accounts.csv"):
    df.to_csv(
        filename,
        index=False
    )

    print(
        f"\nSaved {len(df)} CRM accounts "
        f"to {filename}"
    )


if __name__ == "__main__":

    accounts = get_all_accounts()

    df = pd.DataFrame(accounts)

    validate_accounts(df)

    show_bellhaven_summary(df)

    save_accounts(df)