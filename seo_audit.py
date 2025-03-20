import streamlit as st
import requests
from bs4 import BeautifulSoup
import validators
import urllib.parse

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

    return {
        "Title": title,
        "Meta Description": meta_desc,
        "Title Length": len(title),
        "Meta Description Length": len(meta_desc)
    }

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
    return h1_tags, "⚠️ Use only one main H1 tag for SEO!" if len(h1_tags) > 1 else "✅ Good!"

# Function to analyze images
def analyze_images(soup, base_url):
    images, missing_alt, broken_images = soup.find_all("img"), [], []
    for img in images:
        src = img.get("src")
        full_src = urllib.parse.urljoin(base_url, src)
        if not img.get("alt", "").strip():
            missing_alt.append(full_src)
        try:
            response = requests.head(full_src, timeout=5)
            if response.status_code >= 400:
                broken_images.append(full_src)
        except:
            broken_images.append(full_src)

    return len(images), missing_alt, broken_images

# Streamlit UI
st.set_page_config(page_title="SEO Audit Tool", layout="wide")

st.title("🕵️ One Page SEO Audit Tool")
st.markdown("**Enter a URL to analyze its SEO performance.**")

url = st.text_input("🔗 Enter Website URL", "")

if st.button("🔍 Analyze"):
    if validators.url(url):
        st.info("Fetching data... Please wait.")
        page_content = get_page_content(url)

        if page_content:
            soup = BeautifulSoup(page_content, "html.parser")

            # **Metadata Analysis**
            st.header("🏷️ **Metadata Analysis**")
            meta_data = analyze_metadata(soup)
            col1, col2 = st.columns(2)
            col1.metric("Title", meta_data["Title"], f"{meta_data['Title Length']} chars")
            col2.metric("Meta Description", meta_data["Meta Description"], f"{meta_data['Meta Description Length']} chars")

            # **Internal Links**
            internal_links, broken_links = check_internal_links(soup, url)
            st.header("🔗 **Internal Link Verification**")
            st.metric("Total Internal Links", len(internal_links))
            st.metric("Broken Links", len(broken_links), delta_color="inverse")

            if broken_links:
                with st.expander("⚠️ View Broken Links"):
                    st.write(broken_links)

            # **H1 Tags**
            h1_tags, h1_warning = analyze_h1_tags(soup)
            st.header("🔖 **H1 Tag Analysis**")
            st.metric("Total H1 Tags", len(h1_tags), h1_warning)
            if h1_tags:
                with st.expander("🔍 View H1 Tags"):
                    st.write(h1_tags)

            # **Image Analysis**
            total_images, missing_alt, broken_images = analyze_images(soup, url)
            st.header("🖼️ **Image Analysis**")
            col3, col4, col5 = st.columns(3)
            col3.metric("Total Images", total_images)
            col4.metric("Missing Alt Text", len(missing_alt), delta_color="inverse")
            col5.metric("Broken Images", len(broken_images), delta_color="inverse")

            if missing_alt:
                with st.expander("⚠️ View Images Without Alt Text"):
                    st.write(missing_alt)

            if broken_images:
                with st.expander("⚠️ View Broken Images"):
                    st.write(broken_images)

            # **Final Recommendations**
            st.header("✅ **SEO Recommendations**")
            recommendations = []
            if meta_data["Title Length"] > 60:
                recommendations.append("🔹 Title is too long. Keep it under 60 characters.")
            if meta_data["Meta Description Length"] > 160:
                recommendations.append("🔹 Meta description is too long. Keep it under 160 characters.")
            if len(h1_tags) > 1:
                recommendations.append("🔹 Use only **one main H1 tag** for SEO.")
            if broken_links:
                recommendations.append(f"🔹 Fix {len(broken_links)} broken internal links.")
            if missing_alt:
                recommendations.append(f"🔹 Add alt text to {len(missing_alt)} images.")
            if broken_images:
                recommendations.append(f"🔹 Fix {len(broken_images)} broken images.")

            if recommendations:
                for rec in recommendations:
                    st.warning(rec)
            else:
                st.success("🎉 No major SEO issues found!")

        else:
            st.error("❌ Could not fetch the webpage. Please check the URL.")
    else:
        st.error("❌ Invalid URL. Please enter a valid one.")
