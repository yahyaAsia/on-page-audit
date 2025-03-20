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

# API Key for Google PageSpeed Insights
GOOGLE_API_KEY = "YOUR_GOOGLE_API_KEY"  # Replace with your actual API Key

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

# Function to get Google PageSpeed Insights
def get_pagespeed_insights(url):
    try:
        service = build("pagespeedonline", "v5", developerKey=GOOGLE_API_KEY)
        result = service.pagespeedapi().runpagespeed(url, strategy="mobile").execute()
        score = result["lighthouseResult"]["categories"]["performance"]["score"] * 100
        return {"Performance Score": score}
    except:
        return {"Error": "Failed to fetch PageSpeed data"}

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
    pdf.setFont("Helvetica", 12)
    pdf.drawString(100, 490, f"Mobile Performance Score: {speed_score['Performance Score']} / 100")

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

            # Compare Competitor Website
            if url2 and validators.url(url2):
                st.markdown("---")
                st.header("🆚 Competitor Analysis")

                page_content2 = get_page_content(url2)
                if page_content2:
                    soup2 = BeautifulSoup(page_content2, "html.parser")

                    metadata2 = analyze_metadata(soup2)
                    links2 = check_internal_links(soup2, url2)
                    h1_tags2 = analyze_h1_tags(soup2)
                    speed_score2 = get_pagespeed_insights(url2)

                    col1, col2 = st.columns(2)

                    with col1:
                        st.subheader("Your Page")
                        st.write(metadata1)
                        st.write(f"Total Internal Links: {len(links1[0])}")
                        st.write(f"Broken Links: {len(links1[1])}")
                        st.write(f"H1 Tags: {len(h1_tags1)}", h1_tags1)
                        st.write(f"PageSpeed Score: {speed_score1}")

                    with col2:
                        st.subheader("Competitor Page")
                        st.write(metadata2)
                        st.write(f"Total Internal Links: {len(links2[0])}")
                        st.write(f"Broken Links: {len(links2[1])}")
                        st.write(f"H1 Tags: {len(h1_tags2)}", h1_tags2)
                        st.write(f"PageSpeed Score: {speed_score2}")

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
