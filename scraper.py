#pip install requests beautifulsoup4 pandas

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import pandas as pd
import re

BASE_URL = "https://analyst-assessment-production.up.railway.app"


def get_soup(url):
    response = requests.get(url, timeout=20)
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")


def collect_community_links():
    """
    Collect all unique Bellhaven community detail-page URLs.

    We check:
    1. All paginated community directory pages
    2. The homepage, because newly added facilities may appear there
       before being added to the directory
    """

    community_links = set()

    # Community directory pages
    for page in range(1, 4):
        url = f"{BASE_URL}/communities?page={page}"
        soup = get_soup(url)

        for tag in soup.find_all("a", href=True):
            href = tag["href"]

            if href.startswith("/communities/"):
                community_links.add(urljoin(BASE_URL, href))

    # Homepage
    soup = get_soup(BASE_URL)

    for tag in soup.find_all("a", href=True):
        href = tag["href"]

        if href.startswith("/communities/"):
            community_links.add(urljoin(BASE_URL, href))

    return sorted(community_links)


def scrape_community(url):
    """
    Scrape one Bellhaven community page.
    """

    soup = get_soup(url)

    # -------------------------
    # Facility name
    # -------------------------
    h1 = soup.find("h1")

    name = h1.get_text(strip=True) if h1 else ""

    # -------------------------
    # Address
    # -------------------------
    address = ""
    city = ""
    state = ""
    zip_code = ""

    address_dt = soup.find(
        "dt",
        string=lambda x: x and "address" in x.lower()
    )

    if address_dt:
        address_dd = address_dt.find_next_sibling("dd")

        if address_dd:
            parts = list(address_dd.stripped_strings)

            # Example:
            # [
            #   "1800 N Blanchard St",
            #   "Findlay, OH 45840"
            # ]

            if len(parts) >= 1:
                address = parts[0].strip()

            if len(parts) >= 2:
                city_state_zip = parts[1].strip()

                match = re.match(
                    r"(.+?),\s*([A-Z]{2})\s+(\d{5}(?:-\d{4})?)",
                    city_state_zip
                )

                if match:
                    city = match.group(1).strip()
                    state = match.group(2).strip()
                    zip_code = match.group(3).strip()
    # -------------------------
    # Phone
    # -------------------------
    phone = ""
    
    phone_dt = soup.find(
        "dt",
        string=lambda x: x and "phone" in x.lower()
    )
    
    if phone_dt:
        phone_dd = phone_dt.find_next_sibling("dd")
    
        if phone_dd:
            phone = phone_dd.get_text(" ", strip=True)

    # -------------------------
    # Care offerings
    # -------------------------
    care_offerings = [
        badge.get_text(" ", strip=True)
        for badge in soup.select(".detail .badge")
    ]

    # Remove duplicate offerings while keeping order
    care_offerings = list(dict.fromkeys(care_offerings))

    care_offerings_text = ", ".join(care_offerings)

    return {
        "name": name,
        "address": address,
        "city": city,
        "state": state,
        "zip": zip_code,
         "phone": phone,
        "care_offerings": care_offerings_text,
        "source_url": url
    }


def scrape_all_communities():
    """
    Scrape all Bellhaven community pages.
    """

    links = collect_community_links()

    print(f"Found {len(links)} unique community URLs.\n")

    records = []

    for index, url in enumerate(links, start=1):

        try:
            record = scrape_community(url)

            records.append(record)

            print(
                f"{index}/{len(links)} "
                f"Scraped: {record['name']}"
            )

        except Exception as error:

            print(
                f"{index}/{len(links)} "
                f"FAILED: {url}"
            )

            print(f"Error: {error}")

    df = pd.DataFrame(records)

    # Remove any accidental duplicate facility URLs
    df = df.drop_duplicates(
        subset=["source_url"]
    ).reset_index(drop=True)

    return df


def validate_results(df):
    """
    Basic quality checks.
    """

    print("\n--- Validation ---")

    print(f"Total facilities: {len(df)}")

    print(
        "Missing names:",
        df["name"].eq("").sum()
    )

    print(
        "Missing addresses:",
        df["address"].eq("").sum()
    )

    print(
        "Missing cities:",
        df["city"].eq("").sum()
    )

    print(
        "Missing states:",
        df["state"].eq("").sum()
    )

    print(
        "Missing ZIP codes:",
        df["zip"].eq("").sum()
    )
    
    print(
        "Missing phone:",
        df["phone"].eq("").sum()
    )

    print(
        "Missing care offerings:",
        df["care_offerings"].eq("").sum()
    )


if __name__ == "__main__":

    df = scrape_all_communities()

    validate_results(df)

    # Display sample
    print("\n--- Sample ---")

    print(
        df[
            [
                "name",
                "address",
                "city",
                "state",
                "zip",
                "phone",
                "care_offerings"
            ]
        ].head()
    )

    # Save CSV
    output_file = "bellhaven_locations.csv"

    df.to_csv(
        output_file,
        index=False
    )

    print(
        f"\nSaved {len(df)} facilities "
        f"to {output_file}"
    )