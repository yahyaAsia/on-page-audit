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
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from dotenv import load_dotenv
import os
import aiohttp
import asyncio
from functools import cache, lru_cache
import logging
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Function to fetch page content with caching
@cache
def get_page_content(url):
    try:
        logger.info(f"Fetching content for {url}")
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching {url}: {e}")
        return None

# Function to analyze metadata
def analyze_metadata(soup):
    title = soup.title.string.strip() if soup.title else "❌ No Title Found"
    meta_desc = soup.find("meta", attrs={"name": "description"})
    meta_desc = meta_desc["content"].strip() if meta_desc and meta_desc.get("content") else "❌ No Meta Description Found"
    return {"Title": title, "Meta Description": meta_desc}

# Asynchronous function to check a single link
async def check_link(session, url):
    try:
        async with session.head(url, timeout=5) as response:
            return url, response.status < 400
    except Exception as e:
        logger.error(f"Error checking link {url}: {e}")
        return url, False

# Asynchronous function to check internal links
async def check_internal_links_async(soup, base_url):
    links = [
        urllib.parse.urljoin(base_url, link["href"])
        for link in soup.find_all("a", href=True)
        if base_url in urllib.parse.urljoin(base_url, link["href"])
    ]
    async with aiohttp.ClientSession() as session:
        tasks = [check_link(session, link) for link in links[:50]]  # Limit to 50 links
        results = await asyncio.gather(*tasks)
    internal_links = [url for url, is_valid in results if is_valid]
    broken_links = [url for url, is_valid in results if not is_valid]
    return internal_links, broken_links

# Function to analyze H1 tags
def analyze_h1_tags(soup):
    h1_tags = [h1.get_text(strip=True) for h1 in soup.find_all("h1")]
    return h1_tags if h1_tags else ["❌ No H1 Tags Found"]

# Function to get Google PageSpeed Insights with caching and retry logic
@lru_cache(maxsize=100)
def get_pagespeed_insights(url, strategy="mobile"):
    try:
        if not GOOGLE_API_KEY:
            return {
                "Performance Score": "⚠️ API Key Missing",
                "Core Web Vitals": {},
                "Error": "No valid API Key found. Set GOOGLE_API_KEY in .env.",
                "Strategy": strategy.capitalize(),
            }

        logger.info(f"Fetching PageSpeed Insights for {url} ({strategy})")
        service = build("pagespeedonline", "v5", developerKey=GOOGLE_API_KEY)
        result = service.pagespeedapi().runpagespeed(url=url, strategy=strategy).execute()

        lighthouse_data = result.get("lighthouseResult", {})
        categories = lighthouse_data.get("categories", {})
        audits = lighthouse_data.get("audits", {})

        performance_score = categories.get("performance", {}).get("score")
        performance_score = round(performance_score * 100) if performance_score is not None else "⚠️ Not Available"

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
        logger.error(f"PageSpeed API error for {url}: {e}")
        return {
            "Performance Score": "⚠️ Not Available",
            "Core Web Vitals": {},
            "Error": str(e),
            "Strategy": strategy.capitalize(),
        }

# Function to generate a PDF report with dynamic content
def generate_pdf_report(url, metadata, links, h1_tags, speed_score):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    # Title
    story.append(Paragraph("SEO Audit Report", styles["Title"]))
    story.append(Spacer(1, 12))

    # Website URL
    story.append(Paragraph(f"Website: {url}", styles["Normal"]))
    story.append(Spacer(1, 12))

    # Metadata
    story.append(Paragraph("🏷️ Metadata Analysis", styles["Heading2"]))
    story.append(Paragraph(f"Title: {metadata['Title']}", styles["Normal"]))
    story.append(Paragraph(f"Meta Description: {metadata['Meta Description']}", styles["Normal"]))
    story.append(Spacer(1, 12))

    # Internal Links
    story.append(Paragraph("🔗 Internal Link Verification", styles["Heading2"]))
    story.append(Paragraph(f"Total Internal Links: {len(links[0])}", styles["Normal"]))
    story.append(Paragraph(f"Broken Links: {len(links[1])}", styles["Normal"]))
    story.append(Spacer(1, 12))

    # H1 Tags
    story.append(Paragraph("🔖 H1 Tag Analysis", styles["Heading2"]))
    story.append(Paragraph(f"H1 Count: {len(h1_tags)}", styles["Normal"]))
    for i, h1 in enumerate(h1_tags, 1):
        story.append(Paragraph(f"H1 #{i}: {h1}", styles["Normal"]))
    story.append(Spacer(1, 12))

    # PageSpeed Score
    story.append(Paragraph("⚡ PageSpeed Insights", styles["Heading2"]))
    score = speed_score.get("Performance Score", "⚠️ Not Available")
    story.append(Paragraph(f"Mobile Performance Score: {score} / 100", styles["Normal"]))
    for metric, value in speed_score.get("Core Web Vitals", {}).items():
        story.append(Paragraph(f"{metric}: {value}", styles["Normal"]))

    doc.build(story)
    buffer.seek(0)
    return buffer

# Streamlit UI
st.set_page_config(page_title="Advanced SEO Audit Tool", layout="wide")
st.title("🕵️ Advanced SEO Audit Tool")
st.markdown("Analyze your **SEO performance, speed, and technical issues**. Compare two pages and export reports.")

url1 = st.text_input("🔗 Enter First Website URL", "")
url2 = st.text_input("🆚 Enter Competitor Website URL (Optional)", "")

if st.button("🔍 Analyze"):
    if not (validators.url(url1) and (not url2 or validators.url(url2))):
        st.error("❌ Please enter valid URLs.")
        st.stop()

    st.info("Fetching data... Please wait.")
    progress_bar = st.progress(0)
    col1, col2 = st.columns(2) if url2 else (st, None)

    # Analyze first website
    with col1:
        st.subheader("Primary Website")
        page_content1 = get_page_content(url1)
        progress_bar.progress(25)
        if page_content1:
            soup1 = BeautifulSoup(page_content1, "html.parser")
            metadata1 = analyze_metadata(soup1)
            links1 = asyncio.run(check_internal_links_async(soup1, url1))
            h1_tags1 = analyze_h1_tags(soup1)
            speed_score1 = get_pagespeed_insights(url1)
            progress_bar.progress(75)
            st.write("**Metadata**", metadata1)
            st.write("**Links**", f"Internal: {len(links1[0])}, Broken: {len(links1[1])}")
            st.write("**H1 Tags**", h1_tags1)
            st.write("**PageSpeed**", speed_score1)
            pdf_buffer = generate_pdf_report(url1, metadata1, links1, h1_tags1, speed_score1)
            st.download_button(
                label="📄 Download Report",
                data=pdf_buffer,
                file_name="SEO_Audit_Report_Primary.pdf",
                mime="application/pdf",
            )
        else:
            st.error("❌ Could not fetch the webpage.")
        progress_bar.progress(100)

    # Analyze competitor website
    if url2 and col2:
        with col2:
            progress_bar = st.progress(0)
            st.subheader("Competitor Website")
            page_content2 = get_page_content(url2)
            progress_bar.progress(25)
            if page_content2:
                soup2 = BeautifulSoup(page_content2, "html.parser")
                metadata2 = analyze_metadata(soup2)
                links2 = asyncio.run(check_internal_links_async(soup2, url2))
                h1_tags2 = analyze_h1_tags(soup2)
                speed_score2 = get_pagespeed_insights(url2)
                progress_bar.progress(75)
                st.write("**Metadata**", metadata2)
                st.write("**Links**", f"Internal: {len(links2[0])}, Broken: {len(links2[1])}")
                st.write("**H1 Tags**", h1_tags2)
                st.write("**PageSpeed**", speed_score2)
                pdf_buffer = generate_pdf_report(url2, metadata2, links2, h1_tags2, speed_score2)
                st.download_button(
                    label="📄 Download Report",
                    data=pdf_buffer,
                    file_name="SEO_Audit_Report_Competitor.pdf",
                    mime="application/pdf",
                )
            else:
                st.error("❌ Could not fetch the competitor webpage.")
            progress_bar.progress(100)
