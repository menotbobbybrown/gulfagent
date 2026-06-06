"""
Seed skills for GulfAgent — Phase 3 (T53-T62).
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from db.models import Skill

SEED_SKILLS = [
    {
        "name": "Daily Gulf News Briefing",
        "slug": "daily-gulf-news",
        "description": "Daily summary of top business and political news across the GCC (UAE, Saudi, Qatar).",
        "category": "Research",
        "prompt_template": "Analyze top news from Gulf News, Khaleej Times, and Al Arabiya for today. Summarize the top 5 stories relevant to GCC business founders. Focus on UAE and Saudi Arabia.",
        "icon": "newspaper",
        "default_cron": "0 8 * * 1-5",
        "credit_cost": 50,
    },
    {
        "name": "Price Monitor",
        "slug": "price-monitor",
        "description": "Monitor prices for a specific product on Noon or Amazon.ae and alert on drops.",
        "category": "E-commerce",
        "prompt_template": "Check the price of the item at this URL: {{url}}. If the price is below {{target_price}} AED, notify me. Otherwise, just record the current price.",
        "icon": "trending-down",
        "default_cron": "0 */6 * * *",
        "credit_cost": 30,
    },
    {
        "name": "Lead Researcher",
        "slug": "lead-researcher",
        "description": "Find contact info for companies in a specific sector in the Gulf.",
        "category": "Research",
        "prompt_template": "Search for companies in the {{sector}} sector based in {{city}}. Find their website, LinkedIn page, and a general contact email if possible.",
        "icon": "search",
        "default_cron": "0 10 * * 1",
        "credit_cost": 100,
    },
    {
        "name": "Gmail to Linear",
        "slug": "gmail-to-linear",
        "description": "Sync specific customer feedback emails to Linear issues.",
        "category": "HR",
        "prompt_template": "Check my Gmail for new messages with the subject 'Feedback'. For each one, summarize the issue and create a new task in Linear under the 'Customer Support' project.",
        "icon": "mail",
        "default_cron": "0 */12 * * *",
        "credit_cost": 40,
    },
    {
        "name": "Weekly Competitor Intel",
        "slug": "competitor-intel",
        "description": "Weekly report on competitor social media activity and new product launches.",
        "category": "Research",
        "prompt_template": "Visit the websites and LinkedIn pages of these competitors: {{competitors}}. Summarize any new product announcements or major updates from the past week.",
        "icon": "eye",
        "default_cron": "0 9 * * 1",
        "credit_cost": 150,
    },
    {
        "name": "DubaiNow Reminder",
        "slug": "dubainow-reminder",
        "description": "Check for upcoming bill payments or license renewals on DubaiNow.",
        "category": "Government",
        "prompt_template": "Log in to my DubaiNow account (if credentials provided) or search for any public renewal notices for my company {{company_name}}. Alert me of anything due within 7 days.",
        "icon": "bell",
        "default_cron": "0 8 * * 1",
        "credit_cost": 60,
    },
    {
        "name": "LinkedIn Outreach",
        "slug": "linkedin-outreach",
        "description": "Automate personalized connection requests to potential partners.",
        "category": "HR",
        "prompt_template": "Search LinkedIn for people with the title {{title}} at {{company_type}} in {{location}}. Send a personalized connection request mentioning {{context}}.",
        "icon": "users",
        "default_cron": None, # on-demand
        "credit_cost": 200,
    },
    {
        "name": "Mag 7 Stock Brief",
        "slug": "mag7-stock-brief",
        "description": "Daily briefing on Magnificent 7 tech stocks before the market opens.",
        "category": "Finance",
        "prompt_template": "Provide a quick update on the 'Magnificent 7' tech stocks (AAPL, MSFT, GOOGL, AMZN, NVDA, META, TSLA). Include current price, 24h change, and any major overnight news.",
        "icon": "bar-chart",
        "default_cron": "0 7 * * 1-5",
        "credit_cost": 40,
    },
    {
        "name": "Tender Monitor",
        "slug": "tender-monitor",
        "description": "Monitor government tender portals for new relevant opportunities.",
        "category": "Government",
        "prompt_template": "Check the UAE Etisalat and DEWA tender portals for new tenders related to {{keywords}}. Summarize any new listings found.",
        "icon": "file-text",
        "default_cron": "0 */4 * * *",
        "credit_cost": 120,
    },
    {
        "name": "WhatsApp Report",
        "slug": "whatsapp-report",
        "description": "Weekly summary of business performance delivered via WhatsApp.",
        "category": "Finance",
        "prompt_template": "Aggregate the key performance metrics from my dashboard for the past week. Format them into a concise WhatsApp message and send it to me.",
        "icon": "message-square",
        "default_cron": "0 18 * * 5",
        "credit_cost": 50,
    },
    {
        "name": "Data Analyst",
        "slug": "data-analyst",
        "description": "Upload a CSV file via WhatsApp and get automated analysis with charts.",
        "category": "Research",
        "prompt_template": "Analyze the uploaded data file. Describe all columns, key statistics, trends, and create a visualization chart. Save the chart as 'chart.png'.",
        "icon": "bar-chart-2",
        "default_cron": None,
        "credit_cost": 100,
    },
    {
        "name": "Excel Automator",
        "slug": "excel-automator",
        "description": "Describe what you want in Excel and get a processed .xlsx file back.",
        "category": "HR",
        "prompt_template": "Write Python code using openpyxl and pandas to create/modify an Excel file based on this request: {{request}}. Save the output as 'output.xlsx'.",
        "icon": "file-spreadsheet",
        "default_cron": None,
        "credit_cost": 80,
    },
    {
        "name": "PDF Summarizer",
        "slug": "pdf-summarizer",
        "description": "Send any PDF via WhatsApp and receive a structured summary back.",
        "category": "Research",
        "prompt_template": "Extract text from the uploaded PDF file. Summarize it into: key points, actionable items, and a brief TL;DR. Use PyMuPDF (fitz) for extraction.",
        "icon": "file-text",
        "default_cron": None,
        "credit_cost": 60,
    },
    {
        "name": "Custom Script Runner",
        "slug": "custom-script-runner",
        "description": "Describe an automation in plain English and the agent will write and execute it.",
        "category": "Finance",
        "prompt_template": "Write and execute Python script for: {{request}}. Handle errors gracefully. Print all output. Save any files to current directory.",
        "icon": "terminal",
        "default_cron": None,
        "credit_cost": 150,
    },
    {
        "name": "Market Data Puller",
        "slug": "market-data-puller",
        "description": "Get financial data, news, and price charts for any company.",
        "category": "Finance",
        "prompt_template": "Research company {{company_name}}. Search for: 1) Current stock price and financials 2) Recent news and sentiment 3) Competitor comparison. Create a price chart using yfinance and save as 'chart.png'.",
        "icon": "trending-up",
        "default_cron": None,
        "credit_cost": 120,
    },
]

async def seed_skills(db: AsyncSession):
    """Inserts seed skills if they don't exist (idempotent)."""
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    for skill_data in SEED_SKILLS:
        stmt = pg_insert(Skill).values(**skill_data).on_conflict_do_nothing(index_elements=['slug'])
        await db.execute(stmt)
    await db.commit()
