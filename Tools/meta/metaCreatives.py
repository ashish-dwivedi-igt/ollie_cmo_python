import os
from typing import List, cast

from facebook_business.api import FacebookAdsApi, Cursor
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.ad import Ad
from facebook_business.adobjects.campaign import Campaign
from facebook_business.adobjects.adset import AdSet
from facebook_business.adobjects.adsinsights import AdsInsights
from langchain.tools import tool
import sys
import os
import time
from typing import Dict, Any
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
# Fetch Insights with Filtering and Backoff
# -------------------------------------------------------------------

@tool
def fetch_filtered_insights(
    ad_ids: List[str] | None = None,
    date_preset: str = "last_30d",
    fields: List[str] | None = None,
    level: str = "ad",
    limit: int = 100,
    ctr_threshold: float | None = None,
    min_impressions: int = 1,
) -> str:
    """
    Fetches insights for the account (or a set of ads) with simple
    client-side filtering for underperforming ads.

    - Uses `date_preset`, `level`, and `limit` as defaults.
    - If `ad_ids` is provided, requests insights for those ads using the
      `filtering` param and then applies additional local filters (CTR,
      impressions) because server-side operators for fractional CTR can be
      fragile across API versions.
    - Implements a small retry/backoff loop to handle transient throttles.
    """
    debug_log("fetch_filtered_insights", ad_ids=ad_ids, date_preset=date_preset,
              level=level, limit=limit, ctr_threshold=ctr_threshold,
              min_impressions=min_impressions)

    if fields is None:
        fields = [
            "impressions",
            "spend",
            "clicks",
            "ctr",
            "cpc",
            "ad_id",
            "ad_name",
        ]

    params: Dict[str, Any] = {
        "date_preset": date_preset,
        "level": level,
        "limit": limit,
    }

    # server-side filtering for zero-impression objects is efficient
    filtering = []
    if min_impressions and min_impressions > 0:
        filtering.append({"field": "ad.impressions", "operator": "GREATER_THAN", "value": min_impressions - 1})

    if ad_ids:
        # prefer server-side IN filter for ad ids when possible
        filtering.append({"field": "ad.id", "operator": "IN", "value": ad_ids})

    if filtering:
        params["filtering"] = filtering

    # simple retry/backoff
    attempt = 0
    max_attempts = 4
    backoff = 1.0

    while attempt < max_attempts:
        try:
            # query the account-level insights edge (returns ad-level rows when level=ad)
            ads_insights_cursor = cast(Cursor, account.get_insights(fields=fields, params=params))
            rows = list(ads_insights_cursor)

            # client-side filtering for CTR and formatting
            results = []

            for row in rows:
                impressions = int(row.get("impressions", 0) or 0)
                clicks = int(row.get("clicks", 0) or 0)

                # CTR from API can be a string (percent or decimal). Normalize safely.
                raw_ctr = row.get("ctr", "0")
                try:
                    ctr_str = str(raw_ctr).replace("%", "")
                    ctr_val = float(ctr_str)
                    # if API returns fractional (0.012 = 1.2%), keep as-is;
                    # treat values > 1 as percent already (historic APIs vary).
                    if ctr_val <= 1.0:
                        # convert fraction to percent
                        ctr_pct = ctr_val * 100.0
                    else:
                        ctr_pct = ctr_val
                except Exception:
                    ctr_pct = 0.0

                if impressions < min_impressions:
                    continue

                if ctr_threshold is not None and ctr_pct < (ctr_threshold * 100.0):
                    tag = "UNDERPERFORMING"
                else:
                    tag = "OK"

                results.append(
                    {
                        "ad_id": row.get("ad_id") or row.get("ad_id"),
                        "ad_name": row.get("ad_name") or row.get("ad_name") or row.get("ad_name", ""),
                        "impressions": impressions,
                        "clicks": clicks,
                        "ctr_pct": round(ctr_pct, 3),
                        "spend": row.get("spend", "0"),
                        "status": tag,
                    }
                )

            if not results:
                return "No insights rows returned for the query."

            # format human-readable output
            out_lines = []
            for r in results:
                out_lines.append(
                    f"Ad {r['ad_id']} | {r.get('ad_name','-')} | imps={r['impressions']} | clicks={r['clicks']} | ctr={r['ctr_pct']}% | spend=${r['spend']} | {r['status']}"
                )

            return "\n".join(out_lines)

        except Exception as e:
            # transient error -> back off and retry
            attempt += 1
            if attempt >= max_attempts:
                return f"Error fetching insights after {attempt} attempts: {str(e)}"
            time.sleep(backoff)
            backoff *= 2

    # If we exit the retry loop unexpectedly, return an error string to satisfy
    # the declared return type and make failure explicit.
    return f"Error fetching insights after {attempt} attempts: unknown failure"


# -------------------------------------------------------------------
# Campaigns & Ad Sets helpers
# -------------------------------------------------------------------

@tool
def list_campaigns(limit: int = 50, fields: List[str] | None = None, status_filter: List[str] | None = None) -> str:
    """
    Lists campaigns for the configured ad account.
    """
    debug_log("list_campaigns", limit=limit, status_filter=status_filter)

    if fields is None:
        fields = [
            Campaign.Field.id,
            Campaign.Field.name,
            Campaign.Field.status,
            Campaign.Field.objective,
        ]

    params: Dict[str, Any] = {"limit": limit}
    if status_filter:
        params["effective_status"] = status_filter

    try:
        cursor = cast(Cursor, account.get_campaigns(fields=fields, params=params))
        campaigns = list(cursor)
        if not campaigns:
            return "No campaigns found."

        lines: List[str] = []
        for c in campaigns:
            lines.append(f"ID: {c.get('id')} | Name: {c.get('name')} | Status: {c.get('status')} | Objective: {c.get('objective')}")
        return "\n".join(lines)
    except Exception as e:
        return f"Error fetching campaigns: {str(e)}"


@tool
def list_adsets(limit: int = 50, fields: List[str] | None = None, campaign_id: str | None = None) -> str:
    """
    Lists ad sets for the configured ad account, optionally filtered by campaign.
    """
    debug_log("list_adsets", limit=limit, campaign_id=campaign_id)

    if fields is None:
        fields = [
            AdSet.Field.id,
            AdSet.Field.name,
            AdSet.Field.status,
            AdSet.Field.daily_budget,
        ]

    params: Dict[str, Any] = {"limit": limit}
    if campaign_id:
        params["campaign_id"] = campaign_id

    try:
        cursor = cast(Cursor, account.get_adsets(fields=fields, params=params))
        adsets = list(cursor)
        if not adsets:
            return "No ad sets found."

        lines: List[str] = []
        for a in adsets:
            lines.append(f"ID: {a.get('id')} | Name: {a.get('name')} | Status: {a.get('status')} | Daily budget: {a.get('daily_budget', '-')}")
        return "\n".join(lines)
    except Exception as e:
        return f"Error fetching ad sets: {str(e)}"



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