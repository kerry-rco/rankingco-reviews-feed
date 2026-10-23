#!/usr/bin/env python3
"""Pull Google reviews daily and write reviews.json (feed v1). Stdlib only.

Primary: Google Business Profile API  GET https://mybusiness.googleapis.com/v4/{parent}/reviews
  parent = accounts/{accountId}/locations/{locationId}; returns ALL reviews (paged, 50/page) + averageRating/totalReviewCount.
  Auth: OAuth 2.0, scope https://www.googleapis.com/auth/business.manage, by a Google account that is owner/manager
  of the profile. GBP API access must be requested & approved for the Cloud project. Store a refresh token once,
  then set env GBP_CLIENT_ID, GBP_CLIENT_SECRET, GBP_REFRESH_TOKEN, GBP_PARENT.
Fallback: Places API (New)  GET https://places.googleapis.com/v1/places/{placeId}  (fields rating,userRatingCount,reviews)
  Auth: API key (env PLACES_API_KEY), billing enabled. LIMIT: max 5 reviews, chosen by Google. Check Places ToS on caching/attribution.
Run daily, e.g. cron `0 4 * * * python3 fetch_reviews.py --out /path/reviews.json` or a GitHub Action / Cloud Function,
then upload reviews.json to a public CDN/S3 bucket (CORS: allow GET from client domains) or Duda site files.
"""
import argparse, json, os, sys, urllib.parse, urllib.request, datetime
STAR = {"ONE": 1, "TWO": 2, "THREE": 3, "FOUR": 4, "FIVE": 5}

def http(url, data=None, headers=None):
    req = urllib.request.Request(url, data=data, headers=headers or {})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)

def gbp_token():
    body = urllib.parse.urlencode({"client_id": os.environ["GBP_CLIENT_ID"], "client_secret": os.environ["GBP_CLIENT_SECRET"],
        "refresh_token": os.environ["GBP_REFRESH_TOKEN"], "grant_type": "refresh_token"}).encode()
    return http("https://oauth2.googleapis.com/token", body)["access_token"]

def from_gbp(parent):
    tok, out, page, meta = gbp_token(), [], None, {}
    while True:
        q = {"pageSize": 50, "orderBy": "updateTime desc"}
        if page: q["pageToken"] = page
        d = http(f"https://mybusiness.googleapis.com/v4/{parent}/reviews?" + urllib.parse.urlencode(q), headers={"Authorization": "Bearer " + tok})
        meta = meta or d
        for r in d.get("reviews", []):
            out.append({"id": r["reviewId"], "author": r.get("reviewer", {}).get("displayName", "Google user"),
                "photo": r.get("reviewer", {}).get("profilePhotoUrl"), "rating": STAR.get(r["starRating"], 0),
                "text": (r.get("comment") or "").split("\n\n(Translated by Google)")[0].strip(),
                "created": r["createTime"], "updated": r.get("updateTime", r["createTime"]),
                "reply": {"text": r["reviewReply"]["comment"], "updated": r["reviewReply"]["updateTime"]} if r.get("reviewReply") else None})
        page = d.get("nextPageToken")
        if not page: break
    return out, meta.get("averageRating"), meta.get("totalReviewCount", len(out)), "google_business_profile"

def from_places(place_id):
    d = http(f"https://places.googleapis.com/v1/places/{place_id}", headers={"X-Goog-Api-Key": os.environ["PLACES_API_KEY"],
        "X-Goog-FieldMask": "displayName,rating,userRatingCount,reviews"})
    revs = [{"id": r["name"].split("/")[-1], "author": r.get("authorAttribution", {}).get("displayName", "Google user"),
        "photo": r.get("authorAttribution", {}).get("photoUri"), "rating": r["rating"],
        "text": r.get("originalText", r.get("text", {})).get("text", ""), "created": r["publishTime"], "updated": r["publishTime"]}
        for r in d.get("reviews", [])]
    return revs, d.get("rating"), d.get("userRatingCount", len(revs)), "google_places"

def main():
    a = argparse.ArgumentParser()
    a.add_argument("--name", required=True); a.add_argument("--place-id", required=True)
    a.add_argument("--parent", default=os.environ.get("GBP_PARENT")); a.add_argument("--out", default="reviews.json")
    o = a.parse_args()
    try:
        if not o.parent: raise RuntimeError("no GBP parent")
        revs, avg, total, src = from_gbp(o.parent)
    except Exception as e:
        print("GBP failed (%s); falling back to Places API (max 5 reviews)" % e, file=sys.stderr)
        revs, avg, total, src = from_places(o.place_id)
    if not revs and os.path.exists(o.out): print("No reviews returned; keeping previous file"); return
    revs.sort(key=lambda r: r["created"], reverse=True)
    avg = avg or round(sum(r["rating"] for r in revs) / len(revs), 2)
    feed = {"schemaVersion": 1, "source": src, "isExample": False, "provenance": "Google " + src,
        "generated": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "place": {"name": o.name, "placeId": o.place_id, "gbpLocation": o.parent,
                  "reviewUrl": "https://search.google.com/local/writereview?placeid=" + o.place_id},
        "summary": {"averageRating": round(float(avg), 2), "totalReviews": int(total)}, "reviews": revs}
    tmp = o.out + ".tmp"; json.dump(feed, open(tmp, "w"), ensure_ascii=False, indent=1); os.replace(tmp, o.out)
    print(f"Wrote {len(revs)} reviews ({src}) to {o.out}")

if __name__ == "__main__": main()
