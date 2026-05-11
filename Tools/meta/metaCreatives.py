import os
from typing import List, cast

from facebook_business.api import FacebookAdsApi, Cursor
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.ad import Ad
from facebook_business.adobjects.adsinsights import AdsInsights
from langchain.tools import tool
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from logger import debug_log

# -------------------------------------------------------------------
# Meta API Initialization
# -------------------------------------------------------------------

APP_ID = os.getenv("META_APP_ID")
APP_SECRET = os.getenv("META_APP_SECRET")
ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN")
AD_ACCOUNT_ID = f"act_{os.getenv('META_AD_ACCOUNT_ID')}"

FacebookAdsApi.init(
    app_id=APP_ID,
    app_secret=APP_SECRET,
    access_token=ACCESS_TOKEN,
)

account = AdAccount(AD_ACCOUNT_ID)


# -------------------------------------------------------------------
# List Ads + Creative Data
# -------------------------------------------------------------------

@tool
def list_ads_with_creatives(limit: int = 10) -> str:
    """
    Lists ads from the Meta Ad Account including creative content.
    """
    debug_log("list_ads_with_creatives", limit=limit)

    fields = [
        Ad.Field.id,
        Ad.Field.name,
        Ad.Field.status,
        # Correct modern field
        "creative{id,name,body,title,object_story_spec}",
    ]

    params = {
        "limit": limit,
        "effective_status": ["ACTIVE", "PAUSED"],
    }

    try:
        ads_cursor = cast(
            Cursor,
            account.get_ads(fields=fields, params=params)
        )

        ads = list(ads_cursor)

        results: List[str] = []

        for ad in ads:
            creative = ad.get("creative", {})

            body = creative.get("body", "N/A")
            title = creative.get("title", "N/A")

            # Fallback extraction from object_story_spec
            if body == "N/A":
                object_story_spec = creative.get("object_story_spec", {})

                link_data = object_story_spec.get("link_data", {})
                video_data = object_story_spec.get("video_data", {})

                body = (
                    link_data.get("message")
                    or video_data.get("message")
                    or "N/A"
                )

                title = (
                    link_data.get("name")
                    or title
                )

            results.append(
                f"ID: {ad.get('id')} | "
                f"Name: {ad.get('name')} | "
                f"Status: {ad.get('status')} | "
                f"Body: {body} | "
                f"Title: {title}"
            )

        return "\n".join(results) if results else "No ads found."

    except Exception as e:
        return f"Error fetching ads: {str(e)}"


# -------------------------------------------------------------------
# Ad Performance Insights
# -------------------------------------------------------------------

@tool
def get_ad_performance_insights(
    ad_id: str,
    date_preset: str = "last_30d",
) -> str:
    """
    Fetches Meta ad performance metrics.
    """
    debug_log("get_ad_performance_insights", ad_id=ad_id, date_preset=date_preset)

    fields = [
        AdsInsights.Field.spend,
        AdsInsights.Field.impressions,
        AdsInsights.Field.clicks,
        AdsInsights.Field.ctr,
        AdsInsights.Field.actions,
    ]

    params = {
        "date_preset": date_preset,
        "level": "ad",
    }

    try:
        ad = Ad(ad_id)

        insights_cursor = cast(
            Cursor,
            ad.get_insights(
                fields=fields,
                params=params,
            )
        )

        insights = list(insights_cursor)

        if not insights:
            return (
                f"No performance data found for "
                f"Ad ID {ad_id} in period: {date_preset}."
            )

        data = insights[0]

        return (
            f"Ad ID: {ad_id} | "
            f"Spend: ${data.get('spend', '0')} | "
            f"CTR: {data.get('ctr', '0')}% | "
            f"Clicks: {data.get('clicks', '0')} | "
            f"Impressions: {data.get('impressions', '0')}"
        )

    except Exception as e:
        return f"Error fetching insights: {str(e)}"


# -------------------------------------------------------------------
# Meta Ad Library Search
# -------------------------------------------------------------------

@tool
def search_ad_library(
    search_terms: str,
    country: str = "US",
) -> str:
    """
    Searches Meta Ad Library.
    Requires ads_read permission and Ad Library API approval.
    """
    debug_log("search_ad_library", search_terms=search_terms, country=country)

    return (
        f"Searching Meta Ad Library for "
        f"'{search_terms}' in {country}..."
    )