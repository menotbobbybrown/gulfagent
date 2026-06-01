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
    }
]

async def seed_skills(db: AsyncSession):
    """Inserts seed skills if they don't exist (idempotent)."""
    for skill_data in SEED_SKILLS:
        # Check if exists
        result = await db.execute(select(Skill).where(Skill.slug == skill_data["slug"]))
        if result.scalar_one_or_none():
            continue
            
        skill = Skill(**skill_data)
        db.add(skill)
    
    await db.commit()
