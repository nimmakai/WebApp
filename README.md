# WebApp
Based on my previous work of survey on TanvirSdqBot. 

## 🌍 Wikimedia Cross-Event Retention Dashboard

A Streamlit-based web application designed to analyze and visualize user retention across various Wikimedia photographic campaigns (e.g., Wiki Loves Monuments, Wiki Loves Earth, Wiki Loves Folklore). 

By leveraging the Wikimedia Toolforge API, this dashboard rapidly fetches participant data and calculates how many contributors return to participate in subsequent events, displaying the insights through interactive heatmaps, global maps, and data tables.

---

## ✨ Features

* **⚡ Lightning-Fast Data Fetching:** Uses Wikimedia Toolforge (`ptools.toolforge.org`) and concurrent multithreading to query tens of thousands of category uploaders in seconds.
* **🧭 Guided Code Builder:** A user-friendly sidebar interface to easily generate event codes by selecting campaigns, countries, and year ranges.
* **🌡️ Interactive Heatmaps:** Visualizes retention percentages between overlapping events within specific countries using Seaborn and Matplotlib.
* **🗺️ Global Worldmap:** A Plotly-powered interactive choropleth map to compare average or median retention rates on a global scale.
* **📋 Data Tables & Export:** View raw retention metrics (Average, Median, Max, Standard Deviation) and download the results as a CSV file for offline analysis.
* **🌙 Custom Dark UI:** A beautifully customized, Wikipedia-inspired dark theme with responsive metric cards and segmented controls.

---

## 🚀 Installation & Setup

### 1. Prerequisites
Ensure you have **Python 3.8+** installed on your system.

### 2. Clone the Repository
```bash
git clone [https://github.com/your-username/wikimedia-retention-dashboard.git](https://github.com/your-username/wikimedia-retention-dashboard.git)
cd wikimedia-retention-dashboard
