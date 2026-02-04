import requests
from bs4 import BeautifulSoup

NCS_LANDING = "https://www.gov.uk/government/publications/national-careers-service-course-directory"

def get_latest_ncs_csv_url():
    """
    Scrapes the NCS landing page and extracts the latest 'Live course providers' CSV URL.
    """
    
    r = requests.get(NCS_LANDING, timeout=30)
    r.raise_for_status()
    
    soup = BeautifulSoup(r.text, "html.parser")
    
    # Look for CSV links
    links = soup.find_all("a", href=True)
    csv_links = [a["href"] for a in links if a["href"].lower().endswith(".csv")]
    
    if not csv_links:
        raise RuntimeError("No CSV file links found on the NCS page.")
    
    url = csv_links[0]
    if url.startswith("/"):
        url = "https://www.gov.uk" + url
    return url
    
if __name__ == "__main__":
    print(get_latest_ncs_csv_url())
