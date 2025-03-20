import streamlit as st
import requests
from bs4 import BeautifulSoup
import re
import json
import validators
import urllib.parse

# Function to fetch page content
def get_page_content(url):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        return None

# Function to analyze metadata (Title, Meta Description)
def analyze_metadata(soup):
    title = soup.title.string if soup.title else "No Title Found"
    meta_desc = soup.find("meta", attrs={"name": "description"})
    meta_desc = meta_desc["content"] if meta_desc else "No Meta Description Found"
    
    return {
        "Title": title,
        "Meta Description": meta_desc,
        "Title Length": len(title),
        "Meta Description Length": len(meta_desc)
    }

# Function to check internal links
def check_internal_links(soup, base_url):
    internal_links = []
    broken_links = []

    for link in soup.find_all("a", href=True):
        href = link["href"]
        full_url = urllib.parse.urljoin(base_url, href)
        
        if base_url in full_url:
            try:
                response = requests.head(full_url, timeout=5)
                if response.status_code >= 400:
                    broken_links.append(full_url)
                else:
                    internal_links.append(full_url)
            except:
                broken_links.append(full_url)

    return {
        "Total Internal Links": len(internal_links),
        "Broken Internal Links": broken_links
    }

# Function to analyze H1 tags
def analyze_h1_tags(soup):
    h1_tags = [h1.get_text(strip=True) for h1 in soup.find_all("h1")]
    return {
        "Total H1 Tags": len(h1_tags),
        "H1 Tags": h1_tags,
        "Suggestion": "Use only one main H1 tag for better SEO" if len(h1_tags) > 1 else "Looks Good!"
    }

# Function to analyze anchor texts
def analyze_anchor_texts(soup):
    anchor_texts = [a.get_text(strip=True) for a in soup.find_all("a")]
    empty_anchors = [a for a in anchor_texts if not a]

    return {
        "Total Anchor Links": len(anchor_texts),
        "Empty Anchor Texts": len(empty_anchors),
        "Suggestion": "Ensure all links have meaningful anchor texts."
    }

# Function to analyze images (alt texts, broken images)
def analyze_images(soup, base_url):
    images = soup.find_all("img")
    missing_alt = []
    broken_images = []

    for img in images:
        src = img.get("src")
        alt_text = img.get("alt", "").strip()
        
        full_src = urllib.parse.urljoin(base_url, src)
        if not alt_text:
            missing_alt.append(full_src)
        
        try:
            response = requests.head(full_src, timeout=5)
            if response.status_code >= 400:
                broken_images.append(full_src)
        except:
            broken_images.append(full_src)

    return {
        "Total Images": len(images),
        "Images Missing Alt Text": missing_alt,
        "Broken Images": broken_images
    }

# Function to check accessibility issues (redirects, loops)
def check_accessibility(url):
    try:
        response = requests.get(url, timeout=10, allow_redirects=True)
        final_url = response.url
        return {
            "Final URL": final_url,
            "Redirect Count": len(response.history),
            "Status Code": response.status_code
        }
    except requests.exceptions.RequestException:
        return {"Error": "URL is not accessible"}

# Function to analyze crawlability (JS, CSS issues)
def check_crawlability(soup):
    scripts = soup.find_all("script", src=True)
    stylesheets = soup.find_all("link", rel="stylesheet")

    broken_scripts = []
    broken_stylesheets = []

    for script in scripts:
        src = script["src"]
        try:
            response = requests.head(src, timeout=5)
            if response.status_code >= 400:
                broken_scripts.append(src)
        except:
            broken_scripts.append(src)

    for css in stylesheets:
        href = css["href"]
        try:
            response = requests.head(href, timeout=5)
            if response.status_code >= 400:
                broken_stylesheets.append(href)
        except:
            broken_stylesheets.append(href)

    return {
        "Broken JS Files": broken_scripts,
        "Broken CSS Files": broken_stylesheets
    }

# Function to get Page Speed Insights via Google Lighthouse API
def analyze_page_speed(url):
    try:
        import subprocess
        result = subprocess.run(
            ["lighthouse", url, "--quiet", "--output=json"],
            capture_output=True,
            text=True
        )
        lighthouse_data = json.loads(result.stdout)
        fcp = lighthouse_data["audits"]["first-contentful-paint"]["displayValue"]
        return {"First Contentful Paint": fcp}
    except:
        return {"Error": "Lighthouse API Not Configured"}

# Streamlit UI
st.title("One Page SEO Audit Tool")
st.markdown("### Enter a URL to analyze its SEO performance:")

url = st.text_input("Website URL", "")

if st.button("Analyze"):
    if validators.url(url):
        st.write("Fetching data... Please wait.")

        page_content = get_page_content(url)
        if page_content:
            soup = BeautifulSoup(page_content, "html.parser")

            # SEO Insights
            st.subheader("🔍 SEO Audit Results")
            
            # Metadata
            meta_data = analyze_metadata(soup)
            st.write("🏷️ **Title & Meta Description Analysis**")
            st.json(meta_data)

            # Internal Links
            links_data = check_internal_links(soup, url)
            st.write("🔗 **Internal Link Verification**")
            st.json(links_data)

            # H1 Tags
            h1_data = analyze_h1_tags(soup)
            st.write("🔖 **H1 Tag Examination**")
            st.json(h1_data)

            # Anchor Texts
            anchor_data = analyze_anchor_texts(soup)
            st.write("⚓ **Link Anchor Text Review**")
            st.json(anchor_data)

            # Image Analysis
            image_data = analyze_images(soup, url)
            st.write("🖼️ **Image Diagnostics**")
            st.json(image_data)

            # Accessibility Check
            accessibility_data = check_accessibility(url)
            st.write("♿ **Accessibility Assessment**")
            st.json(accessibility_data)

            # Crawlability
            crawlability_data = check_crawlability(soup)
            st.write("🕷️ **Crawlability Check**")
            st.json(crawlability_data)

            # Page Speed Insights
            speed_data = analyze_page_speed(url)
            st.write("⚡ **Page Speed Insights**")
            st.json(speed_data)
        else:
            st.error("Could not fetch the webpage. Please check the URL and try again.")
    else:
        st.error("Invalid URL. Please enter a valid one.")

