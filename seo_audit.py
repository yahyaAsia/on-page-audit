import streamlit as st
import requests
from bs4 import BeautifulSoup
import validators
import urllib.parse
import json
from googleapiclient.discovery import build
import io
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

# API Key for Google PageSpeed Insights (Replace with your actual API key)
GOOGLE_API_KEY = "AIzaSyBw_Q3wQxHcC4IGI2Gb84Ux73ghPGQPQWc"

# Function to fetch page content
def get_page_content(url):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException:
        return None

# Function to analyze metadata
def analyze_metadata(soup):
    title = soup.title.string if soup.title else "❌ No Title Found"
    meta_desc = soup.find("meta", attrs={"name": "description"})
    meta_desc = meta_desc["content"] if meta_desc else "❌ No Meta Description Found"
    return {"Title": title, "Meta Description": meta_desc}

# Function to check internal links
def check_internal_links(soup, base_url):
    internal_links, broken_links = [], []
    for link in soup.find_all("a", href=True):
        full_url = urllib.parse.urljoin(base_url, link["href"])
        if base_url in full_url:
            try:
                response = requests.head(full_url, timeout=5)
                if response.status_code >= 400:
                    broken_links.append(full_url)
                else:
                    internal_links.append(full_url)
            except:
                broken_links.append(full_url)
    return internal_links, broken_links

# Function to analyze H1 tags
def analyze_h1_tags(soup):
    h1_tags = [h1.get_text(strip=True) for h1 in soup.find_all("h1")]
    return h1_tags

# Function to get Google PageSpeed Insights (with error handling)
def get_pagespeed_insights(url, strategy="mobile"):
    """
    Fetches PageSpeed Insights for a given URL.
    
    Args:
        url (str): The website URL to analyze.
        strategy (str): "mobile" or "desktop" for the analysis.

    Returns:
        dict: PageSpeed scores and Core Web Vitals.
    """
    try:
        if not GOOGLE_API_KEY or GOOGLE_API_KEY == "YOUR_GOOGLE_API_KEY":
            return {
                "Performance Score": "⚠️ API Key Missing",
                "Core Web Vitals": {},
                "Error": "No valid API Key found. Please set GOOGLE_API_KEY correctly.",
                "Strategy": strategy.capitalize(),
            }

        # Initialize the API service
        service = build("pagespeedonline", "v5", developerKey=GOOGLE_API_KEY)
        result = service.pagespeedapi().runpagespeed(url, strategy=strategy).execute()

        # Extract relevant data
        lighthouse_data = result.get("lighthouseResult", {})
        categories = lighthouse_data.get("categories", {})
        audits = lighthouse_data.get("audits", {})

        # Performance score (scaled to 100)
        performance_score = categories.get("performance", {}).get("score")
        performance_score = performance_score * 100 if performance_score is not None else "⚠️ Not Available"

        # Extract Core Web Vitals
        core_web_vitals = {
            "First Contentful Paint (FCP)": audits.get("first-contentful-paint", {}).get("displayValue", "N/A"),
            "Largest Contentful Paint (LCP)": audits.get("largest-contentful-paint", {}).get("displayValue", "N/A"),
            "Cumulative Layout Shift (CLS)": audits.get("cumulative-layout-shift", {}).get("displayValue", "N/A"),
            "Total Blocking Time (TBT)": audits.get("total-blocking-time", {}).get("displayValue", "N/A"),
            "Speed Index": audits.get("speed-index", {}).get("displayValue", "N/A"),
        }

        return {
            "Performance Score": performance_score,
            "Core Web Vitals": core_web_vitals,
            "Strategy": strategy.capitalize(),
        }

    except Exception as e:
        return {
            "Performance Score": "⚠️ Not Available",
            "Core Web Vitals": {},
            "Error": str(e),
            "Strategy": strategy.capitalize(),
        }

# Function to generate a PDF report
def generate_pdf_report(url, metadata, links, h1_tags, speed_score):
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    pdf.setTitle("SEO Audit Report")

    # Title
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(100, 750, "SEO Audit Report")

    # Website URL
    pdf.setFont("Helvetica", 12)
    pdf.drawString(100, 730, f"Website: {url}")

    # Metadata
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(100, 700, "🏷️ Metadata Analysis")
    pdf.setFont("Helvetica", 12)
    pdf.drawString(100, 680, f"Title: {metadata['Title']}")
    pdf.drawString(100, 660, f"Meta Description: {metadata['Meta Description']}")

    # Internal Links
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(100, 630, "🔗 Internal Link Verification")
    pdf.setFont("Helvetica", 12)
    pdf.drawString(100, 610, f"Total Internal Links: {len(links[0])}")
    pdf.drawString(100, 590, f"Broken Links: {len(links[1])}")

    # H1 Tags
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(100, 560, "🔖 H1 Tag Analysis")
    pdf.setFont("Helvetica", 12)
    pdf.drawString(100, 540, f"H1 Count: {len(h1_tags)}")

    # PageSpeed Score
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(100, 510, "⚡ PageSpeed Insights")

    # Ensure the score exists before drawing it
    score = speed_score.get("Performance Score", "⚠️ Not Available")
    pdf.setFont("Helvetica", 12)
    pdf.drawString(100, 490, f"Mobile Performance Score: {score} / 100")

    pdf.save()
    buffer.seek(0)
    return buffer

# Streamlit UI
st.set_page_config(page_title="Advanced SEO Audit Tool", layout="wide")

st.title("🕵️ Advanced SEO Audit Tool")
st.markdown("Analyze your **SEO performance, speed, and technical issues**. Compare two pages and export reports.")

url1 = st.text_input("🔗 Enter First Website URL", "")
url2 = st.text_input("🆚 Enter Competitor Website URL (Optional)", "")

if st.button("🔍 Analyze"):
    if validators.url(url1):
        st.info("Fetching data... Please wait.")
        page_content1 = get_page_content(url1)

        if page_content1:
            soup1 = BeautifulSoup(page_content1, "html.parser")

            # Metadata Analysis
            metadata1 = analyze_metadata(soup1)
            st.header("🏷️ **Metadata Analysis**")
            st.write(metadata1)

            # Internal Links Analysis
            links1 = check_internal_links(soup1, url1)
            st.header("🔗 **Internal Link Verification**")
            st.write(f"Total Internal Links: {len(links1[0])}")
            st.write(f"Broken Links: {len(links1[1])}")

            # H1 Tags Analysis
            h1_tags1 = analyze_h1_tags(soup1)
            st.header("🔖 **H1 Tag Analysis**")
            st.write(f"Total H1 Tags: {len(h1_tags1)}", h1_tags1)

            # PageSpeed Insights
            speed_score1 = get_pagespeed_insights(url1)
            st.header("⚡ **Google PageSpeed Score**")
            st.write(speed_score1)

            # Generate and Download Report
            pdf_buffer = generate_pdf_report(url1, metadata1, links1, h1_tags1, speed_score1)
            st.download_button(
                label="📄 Download PDF Report",
                data=pdf_buffer,
                file_name="SEO_Audit_Report.pdf",
                mime="application/pdf",
            )

        else:
            st.error("❌ Could not fetch the webpage.")
    else:
        st.error("❌ Invalid URL. Please enter a valid one.")
