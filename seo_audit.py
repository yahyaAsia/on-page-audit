import streamlit as st
import requests
from bs4 import BeautifulSoup
import validators
import urllib.parse
import json
from googleapiclient.discovery import build
import io
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
import os
import aiohttp
import asyncio
from collections import Counter
import re
from functools import lru_cache
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load Google API Key from Streamlit secrets
GOOGLE_API_KEY = os.getenv("AIzaSyCL6J5KkQbBw_jiQrhbtZ_Mv2qY3_rcMpc")

# Function to fetch page content
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

# Function to analyze headlines
def analyze_headlines(soup):
    headlines = {
        "H1": [h.get_text(strip=True) for h in soup.find_all("h1")],
        "H2": [h.get_text(strip=True) for h in soup.find_all("h2")],
        "H3": [h.get_text(strip=True) for h in soup.find_all("h3")]
    }
    return headlines

# Asynchronous function to check a single link
async def check_link(session, url):
    try:
        async with session.head(url, timeout=5) as response:
            return url, response.status < 400
    except Exception as e:
        logger.error(f"Error checking link {url}: {e}")
        return url, False

# Function to analyze internal and external links
async def analyze_links(soup, base_url):
    links = soup.find_all("a", href=True)
    internal_links = []
    external_links = []
    broken_links = []

    async with aiohttp.ClientSession() as session:
        tasks = []
        for link in links[:50]:  # Limit to 50 links
            href = link["href"]
            full_url = urllib.parse.urljoin(base_url, href)
            if base_url in full_url:
                internal_links.append(full_url)
                tasks.append(check_link(session, full_url))
            else:
                external_links.append(full_url)
                tasks.append(check_link(session, full_url))

        results = await asyncio.gather(*tasks)
        broken_links = [url for url, is_valid in results if not is_valid]

    return internal_links, external_links, broken_links

# Function to get word count
def get_word_count(soup):
    text = soup.get_text(strip=True)
    words = re.findall(r'\b\w+\b', text.lower())
    return len(words)

# Function to extract main keywords (basic frequency analysis)
def extract_keywords(soup, top_n=5):
    text = soup.get_text(strip=True)
    words = re.findall(r'\b\w+\b', text.lower())
    # Exclude common stop words
    stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
    keywords = [word for word in words if word not in stop_words and len(word) > 3]
    keyword_counts = Counter(keywords)
    return dict(keyword_counts.most_common(top_n))

# Function to analyze images and alt texts
def analyze_images(soup):
    images = soup.find_all("img")
    image_data = []
    for img in images:
        src = img.get("src", "❌ No Src")
        alt = img.get("alt", "❌ No Alt Text")
        image_data.append({"src": src, "alt": alt})
    return image_data

# Function to check additional SEO metrics
def additional_seo_metrics(soup):
    metrics = {}
    # Canonical Tag
    canonical = soup.find("link", rel="canonical")
    metrics["Canonical Tag"] = canonical["href"] if canonical and canonical.get("href") else "❌ No Canonical Tag"
    # Robots Meta Tag
    robots = soup.find("meta", attrs={"name": "robots"})
    metrics["Robots Meta"] = robots["content"] if robots and robots.get("content") else "❌ No Robots Meta"
    # Structured Data (Schema.org)
    scripts = soup.find_all("script", type="application/ld+json")
    metrics["Structured Data"] = "✅ Present" if scripts else "❌ Not Found"
    return metrics

# Function to get Google PageSpeed Insights
@lru_cache(maxsize=100)
def get_pagespeed_insights(url, strategy="mobile"):
    try:
        if not GOOGLE_API_KEY:
            return {
                "Performance Score": "⚠️ API Key Missing",
                "Core Web Vitals": {},
                "Mobile Friendliness": "N/A",
                "Error": "No valid API Key found. Set GOOGLE_API_KEY in Streamlit secrets.",
                "Strategy": strategy.capitalize(),
            }

        logger.info(f"Fetching PageSpeed Insights for {url} ({strategy})")
        service = build("pagespeedonline", "v5", developerKey=AIzaSyCL6J5KkQbBw_jiQrhbtZ_Mv2qY3_rcMpc)
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

        mobile_friendly = audits.get("is-crawlable", {}).get("score", 0) == 1
        mobile_friendly = "✅ Mobile-Friendly" if mobile_friendly else "❌ Not Mobile-Friendly"

        return {
            "Performance Score": performance_score,
            "Core Web Vitals": core_web_vitals,
            "Mobile Friendliness": mobile_friendly,
            "Strategy": strategy.capitalize(),
        }

    except Exception as e:
        logger.error(f"PageSpeed API error for {url}: {e}")
        return {
            "Performance Score": "⚠️ Not Available",
            "Core Web Vitals": {},
            "Mobile Friendliness": "N/A",
            "Error": str(e),
            "Strategy": strategy.capitalize(),
        }

# Function to generate a PDF report
def generate_pdf_report(url, analysis):
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
    story.append(Paragraph(", Metadata Analysis", styles["Heading2"]))
    story.append(Paragraph(f"Title: {analysis['metadata']['Title']}", styles["Normal"]))
    story.append(Paragraph(f"Meta Description: {analysis['metadata']['Meta Description']}", styles["Normal"]))
    story.append(Spacer(1, 12))

    # Headlines
    story.append(Paragraph("📜 Headlines", styles["Heading2"]))
    for tag, headlines in analysis["headlines"].items():
        story.append(Paragraph(f"{tag} Count: {len(headlines)}", styles["Normal"]))
        for i, h in enumerate(headlines[:5], 1):  # Limit to 5 headlines
            story.append(Paragraph(f"{tag} #{i}: {h}", styles["Normal"]))
    story.append(Spacer(1, 12))

    # Links
    story.append(Paragraph("🔗 Links", styles["Heading2"]))
    story.append(Paragraph(f"Internal Links: {len(analysis['internal_links'])}", styles["Normal"]))
    story.append(Paragraph(f"External Links: {len(analysis['external_links'])}", styles["Normal"]))
    story.append(Paragraph(f"Broken Links: {len(analysis['broken_links'])}", styles["Normal"]))
    story.append(Spacer(1, 12))

    # Word Count
    story.append(Paragraph("📝 Word Count", styles["Heading2"]))
    story.append(Paragraph(f"Total Words: {analysis['word_count']}", styles["Normal"]))
    story.append(Spacer(1, 12))

    # Keywords
    story.append(Paragraph("🔑 Main Keywords", styles["Heading2"]))
    for keyword, count in analysis["keywords"].items():
        story.append(Paragraph(f"{keyword}: {count}", styles["Normal"]))
    story.append(Spacer(1, 12))

    # Images
    story.append(Paragraph("🖼️ Images", styles["Heading2"]))
    story.append(Paragraph(f"Total Images: {len(analysis['images'])}", styles["Normal"]))
    for i, img in enumerate(analysis["images"][:5], 1):  # Limit to 5 images
        story.append(Paragraph(f"Image #{i} Src: {img['src']}", styles["Normal"]))
        story.append(Paragraph(f"Image #{i} Alt: {img['alt']}", styles["Normal"]))
    story.append(Spacer(1, 12))

    # Additional SEO Metrics
    story.append(Paragraph("⚙️ Additional SEO Metrics", styles["Heading2"]))
    for metric, value in analysis["additional_metrics"].items():
        story.append(Paragraph(f"{metric}: {value}", styles["Normal"]))
    story.append(Spacer(1, 12))

    # PageSpeed
    story.append(Paragraph("⚡ PageSpeed Insights", styles["Heading2"]))
    score = analysis["pagespeed"].get("Performance Score", "⚠️ Not Available")
    story.append(Paragraph(f"Mobile Performance Score: {score} / 100", styles["Normal"]))
    story.append(Paragraph(f"Mobile Friendliness: {analysis['pagespeed']['Mobile Friendliness']}", styles["Normal"]))
    for metric, value in analysis["pagespeed"].get("Core Web Vitals", {}).items():
        story.append(Paragraph(f"{metric}: {value}", styles["Normal"]))

    doc.build(story)
    buffer.seek(0)
    return buffer

# Streamlit UI
st.set_page_config(page_title="Expert SEO Audit Tool", layout="wide")
st.title("🕵️‍♂️ Expert SEO Audit Tool")
st.markdown("Analyze **SEO performance** for your website and a competitor. Get detailed metrics and export reports.")

url1 = st.text_input("🔗 Enter Your Website URL", "")
url2 = st.text_input("🆚 Enter Competitor Website URL (Optional)", "")

if st.button("🔍 Analyze"):
    if not (validators.url(url1) and (not url2 or validators.url(url2))):
        st.error("❌ Please enter valid URLs.")
        st.stop()

    st.info("Fetching data... Please wait.")
    progress_bar = st.progress(0)
    col1, col2 = st.columns(2) if url2 else (st, None)

    async def analyze_website(url, column, report_name):
        with column:
            st.subheader(f"Website: {url}")
            page_content = get_page_content(url)
            progress_bar.progress(25)
            if page_content:
                soup = BeautifulSoup(page_content, "html.parser")
                
                # Collect all SEO metrics
                analysis = {
                    "metadata": analyze_metadata(soup),
                    "headlines": analyze_headlines(soup),
                    "internal_links": [],
                    "external_links": [],
                    "broken_links": [],
                    "word_count": get_word_count(soup),
                    "keywords": extract_keywords(soup),
                    "images": analyze_images(soup),
                    "additional_metrics": additional_seo_metrics(soup),
                    "pagespeed": get_pagespeed_insights(url)
                }
                
                # Analyze links
                analysis["internal_links"], analysis["external_links"], analysis["broken_links"] = await analyze_links(soup, url)
                progress_bar.progress(75)

                # Display results
                st.write("**Metadata**", analysis["metadata"])
                st.write("**Headlines**", {k: v[:5] for k, v in analysis["headlines"].items()})  # Limit to 5 per tag
                st.write("**Links**", {
                    "Internal": len(analysis["internal_links"]),
                    "External": len(analysis["external_links"]),
                    "Broken": len(analysis["broken_links"])
                })
                st.write("**Word Count**", analysis["word_count"])
                st.write("**Main Keywords**", analysis["keywords"])
                st.write("**Images**", analysis["images"][:5])  # Limit to 5 images
                st.write("**Additional SEO Metrics**", analysis["additional_metrics"])
                st.write("**PageSpeed Insights**", analysis["pagespeed"])

                # Generate and download PDF
                pdf_buffer = generate_pdf_report(url, analysis)
                st.download_button(
                    label="📄 Download Report",
                    data=pdf_buffer,
                    file_name=f"SEO_Audit_Report_{report_name}.pdf",
                    mime="application/pdf",
                )
            else:
                st.error("❌ Could not fetch the webpage.")
            progress_bar.progress(100)

    # Analyze primary website
    asyncio.run(analyze_website(url1, col1, "Primary"))

    # Analyze competitor website
    if url2 and col2:
        progress_bar = st.progress(0)
        asyncio.run(analyze_website(url2, col2, "Competitor"))
